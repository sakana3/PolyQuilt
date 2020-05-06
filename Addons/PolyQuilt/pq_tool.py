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

import os
import bpy
from bpy.types import WorkSpaceTool , Panel
from bpy.utils.toolsystem import ToolDef
from .pq_icon import *


class ToolPolyQuiltBase(WorkSpaceTool):
    bl_space_type='VIEW_3D'
    bl_context_mode='EDIT_MESH'
    is_polyquilt = True

    @staticmethod
    def subtool_keymaps( tool_header ) :
        return (
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True},  {"properties": [('tool_prop' , tool_header + "_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS', "alt": True}, {"properties": [('tool_prop' , tool_header + "_alt" ) ]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_shift_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_shift_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_ctrl_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "shift": True},  {"properties": [('tool_prop' , tool_header + "_os_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_os_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_os_alt" )]}),

            ("mesh.poly_quilt_daemon", {"type": 'MOUSEMOVE', "value": 'ANY' }, {"properties": []}),        
        )

    @staticmethod
    def tool_keymaps( main_tool , tool_header ) :
        return (
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS'}, {"properties": [("tool_mode", main_tool )]}),            
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True},  {"properties": [('tool_prop' , tool_header + "_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS', "alt": True}, {"properties": [('tool_prop' , tool_header + "_alt" ) ]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_shift_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_shift_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_ctrl_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "shift": True},  {"properties": [('tool_prop' , tool_header + "_os_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_os_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_os_alt" )]}),

            ("mesh.poly_quilt_daemon", {"type": 'MOUSEMOVE', "value": 'ANY' }, {"properties": []}),        
        )


class ToolPolyQuilt(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt"
    bl_label = "PolyQuilt"
    bl_description = ( "Lowpoly Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_icon")
    bl_widget = "MESH_GGT_PQ_Preselect"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'MASTER' , 'master_tool' )

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'master_tool' , 'Master Tool' , tool )
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout.column().box() , tool )
            draw_sub_tool( layout , 'master_tool' , 'Master Tool' , tool )
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )


class ToolPolyQuiltPoly(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_poly"
    bl_label = "PolyQuilt:Poly"
    bl_description = ( "Lowpoly Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_poly_icon")
    bl_widget = "MESH_GGT_PQ_Lowpoly"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'LOWPOLY' , 'lowpoly_tool' )

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' or reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'lowpoly_tool' , 'LowPoly Tool' , tool )
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )

class ToolPolyQuiltKnife(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_knife"
    bl_label = "PolyQuilt:Knife"
    bl_description = ( "Quick Knife Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_knife_icon")
    bl_widget = "MESH_GGT_PQ_Knife"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'KNIFE' , 'knife_tool' )    

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'knife_tool' , 'Knife Tool' , tool )            
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'knife_tool' , 'Knife Tool' , tool )            
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool , ui = ['BRUSH','OPTION'] )

class ToolPolyQuiltDelete(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_delete"
    bl_label = "PolyQuilt:Delete"
    bl_description = ( "Quick Delete Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_delete_icon")
    bl_widget = "MESH_GGT_PQ_Delete"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'DELETE' , 'delete_tool' )    

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'delete_tool' , 'Delete Tool' , tool )            
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'delete_tool' , 'Delete Tool' , tool )            
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool , ui = ['OPTION'] )

class ToolPolyQuiltExtrude(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_extrude"
    bl_label = "PolyQuilt:EdgeExtrude"
    bl_description = ( "Edge Extrude Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_extrude_icon")
    bl_widget = "MESH_GGT_PQ_Extrude"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'EXTRUDE' , 'extrude_tool' )        

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'extrude_tool' , 'Extrude Tool' , tool )                       
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'extrude_tool' , 'Extrude Tool' , tool )                       
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )

