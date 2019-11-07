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
    instance = None
    subtool = None
    alt = False

    def __init__(self) :
        self.bmo = None
        self.currentElement = None
        self.preferences = bpy.context.preferences.addons[__package__].preferences
        self.run_operator = False
        self.DrawHighlight = None
        PQ_Gizmo_Preselect.instance = self
        PQ_Gizmo_Preselect.subtool = SubToolDefault
        PQ_Gizmo_Preselect.alt = False

    def __del__(self) :
        PQ_Gizmo_Preselect.instance = None

    def setup(self):
        self.bmo = None        
        self.currentElement = ElementItem.Empty()

    def init( self , context ) :
        self.bmo = QMesh( context.active_object , self.preferences )
        QSnap.start(context)

    def exit( self , context, cancel) :
        print("Exit")
        if self.bmo :
            del self.bmo
        self.currentElement = None
        QSnap.exit()
        PQ_Gizmo_Preselect.instance = None
        PQ_Gizmo_Preselect.subtool = None

    def test_select(self, context, location):
        if self.currentElement == None :
            self.currentElement = ElementItem.Empty()

        PQ_Gizmo_Preselect.instance = self
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
        if PQ_Gizmo_Preselect.subtool != None :
            if PQ_Gizmo_Preselect.subtool.UpdateHighlight( self , element ) :
                context.area.tag_redraw()

        self.currentElement = element

        self.DrawHighlight = PQ_Gizmo_Preselect.subtool.DrawHighlight( self , self.currentElement )

        return -1

    def draw(self, context):
        if self.DrawHighlight != None :
            self.DrawHighlight()
        return 
        if not self.run_operator and self.currentElement != None :
            if PQ_Gizmo_Preselect.subtool != None :
                PQ_Gizmo_Preselect.subtool.DrawHighlight( self , self.currentElement )

    def invoke(self, context, event):
        return {'RUNNING_MODAL'}

    def modal( self , context, event, tweak) :
        return {'RUNNING_MODAL'}

    def refresh( self , context ) :
        if self.bmo != None :
            self.bmo.invalid = True
            self.currentElement = ElementItem.Empty()
            self.DrawHighlight = None

    def use(self , is_using ) :
        self.run_operator = is_using
        self.currentElement = ElementItem.Empty()
        self.DrawHighlight = None

    @classmethod
    def check_modifier_key( cls , context , shift , ctrl , alt ) :
        subtool = SubToolDefault
        if shift :
            subtool = SubToolBrush
        elif ctrl :
            subtool = SubToolExtr
        if PQ_Gizmo_Preselect.subtool != subtool :
            PQ_Gizmo_Preselect.subtool = subtool
            context.area.tag_redraw()            
        PQ_Gizmo_Preselect.alt = alt

class PQ_GizmoGroup_Preselect(bpy.types.GizmoGroup):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"
    bl_options = {'3D'}    
    bl_region_type = 'WINDOW'
    bl_space_type = 'VIEW_3D'

    def __init__(self) :
        self.widget = None

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH' :
            return False
        # 自分を使っているツールを探す。
        workspace = context.workspace
        for tool in workspace.tools:
            if tool.widget == cls.bl_idname:
                break
        else:
            context.window_manager.gizmo_group_type_unlink_delayed(cls.bl_idname)
            return False
        context.window.cursor_set( 'DEFAULT' )        
        return True

    def setup(self, context):
        self.preselect = self.gizmos.new(PQ_Gizmo_Preselect.bl_idname)     
        self.preselect.init(context)   

    def refresh( self , context ) :
        self.preselect.refresh(context)

