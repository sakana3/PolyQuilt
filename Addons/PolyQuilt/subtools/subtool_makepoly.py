# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import bpy
import math
import mathutils
import bmesh
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..utils.dpi import *
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import SubTool


class vert_array_util :
    def __init__(self , qmesh ) :
        self.qmesh = qmesh
        self.verts_list = []
        self.face_count = 0
        self.edge_count = 0

    def get( self , index : int ) :
        return self.verts[index]

    def add( self , vert ) :
        world = self.qmesh.local_to_world_pos( vert.co )
        screen = pqutil.location_3d_to_region_2d( world )
        self.verts_list.append( [vert,vert.index,vert.co.copy(),world,screen] )
        self.qmesh.bm.select_history.discard(vert)
        self.qmesh.bm.select_history.add(vert)
        vert.select_set(True)

    def add_face( self , face ) :
        self.qmesh.bm.select_history.discard(face)
        self.qmesh.bm.select_history.add(face)
        self.face_count = self.face_count + 1

    def add_edge( self , edge ) :
        self.qmesh.bm.select_history.discard(edge)
        self.qmesh.bm.select_history.add(edge)
        self.edge_count = self.edge_count + 1

    def add_line( self , vert ) :
        self.add( vert )
        edge = self.qmesh.add_edge( self.get(-2) , self.get(-1) )          
        self.add_edge( edge )
        self.qmesh.UpdateMesh()                      
        return edge

    def clear_verts( self ) :
        self.verts_list = []

    def reset_verts( self ) :
        self.verts_list = [ self.verts_list[-1] ]

    @property
    def vert_count( self ) :
        return len(self.verts_list)

    @property
    def verts( self ) :
        if len(self.verts_list) == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMVert) ][-len(self.verts_list):]

    @property
    def faces( self ) :
        if self.face_count == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMFace) ][-self.face_count:]

    @property
    def last_vert( self ) :
        return self.verts[-1]

    @property
    def last_edge( self ) :
        return self.edges[-1]

    @property
    def last_face( self ) :
        return self.faces[-1]

    @property
    def edges( self ) :
        if self.edge_count == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMEdge) ][-self.edge_count:]

    def clear_faces( self ) :
        self.face_count = 0

    def clear_edges( self ) :
        self.edge_count = 0

    @property
    def cos( self ) :
        return [ i[1] for i in self.verts_list ]

    @property
    def world_positions( self ) :
        return [ i[3] for i in self.verts_list ]

    @property
    def screen_positions( self ) :
        return [ i[4] for i in self.verts_list ]


