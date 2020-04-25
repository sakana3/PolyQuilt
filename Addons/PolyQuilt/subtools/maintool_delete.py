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

class MainToolDelete(MainTool) :
    name = "DeleteTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = True )        

    @staticmethod
    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)

        if event.type == MBEventType.Release :
            self.isExit = True
        elif event.type == MBEventType.Click or event.type == MBEventType.LongClick:
            self.RemoveElement(self.currentTarget)
            self.currentTarget = ElementItem.Empty()
        elif event.type == MBEventType.Drag or event.type == MBEventType.LongPressDrag :
            self.currentTarget = ElementItem.Empty()

    def RemoveElement( self , element ) :
        if element.isNotEmpty :
            if element.isVert :
                self.bmo.dissolve_vert( element.element , False , False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle  )
            elif element.isEdge :
                self.bmo.dissolve_edge( element.element , use_verts = False , use_face_split = False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle )
            elif element.isFace :
                self.bmo.Remove( element.element )
            self.bmo.UpdateMesh()

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element != None and gizmo.bmo != None :
            return element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.delete_color , gizmo.preferences , False , edge_pivot = False )
        return None

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.currentTarget.isNotEmpty :
            self.currentTarget.Draw( self.bmo.obj , self.preferences.delete_color  , self.preferences , edge_pivot = False )

    def OnExit( self ) :
        pass

    @classmethod
    def GetCursor(cls) :
        return 'ERASER'

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight )        
        return element
