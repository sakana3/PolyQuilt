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
            self.currentTarget = ElementItem( self.bmo , vert , mouse_pos , self.bmo.local_to_world_pos(vert.co) , 0 ); 
        elif startElement.isEdge :
            self.currentTarget = self.edge_split( startElement )
            self.bmo.UpdateMesh()
        else :
            if self.bmo.is_mirror_mode and startElement.isVert and self.bmo.is_x_zero_pos( startElement.element.co ) is False and startElement.mirror == None :
                self.bmo.AddVertex( self.bmo.mirror_pos( startElement.element.co ) , False )
                self.bmo.UpdateMesh()
                startElement.setup_mirror()
        self.pivot = self.currentTarget.hitPosition.copy()

        self.mekePolyList.append( self.currentTarget.element.index )
        self.PlanlagtePos =  self.calc_planned_construction_position()
        self.targetElement = None
        self.isEnd = False
        self.LMBEvent = ButtonEventUtil('LEFTMOUSE' , self , SubToolMakePoly.LMBEventCallback , op.preferences )
        self.mode = op.geometry_type
        self.EdgeLoops = None
        self.VertLoops = None
        if self.mode == 'VERT' :
            self.isEnd = True
        self.currentTarget = ElementItem.Empty()

    def is_animated( self , context ) :
        return self.LMBEvent.is_animated()

    def getPolyVert( self , index : int ) :
        return self.bmo.bm.verts[ self.mekePolyList[index] ]

    def getPolyVerts( self ) :
        return [ self.bmo.bm.verts[i] for i in self.mekePolyList ]

    def setPolyList( self , vert ) :
        self.mekePolyList.append( vert.index )

    @staticmethod
    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Down :
            pass
        elif event.type == MBEventType.Release :
            if self.currentTarget.element == self.getPolyVert(-1) :
                self.isEnd = True
            else :
                if self.EdgeLoops != None :
                    self.DoEdgeLoopsRemove( self.EdgeLoops , self.VertLoops )
                    self.EdgeLoops = None
                    self.VertLoops = None
                    self.isEnd = True       
                    self.bmo.UpdateMesh()
                    self.currentTarget = ElementItem.Empty()
                elif self.currentTarget.isEdge :
                    self.currentTarget = self.edge_split( self.currentTarget )
                    self.isEnd = self.AddVert(self.currentTarget ) == False
                elif self.currentTarget.isEmpty :
                    self.pivot = self.calc_planned_construction_position()
                    addVert = self.bmo.AddVertexWorld( self.pivot )
                    self.bmo.UpdateMesh()
                    self.currentTarget = ElementItem( self.bmo ,addVert , self.mouse_pos , self.pivot , 0.0 )
                if self.currentTarget.isVert :
                    if self.currentTarget.element.index not in self.mekePolyList :
                        self.isEnd = self.AddVert(self.currentTarget ) == False
            self.currentTarget = ElementItem.Empty()                    
        elif event.type == MBEventType.Click :            
            pass
        elif event.type == MBEventType.LongPress :
            if len(self.mekePolyList) <= 1 and self.currentTarget.isVert and self.getPolyVert(-1) != self.currentTarget.element :
                edge = self.bmo.edges.get( (self.getPolyVert(0) , self.currentTarget.element) )
                if edge != None and self.EdgeLoops == None :
                    self.EdgeLoops , self.VertLoops = self.SelectEdgeLoops( edge )
        elif event.type == MBEventType.LongClick :
            if len(self.mekePolyList) <= 1 :
                self.mode = 'EDGE'
        elif event.type == MBEventType.Move :
            self.PlanlagtePos =  QSnap.view_adjust(self.calc_planned_construction_position())
            tmp = self.currentTarget
            ignore = []
            if isinstance( self.targetElement , bmesh.types.BMFace ) :
                ignore = self.targetElement.edges
            elif isinstance( self.targetElement , bmesh.types.BMEdge ):
                ignore =  [ self.targetElement ]
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , ignore=ignore )
            if tmp != self.currentTarget :
                self.EdgeLoops = None
                self.VertLoops = None
            if (self.currentTarget.isVert or self.currentTarget.isEdge ) is False :
                self.currentTarget = ElementItem.Empty()

    def OnUpdate( self , context , event ) :
        self.LMBEvent.Update( context , event )

        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE' :
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
        polyVerts = self.getPolyVerts()
        l = len(self.mekePolyList)        
        v3d = [ i.world for i in pqutil.TransformBMVerts( self.bmo.obj, polyVerts ) ]
        v3d.append( self.PlanlagtePos )

        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width
        color = self.color_create()

        if l == 1:
            same_edges , same_faces = self.CheckSameFaceAndEdge( self.getPolyVert(0) , self.currentTarget.element )
            if same_edges :
                if len(same_faces) > 1 :
                    if self.LMBEvent.presureComplite :
                        color = self.color_delete()
                    else :
                        color = self.color_delete()
            elif same_faces :
                color = self.color_split()
            self.draw_lines( context , v3d , color )
        elif l > 1:
            if self.currentTarget.element not in polyVerts :
                v3d.append( v3d[0] )
            self.draw_lines( context , v3d , color )

        if self.currentTarget.isNotEmpty :
            if self.currentTarget.element == self.getPolyVert(-1) :
                draw_util.draw_pivots3D(  [self.PlanlagtePos,] , vertex_size * 1.5 , self.color_create() )
            elif self.currentTarget.element in polyVerts:
                draw_util.draw_pivots3D(  [self.PlanlagtePos,] , vertex_size * 1.5 , self.color_delete() )

            draw_util.draw_pivots3D( [self.PlanlagtePos,] , vertex_size , color )
            self.currentTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )
        else :
            draw_util.draw_pivots3D( [self.PlanlagtePos,] , vertex_size , self.color_create() )

        draw_util.drawElementsHilight3D( self.bmo.obj , polyVerts , vertex_size ,width,alpha, self.color_create() )

        if self.EdgeLoops != None :
            draw_util.drawElementsHilight3D( self.bmo.obj , self.EdgeLoops , vertex_size ,width,alpha, self.color_delete() )

    def OnDraw( self , context  ) :
        l = len(self.mekePolyList)
        if l == 1:
            text = None
            same_edges , same_faces = self.CheckSameFaceAndEdge( self.getPolyVert(0) , self.currentTarget.element )
            if same_edges :
                if len(same_faces) > 1 :
                    text = "Edge Loop"
            elif same_faces :
                pass
            else :
                text = "Line"                    
            if text != None :
                self.LMBEvent.Draw( self.currentTarget.coord , text )

    def AddVert( self , target ) :
        ret = True
        dirty = False
        if target.element.index not in self.mekePolyList :
            if self.bmo.is_mirror_mode :
                if target.mirror == None and target.is_x_zero is False :
                    self.bmo.AddVertex( self.bmo.mirror_pos( target.element.co ) , False )
                    self.bmo.UpdateMesh()

            self.setPolyList( target.element )
            ret = True
            pts = len( self.mekePolyList )

            # 既に存在する辺ならExit
            if pts > 2 :
                edge = self.bmo.edges.get( ( self.getPolyVert(0) , self.getPolyVert(-1) ) )
                if edge != None :
                    ret = False
            if pts == 2 :
                same_edges , same_faces = self.CheckSameFaceAndEdge(self.getPolyVert(-2) , self.getPolyVert(-1))

                if same_edges :
                    if len(same_faces) > 1 :
