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

bl_info = {
    "name" : "PolyQuilt",
    "author" : "Sakana3",
    "version": (0, 9,0),
    "blender" : (2, 80, 0),
    "location": "View3D > Mesh > PolyQuilt",
    "description": "Lowpoly Tool",
    "warning" : "",
    "wiki_url": "",
    "category": "Mesh",
}

import bpy
from bpy.utils.toolsystem import ToolDef
from .pq_operator import MESH_OT_poly_quilt
from .pq_icon import *
from .pq_tool import ToolPolyQuilt , tool_poly_quilt , register_keymaps , unregister_keymaps
from .gizmo_preselect import PQ_GizmoGroup_Preselect , PQ_Gizmo_Preselect
from .pq_preferences import *
from .translation import pq_translation_dict


classes = (
    PQ_Gizmo_Preselect ,
    PQ_GizmoGroup_Preselect ,
    MESH_OT_poly_quilt ,
    PQ_OT_SetupUnityLikeKeymap ,
    PolyQuiltPreferences ,
    PQ_OT_CheckAddonUpdate ,
    PQ_OT_UpdateAddon
)

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



def register():
    bpy.app.translations.register(__name__, pq_translation_dict)    
    register_icons()
    register_updater(bl_info)

    for cls in classes:
        bpy.utils.register_class(cls)

#   bpy.utils.register_tool(ToolPolyQuilt , after={"builtin.poly_build"} )
    register_tools()
    register_keymaps()

def unregister():
#   bpy.utils.unregister_tool(ToolPolyQuilt)
    unregister_keymaps()
    unregister_tools()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    unregister_icons()
    bpy.app.translations.unregister(__name__)

if __name__ == "__main__":
    register()
