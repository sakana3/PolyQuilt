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
import os
import gc
from .utils.pqutil import *
from .utils import draw_util
from .utils.dpi import *
from .pq_icon import *
from .subtools import *
from .QMesh import *
from .gizmo_preselect import PQ_GizmoGroup_Base            

import bpy.utils.previews

__all__ = ['MESH_OT_poly_quilt', 'MESH_OT_poly_quilt_daemon' , 'MESH_OT_poly_quilt_brush_size']

if not __package__:
    __package__ = "poly_quilt"

def enum_geometry_type_callback(scene, context):
    items=(('VERT', "Vertex", "" , custom_icon("icon_geom_vert") , 1),
            ('EDGE', "Edge", "", custom_icon("icon_geom_edge") , 2),
            ('TRI' , "Triangle", "", custom_icon("icon_geom_triangle") , 3 ),
            ('QUAD', "Quad" , "", custom_icon("icon_geom_quad") , 0),
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

def enum_brush_type_callback(scene, context):
        items=(('SMOOTH' , "Smooth", "" , custom_icon("icon_brush_relax") , 0),
               ('MOVE' , "Move", "" , custom_icon("icon_brush_move") , 1 ) ,
               ('DELETE' , "Delete", "" , custom_icon("icon_brush_delete") , 2 ) )
        return items

def enum_override_brush_type_callback(scene, context):
        items=(('NONE' , "None", "" , 'DOT' , 0),
               ('SMOOTH' , "Smooth", "" , custom_icon("icon_brush_relax") , 1),
               ('MOVE' , "Move", "" , custom_icon("icon_brush_move") , 2 ) ,
               ('DELETE' , "Delete", "" , custom_icon("icon_brush_delete") , 3 ) )
        return items

class MESH_OT_poly_quilt(bpy.types.Operator):
    """Draw Polygons with the mouse"""
    bl_idname = "mesh.poly_quilt"
    bl_label = "PolyQuilt"
    bl_options = {'REGISTER' , 'UNDO'}
    __draw_handle2D = None
    __draw_handle3D = None
    __timer_handle = None
    __pre_timr = 0
    __cur_timr = 0

    tool_mode : bpy.props.EnumProperty(
        name="Tool Mode",
        description="Tool Mode",
        items=enum_tool_callback,
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

    snap_mode : bpy.props.EnumProperty(
        name="Snap Mode",
        description="Snap Mode",
        items=[('ON' , "On", "" ),
               ('OFF' , "Off", "" ) ,
               ('AUTO' , "Auto", "" ) ],
        default='ON',
    )

    loopcut_mode : bpy.props.EnumProperty(
        name="LoopCut Mode",
        description="LoopCut Mode",
        items=[('EQUAL' , "Equal", "" ),
               ('EVEN' , "Even", "" ) ],
        default='EQUAL',
    )

    extrude_mode : bpy.props.EnumProperty(
        name="Extrude Mode",
        description="Extrude Mode",
        items=[('PARALLEL' , "Parallel", "" ),
               ('BEND' , "Bend", "" ) ,
               ('FLEXIBLE' , "Flex", "" ) ],
        default='PARALLEL',
    )


    brush_type : bpy.props.EnumProperty(
        name="Brush Type",
        description="Brush Type.",
        items=enum_brush_type_callback,
    )

#    brush_override : bpy.props.EnumProperty(
#        name="Override Brush Type",
#        description="Override Brush Type.",
#        items=enum_override_brush_type_callback,
#    )
    

    def __del__(self):
        MESH_OT_poly_quilt.handle_remove()

    def modal(self, context, event):
        def Exit() :
            MESH_OT_poly_quilt.handle_remove()
            self.RemoveTimerEvent(context)
            self.bmo = None
            PQ_GizmoGroup_Base.running_polyquilt = False

        if context.region == None :
            self.report({'WARNING'}, "Oops!context.region is None!Cancel operation:(" )
            return {'CANCELLED'}            

        if self.bmo.CheckValid(context) == False :
            self.report({'WARNING'}, "Oops!Data black was broken! Cancel operation:(" )
            return {'CANCELLED'}            

        try :
            val = self.update( context, event)
        except Exception as e:
            self.bmo.invalid = True
            Exit()
            raise e
            return {'CANCELLED'}

        if 'CANCELLED' in val or 'FINISHED' in val :
            Exit()
#           self.preselect.test_select( context , mathutils.Vector((event.mouse_region_x, event.mouse_region_y)) )
        return val

    def update(self, context, event):
        if self.preferences.is_debug :
            t = time.time()
                    
        if event.type == 'TIMER':
            if self.currentSubTool is None or not self.currentSubTool.check_animated(context) :
                return {'PASS_THROUGH'}

        context.area.tag_redraw()

        MESH_OT_poly_quilt.handle_remove()

        if self.bmo.obj != context.active_object or self.bmo.bm.is_valid is False :            
            self.report({'WARNING'}, "BMesh Broken..." )
            return {'CANCELLED'}

        self.bmo.CheckValid( context )
        ret = 'FINISHED'

        if event.type == 'ESC':
            if self.currentSubTool is not None :
                self.currentSubTool.OnExit()     
                self.currentSubTool = None 

        if self.currentSubTool is not None :
            ret = self.currentSubTool.Update(context, event)
            context.window.cursor_set( self.currentSubTool.CurrentCursor() )

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
        MESH_OT_poly_quilt.__pre_timr = MESH_OT_poly_quilt.__cur_timr
        MESH_OT_poly_quilt.__cur_timr = time.time()

        self.preferences = context.preferences.addons[__package__].preferences
        if context.region == None :
            self.report({'WARNING'}, "Oops!context.region is None!Cancel operation:(" )
            return {'CANCELLED'}            

        tool_mode = self.tool_mode
        if self.tool_mode == 'NONE' :
            return {'PASS_THROUGH'}

        if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH' :
            self.preselect = PQ_GizmoGroup_Base.get_gizmo( context.region_data )
            if self.preselect == None or self.preselect.bmo  == None :
                self.report({'WARNING'}, "Gizmo Error" )
                return {'CANCELLED'}            

            if self.preselect.currentElement == None :
                return {'CANCELLED'} 


            if context.space_data.show_gizmo is False :
                self.report({'WARNING'}, "Gizmo is not active.Please check Show Gizmo and try again" )
                return {'CANCELLED'}

            if not self.preselect.currentElement.is_valid :
                self.report({'WARNING'}, "Element data is invalid!" )
                return {'CANCELLED'}

            element = copy.copy(self.preselect.currentElement)

            if element == None or ( element.isEmpty == False and element.is_valid == False ) :
                self.report({'WARNING'}, "Invalid Data..." )
                return {'CANCELLED'}

            self.bmo = self.preselect.bmo
            if self.bmo.obj != context.active_object or self.bmo.bm.is_valid is False :            
                self.report({'WARNING'}, "BMesh Broken..." )
                return {'CANCELLED'}

            self.currentSubTool = maintools[self.tool_mode](self , element, event.type )
            self.currentSubTool.OnInit(context )
#            self.currentSubTool.Update(context, event)

            if self.preferences.is_debug :
                self.debugStr = "invoke"
                self.count = 0
                self.time = 0
                self.maxTime = 0

            bpy.context.window.cursor_set( self.currentSubTool.CurrentCursor() )
            context.window_manager.modal_handler_add(self)
#           MESH_OT_poly_quilt.handle_add(self,context)
            self.AddTimerEvent(context)
            PQ_GizmoGroup_Base.running_polyquilt = True
            QSnap.update(context)
            
            return { self.currentSubTool.Update(context, event) }
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator" + event.type + "|" + event.value )
            return {'CANCELLED'}

    def cancel( self , context):
        MESH_OT_poly_quilt.handle_remove()
        self.RemoveTimerEvent(context)
        gc.collect()

    @staticmethod
    def draw_callback_px(self , context , region_data):
        draw_util.begin_draw()
        if self != None and context.region_data == region_data :
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
    def draw_callback_3d(self , context , region_data):
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
        args = (self, context , context.region_data)        
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

    @property
    def is_snap( self ) :
        if self.snap_mode == 'ON' :
            return True
        if self.snap_mode == 'OFF' :
            return False
        return bpy.context.scene.tool_settings.use_snap

class MESH_OT_poly_quilt_daemon(bpy.types.Operator):
    """Check Modifire"""
    bl_idname = "mesh.poly_quilt_daemon"
    bl_label = "PolyQuiltDaemon"

    is_running = False
    is_scene_update = False

    @classmethod
    def poll( cls , context ) :
        return not MESH_OT_poly_quilt_daemon.is_running

    def modal(self, context, event):
        if event.type == 'TIMER' :
            return {'PASS_THROUGH'}

        # 自分を使っているツールを探す。
        if context.mode != 'EDIT_MESH' or not any( [ "mesh_tool.poly_quilt" in tool.idname for tool in context.workspace.tools ] ) :
            MESH_OT_poly_quilt_daemon.is_running = False
            QSnap.remove_ref()
            context.window.cursor_set( 'DEFAULT' )
            bpy.app.handlers.depsgraph_update_post.remove( MESH_OT_poly_quilt_daemon.depsgraph_update_post_handler )
            bpy.app.handlers.depsgraph_update_pre.remove( MESH_OT_poly_quilt_daemon.depsgraph_update_pre_handler )
            return {'CANCELLED'}

        PQ_GizmoGroup_Base.recive_event( context, event )
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if MESH_OT_poly_quilt_daemon.is_running :
            return {'CANCELLED'}
        QSnap.add_ref( context )
        MESH_OT_poly_quilt_daemon.is_running = True
        context.window_manager.modal_handler_add(self)
        bpy.app.handlers.depsgraph_update_post.append( MESH_OT_poly_quilt_daemon.depsgraph_update_post_handler )
        bpy.app.handlers.depsgraph_update_pre.append( MESH_OT_poly_quilt_daemon.depsgraph_update_pre_handler )
        return {'RUNNING_MODAL'}

    @staticmethod
    def depsgraph_update_post_handler( scene):
        PQ_GizmoGroup_Base.depsgraph_update_post( scene )

    @staticmethod
    def depsgraph_update_pre_handler( scene):
        PQ_GizmoGroup_Base.depsgraph_update_post( scene )

class MESH_OT_poly_quilt_brush_size(bpy.types.Operator):
    """Change Brush Size"""
    bl_idname = "mesh.poly_quilt_brush_size"
    bl_label = "PolyQuiltBrushSize"
    
    brush_size_value : bpy.props.FloatProperty(
        name="Brush Size Value",
        description="Brush Size Value",
        default=0.0,
        min=-1000.0,
        max=1000.0)

    brush_strong_value : bpy.props.FloatProperty(
        name="Brush Strong Value",
        description="Brush Strong Value",
        default=0.0,
        min=-1.0,
        max=1.0)

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D' :
            preferences = context.preferences.addons[__package__].preferences        

            a = (preferences.brush_size * preferences.brush_size) / 40000.0 + 0.1
            preferences.brush_size += self.brush_size_value * a       
            strength = min( max( 0 , preferences.brush_strength + self.brush_strong_value ) , 1 )
            preferences.brush_strength = strength
            context.area.tag_redraw()

        return {'CANCELLED'}

