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
from .subtool_relax import *
from .subtool_brush_size import *
from .subtool_brush_move import *
from .subtool_move import *
from .subtool_fin_slice import *
from .subtool_autoquad import *

class SubToolBrush(SubTool) :
    name = "BrushSubTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op, button)        
        self.currentTarget = currentTarget
        self.LMBEvent = ButtonEventUtil('LEFTMOUSE' , self , SubToolBrush.LMBEventCallback , op , True )
        self.isExit = False

    def is_animated( self , context ) :
        return self.LMBEvent.is_animated()

    @staticmethod
    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)

        if event.type == MBEventType.Release :
            self.isExit = True

        elif event.type == MBEventType.Click :
            if self.currentTarget.isVert or self.currentTarget.isEdge or self.currentTarget.isEmpty:
                if SubToolAutoQuad.Check(self.currentTarget) :
                    self.SetSubTool( SubToolAutoQuad(self.operator,self.currentTarget,self.mouse_pos))
            self.isExit = True
        elif event.type == MBEventType.LongClick :
            self.isExit = True
        elif event.type == MBEventType.LongPressDrag :
            self.SetSubTool( SubToolBrushSize(self.operator,self.currentTarget , self.mouse_pos ) )
        elif event.type == MBEventType.Drag :
            if self.preferences.brush_type == 'SMOOTH' :
                self.SetSubTool( SubToolRelax(self.operator,self.currentTarget , self.mouse_pos ) )
            else :
                self.SetSubTool( SubToolBrushMove(self.operator,self.currentTarget , self.mouse_pos ) )
#            self.SetSubTool( SubToolRelax(self.operator,self.currentTarget , self.mouse_pos ) )

    def OnUpdate( self , context , event ) :
        if self.isExit :
            return 'FINISHED'
        self.LMBEvent.Update(context,event)

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        radius = self.preferences.brush_size * dpm()
        strength = self.preferences.brush_strength        
        draw_util.draw_circle2D( self.LMBEvent.PressPos , radius * strength , color = (1,0.25,0.25,0.5), fill = False , subdivide = 64 , dpi= False )
        draw_util.draw_circle2D( self.LMBEvent.PressPos , radius , color = (1,1,1,1), fill = False , subdivide = 64 , dpi= False )
        if self.LMBEvent.isPresure :
            if self.currentTarget.isNotEmpty :
                self.LMBEvent.Draw( self.currentTarget.coord )
            else:
                self.LMBEvent.Draw( None )

    def OnDraw3D( self , context  ) :
        pass

    def OnEnterSubTool( self ,context,subTool ):
        self.currentTarget = ElementItem.Empty()
        self.LMBEvent.Reset(context)

    def OnExitSubTool( self ,context,subTool ):
        self.currentTarget = ElementItem.Empty() # self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight )

    def OnExit( self ) :
        pass
