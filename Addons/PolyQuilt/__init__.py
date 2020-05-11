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
    "version": (1, 3, 0),
    "blender" : (2, 80, 0),
    "location": "View3D > Mesh > PolyQuilt",
    "description": "Lowpoly Tool",
    "warning" : "",
    "wiki_url": "",
    "category": "Mesh",
}

import bpy
from bpy.utils.toolsystem import ToolDef
from .pq_operator import *
from .pq_operator_add_empty_object import *
from .pq_icon import *
from .pq_tool import PolyQuiltTools
from .pq_tool_ui import VIEW3D_PT_tools_polyquilt_options
from .pq_keymap_editor import PQ_OT_DirtyKeymap
from .gizmo_preselect import * 
from .pq_preferences import *
from .translation import pq_translation_dict

classes = (
    MESH_OT_poly_quilt ,
    MESH_OT_poly_quilt_brush_size ,
    MESH_OT_poly_quilt_daemon ,
    PQ_OT_SetupUnityLikeKeymap ,
    PolyQuiltPreferences ,
    PQ_OT_CheckAddonUpdate ,
    PQ_OT_UpdateAddon ,
    VIEW3D_PT_tools_polyquilt_options ,
    PQ_OT_DirtyKeymap ,
) + gizmo_preselect.all_gizmos


def register():
    bpy.app.translations.register(__name__, pq_translation_dict)    
    register_icons()
    register_updater(bl_info)

    # 空メッシュ追加
    bpy.utils.register_class(pq_operator_add_empty_object.OBJECT_OT_add_object)
    bpy.utils.register_manual_map(pq_operator_add_empty_object.add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.append(pq_operator_add_empty_object.add_object_button)

    for cls in classes:
        bpy.utils.register_class(cls)

    for tool in PolyQuiltTools :
        bpy.utils.register_tool(tool['tool'] ,  after = tool['after'] , group = tool['group'] )

def unregister():
    for tool in PolyQuiltTools :
        bpy.utils.unregister_tool(tool['tool'])

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)        

    bpy.utils.unregister_class(pq_operator_add_empty_object.OBJECT_OT_add_object)
    bpy.utils.unregister_manual_map(pq_operator_add_empty_object.add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.remove(pq_operator_add_empty_object.add_object_button)

    unregister_icons()
    bpy.app.translations.unregister(__name__)

if __name__ == "__main__":
    register()
