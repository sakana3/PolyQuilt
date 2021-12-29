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
from functools import cmp_to_key
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
                self.FillHole(bpy.context)
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

    def MakeQuad( self , context ) :
        targetLoop, targetVerts = SubToolDrawPatch.find_target_loop(  self.bmo.bm )

        loops = self.select_circle(context)

        if not loops :
            return

        if targetLoop and targetVerts[0] == targetVerts[-1] :
            pts = SubToolDrawPatch.calc_new_points( loops[0] ,targetLoop, targetVerts )
        else :
            pts = SubToolDrawPatch.make_loop_by_stroke( loops[0] , [1,1,1,1,1,1,1,1,1,1,1,1,1,1] )

        self.bmo.select_flush()

        verts = []
        for pt in pts[ 0 : - 1] :
            vt = self.bmo.AddVertex( pt )
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

        selected = [ edge for edge in self.bmo.bm.edges if edge.select and (edge.is_boundary or edge.is_wire) ]
        targetLoops =  pqutil.grouping_loop_edge( selected )
        if len(targetLoops) != 1 :
            return

        vt = self.bmo.AddVertex( pivot )

        for edge in targetLoops[0] :
            self.bmo.AddFace( [ edge.verts[0] , edge.verts[1] , vt ] )

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