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

class ToolPolyQuilt(WorkSpaceTool):
    bl_space_type='VIEW_3D'
    bl_context_mode='EDIT_MESH'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt"
    bl_label = "PolyQuilt"
    bl_description = ( "Lowpoly Tool" )
    bl_icon = bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_icon")
    bl_widget = "MESH_GGT_PQ_Preselect"
    bl_keymap = (
        ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS'},None) ,
    )

    def draw_settings(context, layout, tool):
        global custom_icons

        props = tool.operator_properties("mesh.poly_quilt")
#       layout.label(text="Make",text_ctxt="Make", translate=True, icon='NORMALS_FACE')
        layout.prop(props, "geometry_type" , text = "Geom" , icon = "OUTLINER_DATA_LATTICE", toggle = True , expand = True , icon_only = True  )
        layout.prop(props, "plane_pivot" , text = "Pivot", toggle = True, expand = True )
        layout.prop(props, "move_type" , text = "Move", toggle = True, expand = True )
        layout.prop( bpy.context.preferences.addons[__package__].preferences, "fix_to_x_zero" , text = "Fix X=0"  )

#       layout.prop(props, "backface" , text = "Use backface", icon = 'NORMALS_FACE')


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

        col.label( text = "Brush" )        
        col.prop( preferences, "brush_size" , text = "Brush Size" , expand = True, slider = True , icon_only = False )
        col.prop( preferences, "brush_strength" , text = "Brush Strength" , expand = True, slider = True , icon_only = False )


km_tool_snap_utilities_line = "3D View Tool: Edit Mesh, PolyQuilt"


@ToolDef.from_fn
def tool_poly_quilt():
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

        row = layout.row(align=True)
        row.prop(props, "loopcut_mode" , text = "LOOPCUT" , expand = True )
        row = layout.row(align=True)
        row.prop( preferences, "loopcut_division" , text = "Edge Snap Div" , expand = True, slider = True  )

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

    def draw_settings_toolheader(context, layout, tool):
        props = tool.operator_properties("mesh.poly_quilt")

        row = layout.row( align=True)
        row.label( text = "Geom" )
        row.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = True  )

        row = layout.row( align=True)
        row.label( text = "Brush" )
        row.prop( bpy.context.preferences.addons[__package__].preferences, "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = True )

       # Expand panels from the side-bar as popovers.
        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".poly_quilt_option", **popover_kw)
 
    def draw_settings(context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")

    return dict(
        idname="mesh_tool.poly_quilt",
        label="PolyQuilt",
        description=(
            "Lowpoly Tool"
        ),
        icon=os.path.join(icons_dir, "addon.poly_quilt_icon"),
        widget="MESH_GGT_PQ_Preselect",
        keymap = km_tool_snap_utilities_line ,      
        draw_settings=draw_settings,
    )

def km_3d_view_tool_snap_utilities_line(tool_mouse):
    return (
        km_tool_snap_utilities_line,
        {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
        {"items": [
            ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS'}, {"properties": [("tool_mode", 'LOWPOLY')]}),
            ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS' , "alt": True}, {"properties": [("lock_hold", True)]}),
#           ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS' , "ctrl": True}, {"properties": [("tool_mode", 'EXTRUDE')]}),
            ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS' , "shift": True},  {"properties": [("tool_mode", 'BRUSH')]}),
#           ("mesh.poly_quilt", {"type": "MIDDLEMOUSE", "value": 'PRESS' , "shift": True},  {"properties": [("tool_mode", 'BRUSH'),("alternative",True)]}),
            ("mesh.poly_quilt_hold_lock", {"type": 'LEFT_ALT', "value": 'DOUBLE_CLICK' } , {} ),
            ("mesh.poly_quilt_key_check", {"type": 'MOUSEMOVE', "value": 'ANY' }, {"properties": []}),
            ("mesh.poly_quilt_brush_size", {"type": 'WHEELINMOUSE', "value": 'PRESS', "shift": True }, {"properties": [("brush_size_value",50)]}),
            ("mesh.poly_quilt_brush_size", {"type": 'WHEELOUTMOUSE', "value": 'PRESS', "shift": True }, {"properties": [("brush_size_value",-50)]}),
            ("mesh.poly_quilt_brush_size", {"type": 'WHEELINMOUSE', "value": 'PRESS', "shift": True, "ctrl": True }, {"properties": [("brush_strong_value",-0.05)]}),
            ("mesh.poly_quilt_brush_size", {"type": 'WHEELOUTMOUSE', "value": 'PRESS', "shift": True , "ctrl": True}, {"properties": [("brush_strong_value",0.05)]}),
         ]},
    )

def km_view3d_empty(km_name):
    return (
        km_name,
        {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
        {"items": []},
    )

def generate_empty_snap_utilities_tools_keymaps():
    return [
        km_view3d_empty(km_tool_snap_utilities_line),
    ]

def generate_snap_utilities_keymaps(tool_mouse = 'LEFTMOUSE'):
    return [
        # Tool System.
        km_3d_view_tool_snap_utilities_line(tool_mouse),
    ]

def register_keymaps():
    keyconfigs = bpy.context.window_manager.keyconfigs
    kc_defaultconf = keyconfigs.default
    kc_addonconf   = keyconfigs.addon

    # TODO: find the user defined tool_mouse.
    from bl_keymap_utils.io import keyconfig_init_from_data
    keyconfig_init_from_data(kc_defaultconf, generate_empty_snap_utilities_tools_keymaps())
    keyconfig_init_from_data(kc_addonconf, generate_snap_utilities_keymaps())

    #snap_modalkeymap = kc_addonconf.keymaps.find(keys.km_snap_utilities_modal_keymap)
    #snap_modalkeymap.assign("MESH_OT_snap_utilities_line")


def unregister_keymaps():
    keyconfigs = bpy.context.window_manager.keyconfigs
    defaultmap = keyconfigs.get("blender").keymaps
    addonmap   = keyconfigs.get("blender addon").keymaps

    for keyconfig_data in generate_snap_utilities_keymaps():
        km_name, km_args, km_content = keyconfig_data
        addonmap.remove(addonmap.find(km_name, **km_args))

    for keyconfig_data in generate_empty_snap_utilities_tools_keymaps():
        km_name, km_args, km_content = keyconfig_data
        defaultmap.remove(defaultmap.find(km_name, **km_args))

def get_tool_list(space_type, context_mode):
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    return cls._tools[context_mode]


def register_tools():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')

    for index, tool in enumerate(tools, 1):
        if isinstance(tool, ToolDef) and tool.label == "Poly Build":
            break

    tools[:index] += None, tool_poly_quilt

    del tools


def unregister_tools():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')

    index = tools.index(tool_poly_quilt) - 1 #None
    tools.pop(index)
    tools.remove(tool_poly_quilt)

    del tools
    del index