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
from .subtools import *

__all__ = ['PQ_Gizmo_Preselect','PQ_GizmoGroup_Preselect','PQ_GizmoGroup_Lowpoly']


def is_running_poly_quilt_operator():
    operators = bpy.context.window_manager.operators
    op = operators[-1] if operators else None
    if op != None and "poly_quilt" in op.bl_idname :
        return False
    return False

class PQ_Gizmo_Preselect( bpy.types.Gizmo):
    bl_idname = "MESH_GT_PQ_Preselect"

    def __init__(self) :
        self.bmo = None
        self.currentElement = None
        self.preferences = bpy.context.preferences.addons[__package__].preferences
        self.DrawHighlight = None
        self.region = None
        self.subtool = None
        self.tool_table = [None,None,None,None]

    def __del__(self) :
        pass

    def setup(self):
        self.bmo = None        
        self.currentElement = ElementItem.Empty()

    def init( self , context , tools ) :
        self.tool_table = [ maintools[t] for t in tools ]
        self.subtool = self.tool_table[0]
        self.region = context.region_data
        self.bmo = QMesh( context.active_object , self.preferences )

    def exit( self , context, cancel) :
        pass

    def test_select(self, context, location):
        if PQ_GizmoGroup_Base.running_polyquilt :
            self.DrawHighlight = None
            return -1
        
        if self.currentElement == None :
            self.currentElement = ElementItem.Empty()

        self.mouse_pos = mathutils.Vector(location) 
        if context.region == self.region :
            return -1
        if self.bmo == None :
            self.bmo = QMesh( context.active_object , self.preferences )
        self.bmo.CheckValid( context )
        self.bmo.UpdateView(context)
        QSnap.update(context)

        element = self.bmo.PickElement( location , self.preferences.distance_to_highlight )
        element.set_snap_div( self.preferences.loopcut_division )
        if self.subtool != None :
            if self.subtool.UpdateHighlight( self , element ) :
                context.area.tag_redraw()

        self.currentElement = element

        self.DrawHighlight = self.subtool.DrawHighlight( self , self.currentElement )
        return -1

    def draw(self, context):
        if PQ_GizmoGroup_Base.running_polyquilt  :
            self.DrawHighlight = None

        if self.DrawHighlight != None :
            self.DrawHighlight()

    def refresh( self , context ) :
        if self.bmo != None :
            self.bmo.invalid = True
            self.currentElement = ElementItem.Empty()
            self.DrawHighlight = None

    def check_modifier_key( self , shift , ctrl , alt ) :
        subtool = self.tool_table[0]
        if shift and self.tool_table[1] :
            subtool = self.tool_table[1]
        elif ctrl and self.tool_table[2] and False :
            subtool = self.tool_table[2]

        PQ_GizmoGroup_Base.set_cursor( subtool.GetCursor() )

        if self.subtool != subtool :
            self.subtool = subtool
            bpy.context.area.tag_redraw()

class PQ_GizmoGroup_Base(bpy.types.GizmoGroup):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"
    bl_options = {'3D'}    
    bl_region_type = 'WINDOW'
    bl_space_type = 'VIEW_3D'
 
    child_gizmos = []
    cursor = 'DEFAULT'

    running_polyquilt = False

    def __init__(self) :
        self.gizmo = None

    def __del__(self) :
        if hasattr( self , "gizmo" ) :               
            PQ_GizmoGroup_Base.child_gizmos.remove( self.gizmo )
        if not PQ_GizmoGroup_Base.child_gizmos :
            QSnap.remove_ref()

    def tool_table( self ) :
        return ['MASTER','BRUSH' ,'EXTRUDE','MASTER']

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
        if not PQ_GizmoGroup_Base.running_polyquilt :
            context.window.cursor_set( cls.cursor )        
        return True

    def setup(self, context):
        QSnap.add_ref(context)
        self.gizmo = self.gizmos.new(PQ_Gizmo_Preselect.bl_idname)
        self.gizmo.init(context , self.tool_table() )
        PQ_GizmoGroup_Base.child_gizmos.append(self.gizmo)

    def refresh( self , context ) :
        if hasattr( self , "gizmo" ) :        
            self.gizmo.refresh(context)

    @classmethod
    def set_cursor(cls, cursor ):
        cls.cursor = cursor

    @classmethod
    def get_gizmo(cls, region ):
        gizmo = [ i for i in cls.child_gizmos if i.region == region ]
        if gizmo :
            return gizmo[0]
        return None

    @classmethod
    def check_modifier_key( cls , shift , ctrl , alt ) :
        for gizmo in cls.child_gizmos :
            gizmo.check_modifier_key( shift , ctrl , alt )


class PQ_GizmoGroup_Preselect(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"

    def tool_table( self ) :
        return ['MASTER','BRUSH' ,'EXTRUDE','MASTER']

class PQ_GizmoGroup_Lowpoly(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Lowpoly"
    bl_label = "PolyQuilt Lowpoly Gizmo"

    def tool_table( self ) :
        return ['LOWPOLY','BRUSH','LOWPOLY','LOWPOLY']

class PQ_GizmoGroup_Knife(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Knife"
    bl_label = "PolyQuilt Knife Gizmo"

    def tool_table( self ) :
        return ['KNIFE','BRUSH','KNIFE','KNIFE']

class PQ_GizmoGroup_Delete(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Delete"
    bl_label = "PolyQuilt Delete Gizmo"

    def tool_table( self ) :
        return ['DELETE','BRUSH','DELETE','DELETE']

all_gizmos = ( PQ_Gizmo_Preselect , PQ_GizmoGroup_Preselect , PQ_GizmoGroup_Lowpoly , PQ_GizmoGroup_Knife , PQ_GizmoGroup_Delete )

