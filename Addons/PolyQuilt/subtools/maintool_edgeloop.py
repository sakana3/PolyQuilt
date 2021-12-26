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
from .subtool_edgeloop_cut import *
from .subtool_edgeloop_dissolve import *
from .subtool_edgeloop_extrude import SubToolEdgeLoopExtrude
from .subtool_edgeloop_slide import SubToolEdgeSlide
from .subtool_edgeloop_tweak import SubToolEdgeLoopTweak
from .subtool_edgering_extrude import SubToolEdgeRingExtrude

class MainToolEdgeLoop(MainTool) :
    name = "EdgeLoop Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = False )        
        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Click           : [] ,
            MBEventType.LongClick       : [] ,
            MBEventType.LongPressDrag   : [ [SubToolEdgeLoopCut.Check , SubToolEdgeLoopCut ] , [SubToolEdgeRingExtrude.CheckMarker , SubToolEdgeRingExtrude ] , [SubToolEdgeLoopExtrude.Check , SubToolEdgeLoopExtrude ] ] ,
            MBEventType.Drag            : [ [SubToolEdgeLoopExtrude.CheckMarker , SubToolEdgeLoopExtrude ] , [SubToolEdgeLoopTweak.Check ,SubToolEdgeLoopTweak]] ,
        }

    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)

        if event.type == MBEventType.LongClick :                
            if self.currentTarget.isEdge :
                self.bmo.dissolve_edges( self.currentTarget.both_loops , use_verts = False , use_face_split = False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle )
                self.bmo.UpdateMesh()
                self.isExit = True

        elif event.type == MBEventType.Click :                
            if self.currentTarget.isEdge :
                self.bmo.select_flush()
                self.bmo.select_components( self.currentTarget.both_loops , True )
                self.bmo.UpdateMesh()
                self.isExit = True

        if event.type in self.callback.keys() :
            tools = [ t[1]( self.operator , self.currentTarget , self.buttonType ) for t in self.callback[event.type] if t[0]( self , self.currentTarget ) ]
            if tools :
                self.SetSubTool( tools )
            self.isExit = True

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['EDGE'] )
        return element

    @staticmethod
    def Check( root , target ) :
        if target.isEdge :
            return True
        return True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        funcs = []
        funcs.append( element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.highlight_color , gizmo.preferences , True ) )

        if element.isEdge :
            alpha = gizmo.preferences.highlight_face_alpha
            vertex_size = gizmo.preferences.highlight_vertex_size        
            width = gizmo.preferences.highlight_line_width
            color = gizmo.preferences.highlight_color
            if element.can_extrude() :
                color = gizmo.preferences.makepoly_color
                width = gizmo.preferences.highlight_line_width + 1
            funcs.append( draw_util.drawElementsHilight3DFunc( gizmo.bmo.obj , gizmo.bmo.bm, element.both_loops , vertex_size ,width,alpha, color ) )
            return funcs
        return None

    def OnDraw( self , context  ) :
        if self.LMBEvent.isPresure :
            if self.currentTarget.isNotEmpty :
                self.LMBEvent.Draw( self.currentTarget.coord )
            else:
                self.LMBEvent.Draw( None )

    def OnDraw3D( self , context  ) :
        if self.currentTarget.isNotEmpty and not self.isExit:
            if self.currentTarget.isEdge :
                alpha = self.preferences.highlight_face_alpha
                vertex_size = self.preferences.highlight_vertex_size        
                width = self.preferences.highlight_line_width
                color = self.preferences.highlight_color
                if self.currentTarget.can_extrude() :
                    self.currentTarget.Draw( self.bmo.obj , self.preferences.highlight_color , self.preferences , True )
                if self.LMBEvent.is_hold :
                    if self.currentTarget.can_extrude() :
                        color = self.color_create()            
                        draw_util.drawElementsHilight3D( self.bmo.obj  , self.bmo.bm, self.currentTarget.both_rings , vertex_size ,width,alpha, color )
                    else :
                        color = self.color_delete() 
                        draw_util.drawElementsHilight3D( self.bmo.obj  , self.bmo.bm, self.currentTarget.both_loops , vertex_size ,width,alpha, color )

    def OnExit( self ) :
        pass

    @classmethod
    def GetCursor(cls) :
        return 'DEFAULT'