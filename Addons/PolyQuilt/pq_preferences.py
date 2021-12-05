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
from .pq_keymap_editor import draw_tool_keymap

from bpy.props import (
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from .utils.addon_updater import (
    AddonUpdaterManager,
    AddonUpdaterConfig,
    get_separator,
)
from bpy.types import AddonPreferences
from .pq_icon import *
from .subtools import *

__all__ = [
    "PolyQuiltPreferences" ,
    "PQ_OT_SetupUnityLikeKeymap",
    "PQ_OT_CheckAddonUpdate" ,
    "PQ_OT_UpdateAddon" ,
    "register_updater"
]

class PQ_OT_CheckAddonUpdate(bpy.types.Operator):
    bl_idname = "mesh.pq_ot_check_addon_update"
    bl_label = "Check Update"
    bl_description = "Check Add-on Update"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _):
        updater = AddonUpdaterManager.get_instance()
        updater.check_update_candidate()

        return {'FINISHED'}

class PQ_OT_UpdateAddon(bpy.types.Operator):
    bl_idname = "mesh.pq_ot_update_addon"
    bl_label = "Update"
    bl_description = "Update Add-on"
    bl_options = {'REGISTER', 'UNDO'}

    branch_name : StringProperty(
        name="Branch Name",
        description="Branch name to update",
        default="",
    )

    def execute(self, _):
        updater = AddonUpdaterManager.get_instance()
        updater.update(self.branch_name)

        return {'FINISHED'}




def register_updater(bl_info):
    config = AddonUpdaterConfig()
    config.owner = "sakana3"
    config.repository = "PolyQuilt"
    config.current_addon_path = os.path.dirname(os.path.realpath(__file__))
    config.branches = ["master", "develop","Future" ]
    config.addon_directory = \
        config.current_addon_path[
            :config.current_addon_path.rfind(get_separator())]
    config.min_release_version = bl_info["version"]
    config.default_target_addon_path = "PolyQuilt"
    config.target_addon_path = {
        "master": "Addons{}PolyQuilt".format(get_separator()),
        "develop": "Addons{}PolyQuilt".format(get_separator()),
        "Future": "Addons{}PolyQuilt".format(get_separator()),
    }
    updater = AddonUpdaterManager.get_instance()
    updater.init(bl_info, config)

def get_update_candidate_branches(_, __):
    manager = AddonUpdaterManager.get_instance()
    if not manager.candidate_checked():
        return []

    return [(name, name, "") for name in manager.get_candidate_branch_names()]



