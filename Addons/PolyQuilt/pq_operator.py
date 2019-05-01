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
import blf
import math
import mathutils
import bmesh
import bpy_extras
import collections
import time
from . import handleutility
from . import draw_util
from .subtools.subtool_default import SubToolDefault
from .subtools.subtool import SubTool
from .QMesh import *

__all__ = ['MESH_OT_poly_quilt']

if not __package__:
    __package__ = "poly_quilt"

class MESH_OT_poly_quilt(bpy.types.Operator):
    """Draw Polygons with the mouse"""
    bl_idname = "mesh.poly_quilt"
    bl_label = "PolyQuilt"
    bl_options = {'REGISTER' , 'UNDO'}
    __draw_handle2D = None
    __draw_handle3D = None

    backface : bpy.props.BoolProperty(
            name="backface",
            description="Ignore Backface",
            default=True)

    geometry_type : bpy.props.EnumProperty(
        name="Geometry Type",
        description="Geometry Type.",
        items=(('VERT', "Vertex", ""),
               ('EDGE', "Edge", ""),
               ('TRI' , "Triangle", "" ),
               ('QUAD', "Quad", ""),
               ('POLY', "Polygon", "")),
        default='QUAD',
    )

    plane_pivot : bpy.props.EnumProperty(
        name="Plane Pivot",
        description="Plane Pivot",
        items=[('OBJ' , "Object Center", "" , "OBJECT_ORIGIN" , 0),
               ('3D' , "3D Cursor", "" , "PIVOT_CURSOR" , 1 ),
               ('Origin'  , "Origin", "" , "ORIENTATION_GLOBAL" , 2) ],
        default='OBJ',
    )

    move_type : bpy.props.EnumProperty(
        name="Geometry Type",
        description="Move Type.",
        items=(('FREE', "Free", ""),
               ('X', "X", ""),
               ('Y' , "Y", "" ),
               ('Z', "Z", ""),
               ('NORMAL', "Normal", "")
            ),
        default='FREE',
    )

    fix_to_x_zero : bpy.props.BoolProperty(
              name = "fix_to_x_zero" ,
              default = False ,
              description="fix_to_x_zero",
            )

    radius : bpy.props.FloatProperty(
              name = "radius" ,
              default = 8.0 ,
              description="radius",
              min = 4.0 ,
              max = 32.0 ,
              precision = 1 )

    def __del__(self):
        MESH_OT_poly_quilt.handle_remove()

    def modal(self, context, event):

        self.count = self.count + 1
        context.area.tag_redraw()
        t = time.time()
        self.bmo.UpdateView( context )
        ret = 'FINISHED'

        if event.type == 'ESC':
            if self.currentSubTool is not None :
                self.currentSubTool.OnExit()     
                self.currentSubTool = None 

        if self.currentSubTool is not None :
            ret = self.currentSubTool.Update(context, event)

        if ret == 'FINISHED' :
            MESH_OT_poly_quilt.handle_remove()
            bpy.context.window.cursor_modal_restore()

        self.time = time.time() - t

        if self.maxTime < self.time :
            self.maxTime = self.time

        self.debugStr = "eventValue = " + str(event.value) + " type = "+ str(event.type) + " - " + str(self.count) + " time = " + str(self.time) + " max = " + str(self.maxTime)

        return {ret}
        if ret == 'RUNNING_MODAL' :
            return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.preferences = context.preferences.addons[__package__].preferences
        from .gizmo_preselect import PQ_GizmoGroup_Preselect , PQ_Gizmo_Preselect        
        if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH':
            args = (self, context)
            self.bmo = PQ_Gizmo_Preselect.instance.bo
            self.bmo.UpdateView( context )
            self.currentSubTool = SubToolDefault(self , PQ_Gizmo_Preselect.instance.currentElement)
            self.currentSubTool.OnInit(context )
            self.currentSubTool.Update(context, event)
            PQ_Gizmo_Preselect.instance.use()

            self.debugStr = "invoke"
            self.count = 0
            self.time = 0
            self.maxTime = 0

            bpy.context.window.cursor_modal_set( self.currentSubTool.GetCursor() )
            context.window_manager.modal_handler_add(self)
            MESH_OT_poly_quilt.__draw_handle2D = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_poly_quilt.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            MESH_OT_poly_quilt.__draw_handle3D = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_poly_quilt.draw_callback_3d, args, 'WINDOW', 'POST_VIEW')
            
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator" + event.type + "|" + event.value )
            return {'CANCELLED'}

    def cancel( self , context):
        MESH_OT_poly_quilt.handle_remove()

    @staticmethod
    def draw_callback_px(self , context):
        try:
            draw_util.begin2d()
            if self != None :
                if self.preferences.is_debug :
                    font_id = 0  # XXX, need to find out how best to get this.
                    # draw some text
                    blf.position(font_id, 15, 40, 0)
                    blf.size(font_id, 20, 72)
                    blf.draw(font_id, ">>" + self.debugStr )
                    if self.currentSubTool is not None :
                        blf.position(font_id, 15, 20, 0)
                        blf.size(font_id, 20, 72)
                        blf.draw(font_id, self.currentSubTool.Active().name +" > " + self.currentSubTool.Active().debugStr )

                if self.currentSubTool is not None :
                    self.currentSubTool.Draw2D(context)
        except Exception as e:
            print("Exception:", e.args)
            MESH_OT_poly_quilt.handle_remove()            

    def draw_callback_3d(self , context):
        try:
            if self != None :
                if self.currentSubTool is not None :
                    self.currentSubTool.Draw3D(context)
        except Exception as e:
            print("Exception:", e.args)
            MESH_OT_poly_quilt.handle_remove()            

    @staticmethod
    def handle_remove():
        if MESH_OT_poly_quilt.__draw_handle3D is not None:
            bpy.types.SpaceView3D.draw_handler_remove( MESH_OT_poly_quilt.__draw_handle3D, 'WINDOW')
            MESH_OT_poly_quilt.__draw_handle3D = None

        if MESH_OT_poly_quilt.__draw_handle2D is not None:
            bpy.types.SpaceView3D.draw_handler_remove( MESH_OT_poly_quilt.__draw_handle2D, 'WINDOW')
            MESH_OT_poly_quilt.__draw_handle2D = None            


