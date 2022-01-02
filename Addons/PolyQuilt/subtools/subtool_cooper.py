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
import bmesh
import math
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *
from .subtool_draw_patch import SubToolDrawPatch

class SubToolCooper(SubTool) :
    name = "Cooper Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op)        

        self.startPos = self.operator.start_mouse_pos
        self.currentPos = self.operator.start_mouse_pos


    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Drag or event.type == MBEventType.LongPressDrag :
            self.currentPos = self.mouse_pos
        elif event.type == MBEventType.Release :
            if (self.startPos-self.currentPos).length > 10 :
                self.MakeQuad(bpy.context)
            else :
                self.FillHoleQuad(bpy.context)
            self.isExit = True


    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        return ElementItem.Empty()

    @staticmethod
    def Check( root , target ) :
        return target.isEmpty

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return []

    def OnDraw( self , context  ) :
        if (self.startPos-self.currentPos).length > 10 :
            draw_util.draw_dot_lines2D( [self.startPos,self.currentPos] , self.color_delete() , 4 , pattern=(4,2) )        

    def OnDraw3D( self , context  ) :
        pass

    def OnExit( self ) :
        pass

    def MakeQuad( self , context , segment = 0.1 ) :
        targetLoop, targetVerts , num = SubToolDrawPatch.find_target_loop(  self.bmo.bm )

        loops = self.select_circle(context)

        if not loops :
            return

        if targetLoop and targetVerts[0] == targetVerts[-1] :
            pts = SubToolDrawPatch.calc_new_points( loops[0] ,targetLoop, targetVerts )
        else :
            ttl = sum( (e1-e2).length for e1,e2 in zip( loops[0][ 0 : len(loops[0]) - 1 ] , loops[0][ 1 : len(loops[0]) ] ) )
            num = int( ttl / segment + 0.5 )
            num = max( 8 , num )
            pts = SubToolDrawPatch.make_loop_by_stroke( loops[0] , [1] * num )

        self.bmo.select_flush()

        verts = []
        for pt in pts[ 0 : - 1] :
            vt = self.bmo.AddVertex( self.bmo.world_to_local_pos( pt ) )
            verts.append(vt)

        newEdges = []
        for i in range( 0  , len(verts) ) :
            ed = self.bmo.add_edge( verts[i] , verts[(i + 1) % len(verts) ] )
            self.bmo.select_component(ed)
            newEdges.append(ed)

        if targetLoop and targetVerts[0] == targetVerts[-1]  :
            SubToolDrawPatch.bridge_loops( self.bmo , newEdges , targetLoop )

        self.bmo.UpdateMesh()

    def FillHole( self , context ) :
        pivot = None
        if QSnap.is_active() :
            pivot = QSnap.screen_adjust(self.startPos)

        if not pivot :
            return

        targetLoop, targetVerts , num = SubToolDrawPatch.find_target_loop(  self.bmo.bm )
        if not targetLoop:
            return

        vt = self.bmo.AddVertex(  self.bmo.world_to_local_pos(pivot) )

        for edge in targetLoop :
            self.bmo.AddFace( [ edge.verts[0] , edge.verts[1] , vt ] )

        self.bmo.select_flush()
        self.bmo.UpdateMesh()

    def FillHoleQuad( self , context ) :
        pivot = None
        if QSnap.is_active() :
            pivot = QSnap.screen_adjust(self.startPos)

        if not pivot :
            return

        targetLoop, targetVerts , num = SubToolDrawPatch.find_target_loop(  self.bmo.bm )
        if not targetLoop:
            return

        #
        seg = len(targetLoop)
        half1 = math.ceil( seg / 2 )
        half2 = seg - half1

        quad1 = math.ceil( half1 / 2 )
        quad2 = half1 - quad1
        quad3 = quad1
        quad4 = half2 - quad3

        fillEdges = list(targetLoop[0:quad1])
        fillEdges.extend( list( targetLoop[quad1+quad2:quad1+quad2+quad3] ) )
        newFaces = bmesh.ops.grid_fill( self.bmo.bm, edges = fillEdges, mat_nr = 0, use_smooth = False, use_interp_simple = False)

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
                    vert.co = QSnap.adjust_by_normal( self.bmo.world_to_local_pos(vert.co) , self.bmo.world_to_local_nrm(vert.normal) )
#                    QSnap.adjust_point( self.bmo.world_to_local_pos(vert.co) )


        self.bmo.select_flush()
        self.bmo.UpdateMesh()

    def select_circle( self, context  ) :
        depsgraph = context.evaluated_depsgraph_get()

        loops = {}

        for obj in QSnap.snap_objects(context):
            # make planes
            slice_plane , plane0 , plane1 = pqutil.make_slice_planes(context, self.startPos , self.currentPos)
            slice_plane = slice_plane.world_to_object( obj )
            plane0 = plane0.world_to_object( obj )
            plane1 = plane1.world_to_object( obj )
            viewPlane = pqutil.Plane.from_screen_near(context).world_to_object( obj )
            planes = [plane0.distance_point,plane1.distance_point,viewPlane.distance_point]

            bm = bmesh.new()
            bm.from_object(obj ,depsgraph )
            ret = bmesh.ops.bisect_plane( bm , geom=bm.verts[:] + bm.edges[:] + bm.faces[:] ,dist=0.00000001,plane_co= slice_plane.origin ,plane_no= slice_plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)

            # check edge in area
            def check(e) :
                if isinstance( e , bmesh.types.BMEdge ) :
                    if all( all( p( v.co ) > 0 for v in e.verts ) for p in planes ) :
                        return True
                return False
            edges = [ e for e in ret['geom_cut'] if check( e ) ]

            # serch egde groups
            groups = pqutil.grouping_loop_edge( edges )
            for group in groups :
                le , lv = pqutil.sort_edgeloop( group )
                if lv[0] == lv[-1] :
                    key = min( [ viewPlane.distance_point(v.co) for v in lv ] )
                    loops[key] = [ obj.matrix_world @ v.co for v in lv ]

            del ret
            del edges
            bm.free()

        return [ loop[1] for loop in sorted(loops.items(), reverse=False) ]

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'