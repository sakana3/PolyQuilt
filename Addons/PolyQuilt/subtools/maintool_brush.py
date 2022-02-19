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
import math
import mathutils
import bmesh
import bpy_extras
import collections
import copy
from ..utils import pqutil
from ..utils import draw_util
from ..utils.dpi import *
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *
from .subtool_brush_relax import *
from .subtool_brush_size import *
from .subtool_brush_move import *
from .subtool_brush_delete import *
from .subtool_move import *
from .subtool_autoquad import *
from ..utils.dpi import *


class MainToolBrush(MainTool) :
    name = "Brush"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button)        
        brush_tbl = {
            'SMOOTH' : SubToolBrushRelax ,
            'MOVE' : SubToolBrushMove ,
            'DELETE' : SubToolBrushDelete ,
        }

        brush = op.brush_type
        self.brush_type = brush_tbl[ brush ]

        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [SubToolAutoQuad] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [SubToolBrushSize] ,
            MBEventType.Drag            : [self.brush_type] ,
        }

    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)
        if event.type in self.callback.keys() :
            tools = [ t( event.event , self) for t in self.callback[event.type] if t.Check( self , self.currentTarget ) ]
            if tools :
                self.SetSubTool( tools )
            self.isExit = True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if SubToolAutoQuad.Check( None , element ) :
            Draw = [SubToolAutoQuad.DrawHighlight(gizmo,element)]
        else :
            Draw = []

        radius = display.dot( gizmo.preferences.brush_size )
        strength = gizmo.preferences.brush_strength
        mode = gizmo.keyitem.properties.brush_type

        if gizmo.keyitem.properties.is_property_set("brush_type") :
            mode = gizmo.keyitem.properties.brush_type
        else :
            from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
            tool = ToolSelectPanelHelper.tool_active_from_context(bpy.context)
            props = tool.operator_properties( gizmo.tool.pq_operator )            
            mode =props.brush_type

        if mode == 'MOVE' :
            Draw.append( SubToolBrushMove.DrawHighlight( gizmo , element ) )
        elif mode == 'DELETE' :
            Draw.append( SubToolBrushDelete.DrawHighlight( gizmo , element ) )
        else :
            Draw.append( SubToolBrushRelax.DrawHighlight( gizmo , element ) )

        return Draw

    @classmethod
    def UpdateHighlight( cls , gizmo , element ) :
        return True

    def OnDraw( self , context  ) :
        self.brush_type.Draw( self.preferences , self.mouse_pos )

        self.LMBEvent.Draw( self.mouse_pos )

        if self.LMBEvent.is_hold :
            draw_util.DrawFont( "Strenght = " + '{:.0f}'.format(self.preferences.brush_strength * 100) , 10 , self.mouse_pos , (0,0) )
            draw_util.DrawFont( "Radius = " + '{:.0f}'.format( display.dot(self.preferences.brush_size ) ) , 10 , self.mouse_pos , (0,-8) )

    def OnDraw3D( self , context  ) :
        if not self.LMBEvent.presureComplite :        
            if SubToolAutoQuad.Check( self , self.currentTarget ) :
                draw = SubToolAutoQuad.DrawHighlight(self,self.currentTarget)
                if draw :
                    draw()

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'

    @classmethod
    def recive_event( cls , gizmo , context , event ) :
        if any( [ event.shift , event.ctrl , event.alt,  event.oskey ] ) :
            if event.type == 'WHEELUPMOUSE' :
                cls.change_brush_size( gizmo.preferences , context ,-50 , 0 )
                return True

            if event.type == 'WHEELDOWNMOUSE' :
                cls.change_brush_size( gizmo.preferences , context , 50 , 0 )
                return True

        return False

    @classmethod
    def change_brush_size( cls , preferences , context , brush_size_value , brush_strong_value ):
        if context.area.type == 'VIEW_3D' :
            a = (preferences.brush_size * preferences.brush_size) / 40000.0 + 0.1
            preferences.brush_size = preferences.brush_size + brush_size_value * a       
            strength = min( max( 0 , preferences.brush_strength + brush_strong_value ) , 1 )
            preferences.brush_strength = strength
            context.area.tag_redraw()