#                       bmesh.utils.vert_separate( vert , same_edges )
                        self.bmo.dissolve_edges( edges = same_edges , use_verts = False , use_face_split = False )
                        dirty = True
                        self.mekePolyList = [ self.mekePolyList[-1] ] 
                elif same_faces:
                    for face in same_faces :
                        self.bmo.face_split( face , self.getPolyVert(-2) , self.getPolyVert(-1) )
                        dirty = True
                    self.mekePolyList = [ self.mekePolyList[-1] ]                        
                else :
                    edge = self.bmo.add_edge( self.getPolyVert(-2) , self.getPolyVert(-1) )
#                    edge.select = True
                    self.targetElement = edge
                    dirty = True
            elif pts == 3 :
                face = self.bmo.AddFace( self.getPolyVerts() , pqutil.getViewDir() )
#                face.select = True
                dirty = True
                self.targetElement = face
            elif pts > 3:
#               self.bmo.Remove( self.targetElement )
                edge = self.bmo.edges.get( ( self.getPolyVert(0) , self.getPolyVert(-2) ) )
                if edge != None :
                    self.bmo.Remove( edge )
                self.targetElement = self.bmo.AddFace( self.getPolyVerts() , pqutil.getViewDir()  )
                self.bmo.UpdateMesh()


        if self.mode == 'TRI' and pts == 3 :
            ret = False

        if self.mode == 'QUAD' and pts == 4 :
            ret = False

        if self.mode == 'EDGE' :
            self.mekePolyList = [ self.mekePolyList[-1] ]

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

    def SelectEdgeLoops( self , startEdge ) :
        edges = []
        verts = []

        def append( lst , geom ) :
            if geom not in lst :
                lst.append(geom)
                if self.bmo.is_mirror_mode :
                    mirror =self.bmo.find_mirror( geom )
                    if mirror :
                        lst.append( mirror )

        for vert in startEdge.verts :
            preEdge = startEdge
            currentV = vert
            while currentV != None :
                append(edges , preEdge)

                if currentV.is_boundary :
                    if len( currentV.link_faces )== 2 :
                        if not any( [ len(f.verts) == 3 for f in currentV.link_faces ] ):
                            if currentV not in verts :
                                append(verts , currentV)
                    break

                if len(currentV.link_faces) == 4 :
                    faces = set(currentV.link_faces ) ^ set(preEdge.link_faces )
                    if len( faces ) != 2 :
                        break
                    faces = list(faces)
                    share_edges = set(faces[0].edges) & set(faces[1].edges) & set(currentV.link_edges )
                    if len(share_edges) != 1 :
                        break
                    preEdge = list(share_edges)[0]

                    if currentV not in verts :
                        append(verts , currentV)

                elif len(currentV.link_faces) == 2 :
                    share_edges = [ e for e in currentV.link_edges if e != preEdge ]
                    if len(share_edges) != 1 :
                        break
                    preEdge = share_edges[0]
                else :
                    break
                currentV = preEdge.other_vert(currentV)
                if currentV == vert:
                    break
        return edges , verts


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
        QSnap.adjust_verts( self.bmo.obj , [new_vert] , self.operator.fix_to_x_zero )
        self.bmo.UpdateMesh()

        newItem = ElementItem.FormVert( self.bmo , new_vert )
        if self.bmo.is_mirror_mode and newItem.mirror == None and newItem.is_x_zero is False :
            self.bmo.AddVertex( self.bmo.mirror_pos( new_vert.co ) , False )
            self.bmo.UpdateMesh()
            newItem.setup_mirror()
        return newItem
