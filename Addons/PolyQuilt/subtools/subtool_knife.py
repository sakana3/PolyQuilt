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
        self.CutEdgePos = []

    def OnUpdate( self , context , event ) :
        self.endPos = self.mouse_pos
        if event.type == 'MOUSEMOVE':
            if( self.startPos - self.endPos ).length > 2 :
                self.CalcKnife( context,self.startPos,self.endPos )
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if len(self.CutEdgePos) > 0 :
                    self.DoKnife(context,self.startPos,self.endPos)
                    self.bmo.UpdateMesh()                
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_lines2D( (self.startPos,self.endPos) , self.color_delete() , self.preferences.highlight_line_width )

        for pos in self.CutEdgePos :
            draw_util.draw_pivot2D( pos , 1 , self.color_delete() )
    
    def CalcKnife( self ,context,startPos , endPos ) :
        edges = self.bmo.highlight.viewPosEdges
        intersect = mathutils.geometry.intersect_line_line_2d        
        self.CutEdgePos = [ intersect( edge[1], edge[2] , startPos, endPos) for edge in edges ]
        self.CutEdgePos = [ p for p in self.CutEdgePos if p != None ]

    def DoKnife( self ,context,startPos , endPos ) :
        plane = handleutility.Plane.from_screen_slice( context,startPos , endPos ).to_object_space( self.bmo.obj )

        bm = self.bmo.bm
        edges = self.bmo.highlight.viewPosEdges
        intersect = mathutils.geometry.intersect_line_line_2d
        cutEdge = [ edge[0] for edge in edges if intersect( edge[1], edge[2] , startPos, endPos) is not None ]

        elements = cutEdge[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm,geom=elements,dist=0.00000001,plane_co= plane.origin ,plane_no= plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)
            
