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


import bpy
import math
import mathutils
import bmesh
import bpy_extras
import collections
import copy
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *

class SubToolDrawPatch(SubTool) :
    name = "DrawPatch Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op)        

        self.plane = self.default_plane

        self.stroke2D = [self.operator.start_mouse_pos]

        if QSnap.is_active() :
            coord = QSnap.screen_adjust(self.operator.start_mouse_pos)
        else :
            ray = pqutil.Ray.from_screen( bpy.context , self.operator.start_mouse_pos )
            coord = self.plane.intersect_ray( ray )

        self.stroke3D = [coord]

        self.activeTarget = ElementItem.Empty()
        self.firstVert =  None if not currentTarget.isVert else currentTarget.element
        self.lastVert = None

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.activeTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ['VERT'] )

            self.stroke2D.append( self.mouse_pos )
            ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
            coord = self.plane.intersect_ray( ray )
            if coord :
                if QSnap.is_active() :
                    coord = QSnap.view_adjust(coord)
                self.stroke3D.append( coord )
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                self.MakeQuad()
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        def check( target ) :
            if target.isVert :
                return target.element.select == False
            return True
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['VERT','EDGE'] , edgering = True , check_func = check )        
        return element

    @staticmethod
    def Check( root , target ) :
        return target.isEmpty or target.isVert

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return []

    def OnDraw( self , context  ) :
        if self.stroke2D :
            draw_util.draw_dot_lines2D( self.stroke2D , self.color_create() , 4 , pattern=(2,1) )        

    def OnDraw3D( self , context  ) :
#        self.activeTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )
        if self.startTargte.isVert :
            self.startTargte.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

#        draw_util.draw_lines3D( context , self.stroke3D  )

    def OnExit( self ) :
        pass

    def MakeQuad( self ) :
        targetLoop, targetVerts = SubToolDrawPatch.find_target_loop( self.bmo.bm )
        if not targetLoop :
            self.report_message = ("ERROR" , "Choose one boundary edge loop first." )
            return

        isLoop = targetVerts[0] == targetVerts[-1]

        pts = SubToolDrawPatch.calc_new_points( self.stroke3D ,targetLoop ,targetVerts )

        if isLoop :
            pts = pts[0:-1]

        newVerts = []
        for p in pts :
            v = self.make_vert( p , p )
            newVerts.append( v )

        if isLoop :
            newVerts.append( newVerts[0] )

        self.bmo.select_flush()
        v1 = newVerts[0]
        newEdges = []
        for  i in range(1,len(newVerts)) :
            edge = self.bmo.add_edge( v1 , newVerts[i]  )
            self.bmo.select_component(edge)
            newEdges.append( edge )
            v1 = newVerts[i]

        SubToolDrawPatch.bridge_loops( self.bmo , newEdges , targetLoop )

    #       self.bmo.select_components( newEdges , True )
        self.bmo.select_components( newVerts , True )
        self.bmo.UpdateMesh()

    @staticmethod
    def make_loop_by_stroke( stroke , targets ) :
        stroke_length = [ ( s - e ).length for s,e in zip( stroke[0: len(stroke)-1] , stroke[1: len(stroke)] ) ]

        stroke_total  = sum( stroke_length )
        targets_total = sum( targets )
        segments = [ t / targets_total * stroke_total for t in targets ]

        retPositions = [ stroke[0] ]
        cur = 0
        segment = 0
        pre = stroke[0]
        segmentLen = segments[cur]
        for pos , length in zip( stroke[1:len(stroke)] , stroke_length ) :
            tmp = segment
            segment += length
            while segment > segmentLen :
                t = ( segmentLen - tmp ) / length
                pre = pre.lerp( pos , t )
                retPositions.append(pre)
                segment -= segmentLen
                tmp = 0
                cur += 1
                if cur >= len(segments) :
                    break
                segmentLen = segments[cur]
            pre = pos

        if len(retPositions) < len(targets) + 1 :
            retPositions.append( stroke[-1] )

        return retPositions

    def make_vert( self , src , tar ) :
        if not QSnap.is_active() :
            pl = pqutil.Plane.from_screen( bpy.context , src )
            pr = pqutil.Ray.from_world_to_screen( bpy.context , tar )
            pt = pl.intersect_ray( pr )
        else :
            pt = tar
        v = self.bmo.AddVertexWorld( pt )
        return v

    @staticmethod
    def bridge_loops( bmo , edge1 , edge2 ) :

        loopPair = copy.copy(edge1)
        loopPair.extend( edge2 )

        newFaces = bmesh.ops.grid_fill( bmo.bm, edges = loopPair, mat_nr = 0, use_smooth = False, use_interp_simple = False)
        if newFaces['faces'] :
            if QSnap.is_active() :
                vertsets = set()
                facesets = []
                for face in newFaces['faces'] :
                    facesets.append(face)
                    for vert in face.verts :
                        vertsets.add(vert)
#                bmesh.ops.join_triangles(self.bmo, faces = facesets)                        
                for vert in vertsets :
                    vert.normal_update()
                for vert in vertsets :
                    QSnap.adjust_by_normal( bmo.world_to_local_pos(vert.co) , bmo.world_to_local_nrm(vert.normal) )
#                    QSnap.adjust_point( self.bmo.world_to_local_pos(vert.co) )
        else :
            bmesh.ops.bridge_loops(bmo.bm, edges = loopPair, use_pairs = False, use_cyclic = False, use_merge = False, merge_factor = 0.0 , twist_offset = 0.0 )


    @staticmethod
    def find_target_loop( bm ) :
        selected = [ edge for edge in bm.edges if edge.select and (edge.is_boundary or edge.is_wire) ]
        targetLoops = pqutil.grouping_loop_edge( selected )

        if len(targetLoops) != 1 :
            return None , None

        targetLoop = targetLoops[0]
        targetLoop, targetVerts = pqutil.sort_edgeloop(targetLoop)

        return  targetLoop, targetVerts

    @staticmethod
    def calc_new_points( stroke , edges , verts ) :
        '''
        新しいポイントを作る
        '''
        isLoop = verts[0] == verts[-1]
        if isLoop :
            # 一番近い点に移動する
            lens = [ (s-verts[0].co).length for s in stroke ]
            idx = lens.index( min(lens) )
            for i in range(0,idx) :
                stroke.append( stroke.pop(0) )
            stroke.append( stroke[0] )

            loop = [ ( e.verts[0].co - e.verts[1].co ).length for e in edges ]
            pts1 = SubToolDrawPatch.make_loop_by_stroke( stroke , loop )
            pts2 = SubToolDrawPatch.make_loop_by_stroke( list(reversed(stroke)) , loop )

            if ( pts1[1] - verts[1].co ).length < ( pts2[1] - verts[1].co ).length :
                pts = pts1
            else :
                pts = pts2
        else :
            if (verts[0].co - stroke[0]).length > (verts[0].co - stroke[-1]).length :
                edges.reverse()
                verts.reverse()
            pts = SubToolDrawPatch.make_loop_by_stroke( stroke , [ ( e.verts[0].co - e.verts[1].co ).length for e in edges ] )


        return pts



    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'