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
import blf
import math
import mathutils
import bmesh
import bpy_extras
import collections
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from .subtool import SubTool

class SubToolKnife(SubTool) :
    name = "KnifeTool2"

    def __init__(self,op,startPos) :
        super().__init__(op)
        self.startPos = startPos
        self.endPos = startPos
        self.CutEdgePos3D = []
        self.CutEdge = []

    def OnUpdate( self , context , event ) :
        self.endPos = self.mouse_pos
        if event.type == 'MOUSEMOVE':
            if( self.startPos - self.endPos ).length > 2 :
                self.CalcKnife( context,self.startPos,self.endPos )
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.CutEdge :
                    self.DoKnife(context,self.startPos,self.endPos)
                    self.bmo.UpdateMesh()                
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_lines2D( (self.startPos,self.endPos) , self.color_delete() , self.preferences.highlight_line_width )

#        for pos in self.CutEdgePos :
#            draw_util.draw_pivot2D( pos , 1 , self.color_delete() )

    def OnDraw3D( self , context  ) :
        if self.CutEdgePos3D :
            draw_util.draw_pivots3D( self.CutEdgePos3D , 1 , self.color_delete() )

    def CalcKnife( self ,context,startPos , endPos ) :
        slice_plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
        self.CutEdge , self.CutEdgePos3D = self.calc_slice( slice_plane , plane0 , plane1 )

    def make_slice_planes( self , context,startPos , endPos ):
        slice_plane_world = handleutility.Plane.from_screen_slice( context,startPos , endPos )
        slice_plane_object = slice_plane_world.world_to_object( self.bmo.obj )

        ray0 = handleutility.Ray.from_screen( context , startPos ).world_to_object( self.bmo.obj )
        plane0 = handleutility.Plane( ray0.origin , slice_plane_object.vector.cross(ray0.vector) )
        ray1 = handleutility.Ray.from_screen( context ,endPos ).world_to_object( self.bmo.obj )
        plane1 = handleutility.Plane( ray1.origin , slice_plane_object.vector.cross(ray1.vector) )

        return slice_plane_object , plane0 , plane1

    def calc_slice( self ,slice_plane , plane0 , plane1 ) :
        edges = [ edge for edge in self.bmo.edges if edge.hide is False ]

        def chk( edge ) :        
            p0 = edge.verts[0].co
            p1 = edge.verts[1].co
            p = slice_plane.intersect_line( p0 , p1 )

            if p != None :
                a0 = plane0.distance_point( p )
                a1 = plane1.distance_point( p )
                if (a0 >= 0 and a1 >= 0 ) or (a0 <= 0 and a1 <= 0 ):
                    return None

            return p

        matrix = self.bmo.obj.matrix_world
        CutEdge = [ p for p in [ (edge,chk( edge )) for edge in edges ] if p[1] != None ]
        return [ e[0] for e in CutEdge ] , [ matrix @ e[1] for e in CutEdge ]

    def DoKnife( self ,context,startPos , endPos ) :
        bm = self.bmo.bm
        threshold = bpy.context.scene.tool_settings.double_threshold
        plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
        faces = [ face for face in self.bmo.faces if face.hide is False ]
        elements = self.CutEdge[:] + faces[:]
        bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= plane.origin ,plane_no= plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)

        if self.bmo.is_mirror :
            slice_plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()
            self.bmo.UpdateMesh()
            cutEdgeMirror , CutEdgePos3DMirror = self.calc_slice( slice_plane , plane0 , plane1 )
            if cutEdgeMirror :
                faces = [ face for face in self.bmo.faces if face.hide is False ]          
                elements = cutEdgeMirror[:] + faces[:]
                bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= slice_plane.origin ,plane_no= slice_plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)


