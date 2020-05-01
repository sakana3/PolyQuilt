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
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubTool

class SubToolEdgeloopCut(SubTool) :
    name = "EdgeLoopCutTool"

    def __init__(self,op, target : ElementItem ) :
        super().__init__(op)
        self.currentEdge = target
        self.is_forcus = False
        self.EdgeLoops = None
        self.VertLoops = None

    def Check( root ,target : ElementItem ) :
        if len( target.element.link_faces ) == 2 :
            return True
        return False

    def OnForcus( self , context , event  ) :
        if event.type == 'MOUSEMOVE':
            self.is_forcus = False
            p0 = self.bmo.local_to_2d( self.currentEdge.element.verts[0].co )
            p1 = self.bmo.local_to_2d( self.currentEdge.element.verts[1].co )
            if self.bmo.is_snap2D( self.mouse_pos , p0 ) or self.bmo.is_snap2D( self.mouse_pos , p1 ) :
                self.is_forcus = True
                if self.EdgeLoops == None :
                    self.EdgeLoops , self.VertLoops = self.bmo.calc_edge_loop( self.currentEdge.element )
        return self.is_forcus

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.EdgeLoops != None :
#                   bpy.ops.mesh.select_all(action='DESELECT')
                    self.bmo.do_edge_loop_cut( self.EdgeLoops , self.VertLoops )
                    self.bmo.UpdateMesh()
                    self.currentTarget = ElementItem.Empty() 
                    return 'FINISHED'
                return 'CANCELLED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.EdgeLoops != None :
            alpha = self.preferences.highlight_face_alpha
            vertex_size = self.preferences.highlight_vertex_size        
            width = self.preferences.highlight_line_width
            color = self.color_delete()
            draw_util.drawElementsHilight3D( self.bmo.obj , self.EdgeLoops , vertex_size ,width,alpha, color )

