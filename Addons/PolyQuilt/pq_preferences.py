import os
import bpy
from bpy.props import (
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from .utils.addon_updator import (
    AddonUpdatorManager,
    AddonUpdatorConfig,
    get_separator,
)
from bpy.types import AddonPreferences

__all__ = [
    "PolyQuiltPreferences" ,
    "PQ_OT_SetupLeftMouseDownToClick",
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
        updater = AddonUpdatorManager.get_instance()
        updater.check_update_candidate()

        return {'FINISHED'}

class PQ_OT_UpdateAddon(bpy.types.Operator):
    bl_idname = "mesh.pq_ot_update_addon"
    bl_label = "Update"
    bl_description = "Update Add-on"
    bl_options = {'REGISTER', 'UNDO'}

    branch_name = StringProperty(
        name="Branch Name",
        description="Branch name to update",
        default="",
    )

    def execute(self, _):
        updater = AddonUpdatorManager.get_instance()
        updater.update(self.branch_name)

        return {'FINISHED'}



def register_updater(bl_info):
    config = AddonUpdatorConfig()
    config.owner = "sakana3"
    config.repository = "PolyQuilt"
    config.current_addon_path = os.path.dirname(os.path.realpath(__file__))
    config.branches = ["master", "develop"]
    config.addon_directory = \
        config.current_addon_path[
            :config.current_addon_path.rfind(get_separator())]
    config.min_release_version = bl_info["version"]
    config.target_addon_path = "src/magic_uv"
    updater = AddonUpdatorManager.get_instance()
    updater.init(bl_info, config)

def get_update_candidate_branches(_, __):
    manager = AddonUpdatorManager.get_instance()
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
        default= 1.5,
        min=0.5,
        max=8.0)

    highlight_line_width : FloatProperty(
        name="Highlight Line Width",
        description="Highlight Line Width",
        default=3.0,
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
        default=0.5,
        min=0.3,
        max=2.0)             


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

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Tool settings:", icon = 'TOOL_SETTINGS')
        box = row.box()
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

        row = layout.row()
        row.column().label(text="Color settings:" , icon = 'COLOR')
        box = row.box()
        box.row().prop(self, "highlight_color" , text = "Highlight")
        box.row().prop(self, "makepoly_color" , text = "Make Polygon")
        box.row().prop(self, "split_color" , text = "Split" )
        box.row().prop(self, "delete_color" , text = "Delete")

        layout.prop( self, "extra_setting_expanded", text="Extra Settings",
            icon='DISCLOSURE_TRI_DOWN' if self.extra_setting_expanded
            else 'DISCLOSURE_TRI_RIGHT')
        if self.extra_setting_expanded : 
            layout.row().prop(self, "is_debug" , text = "Debug")

            self.draw_updater_ui()            
            col = layout.column()
            col.scale_y = 2            
            col.operator(PQ_OT_SetupLeftMouseDownToClick.bl_idname,
                        text="Setup metaseq like Keymap(experimental)",
                        icon='MONKEY')

    def draw_updater_ui(self):
        layout = self.layout
        updater = AddonUpdatorManager.get_instance()

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




class PQ_OT_SetupLeftMouseDownToClick(bpy.types.Operator) :
    bl_idname = "addon.setup_leftmouse_down_to_click"
    bl_label = "SetupLeftMouse"
    bl_description = "Setup Left Mouse Click"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for keymap in context.window_manager.keyconfigs.user.keymaps:                        
            if keymap.space_type == 'EMPTY':
                for key in keymap.keymap_items:
                    if True not in [ key.any , key.alt , key.ctrl ,key.shift ]:
                        if key.map_type == 'MOUSE' and key.type == 'RIGHTMOUSE' :
                            key.value = 'CLICK'
        for keymap in context.window_manager.keyconfigs.user.keymaps:                        
            if keymap.space_type == 'VIEW_3D':
                for key in keymap.keymap_items:
                    if True not in [ key.any , key.alt , key.ctrl ,key.shift ]:
                        if key.idname == 'view3d.rotate' and key.map_type == 'MOUSE' :
                            key.type == 'RIGHTMOUSE'
                            key.value = 'CLICK_DRAG'
                        elif key.idname == 'view3d.move' and key.map_type == 'MOUSE' :
                            key.type == 'MIDDLEMOUSE'
                            key.value = 'CLICK_DRAG'

        return {'FINISHED'}