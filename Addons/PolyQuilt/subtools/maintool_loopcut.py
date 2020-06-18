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
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *
from .subtool_makepoly import *
from .subtool_knife import *
from .subtool_edge_slice import *
from .subtool_edgeloop_cut import *
from .subtool_edge_extrude import *
from .subtool_vert_extrude import *
from .subtool_move import *
from .subtool_fin_slice import *
from .subtool_polypen import *

class MainToolLoopCut(MainTool) :
    name = "Loop Cut"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = True )        

    @staticmethod
    def LMBEventCallback(self , event ):
        last_mouse_pos = event.mouse_pos
        self.debugStr = str(event.type)

        if event.type == MBEventType.Release :
            self.isExit = True

        elif event.type == MBEventType.Down :
            if SubToolEdgeSlice.Check( self , self.currentTarget ):
                self.SetSubTool( SubToolEdgeSlice(self.operator,self.currentTarget, self.mouse_pos ) )

    @classmethod
    def DrawHighlight( cls , gizmo , target ) :
        if SubToolEdgeSlice.Check( None , target ) :
            return SubToolEdgeSlice.DrawHighlight( gizmo , target )
        return None

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight, edgering = False, elements = ['EDGE'] )        
        element.set_snap_div( preferences.loopcut_division )
        return element

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        self.currentTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

    def OnExit( self ) :
        pass