class PolyQuiltPreferences(AddonPreferences):
    """Preferences class: Preferences for this add-on"""
    bl_idname = __package__

    highlight_color : FloatVectorProperty(
        name="HighlightColor",
        description="HighlightColor",
        default=(1,1,0.2,1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    makepoly_color : FloatVectorProperty(
        name="MakePolyColor",
        description="MakePoly Color",
        default=(0.4,0.7,0.9,1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    split_color : FloatVectorProperty(
        name="SplitColor",
        description="Split Color",
        default=(0.1,1.0,0.25,1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    threshold : FloatVectorProperty(
        name="DeleteColor",
        description="Delete Color",
        default=(1,0.1,0.1,1.0)    ,
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    delete_color : FloatVectorProperty(
        name="DeleteColor",
        description="Delete Color",
        default=(1,0.1,0.1,1.0)    ,
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    distance_to_highlight : FloatProperty(
        name="distance_to_highlight",
        description="distance_to_highlight",
        default=4.0,
        min=1.0,
        max=10.0)

    highlight_vertex_size : FloatProperty(
        name="Highlight Vertex Size",
        description="Highlight Vertex Size",
        default= 1.25,
        min=0.5,
        max=8.0)

    highlight_line_width : FloatProperty(
        name="Highlight Line Width",
        description="Highlight Line Width",
        default=2.0,
        min=1.0,
        max=10.0)

    highlight_face_alpha : FloatProperty(
        name="Highlight Face Alpha",
        description="Highlight Face Alpha",
        default=0.2,
        min=0.1,
        max=1.0)

    longpress_time : FloatProperty(
        name="LongPressTime",
        description="Long press Time",
        default=0.4,
        min=0.2,
        max=1.0)

    marker_size : bpy.props.FloatProperty(
        name="Marker Size",
        description="Marker Size",
        default=1.0,
        min=0.1,
        max=5.0)    


    extra_setting_expanded : BoolProperty(
        name="Extra",
        description="Extra",
        default=False
    )

    is_debug : BoolProperty(
        name="is Debug",
        description="is Debug",
        default=False
    )

    # for add-on updater
    updater_branch_to_update : EnumProperty(
        name="branch",
        description="Target branch to update add-on",
        items=get_update_candidate_branches
    )

    loopcut_division : bpy.props.IntProperty(
        name="LoopCut DIVISON",
        description="LoopCut Division",
        min = 0,
        max = 16,
        default=0,
    )

    brush_size : bpy.props.FloatProperty(
        name="Brush Size",
        description="Brush Size",
        default=50.0,
        min=5.0,
        max=200.0)    

    brush_strength : bpy.props.FloatProperty(
        name="Brush Strength",
        description="Brush Strength",
        default=0.5,
        min=0.0,
        max=1.0)    

    fix_to_x_zero : bpy.props.BoolProperty(
              name = "fix_to_x_zero" ,
              default = False ,
              description="Fix X=0",
            )

    space_drag_op : bpy.props.EnumProperty(
        name="Space Drag Operation",
        description="Space Drag Operation",
        items=[('NONE' , "None", "" ),
               ('ORBIT' , "Orbit", "" ),
               ('PAN' , "Pan", "" ) ,
               ('DOLLY' , "Dolly", "" ) ,
               ('KNIFE' , "Knife", "" ) ,
               ('SELECT_BOX' , "Select Box", "" ) ,
               ('SELECT_LASSO' , "Select Lasso", "" ) ],
        default='ORBIT',
    )

    vertex_dissolve_angle : FloatProperty(
        name="Vertex Dessolve Angle",
        description="Vertex Dessolve Angle",
        default= 160,
        min=0,
        max=180)

    keymap_setting_expanded : BoolProperty(
        name="Keymap",
        description="Keymap",
        default=False
    )

    keymap_category : EnumProperty(
        name="Category",
        description="Preferences Category",
        items=[
            ('PolyQuilt', "Master", ""),
            ('PolyQuilt:Poly', "Lowpoly", ""),
            ('PolyQuilt:Extrude', "Extrude", ""),
            ('PolyQuilt:LoopCut', "LoopCut", ""),
            ('PolyQuilt:Knife', "Knife", ""),
            ('PolyQuilt:Delete', "Delete", ""),
            ('PolyQuilt:Brush', "Brush", ""),
        ],
        default='PolyQuilt'
    )    


    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Tool settings:", icon = 'TOOL_SETTINGS')
        box = row.box().column()
        row = box.row()
        row.label(text="Long Press Time")
        row.prop(self, "longpress_time" , text = "Time" )
        row = box.row()
        row.label(text="Distance to Highlight")
        row.prop(self, "distance_to_highlight" , text = "Distance" )
        row = box.row()
        row.label(text="Highlight Vertex Size", icon = 'VERTEXSEL' )
        row.prop(self, "highlight_vertex_size" , text = "Size" )
        row = box.row()
        row.label(text="Highlight Line Width", icon = 'EDGESEL' )
        row.prop(self, "highlight_line_width" , text = "Width" )
        row = box.row()
        row.label(text="Highlight Face Alpha", icon = 'FACESEL' )
        row.prop(self, "highlight_face_alpha" , text = "Alpha" )
        row = box.row()
        row.label(text="Marker Size" )
        row.prop(self, "marker_size" , text = "Size" )

        row = box.row()
        row.label(text="Space Drag Operation" )
        row.prop(self, "space_drag_op" , text = "")

        row = layout.row()
        row.column().label(text="Color settings:" , icon = 'COLOR')
        box = row.box().column()
        box.row().prop(self, "highlight_color" , text = "HighlightColor")
        box.row().prop(self, "makepoly_color" , text = "MakePolyColor")
        box.row().prop(self, "split_color" , text = "SplitColor" )
        box.row().prop(self, "delete_color" , text = "DeleteColor")

        layout.prop( self, "keymap_setting_expanded", text="Keymap setting",
            icon='TRIA_DOWN' if self.keymap_setting_expanded else 'TRIA_RIGHT')

        if self.keymap_setting_expanded :
            col = layout.column()
            col.row().prop(self, "keymap_category", expand=True)

            keyconfing = context.window_manager.keyconfigs.user            
            draw_tool_keymap( col.box() ,keyconfing , "3D View Tool: Edit Mesh, " + self.keymap_category )

        layout.prop( self, "extra_setting_expanded", text="Extra Settings",
            icon='TRIA_DOWN' if self.extra_setting_expanded
            else 'TRIA_RIGHT')
        if self.extra_setting_expanded :
            self.draw_updater_ui(layout)
            col = layout.column()
            col.scale_y = 2
            col.operator(PQ_OT_SetupUnityLikeKeymap.bl_idname,
                        text= bpy.app.translations.pgettext("Setup GameEngine like Keymaps"),
                        icon='MONKEY')
            col = layout.column()
            col.scale_y = 1
            layout.row().prop(self, "is_debug" , text = "Debug")

    def draw_updater_ui(self,layout):
        updater = AddonUpdaterManager.get_instance()

        layout.separator()

        if not updater.candidate_checked():
            col = layout.column()
            col.scale_y = 2
            row = col.row()
            row.operator(PQ_OT_CheckAddonUpdate.bl_idname,
                        text="Check 'PolyQuilt' add-on update",
                        icon='FILE_REFRESH')
        else:
            row = layout.row(align=True)
            row.scale_y = 2
            col = row.column()
            col.operator(PQ_OT_CheckAddonUpdate.bl_idname,
                        text="Check 'PolyQuilt' add-on update",
                        icon='FILE_REFRESH')
            col = row.column()
            if updater.latest_version() != "":
                col.enabled = True
                ops = col.operator(
                    PQ_OT_UpdateAddon.bl_idname,
                    text="Update to the latest release version (version: {})"
                    .format(updater.latest_version()),
                    icon='TRIA_DOWN_BAR')
                ops.branch_name = updater.latest_version()
            else:
                col.enabled = False
                col.operator(PQ_OT_UpdateAddon.bl_idname,
                            text="No updates are available.")

            layout.separator()
            layout.label(text="Manual Update:")
            row = layout.row(align=True)
            row.prop(self, "updater_branch_to_update", text="Target")
            ops = row.operator(
                PQ_OT_UpdateAddon.bl_idname, text="Update",
                icon='TRIA_DOWN_BAR')
            ops.branch_name = self.updater_branch_to_update

            layout.separator()
            if updater.has_error():
                box = layout.box()
                box.label(text=updater.error(), icon='CANCEL')
            elif updater.has_info():
                box = layout.box()
                box.label(text=updater.info(), icon='ERROR')




class PQ_OT_SetupUnityLikeKeymap(bpy.types.Operator) :
    bl_idname = "addon.set_unity_like_keymap"
    bl_label = "SetupGameEngineLikeKeymap"
    bl_description = "Setup GameEngine like Keymaps"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for keymap in context.window_manager.keyconfigs.user.keymaps:
#            print( keymap.name + "----" + keymap.space_type )
            if keymap.space_type == 'EMPTY' or keymap.space_type == 'NODE_EDITOR'  or keymap.space_type == 'IMAGE_EDITOR' :
                # Add View2D RMB pan
                if keymap.name == 'Image' :
                    PQ_OT_SetupUnityLikeKeymap.AddKeyToKeyMap( keymap , 'image.view_pan', 'MOUSE' , 'RIGHTMOUSE' , 'CLICK_DRAG' )
                if keymap.name == "View2D" :
                    PQ_OT_SetupUnityLikeKeymap.AddKeyToKeyMap( keymap , 'view2d.pan', 'MOUSE' , 'RIGHTMOUSE' , 'CLICK_DRAG' )

                for key in keymap.keymap_items:
                    if True not in [ key.any , key.alt , key.ctrl ,key.shift ]:
                        if key.map_type == 'MOUSE' and key.type == 'RIGHTMOUSE' and key.value != 'CLICK_DRAG' :
                            key.value = 'CLICK'

        for keymap in context.window_manager.keyconfigs.user.keymaps:
            if keymap.space_type == 'VIEW_3D':
                for key in keymap.keymap_items:
                    if key.idname == 'view3d.rotate' and key.map_type == 'MOUSE' :
                        key.type = 'RIGHTMOUSE'
                        key.value = 'CLICK_DRAG'
                        key.any = False
                        key.alt = False
                        key.ctrl = False
                        key.shift = False
                    elif key.idname == 'view3d.move' and key.map_type == 'MOUSE' :
                        key.type = 'MIDDLEMOUSE'
                        key.value = 'CLICK_DRAG'
                        key.any = False
                        key.alt = False
                        key.ctrl = False
                        key.shift = False

        return {'FINISHED'}

    def AddKeyToKeyMap( keymap , idname ,map_type, type , value , any=False, shift=0, ctrl=0, alt=0, oskey=0, key_modifier='NONE', repeat=False, head=False) :
        for key in keymap.keymap_items:
            if key.idname == idname and key.map_type == map_type and key.type ==type and key.value == value and key.any == any and key.alt == alt and key.ctrl == ctrl and key.shift == shift :
                key.active = True
                break
        else :
            keymap.keymap_items.new(idname = idname, type = type , value = value , any=any, shift=shift, ctrl=ctrl, alt=alt, oskey=oskey, key_modifier=key_modifier, repeat=repeat, head=head)

