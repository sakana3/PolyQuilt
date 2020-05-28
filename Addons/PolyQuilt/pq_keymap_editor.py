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
from bpy.types import AddonPreferences

def draw_tool_keymap( layout ,keyconfing,keymapname ) :
    keymap = keyconfing.keymaps[keymapname]            
    layout.context_pointer_set('keymap', keymap)
    cnt = 0


    for item in reversed(keymap.keymap_items) :
        cnt = max( cnt , (item.oskey,item.shift,item.ctrl,item.alt).count(True) )

    for item in reversed(keymap.keymap_items) :
        if True in (item.oskey,item.shift,item.ctrl,item.alt) :
            it = layout.row( )
#            it.prop(item , "active" , text = "" )
            if item.idname == 'mesh.poly_quilt' :
#               for i3d in keyconfing.keymaps["Mesh"].keymap_items :
#                    if i3d.type == 'LEFTMOUSE' and i3d.shift == item.shift and i3d.ctrl == item.ctrl and i3d.alt == item.alt and i3d.oskey == item.oskey :
#                        ic = layout.row(align = True)
#                        ic.template_event_from_keymap_item(i3d)
#                        ic.label( icon = 'ERROR' , text = i3d.name  )
#                for i3d in keyconfing.keymaps["3D View"].keymap_items :
#                    if i3d.type == 'LEFTMOUSE' and i3d.shift == item.shift and i3d.ctrl == item.ctrl and i3d.alt == item.alt and i3d.oskey == item.oskey :
#                        ic = layout.row(align = True)
#                        ic.template_event_from_keymap_item(i3d)
#                        ic.label( icon = 'ERROR' , text = i3d.name  )

#               ic = it.row(align = True)
#               ic.prop( item ,   icon = 'ERROR' )

                ic = it.row(align = True)
                ic.ui_units_x = cnt + 2
                ic.prop(item , "active" , text = "" , emboss = True )
                ic.template_event_from_keymap_item(item)

                ic = it.row(align = True)
                ic.prop(item.properties , "tool_mode" , text = "" , emboss = True )

#               op = it.popover(panel="VIEW3D_PT_tools_polyquilt_keymap_properties" , text = item.properties.tool_mode )
#               op.item_id = 0

                if( item.properties.tool_mode == 'LOWPOLY' ) :
                    im = ic.row()
                    im.active = item.properties.is_property_set("geometry_type")
                    im.prop(item.properties, "geometry_type" , text = "" , emboss = True , expand = False , icon_only = False )

                if( item.properties.tool_mode == 'BRUSH' ) :
                    im = ic.row()
                    im.active = item.properties.is_property_set("brush_type")
                    im.prop(item.properties, "brush_type" , text = "" , emboss = True , expand = False , icon_only = False )

                if( item.properties.tool_mode == 'LOOPCUT' ) :
                    im = ic.row()
                    im.active = item.properties.is_property_set("loopcut_mode")
                    im.prop(item.properties, "loopcut_mode" , text = "" , emboss = True , expand = False , icon_only = False )


                if (not item.is_user_defined) and item.is_user_modified:
                    it.operator("preferences.keyitem_restore", text="", icon='BACK').item_id = item.id
                elif item.is_user_defined :
                    it.operator("preferences.keyitem_remove", text="", icon='X').item_id = item.id

#    layout.operator("preferences.keyitem_add", text="Add New", text_ctxt=i18n_contexts.id_windowmanager, icon='ADD')
    layout.operator(PQ_OT_DirtyKeymap.bl_idname)
#    popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}    
#    op = layout.popover_group(context=".poly_quilt_keymap_properties", **popover_kw)
#                   if it.active :
#                      it.context_pointer_set( "brush_type"  , item.properties )
#                it = layout.column()
#                        rna_keymap_ui.draw_kmi(
#                                [], keyconfing, keymap, item, it, 0)
#                       it.template_keymap_item_properties(item)
#                            for m in inspect.getmembers(item.properties):
#                                print(m)


def draw_tool_keymap_ui( context , _layout , text , tool) :

    preferences = context.preferences.addons[__package__].preferences

    column = _layout.box().column()    
    row = column.row()
    row.prop( preferences, "keymap_setting_expanded", text="",
        icon='TRIA_DOWN' if preferences.keymap_setting_expanded else 'TRIA_RIGHT')

    row.label(text =text + " Setting")

    if preferences.keymap_setting_expanded :
        keyconfing = context.window_manager.keyconfigs.user
        draw_tool_keymap( column, keyconfing,"3D View Tool: Edit Mesh, " + tool.bl_label )

class PQ_OT_DirtyKeymap(bpy.types.Operator) :
    bl_idname = "addon.polyquilt_dirty_keymap"
    bl_label = "Save Keymap"

    def execute(self, context):
        for keymap in [ k for k in context.window_manager.keyconfigs.user.keymaps if "PolyQuilt" in k.name ] :
            keymap.show_expanded_items = keymap.show_expanded_items
            for item in reversed(keymap.keymap_items) :
                if True in (item.oskey,item.shift,item.ctrl,item.alt) :
                    if item.idname == 'mesh.poly_quilt' :
                        item.active = item.active

        context.preferences.is_dirty = True
#       bpy.ops.wm.save_userpref()
        return {'FINISHED'}

