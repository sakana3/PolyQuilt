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
from .subtool_knife import *
from .subtool_edge_slice import *
from .subtool_edgeloop_cut import *
from .subtool_delete import *

class MainToolEdgeLoopDissolve(MainTool) :
    name = "Dissolve Loop"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = True )        
        self.currentTarget = currentTarget
        self.removes , v = self.bmo.calc_edge_loop( self.currentTarget.element )   

    @staticmethod
    def Check( root , target ) :
        return target.isEdge

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ['EDGE']  )
            if self.currentTarget.isEdge :
                self.removes , v = self.bmo.calc_edge_loop( self.currentTarget.element )        
            else :
                self.removes = []
        elif event.type == self.buttonType : 
            if event.value == 'RELEASE' :
                if self.removes :
                    self.bmo.dissolve_edges( self.removes , use_verts = False , use_face_split = False , dissolve_vert_angle=0 )
                    self.bmo.UpdateMesh()                    
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'        

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        e , v = gizmo.bmo.calc_edge_loop( element.element )        
        alpha = gizmo.preferences.highlight_face_alpha
        vertex_size = gizmo.preferences.highlight_vertex_size        
        width = gizmo.preferences.highlight_line_width        
        color = gizmo.preferences.delete_color         
        return draw_util.drawElementsHilight3DFunc( gizmo.bmo.obj , e , vertex_size , width , alpha , color )        

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.currentTarget.isEdge :        
            alpha = self.preferences.highlight_face_alpha
            vertex_size = self.preferences.highlight_vertex_size        
            width = self.preferences.highlight_line_width        
            color = self.preferences.delete_color         
            draw_util.drawElementsHilight3D( self.bmo.obj , self.removes , vertex_size , width , alpha , color )        

    def OnExit( self ) :
        pass

    @classmethod
    def GetCursor(cls) :
        return 'ERASER'

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['EDGE'] )        
        return element