class SubToolMakePoly(SubTool) :
    name = "MakePolyTool"

    def __init__(self,op,startElement , mouse_pos ) :
        super().__init__(op)        
        self.mekePolyList = []
        self.mouse_pos = mouse_pos
        self.currentTarget = startElement

        if self.operator.plane_pivot == 'OBJ' :
            self.pivot = self.bmo.obj.location
        elif self.operator.plane_pivot == '3D' :
            self.pivot = bpy.context.scene.cursor.location
        elif self.operator.plane_pivot == 'Origin' :
            self.pivot = (0,0,0)

        if startElement.isEmpty :
            p = self.calc_planned_construction_position()
            vert = self.bmo.AddVertexWorld(p)
            self.bmo.UpdateMesh()
            self.currentTarget = ElementItem( self.bmo , vert , mouse_pos , self.bmo.local_to_world_pos(vert.co) , 0 )
        elif startElement.isEdge :
            self.currentTarget = self.edge_split( startElement )
            self.bmo.UpdateMesh()
        else :
            if self.bmo.is_mirror_mode and startElement.isVert and self.bmo.is_x_zero_pos( startElement.element.co ) is False and startElement.mirror == None :
                self.bmo.AddVertex( self.bmo.mirror_pos( startElement.element.co ) , False )
                self.bmo.UpdateMesh()
                self.currentTarget.setup_mirror()
        self.pivot = self.currentTarget.hitPosition.copy()

        self.vert_array = vert_array_util( self.bmo )
        self.vert_array.add( self.currentTarget.element )
        self.PlanlagtePos =  self.calc_planned_construction_position()
        self.targetElement = None
        self.isEnd = False
        self.LMBEvent = ButtonEventUtil('LEFTMOUSE' , self , SubToolMakePoly.LMBEventCallback , op )
        self.mode = op.geometry_type
        self.EdgeLoops = None
        self.VertLoops = None
        if self.mode == 'VERT' :
            self.isEnd = True
        self.original_mode = self.mode
        self.currentTarget = ElementItem.Empty()
        self.will_split = False

    def is_animated( self , context ) :
        return self.LMBEvent.is_animated()

    @staticmethod
    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Down :
            pass
        elif event.type == MBEventType.Release :
            if self.currentTarget.element == self.vert_array.get(-1) :
                self.isEnd = True
            else :
                if self.EdgeLoops != None :
                    self.DoEdgeLoopsRemove( self.EdgeLoops , self.VertLoops )
                    self.EdgeLoops = None
                    self.VertLoops = None
                    self.isEnd = True       
                    self.bmo.UpdateMesh()
                    self.currentTarget = ElementItem.Empty()

                else :
                    if self.mode == 'SPLITE' :
                        self.do_splite()
                    else :
                        if self.currentTarget.isFace :
                            wp = QSnap.view_adjust(self.currentTarget.hitPosition)                
                            if  self.currentTarget.element in self.vert_array.verts[-1].link_faces :
                                self.mode = 'SPLITE'
                                self.vert_array.clear_edges()                             
                                self.vert_array.add_face( self.currentTarget.element )
                                vert = self.bmo.AddVertexWorld( wp )
                                self.bmo.UpdateMesh()                      
                                self.vert_array.add_line( vert )
                                self.bmo.UpdateMesh()
                            else :
                                vert = self.bmo.AddVertexWorld( wp )
                                self.bmo.UpdateMesh()
                                self.currentTarget = ElementItem( self.bmo ,vert , self.mouse_pos , wp , 0.0 )

                        if self.currentTarget.isEdge :
                            self.currentTarget = self.edge_split( self.currentTarget )
                            
                        elif self.currentTarget.isEmpty :
                            self.pivot = self.calc_planned_construction_position()
                            vert = self.bmo.AddVertexWorld( self.pivot )
                            self.bmo.UpdateMesh()                            
                            self.currentTarget = ElementItem( self.bmo ,vert , self.mouse_pos , self.pivot , 0.0 )

                        if self.currentTarget.isVert and self.mode != 'SPLITE' :
                            if self.currentTarget.element not in self.vert_array.verts :
                                self.isEnd = self.AddVert(self.currentTarget ) == False
            self.currentTarget = ElementItem.Empty()                    
        elif event.type == MBEventType.Click :            
            pass
        elif event.type == MBEventType.LongPress :
            if self.vert_array.vert_count <= 1 and self.currentTarget.isVert and self.vert_array.get(-1) != self.currentTarget.element :
                edge = self.bmo.edges.get( (self.vert_array.get(0) , self.currentTarget.element) )
                if edge != None and self.EdgeLoops == None :
                    self.EdgeLoops , self.VertLoops = self.bmo.calc_edge_loop( edge )
        elif event.type == MBEventType.LongClick :
            if self.vert_array.vert_count <= 1 :
                self.mode = 'EDGE'
                self.original_mode = self.mode
        elif event.type == MBEventType.Move :
            self.PlanlagtePos =  QSnap.view_adjust(self.calc_planned_construction_position())
            tmp = self.currentTarget
            ignore = []
            if isinstance( self.targetElement , bmesh.types.BMFace ) :
                ignore = self.targetElement.edges
            elif isinstance( self.targetElement , bmesh.types.BMEdge ):
                ignore =  [ self.targetElement ]
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , ignore=ignore )
            self.currentTarget.set_snap_div( self.preferences.loopcut_division )

            self.will_splite = self.check_splite()

            if tmp != self.currentTarget :
                self.EdgeLoops = None
                self.VertLoops = None
            else :
                self.PlanlagtePos = self.currentTarget.hitPosition


    def OnUpdate( self , context , event ) :
        self.LMBEvent.Update( context , event )

        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE' :
            if self.mode == 'SPLITE' and len(self.vert_array.verts) > 1 :
                # 分割モード中なら一番近い点を選んで終了する
                p = self.vert_array.last_vert.co
                r = sorted( self.vert_array.last_face.verts , key = lambda i:(i.co - p).length_squared )
                self.currentTarget = ElementItem( self.bmo , r[0] , self.mouse_pos , self.bmo.local_to_world_pos(r[0].co) , 0 )
                self.do_splite()
            self.isEnd = True

        if self.isEnd == True :
            return 'FINISHED'

        return 'RUNNING_MODAL'

    def draw_lines( self ,context , v3d , color ) :
        v3d = [v for v in v3d if v != None ]
        draw_util.draw_lines3D( context , v3d , color , self.preferences.highlight_line_width )
        if self.bmo.is_mirror_mode :
            color = (color[0] , color[1] , color[2] , color[3] * 0.5)
            draw_util.draw_lines3D( context , self.bmo.mirror_world_poss(v3d) , color , self.preferences.highlight_line_width )

    def OnDraw3D( self , context  ) :
        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width
        color = self.color_create()

        polyVerts = self.vert_array.verts
        l = self.vert_array.vert_count
        v3d = self.vert_array.world_positions
        v3d.append( self.PlanlagtePos )

        if self.vert_array.vert_count == 1 :
            same_edges , same_faces = self.CheckSameFaceAndEdge( self.vert_array.get(0) , self.currentTarget.element )
            if same_edges :
                if len(same_faces) > 1 :
                    if self.LMBEvent.presureComplite :
                        color = self.color_delete()
                    else :
                        color = self.color_delete()

            if self.will_splite :
                color = self.color_split()

            elif same_faces :
                color = self.color_split()
            self.draw_lines( context , v3d , color )
        elif self.vert_array.vert_count > 1:
            if self.mode == 'SPLITE' :
                color = self.color_split()
            if self.currentTarget.element not in polyVerts and self.mode != 'SPLITE' :
                v3d.append( v3d[0] )
            self.draw_lines( context , v3d , color )

        if self.currentTarget.isNotEmpty :
            if self.currentTarget.element == self.vert_array.get(-1) :
                draw_util.draw_pivots3D(  [self.PlanlagtePos,] , vertex_size * 1.5 , self.color_create() )
            elif self.currentTarget.element in polyVerts:
                draw_util.draw_pivots3D(  [self.PlanlagtePos,] , vertex_size * 1.5 , self.color_delete() )

            draw_util.draw_pivots3D( [self.PlanlagtePos,] , vertex_size , color )
            if self.currentTarget.isVert or self.currentTarget.isEdge :
                self.currentTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )
        else :
            draw_util.draw_pivots3D( [self.PlanlagtePos,] , vertex_size , self.color_create() )

        draw_util.drawElementsHilight3D( self.bmo.obj , polyVerts , vertex_size ,width,alpha, self.color_create() )

        if self.EdgeLoops != None :
            draw_util.drawElementsHilight3D( self.bmo.obj , self.EdgeLoops , vertex_size ,width,alpha, self.color_delete() )

    def OnDraw( self , context  ) :
        if self.vert_array.vert_count == 1:
            text = None
            same_edges , same_faces = self.CheckSameFaceAndEdge( self.vert_array.get(0) , self.currentTarget.element )
            if same_edges :
                if len(same_faces) > 1 :
                    text = "Edge Loop"
            elif same_faces :
                pass
            else :
                text = "Line"                    
            if text != None :
                self.LMBEvent.Draw( self.currentTarget.coord , text )
