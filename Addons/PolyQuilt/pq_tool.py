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

import os
import bpy
from bpy.types import WorkSpaceTool , Panel
from bpy.utils.toolsystem import ToolDef
from .pq_icon import *
from .pq_tool_ui import *


class ToolPolyQuiltBase(WorkSpaceTool):
    pq_main_tool = 'MASTER'
    pq_prop_name = 'master_tool'
    pq_description = 'Master Tool'

    bl_space_type='VIEW_3D'
    bl_context_mode='EDIT_MESH'
    
    @staticmethod
    def tool_keymaps( main_tool , tool_header ) :
        return (
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS'}, {"properties": [("tool_mode", main_tool )]}),            
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True},  {"properties": [('tool_prop' , tool_header + "_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS', "alt": True}, {"properties": [('tool_prop' , tool_header + "_alt" ) ]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_shift_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "shift": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_shift_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "ctrl": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_ctrl_alt" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "shift": True},  {"properties": [('tool_prop' , tool_header + "_os_shift" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "ctrl": True},  {"properties": [('tool_prop' , tool_header + "_os_ctrl" )]}),
            ("mesh.poly_quilt", {"type": 'LEFTMOUSE', "value": 'PRESS' , "oskey": True, "alt": True},  {"properties": [('tool_prop' , tool_header + "_os_alt" )]}),

            ("mesh.poly_quilt_daemon", {"type": 'MOUSEMOVE', "value": 'ANY' }, {"properties": []}),        
        )

    @classmethod
    def draw_settings( cls ,context, layout, tool):
        reg = context.region.type
        if reg == 'UI' :
            draw_settings_ui( context , layout , tool )
        elif reg == 'WINDOW' :
            draw_settings_ui( context , layout , tool )
            draw_sub_tool( layout , cls.pq_prop_name , cls.pq_description , tool )
        elif reg == 'TOOL_HEADER' :
            draw_settings_toolheader( context , layout , tool )


class ToolPolyQuilt(ToolPolyQuiltBase):
    pq_main_tool = 'MASTER'
    pq_prop_name = 'master_tool'
    pq_description = 'Master Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt"
    bl_label = "PolyQuilt"
    bl_description = ( "Lowpoly Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_icon")
    bl_widget = "MESH_GGT_PQ_Preselect"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name )

class ToolPolyQuiltPoly(ToolPolyQuiltBase):
    pq_main_tool = 'LOWPOLY'
    pq_prop_name = 'lowpoly_tool'
    pq_description = 'LowPoly Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_poly"
    bl_label = "PolyQuilt:Poly"
    bl_description = ( "Lowpoly Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_poly_icon")
    bl_widget = "MESH_GGT_PQ_Lowpoly"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name )

class ToolPolyQuiltKnife(ToolPolyQuiltBase):
    pq_main_tool = 'KNIFE'
    pq_prop_name = 'knife_tool'
    pq_description = 'Knife Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_knife"
    bl_label = "PolyQuilt:Knife"
    bl_description = ( "Quick Knife Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_knife_icon")
    bl_widget = "MESH_GGT_PQ_Knife"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name )


class ToolPolyQuiltDelete(ToolPolyQuiltBase):
    pq_main_tool = 'DELETE'
    pq_prop_name = 'delete_tool'
    pq_description = 'Delete Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_delete"
    bl_label = "PolyQuilt:Delete"
    bl_description = ( "Quick Delete Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_delete_icon")
    bl_widget = "MESH_GGT_PQ_Delete"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name )

class ToolPolyQuiltExtrude(ToolPolyQuiltBase):
    pq_main_tool = 'EXTRUDE'
    pq_prop_name = 'extrude_tool'
    pq_description = 'Extrude Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_extrude"
    bl_label = "PolyQuilt:EdgeExtrude"
    bl_description = ( "Edge Extrude Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_extrude_icon")
    bl_widget = "MESH_GGT_PQ_Extrude"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name ) 

class ToolPolyQuiltLoopCut(ToolPolyQuiltBase):
    pq_main_tool = 'LOOPCUT'
    pq_prop_name = 'loopcut_tool'
    pq_description = 'LoopCut Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_loopcut"
    bl_label = "PolyQuilt:LoopCut"
    bl_description = ( "LoopCut Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_loopcut_icon")
    bl_widget = "MESH_GGT_PQ_LoopCut"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name ) 


class ToolPolyQuiltBrush(ToolPolyQuiltBase):
    pq_main_tool = 'BRUSH'
    pq_prop_name = 'brush_tool'
    pq_description = 'Brush Tool'

    # The prefix of the idname should be your add-on name.
    bl_idname = "mesh_tool.poly_quilt_brush"
    bl_label = "PolyQuilt:Brush"
    bl_description = ( "Brush Tool" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "addon.poly_quilt_brush_icon")
    bl_widget = "MESH_GGT_PQ_Brush"
    bl_keymap = ToolPolyQuiltBase.tool_keymaps( pq_main_tool , pq_prop_name ) 


PolyQuiltTools = (
    { 'tool' : ToolPolyQuilt       , 'after' : {"builtin.poly_build"} , 'group' : True },
    { 'tool' : ToolPolyQuiltPoly  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltExtrude  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltLoopCut  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltKnife  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltDelete  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
    { 'tool' : ToolPolyQuiltBrush  , 'after' : {"mesh_tool.poly_quilt"} , 'group' : False },
)
