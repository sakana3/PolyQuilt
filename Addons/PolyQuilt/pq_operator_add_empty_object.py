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
import bpy
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a new Empty Mesh Object"""
    bl_idname = "mesh.add_empty_mesh_object"
    bl_label = "Add Empty Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context , event):
        mesh = bpy.data.meshes.new(name="New Empty Mesh")
        object_data_add(context, mesh, operator=self)
        return {'FINISHED'}

def add_object_button(self, context):
    self.layout.operator(
        OBJECT_OT_add_object.bl_idname,
        text="Empty Mesh Object",
        icon='EMPTY_DATA')

# This allows you to right click on a button and link to the manual
def add_object_manual_map():
    url_manual_prefix = "https://docs.blender.org/manual/en/dev/"
    url_manual_mapping = (
        ("bpy.ops.mesh.add_object", "editors/3dview/object"),
    )
    return url_manual_prefix, url_manual_mapping