#       if self.currentTarget.element in self.vert_array.verts:
#           draw_util.DrawFont( "Finish" , 12 , self.currentTarget.coord , (0,2) )                   
    def AddVert( self , target ) :
        ret = True
        dirty = False

        if target.element not in self.vert_array.verts :
            if self.bmo.is_mirror_mode :
                if target.mirror == None and target.is_x_zero is False :
                    self.bmo.AddVertex( self.bmo.mirror_pos( target.element.co ) , False )
                    self.bmo.UpdateMesh()

            self.vert_array.add( target.element )
            ret = True
            pts = self.vert_array.vert_count
            # 既に存在する辺ならExit
            if pts > 2 :
                edge = self.bmo.edges.get( ( self.vert_array.get(0) , self.vert_array.get(-1) ) )
                if edge != None :
                    ret = False
            if pts == 2 :
                same_edges , same_faces = self.CheckSameFaceAndEdge(self.vert_array.get(-2) , self.vert_array.get(-1))
                if same_edges :
                    if len(same_faces) > 1 :
#                       bmesh.utils.vert_separate( vert , same_edges )
                        self.bmo.dissolve_edges( edges = same_edges , use_verts = False , use_face_split = False )
                        dirty = True
                        self.targetElement = None
                        self.vert_array.reset_verts()
                elif same_faces:
                    for face in same_faces :
                        self.bmo.face_split( face , self.vert_array.get(-2) , self.vert_array.get(-1) )
                        dirty = True
                        edge = self.bmo.edges.get( ( self.vert_array.get(-2) , self.vert_array.get(-1) ) )
                        edge.select_set(True)                        
                        self.targetElement = None
                    self.vert_array.reset_verts()
                else :
                    edge = self.bmo.add_edge( self.vert_array.get(-2) , self.vert_array.get(-1) )
