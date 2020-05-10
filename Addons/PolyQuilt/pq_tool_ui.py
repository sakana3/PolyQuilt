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

    if 'GEOM' in ui :
        row = layout.row( align=True)
        row.label( text = "Geom" )
        row.prop(props, "geometry_type" , text = "Geom" , expand = True , icon_only = True  )

    if 'BRUSH' in ui :
        row = layout.row( align=True)
        row.label( text = "Brush" )
        row.prop( props , "brush_type" , text = "Brush", toggle = True , expand = True, icon_only = True )

    if 'OPTION' in ui :
        # Expand panels from the side-bar as popovers.
        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        op = layout.popover_group(context=".poly_quilt_option", **popover_kw)

def draw_tool_keymap( layout ,keyconfing,keymapname ) :
    keymap = keyconfing.keymaps[keymapname]            
    for item in reversed(keymap.keymap_items) :
        if True in (item.oskey,item.shift,item.ctrl,item.alt) :
            it = layout.row( align = True )
#            it.prop(item , "active" , text = "" )
            if item.idname == 'mesh.poly_quilt' :
                it.context_pointer_set('keymap', keymap)
                it.row(align = True).template_event_from_keymap_item(item)
                it.prop(item.properties , "tool_mode" , text = "" , emboss = True )

                item.id_data.tag = True
                if( item.properties.tool_mode == 'BRUSH' ) :
                    it = it.row()
                    it.active = item.properties.is_property_set("brush_type")
                    it.prop(item.properties, "brush_type" , text = "" , emboss = True )
    layout.operator(PQ_OT_DirtyKeymap.bl_idname).keymap_name = keymapname


def Hoge() :
    # Hack!
    # template_keymap_item_propertiesにダーティフラグを処理させるために極小のUIを表示
    for item in reversed(keymap.keymap_items) :
        if True in (item.oskey,item.shift,item.ctrl,item.alt) :
            it = layout.column( align = True )
#            it.scale_x = 0.1
#            it.scale_y = 0.1
#            it.ui_units_x = 0.1
#            it.ui_units_y = 0.1
            if item.idname == 'mesh.poly_quilt' :
                it.context_pointer_set('keymap', keymap)
                it.template_keymap_item_properties(item)

#                   if it.active :
#                      it.context_pointer_set( "brush_type"  , item.properties )
#                it = layout.column()
#                        rna_keymap_ui.draw_kmi(
#                                [], keyconfing, keymap, item, it, 0)
#                       it.template_keymap_item_properties(item)
#                            for m in inspect.getmembers(item.properties):
#                                print(m)

def draw_keymap_sample( context , layout ) :
    keyconfing = context.window_manager.keyconfigs.user    
    keymap = keyconfing.keymaps["My Addon" ]        

    for item in reversed(keymap.keymap_items) :
        row = layout.row( align = True )
        if item.idname == "my_operator" :
            row.template_event_from_keymap_item(item)
            row.prop(item.properties , "tool_mode" , text = "" )

def draw_sub_tool( context , _layout , text , tool ) :

    preferences = context.preferences.addons[__package__].preferences

    column = _layout.box().column()    
    row = column.row()
    row.prop( preferences, "keymap_setting_expanded", text="",
        icon='TRIA_DOWN' if preferences.keymap_setting_expanded else 'TRIA_RIGHT')

    row.label(text =text + " Setting")

    if preferences.keymap_setting_expanded :
        keyconfing = context.window_manager.keyconfigs.user
        draw_tool_keymap( column, keyconfing,"3D View Tool: Edit Mesh, " + tool.bl_label )


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




class PQ_OT_DirtyKeymap(bpy.types.Operator) :
    bl_idname = "addon.polyquilt_dirty_keymap"
    bl_label = "Save Keymap"

    keymap_name : bpy.props.StringProperty()

    def execute(self, context):
        for keymap in [ k for k in context.window_manager.keyconfigs.user.keymaps if "PolyQuilt" in k.name ] :
            for item in reversed(keymap.keymap_items) :
                if True in (item.oskey,item.shift,item.ctrl,item.alt) :
                    if item.idname == 'mesh.poly_quilt' :
                        item.active = item.active

        return {'FINISHED'}
