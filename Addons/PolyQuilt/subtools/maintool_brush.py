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
from .subtool_makepoly import *
from .subtool_knife import *
from .subtool_edge_slice import *
from .subtool_edgeloop_cut import *
from .subtool_edge_extrude import *
from .subtool_brush_relax import *
from .subtool_brush_size import *
from .subtool_brush_move import *
from .subtool_brush_delete import *
from .subtool_move import *
from .subtool_fin_slice import *
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
        brush_type = brush_tbl[ brush ]

        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [SubToolAutoQuad] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [SubToolBrushSize] ,
            MBEventType.Drag            : [brush_type] ,
        }

    @staticmethod
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
            drawAutoQuad = SubToolAutoQuad.DrawHighlight(gizmo,element)
        else :
            drawAutoQuad = None

        def Draw() :
            radius = gizmo.preferences.brush_size * dpm()
            strength = gizmo.preferences.brush_strength  
            if drawAutoQuad :
                drawAutoQuad()
            with draw_util.push_pop_projection2D() :
                draw_util.draw_circle2D( gizmo.mouse_pos , radius * strength , color = (1,0.25,0.25,0.25), fill = False , subdivide = 64 , dpi= False )
                draw_util.draw_circle2D( gizmo.mouse_pos , radius , color = (1,1,1,0.5), fill = False , subdivide = 64 , dpi= False )
        return Draw

    @classmethod
    def UpdateHighlight( cls , gizmo , element ) :
        return True

    def OnDraw( self , context  ) :
        radius = self.preferences.brush_size * dpm()
        strength = self.preferences.brush_strength          
        draw_util.draw_circle2D( self.mouse_pos , radius * strength , color = (1,0.25,0.25,0.25), fill = False , subdivide = 64 , dpi= False )
        draw_util.draw_circle2D( self.mouse_pos , radius , color = (1,1,1,0.5), fill = False , subdivide = 64 , dpi= False )        

        self.LMBEvent.Draw( self.mouse_pos )

        if self.LMBEvent.is_hold :
            draw_util.DrawFont( "Strenght = " + '{:.0f}'.format(self.preferences.brush_strength * 100) , 10 , self.mouse_pos , (0,0) )
            draw_util.DrawFont( "Radius = " + '{:.0f}'.format(self.preferences.brush_size * dpm() ) , 10 , self.mouse_pos , (0,-8) )

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

            if event.type == 'WHEELDOWNMOUSE' :
                cls.change_brush_size( gizmo.preferences , context , 50 , 0 )

        return {'PASS_THROUGH'}

    @classmethod
    def change_brush_size( cls , preferences , context , brush_size_value , brush_strong_value ):
        if context.area.type == 'VIEW_3D' :
            a = (preferences.brush_size * preferences.brush_size) / 40000.0 + 0.1
            preferences.brush_size = preferences.brush_size + brush_size_value * a       
            strength = min( max( 0 , preferences.brush_strength + brush_strong_value ) , 1 )
            preferences.brush_strength = strength
            context.area.tag_redraw()

class MainToolBrushDelete(MainToolBrush) :
    name = "BrushDeleteSubTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button)        
        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [SubToolBrushSize] ,
            MBEventType.Drag            : [SubToolBrushDelete] ,
        }

    def OnDraw3D( self , context  ) :
        pass

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return SubToolBrushDelete.DrawHighlight(gizmo,element)

class MainToolBrushRelax(MainToolBrush) :
    name = "BrushRelaxSubTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button)        
        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [SubToolBrushSize] ,
            MBEventType.Drag            : [SubToolBrushRelax] ,
        }

    def OnDraw3D( self , context  ) :
        pass

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return SubToolBrushRelax.DrawHighlight(gizmo,element)

class MainToolBrushMove(MainToolBrush) :
    name = "BrushMoveSubTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button)        
        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [SubToolBrushSize] ,
            MBEventType.Drag            : [SubToolBrushMove] ,
        }

    def OnDraw3D( self , context  ) :
        pass

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return SubToolBrushMove.DrawHighlight(gizmo,element)
