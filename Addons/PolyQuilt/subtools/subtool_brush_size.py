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
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubTool
from ..utils.dpi import *

class SubToolBrushSize(SubTool) :
    name = "BrushSizeTool"

    def __init__(self,op,startTarget,startMousePos) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.startMousePos = startMousePos
        self.start_radius = self.preferences.brush_size * dpm()
        self.radius = self.start_radius

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            dist = (self.startMousePos - self.mouse_pos ).length
            self.radius = self.start_radius + self.mouse_pos.x - self.startMousePos.x
            self.radius = min( max( 50 , self.radius ) , 500 )
            self.preferences.brush_size = self.radius / dpm()
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                return 'FINISHED'

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_circle2D( self.startMousePos , self.radius , color = (1,1,1,1), fill = False , subdivide = 64 , dpi= False )
        pass

    def OnDraw3D( self , context  ) :
        pass

    def resetMouse(self, context, event):
            context.window.cursor_warp(context.region.x + context.region.width // 2 - 0.5*(event.mouse_x - event.mouse_prev_x), \
                context.region.y + context.region.height // 2 - 0.5*(event.mouse_y - event.mouse_prev_y))