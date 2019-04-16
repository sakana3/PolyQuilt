import bpy
from bpy.types import WorkSpaceTool

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
        props = tool.operator_properties("mesh.poly_quilt")
#       layout.label(text="Make",text_ctxt="Make", translate=True, icon='NORMALS_FACE')
        layout.prop(props, "geometry_type" , text = "Make", toggle = True , expand = True  )
        layout.prop(props, "plane_pivot" , text = "Pivot", toggle = True )
#       layout.prop(props, "backface" , text = "Use backface", icon = 'NORMALS_FACE')


