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
    "version": (0, 0,1),
    "blender" : (2, 80, 0),
    "location": "View3D > Mesh > PolyQuilt",
    "description": "Lowpoly Tool",
    "warning" : "",
    "wiki_url": "",
    "category": "Mesh",
}

import bpy
from .pq_operator import MESH_OT_poly_quilt
from .pq_tool import ToolPolyQuilt
from .gizmo_preselect import PQ_GizmoGroup_Preselect , PQ_Gizmo_Preselect
from .pq_preferences import *

classes = (
    PQ_Gizmo_Preselect ,
    PQ_GizmoGroup_Preselect ,
    MESH_OT_poly_quilt ,
    PQ_OT_SetupLeftMouseDownToClick ,
    PolyQuiltPreferences ,
    PQ_OT_CheckAddonUpdate ,
    PQ_OT_UpdateAddon
)

def register():
    register_updater(bl_info)

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.utils.register_tool(ToolPolyQuilt , after={"builtin.poly_build"} )

def unregister():
    bpy.utils.unregister_tool(ToolPolyQuilt)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

