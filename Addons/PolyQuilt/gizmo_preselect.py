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
import time
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
        self.tool_header = 'master_tool'

    def __del__(self) :
        pass

    def setup(self):
        self.bmo = None        
        self.currentElement = ElementItem.Empty()

    def init( self , context , main_tool , tool_header ) :
        self.tool_header = tool_header
        self.maintool = maintools[main_tool]
        self.subtool = self.maintool
        self.region = context.region_data
        self.bmo = QMesh( context.active_object , self.preferences )
        if self.subtool :
            context.window.cursor_set( self.subtool.GetCursor() )

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


        if self.subtool != None :
            element = self.subtool.pick_element( self.bmo , location , self.preferences )
            element.set_snap_div( self.preferences.loopcut_division )
            if self.subtool.UpdateHighlight( self , element ) :
                context.area.tag_redraw()
        else :
            element = ElementItem.Empty()

        self.currentElement = element

        if self.subtool != None :
            self.DrawHighlight = self.subtool.DrawHighlight( self , self.currentElement )
        else :
            self.DrawHighlight = None

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

    def recive_event( self , context , event ) :
        subtool = self.maintool

        modifier = ""
        if event.oskey :
            modifier = modifier +  '_os'
        if event.shift :
            modifier = modifier +  '_shift'
        if event.ctrl :
            modifier = modifier +  '_ctrl'
        if event.alt :
            modifier = modifier +  '_alt'

        if hasattr( self.preferences, self.tool_header + modifier) :
            subtool = maintools[ getattr(self.preferences, self.tool_header + modifier) ]

        if self.subtool != subtool :
            self.subtool = subtool
            bpy.context.area.tag_redraw()
        if self.subtool :
            PQ_GizmoGroup_Base.set_cursor( subtool.GetCursor() )
        else :
            PQ_GizmoGroup_Base.set_cursor( )

        if context.region_data == self.region and self.subtool:
            self.subtool.recive_event( self , context , event )

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
        maintool , tool_header = self.tool_table()
        self.gizmo.init(context , maintool , tool_header )
        PQ_GizmoGroup_Base.child_gizmos.append(self.gizmo)

    def refresh( self , context ) :
        if hasattr( self , "gizmo" ) :        
            self.gizmo.refresh(context)

    @classmethod
    def set_cursor(cls, cursor = 'DEFAULT' ):
        cls.cursor = cursor

    @classmethod
    def get_gizmo(cls, region ):
        gizmo = [ i for i in cls.child_gizmos if i.region == region ]
        if gizmo :
            return gizmo[0]
        return None

    @classmethod
    def recive_event( cls , context , event ) :
        for gizmo in cls.child_gizmos :
            gizmo.recive_event( context , event)

class PQ_GizmoGroup_Preselect(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"

    def tool_table( self ) :
        return 'MASTER','master_tool'

class PQ_GizmoGroup_Lowpoly(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Lowpoly"
    bl_label = "PolyQuilt Lowpoly Gizmo"

    def tool_table( self ) :
        return 'LOWPOLY','lowpoly_tool'

class PQ_GizmoGroup_Knife(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Knife"
    bl_label = "PolyQuilt Knife Gizmo"

    def tool_table( self ) :
        return 'KNIFE','knife_tool'

class PQ_GizmoGroup_Delete(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Delete"
    bl_label = "PolyQuilt Delete Gizmo"

    def tool_table( self ) :
        return 'DELETE','delete_tool'

class PQ_GizmoGroup_Extrude(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Extrude"
    bl_label = "PolyQuilt Extrude Gizmo"

    def tool_table( self ) :
        return 'EXTRUDE','extrude_tool'

class PQ_GizmoGroup_LoopCut(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_LoopCut"
    bl_label = "PolyQuilt LoopCut Gizmo"

    def tool_table( self ) :
        return 'LOOPCUT','loopcut_tool'

class PQ_GizmoGroup_Brush(PQ_GizmoGroup_Base):
    bl_idname = "MESH_GGT_PQ_Brush"
    bl_label = "PolyQuilt Brush Gizmo"

    def tool_table( self ) :
        return 'BRUSH','brush_tool'

all_gizmos = ( PQ_Gizmo_Preselect , PQ_GizmoGroup_Preselect , PQ_GizmoGroup_Lowpoly , PQ_GizmoGroup_Knife , PQ_GizmoGroup_Delete, PQ_GizmoGroup_Extrude, PQ_GizmoGroup_LoopCut, PQ_GizmoGroup_Brush )


# ursor (enum in ['DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER'], (optional)) – cursor

