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
from .subtool import SubToolEx
from ..utils.dpi import *

class SubToolBrushDelete(SubToolEx) :
    name = "DeleteBrushTool"

    def __init__(self, event ,  root ) :
        super().__init__( root )
        self.radius = self.preferences.brush_size * dpm()
        self.strength = self.preferences.brush_strength
        self.mirror_tbl = {}
        matrix = self.bmo.obj.matrix_world        
        self.remove_faces = self.collect_faces( bpy.context , self.startMousePos )
        if self.bmo.is_mirror_mode :
            mirror = { self.bmo.find_mirror( f ) for f in self.remove_faces }
            mirror = { m for m in mirror if m != None }
            self.remove_faces  = self.remove_faces  | mirror

    @staticmethod
    def Check( root , target ) :
        return True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        def Draw() :
            radius = gizmo.preferences.brush_size * dpm()
            strength = gizmo.preferences.brush_strength  
            color = gizmo.preferences.delete_color
            with draw_util.push_pop_projection2D() :
                draw_util.draw_circle2D( gizmo.mouse_pos , radius * strength , color = color, fill = False , subdivide = 64 , dpi= False )
                draw_util.draw_circle2D( gizmo.mouse_pos , radius , color = color, fill = False , subdivide = 64 , dpi= False )
        return Draw

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            faces = self.collect_faces( context , self.mouse_pos )
            if self.bmo.is_mirror_mode :
                mirror = { self.bmo.find_mirror( f ) for f in faces if f not in self.remove_faces }
                mirror = { m for m in mirror if m != None }
                self.remove_faces  = self.remove_faces  | mirror
            self.remove_faces = self.remove_faces | faces

        elif event.type == self.rootTool.buttonType :
            if event.value == 'RELEASE' :
                if self.remove_faces :
                    self.bmo.delete_faces( list( self.remove_faces ) )
                    self.bmo.UpdateMesh()
                    return 'FINISHED'
                return 'CANCELLED'
        elif event.value == 'RELEASE' :
            self.repeat = False

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        color = self.preferences.delete_color 
        draw_util.draw_circle2D( self.mouse_pos , self.radius , color , fill = False , subdivide = 64 , dpi= False , width = 1.0 )

    def OnDraw3D( self , context  ) :
        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width        
        color = self.preferences.delete_color 
        draw_util.drawElementsHilight3D( self.bmo.obj , self.remove_faces , vertex_size , width , alpha , color )

    def collect_faces( self , context , coord ) :
        radius = self.radius
        bm = self.bmo.bm

        select_stack = SelectStack( context , bm )
        select_stack.push()
        select_stack.select_mode(False,False,True)
        bpy.ops.view3d.select_circle( x = coord.x , y = coord.y , radius = radius , wait_for_input=False, mode='SET' )
        faces = { f for f in self.bmo.bm.faces if f.select }
        select_stack.pop()
        return faces

    @classmethod
    def GetCursor(cls) :
        return 'ERASER'