#                    edge.select = True
                    self.targetElement = edge
                    self.targetElement.select_set(True)
                    self.bmo.bm.select_history.add(self.targetElement)                
                    dirty = True
            elif pts == 3 :
                face = self.bmo.AddFace( self.vert_array.verts , pqutil.getViewDir() )
                self.targetElement = face
                self.targetElement.select_set(True)
                self.bmo.bm.select_history.add(self.targetElement)                
                dirty = True
            elif pts > 3:
                self.bmo.bm.select_history.discard(self.targetElement)                
                edge = self.bmo.edges.get( ( self.vert_array.get(0) , self.vert_array.get(-2) ) )
                if edge != None :
                    self.bmo.Remove( edge )
                self.targetElement = self.bmo.AddFace( self.vert_array.verts , pqutil.getViewDir()  )
                self.targetElement.select_set(True)
                self.bmo.bm.select_history.add(self.targetElement)                
                dirty = True

            if self.mode == 'TRI' and pts == 3 :
                ret = False

            if self.mode == 'QUAD' and pts == 4 :
                ret = False

            if self.mode == 'EDGE' :
               self.vert_array.reset_verts()

        if dirty :
            self.bmo.UpdateMesh()             
            target.setup_mirror()

        return ret

    def CheckSameFaceAndEdge( self , v0 , v1 ) :
        same_edges = []
        same_faces = []
        if isinstance( v0,bmesh.types.BMVert ) :
            if isinstance( v1,bmesh.types.BMVert ) :
                same_edges = list( set(v0.link_edges) & set(v1.link_edges) )
                same_faces = list( set(v0.link_faces) & set(v1.link_faces) )
            elif  isinstance( v1,bmesh.types.BMEdge ) :