class ToolPolyQuiltLoopCut(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_loopcut"
    bl_label = "PolyQuilt:LoopCut"
    bl_description = ( "LoopCut Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_loopcut_icon")
    bl_widget = "MESH_GGT_PQ_LoopCut"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'LOOPCUT' , 'loopcut_tool' )            

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'loopcut_tool' , 'Loop Cut Tool' , tool )                 
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'loopcut_tool' , 'Loop Cut Tool' , tool )                 
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )



class ToolPolyQuiltBrush(ToolPolyQuiltBase):
    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_brush"
    bl_label = "PolyQuilt:Brush"
    bl_description = ( "Brush Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_brush_icon")
    bl_widget = "MESH_GGT_PQ_Brush"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( 'BRUSH' , 'brush_tool' )            

    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'brush_tool' , 'Brush Tool' , tool )                 
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , 'brush_tool' , 'Brush Tool' , tool )                 
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )

PolyQuiltTools = (
    { 'tool' : ToolPolyQuilt       , 'after' : {"builtin.poly_build"} , 'group' : True },
    { 'tool' : ToolPolyQuiltPoly  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltExtrude  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltLoopCut  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltKnife  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltDelete  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltBrush  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
)


def draw_settings_ui(context, layout, tool):
    props = tool.operator_properties("mesh.poly_quilt")
    preferences = bpy.context.preferences.addons[__package__].preferences        
#       layout.label(text="Make",text_ctxt="Make", translate=True, icon='NORMALS_FACE')

    col = layout.column(align=True)
    col.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = False  )

    col = layout.column(align=True)
    col.prop(props, "plane_pivot" , text = "Pivot" , expand = True , icon_only = False )

    col = layout.column(align=True)
    col.prop(props, "move_type" , text = "Move" , expand = True , icon_only = False )

#       layout.prop(context.active_object.data, "use_mirror_x", toggle = toggle , icon_only = False, icon_value = custom_icon("icon_opt_mirror") )
    layout.prop(context.active_object.data, "use_mirror_x", toggle = True , icon_only = False , icon = "MOD_MIRROR" )
    layout.prop( preferences, "fix_to_x_zero", toggle = True , text = "Fix X=0" , icon_only = False, icon_value = custom_icon("icon_opt_x0") )

    row = layout.row(align=True)
    row.prop(props, "extrude_mode" , text = "EXTRUDE" , expand = True )

    layout.separator()
    row = layout.row(align=True)
    row.prop(props, "loopcut_mode" , text = "LOOPCUT" , expand = True )
    row = layout.row(align=True)
    row.prop( preferences, "loopcut_division" , text = "Edge Snap Div" , expand = True, slider = True  )

    layout.separator()
    col = layout.column(align=True)
    col.prop( preferences, "vertex_dissolve_angle" , text = "Vertex Dissolve Angle", expand = True, slider = True , icon_only = False  )

    layout.separator()
    col = layout.column(align=True)
    col.prop( preferences, "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = False )

    col.prop( preferences, "brush_size" , text = "Brush Size" , expand = True, slider = True , icon_only = False )
    col.prop( preferences, "brush_strength" , text = "Brush Strength" , expand = True, slider = True , icon_only = False )
#        shading = get_shading()
#        if shading.type == 'SOLID':        
#            layout.prop( shading , "show_backface_culling", icon_value = custom_icon("icon_opt_backcull"))

#       tool_settings = context.tool_settings
#      layout.prop(tool_settings, "use_edge_path_live_unwrap")
#       layout.prop(tool_settings, "use_mesh_automerge")
#       layout.prop(tool_settings, "double_threshold")
#       layout.prop(tool_settings, "edge_path_mode")

def draw_settings_toolheader(context, layout, tool , ui = ['GEOM','BRUSH','OPTION']  ):
    props = tool.operator_properties("mesh.poly_quilt")

    if 'GEOM' in ui :
        row = layout.row( align=True)
        row.label( text = "Geom" )
        row.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = True  )

    if 'BRUSH' in ui :
        row = layout.row( align=True)
        row.label( text = "Brush" )
        row.prop( bpy.context.preferences.addons[__package__].preferences, "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = True )

    if 'OPTION' in ui :
        # Expand panels from the side-bar as popovers.
        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".poly_quilt_option", **popover_kw)

