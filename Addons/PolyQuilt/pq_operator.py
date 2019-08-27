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
import copy
from .utils.pqutil import *
from .utils import draw_util
from .pq_icon import *
from .subtools.subtool_default import SubToolDefault
from .subtools.subtool import SubTool
from .QMesh import *

import os
import bpy.utils.previews

__all__ = ['MESH_OT_poly_quilt']

if not __package__:
    __package__ = "poly_quilt"

def enum_geometry_type_callback(scene, context):
        items=(('VERT', "Vertex", "" , custom_icon("icon_geom_vert") , 1),
               ('EDGE', "Edge", "", custom_icon("icon_geom_edge") , 2),
               ('TRI' , "Triangle", "", custom_icon("icon_geom_triangle") , 3 ),
               ('QUAD', bpy.app.translations.pgettext("Quad") , "", custom_icon("icon_geom_quad") , 0),
               ('POLY', "Polygon", "", custom_icon("icon_geom_polygon") , 4))
        return items

def enum_move_type_callback(scene, context):
        items=(('FREE', "Free", "" , custom_icon("icon_move_free") , 0),
               ('X', "X", "" , custom_icon("icon_move_x") , 1),
               ('Y' , "Y", ""  , custom_icon("icon_move_y") , 2),
               ('Z', "Z", "" , custom_icon("icon_move_z") , 3),
               ('NORMAL', "Normal", "" , custom_icon("icon_move_normal") , 4) ,
               ('TANGENT', "Tangent", "" , custom_icon("icon_move_tangent") , 5)
            )
        return items

class MESH_OT_poly_quilt(bpy.types.Operator):
    """Draw Polygons with the mouse"""
    bl_idname = "mesh.poly_quilt"
    bl_label = "PolyQuilt"
    bl_options = {'REGISTER' , 'UNDO'}
    __draw_handle2D = None
    __draw_handle3D = None
    __timer_handle = None

    tool_mode : bpy.props.EnumProperty(
        name="Tool Mode",
        description="Tool Mode",
        items=[('LOWPOLY' , "LowPoly", "" ),
               ('EXTRUDE' , "Extrude", "" ) ],
        default='LOWPOLY',
    )

    lock_hold : bpy.props.BoolProperty(
              name = "Lock Hold" ,
              default = False ,
              description="Lock HOLD",
            )

    geometry_type : bpy.props.EnumProperty(
        name="Geometry Type",
        description="Geometry Type.",
        items=enum_geometry_type_callback 
    )

    plane_pivot : bpy.props.EnumProperty(
        name="Plane Pivot",
        description="Plane Pivot",
        items=[('OBJ' , "Object Center", "" , "PIVOT_MEDIAN" , 0),
               ('3D' , "3D Cursor", "" , "PIVOT_CURSOR" , 1 ) ],
        default='OBJ',
    )

    move_type : bpy.props.EnumProperty(
        name="Move Type",
        description="Move Type.",
        items=enum_move_type_callback,
    )

    fix_to_x_zero : bpy.props.BoolProperty(
              name = "fix_to_x_zero" ,
              default = False ,
              description="Fix X=0",
            )

    loopcut_mode : bpy.props.EnumProperty(
        name="LoopCut Mode",
        description="LoopCut Mode",
        items=[('EQUAL' , "Equal", "" ),
               ('EVEN' , "Even", "" ) ],
        default='EQUAL',
    )


    def __del__(self):
        MESH_OT_poly_quilt.handle_remove()

    def modal(self, context, event):
        try :
            val = self.update( context, event)
        except Exception as e:
            MESH_OT_poly_quilt.handle_remove()
            self.RemoveTimerEvent(context)
            self.bmo.invalid = True
            self.bmo = None
            raise e
            return {'CANCELLED'}

        if 'CANCELLED' in val or 'FINISHED' in val :
            bpy.context.window.cursor_modal_restore()
            self.RemoveTimerEvent(context)            
            self.bmo = None
        return val

    def update(self, context, event):
        if event.type == 'TIMER':
            if self.currentSubTool is None or not self.currentSubTool.check_animated(context) :
                return {'PASS_THROUGH'}

        context.area.tag_redraw()

        MESH_OT_poly_quilt.handle_remove()

        if self.bmo.obj != context.active_object or self.bmo.bm.is_valid is False :            
            self.report({'WARNING'}, "BMesh Broken..." )
            return {'CANCELLED'}

        if self.preferences.is_debug :
            t = time.time()

        self.bmo.CheckValid( context )
        ret = 'FINISHED'

        if event.type == 'ESC':
            if self.currentSubTool is not None :
                self.currentSubTool.OnExit()     
                self.currentSubTool = None 

        if self.currentSubTool is not None :
            ret = self.currentSubTool.Update(context, event)

        if self.preferences.is_debug :
            self.count = self.count + 1
            self.time = time.time() - t
            if self.maxTime < self.time :
                self.maxTime = self.time
            self.debugStr = "eventValue = " + str(event.value) + " type = "+ str(event.type) + " - " + str(self.count) + " time = " + str(self.time) + " max = " + str(self.maxTime)

        if ret == 'FINISHED' or ret == 'CANCELLED' :
            pass
        else :
            MESH_OT_poly_quilt.handle_add(self,context)

        return {ret}

    def invoke(self, context, event):
        self.preferences = context.preferences.addons[__package__].preferences
        from .gizmo_preselect import PQ_GizmoGroup_Preselect , PQ_Gizmo_Preselect
        if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH' and PQ_Gizmo_Preselect.instance.bo != None:

            if context.space_data.show_gizmo is False :
                self.report({'WARNING'}, "Gizmo is not active.Please check Show Gizmo and try again" )
                return {'CANCELLED'}

            if not PQ_Gizmo_Preselect.instance.currentElement.is_valid :
                self.report({'WARNING'}, "Element data is invalid!" )
                return {'CANCELLED'}

            element = copy.copy(PQ_Gizmo_Preselect.instance.currentElement)

            if element == None or ( element.isEmpty == False and element.is_valid == False ) :
                self.report({'WARNING'}, "Invalid Data..." )
                return {'CANCELLED'}

            self.bmo = PQ_Gizmo_Preselect.instance.bo
            if self.bmo.obj != context.active_object or self.bmo.bm.is_valid is False :            
                self.report({'WARNING'}, "BMesh Broken..." )
                return {'CANCELLED'}

            self.currentSubTool = SubToolDefault(self , element )
            self.currentSubTool.OnInit(context )
            self.currentSubTool.Update(context, event)
            PQ_Gizmo_Preselect.instance.use()

            if self.preferences.is_debug :
                self.debugStr = "invoke"
                self.count = 0
                self.time = 0
                self.maxTime = 0

            bpy.context.window.cursor_modal_set( self.currentSubTool.GetCursor() )
            context.window_manager.modal_handler_add(self)
