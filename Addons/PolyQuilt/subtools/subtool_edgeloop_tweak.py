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
from .subtool import MainTool
from .subtool_util import move_component_module

class SubToolEdgeLoopTweak(MainTool) :
    name = "EdgeLoop Slide"

    def __init__(self,op,target : ElementItem , button) :        
        super().__init__(op,target, button)
        self.currentEdge = target.element
        self.move_component_module = move_component_module( self.bmo , target , self.mouse_pos , op.move_type , self.preferences.fix_to_x_zero )
        self.loop_edges = self.bmo.sort_edges( target.loops )

        self.move_component_module.set_geoms( self.loop_edges )

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            move = self.move_component_module.move_to( self.mouse_pos )

            if self.move_component_module.update_geoms(move) :
                self.bmo.UpdateMesh()

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        else :
            self.move_component_module.update(event)

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width
        color = self.preferences.highlight_color
        draw_util.drawElementsHilight3D( self.bmo.obj , self.loop_edges , vertex_size ,width,alpha, color )

        self.move_component_module.draw_3D(context)