def draw_sub_tool( _layout , name , text , tool ) :
    preferences = bpy.context.preferences.addons[__package__].preferences

    column = _layout.box().column()    
    row = column.row()
    row.prop( preferences, "keymap_setting_expanded", text="",
        icon='TRIA_DOWN' if preferences.keymap_setting_expanded else 'TRIA_RIGHT')

    row.label(text =text + " Setting")

    if preferences.keymap_setting_expanded :
        _box = column.row()
        _box.label(icon = 'EVENT_SHIFT')
        _box.prop(preferences, name + "_shift" , text = "" )
        _box = column.row()
        _box.label(icon = 'EVENT_CTRL')            
        _box.prop(preferences, name + "_ctrl" , text = "" )
        _box = column.row()
        _box.label(icon = 'EVENT_ALT')            
        _box.prop(preferences, name + "_alt" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_SHIFT')
        _box.label(icon = 'EVENT_CTRL')
        _box.prop(preferences, name + "_shift_ctrl" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_SHIFT')
        _box.label(icon = 'EVENT_ALT')
        _box.prop(preferences, name + "_shift_alt" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_CTRL')
        _box.label(icon = 'EVENT_ALT')
        _box.prop(preferences, name + "_ctrl_alt" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_OS')            
        _box.label(icon = 'EVENT_SHIFT') 
        _box.prop(preferences, name + "_os_shift" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_OS')            
        _box.label(icon = 'EVENT_CTRL') 
        _box.prop(preferences, name + "_os_ctrl" , text = "" )

        _box = column.row()
        _box.label(icon = 'EVENT_OS')            
        _box.label(icon = 'EVENT_ALT') 
        _box.prop(preferences, name + "_os_alt" , text = "" )




class VIEW3D_PT_tools_polyquilt_options( Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    bl_category = "Tool"
    bl_context = ".poly_quilt_option"  # dot on purpose (access from topbar)
    bl_label = "Options"
    bl_options = {'DEFAULT_CLOSED'}
    bl_ui_units_x = 8
    @classmethod
    def poll(cls, context):
        return context.active_object

    def draw(self, context):
        layout = self.layout

        # Active Tool
        # -----------
        from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
        tool = ToolSelectPanelHelper.tool_active_from_context(context)
#       print(tool.idname)
        props = tool.operator_properties("mesh.poly_quilt")
        preferences = bpy.context.preferences.addons[__package__].preferences

        col = layout.column()        
        col.label( text = "Pivot" )
        col.prop(props, "plane_pivot" , text = "Pivot" , expand = True )

        col = layout.column()        
        col.label( text = "Move" )
        row = layout.row()           
        row.ui_units_x = 3.25     
        row.prop(props, "move_type" , text = "" , expand = True , icon_only = True )
  
        layout.label( text = "Fix X=0" )
        layout.prop( preferences, "fix_to_x_zero", toggle = True , text = "" , icon_only = True, icon_value = custom_icon("icon_opt_x0") )

        layout.label( text = "Extrude" )
        layout.prop(props, "extrude_mode" , text = "EXTRUDE" , expand = True )

        layout.label( text = "LOOPCUT" )
        layout.prop(props, "loopcut_mode" , text = "LOOPCUT" , expand = True )
        col = layout.column()              
        col.label( text = "Edge Snap Div" )        
        col.prop( preferences, "loopcut_division" , text = "Edge Snap Div" , expand = True, slider = True , icon_only = False )

        col.label( text = "Vertex Dissolve Angle" )        
        col.prop( preferences, "vertex_dissolve_angle" , text = "Vertex Dissolve Angle", expand = True, slider = True , icon_only = False  )

        col.label( text = "Brush" )        
        col.prop( preferences, "brush_size" , text = "Brush Size" , expand = True, slider = True , icon_only = False )
        col.prop( preferences, "brush_strength" , text = "Brush Strength" , expand = True, slider = True , icon_only = False )