#               same_edges = [] if v1 in v0.link_edges else [v1]
                same_faces = list( set(v0.link_faces) & set(v1.link_faces) )
        return same_edges , same_faces

    def DoEdgeLoopsRemove( self , edges , verts ) :
        bmesh.ops.dissolve_edges( self.bmo.bm , edges = edges , use_verts = False , use_face_split = False )  
        vs = [ v for v in verts if v.is_valid ]
        bmesh.ops.dissolve_verts( self.bmo.bm , verts = vs , use_face_split = True , use_boundary_tear = False )        
        self.currentTarget = ElementItem.Empty()

    def calc_planned_construction_position( self ) :
        if self.currentTarget.isEmpty :
            plane = pqutil.Plane.from_screen( bpy.context , self.pivot )
            ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
            wp = plane.intersect_ray( ray )
        else :
            wp = self.currentTarget.hitPosition
        wp = QSnap.view_adjust(wp)

        if self.bmo.is_mirror_mode :
            lp = self.bmo.world_to_local_pos(wp)
            mp = self.bmo.mirror_pos(lp)
            if self.bmo.check_near( lp , mp ) :
                zp = self.bmo.zero_pos(lp)
                wp =  self.bmo.local_to_world_pos( zp )

        return wp

    def edge_split( self , edgeItem ) :
        pos = self.bmo.world_to_local_pos(edgeItem.hitPosition)

        if self.bmo.check_near( pos , self.bmo.mirror_pos(pos) ) :
            pos = self.bmo.zero_pos(pos)

        new_edge , new_vert = self.bmo.edge_split_from_position( edgeItem.element , pos )
        self.bmo.UpdateMesh()
        QSnap.adjust_verts( self.bmo.obj , [new_vert] , self.preferences.fix_to_x_zero )
        self.bmo.UpdateMesh()

        newItem = ElementItem.FormVert( self.bmo , new_vert )
        if self.bmo.is_mirror_mode and newItem.mirror == None and newItem.is_x_zero is False :
            self.bmo.AddVertex( self.bmo.mirror_pos( new_vert.co ) , False )
            self.bmo.UpdateMesh()
            newItem.setup_mirror()
        return newItem

    def check_splite( self ) :
        b0 = self.vert_array.get(0)
        e0 = self.bmo.local_to_2d( b0.co )
        for f in self.vert_array.last_vert.link_faces :
            if f is self.currentTarget.element :
                return True
#                for e in [ e for e in f.edges if b0 not in e.verts ] :
#                    v0 , v1 = self.bmo.local_to_2d( e.verts[0].co ) , self.bmo.local_to_2d( e.verts[1].co )
 #                   if mathutils.geometry.intersect_line_line_2d( e0 , self.mouse_pos , v0,v1 ) :
  #                      self.will_splite = True
#                        return True
        return False

    def do_splite( self ) : 
        splite_end = False
        mirror_face = None
        if self.currentTarget.isFace :
            if  self.currentTarget.element == self.vert_array.faces[-1] :                            
                wp = QSnap.view_adjust(self.currentTarget.hitPosition)                
                vert = self.bmo.AddVertexWorld( wp )
                self.bmo.UpdateMesh()                                
                self.vert_array.add_line( vert )
                self.bmo.UpdateMesh()

        if self.currentTarget.isEdge :
            if self.vert_array.faces[-1] in self.currentTarget.element.link_faces :
                self.currentTarget = self.edge_split( self.currentTarget )
                self.vert_array.add_line( self.currentTarget.element )
                self.bmo.UpdateMesh()
                splite_end = True
                
        elif self.currentTarget.isVert :
            if self.currentTarget.element in self.vert_array.faces[-1].verts :
                self.vert_array.add_line( self.currentTarget.element )
                self.bmo.UpdateMesh()
                splite_end = True

        if splite_end :
            if self.bmo.is_mirror_mode :
                mirror_face = self.bmo.find_mirror( self.vert_array.faces[-1] , check_same = False )
                if mirror_face != None :
                    # 同一面をカットする時
                    if mirror_face == self.vert_array.faces[-1] :
                        edges = self.vert_array.edges
                        mirror_edges = [ self.bmo.find_mirror(e, check_same = False ) for e in edges ]
                        edges.extend( mirror_edges )
                        facesp = bmesh.utils.face_split_edgenet( self.vert_array.faces[-1] , edges )
                    else :
                        facesp = bmesh.utils.face_split_edgenet( self.vert_array.faces[-1] , self.vert_array.edges )
                        self.bmo.UpdateMesh()
                        mirror_edges = [ self.bmo.find_mirror(e) for e in self.vert_array.edges ]
                        facesp = bmesh.utils.face_split_edgenet( mirror_face , mirror_edges )
                else :
                    facesp = bmesh.utils.face_split_edgenet( self.vert_array.faces[-1] , self.vert_array.edges )
            else :
                facesp = bmesh.utils.face_split_edgenet( self.vert_array.faces[-1] , self.vert_array.edges )
            self.bmo.UpdateMesh()
            self.vert_array.clear_edges()
            self.vert_array.clear_faces()
            self.vert_array.reset_verts()
            self.mode = self.original_mode
