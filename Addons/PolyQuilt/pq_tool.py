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
from bpy.types import WorkSpaceTool
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
        layout.prop(props, "fix_to_x_zero" , text = "Fix X=0" )
#       layout.prop(props, "backface" , text = "Use backface", icon = 'NORMALS_FACE')


km_tool_snap_utilities_line = "3D View Tool: Edit Mesh, PolyQuilt"


@ToolDef.from_fn
def tool_poly_quilt():
    def draw_settings(context, layout, tool):
        props = tool.operator_properties("mesh.poly_quilt")
#       layout.label(text="Make",text_ctxt="Make", translate=True, icon='NORMALS_FACE')

        scale_x = 1.0
        toggle = True
        if context.space_data.type != 'PROPERTIES':
            scale_x = 1.0
            scale_y = 0.75
            toggle = True
        else :
            scale_x = 1.5
            scale_y = 1
            toggle = False


        row = layout.row(align=True)
        row.scale_x = 1.5        
        row.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = True  )
        box = row.box()
        box.ui_units_x = 1.8
        box.scale_y = 0.5
        box.label(text = props.geometry_type)

        row = layout.row(align=True)
        row.prop(props, "plane_pivot" , text = "Pivot" , expand = True , icon_only = True )
        box = row.box()
        box.ui_units_x = 2.2
        box.scale_y = 0.5
        box.label(text = props.plane_pivot)

        row = layout.row(align=True)
        row.prop(props, "move_type" , text = "Move" , expand = True , icon_only = True )
        box = row.box()
        box.ui_units_x = 3.5
        box.scale_y = 0.5
        box.label(text = props.move_type)

        def get_shading():
            # Get settings from 3D viewport or OpenGL render engine
            view = context.space_data
#            return bpy.data.screens["Modeling"].shading
            if view.type == 'VIEW_3D':
                return view.shading
            else:
                return context.scene.display.shading

  
#       layout.prop(context.active_object.data, "use_mirror_x", toggle = toggle , icon_only = False, icon_value = custom_icon("icon_opt_mirror") )
        layout.prop(context.active_object.data, "use_mirror_x", toggle = toggle , icon_only = False , icon = "MOD_MIRROR" )
        layout.prop(props, "fix_to_x_zero" ,text = "Fix X=0", toggle = toggle , icon_only = False, icon_value = custom_icon("icon_opt_x0") )

        row = layout.row(align=True)
        row.prop(props, "loopcut_mode" , text = "LOOPCUT" , expand = True )
        row.prop( bpy.context.preferences.addons[__package__].preferences, "loopcut_division" , text = "Div" , expand = True )


#        shading = get_shading()
#        if shading.type == 'SOLID':        
#            layout.prop( shading , "show_backface_culling", icon_value = custom_icon("icon_opt_backcull"))

#       tool_settings = context.tool_settings
#      layout.prop(tool_settings, "use_edge_path_live_unwrap")
#       layout.prop(tool_settings, "use_mesh_automerge")
#       layout.prop(tool_settings, "double_threshold")
#       layout.prop(tool_settings, "edge_path_mode")


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
#            ("mesh.poly_quilt_check_key", {"type": 'MOUSEMOVE' , "value": 'ANY' },
#            {"properties": []}),
           ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS'},
             {"properties": [("tool_mode", 'LOWPOLY')]}),
            ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS' , "ctrl": True},
             {"properties": [("tool_mode", 'EXTRUDE')]}),
            ("mesh.poly_quilt", {"type": tool_mouse, "value": 'PRESS' , "alt": True},
             {"properties": [("lock_hold", True)]}),
            ("mesh.poly_quilt_hold_lock", {"type": 'LEFT_ALT', "value": 'DOUBLE_CLICK' } , {} ),
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
