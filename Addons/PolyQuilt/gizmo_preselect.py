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
from .QMesh import *
from . import draw_util
from . import handleutility
from .pq_operator import MESH_OT_poly_quilt

__all__ = ['PQ_Gizmo_Preselect','PQ_GizmoGroup_Preselect']

class PQ_Gizmo_Preselect( bpy.types.Gizmo):
    bl_idname = "MESH_GT_PQ_Preselect"
    instance = None

    def __init__(self) :
        self.bo = None
        self.currentElement = None
        self.preferences = bpy.context.preferences.addons[__package__].preferences

    def setup(self):
        self.bo = None        
        self.currentElement = ElementItem.Empty()

    def init( self , context ) :
        self.bo = QMesh( context.active_object , self.preferences )
        self.bo.UpdateView( context )

    def exit( self , context, cancel) :
        if self.bo :
            del self.bo
        self.currentElement = None
        PQ_Gizmo_Preselect.instance = None


    def test_select(self, context, location):
        PQ_Gizmo_Preselect.instance = self        
        if self.bo == None :
            self.bo = QMesh( context.active_object , self.preferences )
        self.bo.CheckValid()
        self.bo.UpdateView( context )

        element = self.bo.PickElement( location , self.preferences.distance_to_highlight )
        if self.currentElement.element != element.element :
            context.area.tag_redraw()
        elif self.currentElement.isEdge :
            if self.currentElement.coord != element.coord :
                context.area.tag_redraw()
        self.currentElement = element
        return -1

    def draw(self, context):
        if self.currentElement != None and self.bo != None :
            self.currentElement.Draw( self.bo.obj , self.preferences.highlight_color , self.preferences )

    def refresh( self , context ) :
        if self.bo != None :
            self.bo.CheckValid()            
            self.bo.UpdateMesh()  
            self.currentElement = ElementItem.Empty()

    def use(self) :
        self.currentElement = ElementItem.Empty()


class PQ_GizmoGroup_Preselect(bpy.types.GizmoGroup):
    bl_idname = "MESH_GGT_PQ_Preselect"
    bl_label = "PolyQuilt Preselect Gizmo"
    bl_options = {'3D'}    
    bl_region_type = 'WINDOW'
    bl_space_type = 'VIEW_3D'

    def __init__(self) :
        self.widget = None

    def __del__(self):
        pass

    @classmethod
    def poll(cls, context):
        # 自分を使っているツールを探す。
        workspace = context.workspace
        mode = workspace.tools_mode
        for tool in workspace.tools:
            if (tool.widget == cls.bl_idname) and (tool.mode == mode):
                break
        else:
            context.window_manager.gizmo_group_type_unlink_delayed(cls.bl_idname)
            return False
        context.window.cursor_set( 'DEFAULT' )        
        return True

    def setup(self, context):
        self.widget = self.gizmos.new(PQ_Gizmo_Preselect.bl_idname)     
        self.widget.init(context)   
#       self.gizmos.new("GIZMO_GT_mesh_preselect_elem_3d")  

        for op in context.window_manager.operators :
            if isinstance(op, MESH_OT_poly_quilt ):
                self.pq = op
                break
        else :
            self.pq = None

    def refresh( self , context ) :
        self.widget.refresh(context)
