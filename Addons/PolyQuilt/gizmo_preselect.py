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
import mathutils
from .QMesh import *
from .utils import draw_util
from .pq_operator import MESH_OT_poly_quilt
from .subtools.subtool_default import SubToolDefault
from .subtools.subtool_extr import SubToolExtr
from .subtools.subtool_brush import SubToolBrush

__all__ = ['PQ_Gizmo_Preselect','PQ_GizmoGroup_Preselect']

class PQ_Gizmo_Preselect( bpy.types.Gizmo):
    bl_idname = "MESH_GT_PQ_Preselect"

    def __init__(self) :
        self.bmo = None
        self.currentElement = None
        self.preferences = bpy.context.preferences.addons[__package__].preferences
        self.run_operator = False

    def setup(self):
        self.bmo = None        
        self.currentElement = ElementItem.Empty()

    def init( self , context ) :
        self.bmo = QMesh( context.active_object , self.preferences )
        QSnap.start(context)

    def exit( self , context, cancel) :
        if self.bmo :
            del self.bmo
        self.currentElement = None
        QSnap.exit()

    def test_select(self, context, location):
        self.mouse_pos = mathutils.Vector(location) 
        if context.region == None :
            return -1
        if self.bmo == None :
            self.bmo = QMesh( context.active_object , self.preferences )
        self.bmo.CheckValid( context )
        self.bmo.UpdateView(context)
        QSnap.update(context)

        element = self.bmo.PickElement( location , self.preferences.distance_to_highlight )

        element.set_snap_div( self.preferences.loopcut_division )
        if self.group.subtool != None :
            if self.group.subtool.UpdateHighlight( self , element ) :
                context.area.tag_redraw()

        self.currentElement = element
        return -1

    def draw(self, context):
        if not self.run_operator :
            if self.group.subtool != None :
                self.group.subtool.DrawHighlight( self , self.currentElement )

    def invoke(self, context, event):
        return {'RUNNING_MODAL'}

    def modal( self , context, event, tweak) :
        return {'RUNNING_MODAL'}

    def refresh( self , context ) :
        if self.bmo != None :
            self.bmo.invalid = True
            self.currentElement = ElementItem.Empty()

    def use(self , is_using ) :
        self.run_operator = is_using
        self.currentElement = ElementItem.Empty()


class PQ_GizmoGroup_Preselect(bpy.types.GizmoGroup):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"
    bl_options = {'3D'}    
    bl_region_type = 'WINDOW'
    bl_space_type = 'VIEW_3D'
    __instance = None

    def __init__(self) :
        self.widget = None
        self.subtool = SubToolDefault
        self.alt = False
        PQ_GizmoGroup_Preselect.__instance = self

    def __del__(self) :
        print("----------------------------------------------------------")
        PQ_GizmoGroup_Preselect.__instance = None

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH' :
#            __instance = None
            return False
        # 自分を使っているツールを探す。
        workspace = context.workspace
        for tool in workspace.tools:
            if tool.widget == cls.bl_idname:
                break
        else:
            context.window_manager.gizmo_group_type_unlink_delayed(cls.bl_idname)
#            PQ_GizmoGroup_Preselect.__instance = None
            return False
        context.window.cursor_set( 'DEFAULT' )        
        return True

    @classmethod
    def instance(cls) : 
        return PQ_GizmoGroup_Preselect.__instance

    @classmethod
    def check_modifier_key( cls , shift , ctrl , alt ) :
        instance = cls.instance()
        if instance :
            instance.subtool = SubToolDefault
            if shift :
                instance.subtool = SubToolBrush
            elif ctrl :
                instance.subtool = SubToolExtr
            instance.alt = alt

    def setup(self, context):
        self.preselect = self.gizmos.new(PQ_Gizmo_Preselect.bl_idname)     
        self.preselect.init(context)   

    def refresh( self , context ) :
        self.preselect.refresh(context)