#           MESH_OT_poly_quilt.handle_add(self,context)
            self.AddTimerEvent(context)
            
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator" + event.type + "|" + event.value )
            return {'CANCELLED'}

    def cancel( self , context):
        MESH_OT_poly_quilt.handle_remove()
        self.RemoveTimerEvent(context)
        
    @staticmethod
    def draw_callback_px(self , context):
        draw_util.begin_draw()
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
        draw_util.end_draw()

    @staticmethod
    def draw_callback_3d(self , context):
        if self != None :
            if self.currentSubTool is not None :
                draw_util.begin_draw()
                self.currentSubTool.Draw3D(context)
                draw_util.end_draw()

    @staticmethod
    def handle_reset(self,context):
        MESH_OT_poly_quilt.handle_remove()
        MESH_OT_poly_quilt.handle_add(self,context)    

    @staticmethod
    def handle_add(self,context):
        args = (self, context)        
        MESH_OT_poly_quilt.__draw_handle2D = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_poly_quilt.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        MESH_OT_poly_quilt.__draw_handle3D = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_poly_quilt.draw_callback_3d, args, 'WINDOW', 'POST_VIEW')

    @staticmethod
    def handle_remove():
        if MESH_OT_poly_quilt.__draw_handle3D is not None:
            bpy.types.SpaceView3D.draw_handler_remove( MESH_OT_poly_quilt.__draw_handle3D, 'WINDOW')
            MESH_OT_poly_quilt.__draw_handle3D = None

        if MESH_OT_poly_quilt.__draw_handle2D is not None:
            bpy.types.SpaceView3D.draw_handler_remove( MESH_OT_poly_quilt.__draw_handle2D, 'WINDOW')
            MESH_OT_poly_quilt.__draw_handle2D = None            

    @classmethod
    def AddTimerEvent( cls , context , time = 1.0 / 30.0 ) :
        if cls.__timer_handle is None :
            cls.__timer_handle = context.window_manager.event_timer_add( time , window = context.window)

    @classmethod
    def RemoveTimerEvent( cls , context ) :
        if cls.__timer_handle is not None:
            context.window_manager.event_timer_remove(cls.__timer_handle)
            cls.__timer_handle = None

    is_lock_hold = False
    def is_hold(self , hold : bool ) -> bool :
        if self.is_lock_hold :
            return True
        if self.lock_hold :
            return True
        return hold

class MESH_OT_poly_quilt_hold_lock(bpy.types.Operator):
    """PolyQuilt hold lock"""
    bl_idname = "mesh.poly_quilt_hold_lock"
    bl_label = "PolyQuiltHoldLock"
    bl_options = {'REGISTER' }

    def invoke(self, context, event):
        if MESH_OT_poly_quilt.is_lock_hold :
            MESH_OT_poly_quilt.is_lock_hold = False
            self.report({'INFO'}, "Unlock Hold" )            
        else :
            MESH_OT_poly_quilt.is_lock_hold = True
            self.report({'INFO'}, "Lock Hold" )            
        print (MESH_OT_poly_quilt.is_lock_hold)
        return {'FINISHED'}
