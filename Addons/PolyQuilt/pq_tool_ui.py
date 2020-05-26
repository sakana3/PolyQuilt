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
import inspect
import rna_keymap_ui
from bpy.app.translations import pgettext_iface as iface_
from bpy.app.translations import contexts as i18n_contexts
from bpy.types import AddonPreferences
def draw_settings_ui(context, layout, tool  , ui ):
    props = tool.operator_properties("mesh.poly_quilt")
    preferences = bpy.context.preferences.addons[__package__].preferences

    hoge =  bpy.props.EnumProperty(
        name="LoopCut Mode",
        description="LoopCut Mode",
        items=[('EQUAL' , "Equal", "" ),
               ('EVEN' , "Even", "" ) ],
        default='EQUAL',
    )

#       layout.label(text="Make",text_ctxt="Make", translate=True, icon='NORMALS_FACE')

    if "MASTER" in ui or "LOWPOLY" in ui :
        col = layout.column(align=True)
        col.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = False  )

        col = layout.column(align=True)
        col.prop(props, "plane_pivot" , text = "Pivot" , expand = True , icon_only = False )

        col = layout.column(align=True)
        col.prop(props, "move_type" , text = "Move" , expand = True , icon_only = False )

        row = layout.row(align=True)
        row.prop(props, "snap_mode" , text = "Snap" , expand = True , icon_only = False )

#       layout.prop(context.active_object.data, "use_mirror_x", toggle = toggle , icon_only = False, icon_value = custom_icon("icon_opt_mirror") )
    layout.prop(context.active_object.data, "use_mirror_x", toggle = True , icon_only = False , icon = "MOD_MIRROR" )
    layout.prop( preferences, "fix_to_x_zero", toggle = True , text = "Fix X=0" , icon_only = False, icon_value = custom_icon("icon_opt_x0") )

    if "MASTER" in ui or "EXTRUDE" in ui :
        row = layout.row(align=True)
        row.prop(props, "extrude_mode" , text = "EXTRUDE" , expand = True )

    if "MASTER" in ui or "LOOPCUT" in ui :
        layout.separator()
        row = layout.row(align=True)
        row.prop(props, "loopcut_mode" , text = "LOOPCUT" , expand = True )

    row = layout.row(align=True)
    row.prop( preferences, "loopcut_division" , text = "Edge Snap Div" , expand = True, slider = True  )

    layout.separator()
    col = layout.column(align=True)
    col.prop( preferences, "vertex_dissolve_angle" , text = "Vertex Dissolve Angle", expand = True, slider = True , icon_only = False  )

    if "MASTER" in ui or "BRUSH" in ui :
        layout.separator()
        col = layout.column(align=True)
        col.prop( props, "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = False )

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

    if "MASTER" in ui or "LOWPOLY" in ui :
        row = layout.row( align=True)
        row.label( text = "Geom" )
        row.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = True  )

    if "MASTER" in ui or "BRUSH" in ui :
        row = layout.row( align=True)
        row.label( text = "Brush" )
        row.prop( props , "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = True )

    # Expand panels from the side-bar as popovers.
    popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
    op = layout.popover_group(context=".poly_quilt_option", **popover_kw)


class VIEW3D_PT_tools_polyquilt_options( Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    bl_category = "Tool"
    bl_context = ".poly_quilt_option"  # dot on purpose (access from topbar)
    bl_label = "Options"
    bl_options = {'DEFAULT_CLOSED'}
#    bl_ui_units_x = 8

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
  
        col = layout.column()        
        col.label( text = "Snap" )
        row = layout.row(align=True)
        row.prop(props, "snap_mode" , text = "Snap" , expand = True , icon_only = False )

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
