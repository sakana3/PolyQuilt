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
from .subtool_edge_slide import *
from .subtool_edgeloop_cut import *
from .subtool_edge_extrude import *
from .subtool_edge_extrude_multi import *
from .subtool_vert_extrude import *
from .subtool_autoquad import *
from .subtool_move import *
from .subtool_fin_slice import *

class MainToolHold(MainTool) :
    name = "Hold"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button)        

    @staticmethod
    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)
        if event.type == MBEventType.Down :
            pass

        elif event.type == MBEventType.Release :
            self.isExit = True

        elif event.type == MBEventType.Click :
            if self.currentTarget.isVert or self.currentTarget.isEdge or self.currentTarget.isEmpty:
                if SubToolAutoQuad.Check( self , self.currentTarget) :
                    self.SetSubTool( SubToolAutoQuad( self ))
            self.isExit = True

        elif event.type == MBEventType.LongClick :
            if self.currentTarget.isVert :
                self.bmo.dissolve_vert( self.currentTarget.element , False , False )
            elif self.currentTarget.isEdge :
                self.bmo.dissolve_edge( self.currentTarget.element , False , False )
            elif self.currentTarget.isFace :
                self.bmo.Remove( self.currentTarget.element )
            self.bmo.UpdateMesh()
            self.currentTarget = ElementItem.Empty()

        elif event.type == MBEventType.Drag :
            if self.currentTarget.isEdge :
                tools = []
                tools.append(SubToolEdgeSlide(self.operator,self.currentTarget))
                self.SetSubTool( tools )
            elif self.currentTarget.isVert :
                tools = []
                if SubToolVertExtrude.Check( self ,self.currentTarget ) :
                    tools.append(SubToolVertExtrude(self.operator,self.currentTarget))
                if tools :
                    self.SetSubTool( tools )
            elif self.currentTarget.isEmpty :
                self.SetSubTool( SubToolKnife(self.operator,self.currentTarget , self.LMBEvent.PressPos ) )   

        elif event.type == MBEventType.LongPressDrag :
            if self.currentTarget.isEdge :
                tools = []
                if len(self.currentTarget.element.link_faces) > 0 :
                    tools.append(SubToolEdgeSlice(self.operator,self.currentTarget, self.mouse_pos))
                if SubToolEdgeloopCut.Check(self ,self.currentTarget) : 
                    tools.append(SubToolEdgeloopCut(self.operator,self.currentTarget))
                if SubToolEdgeExtrudeMulti.Check(self ,self.currentTarget) : 
                    tools.append(SubToolEdgeExtrudeMulti(self.operator,self.currentTarget,True))                    
                self.SetSubTool( tools )
            elif self.currentTarget.isVert :
                tools = []
                if SubToolEdgeExtrudeMulti.Check( self ,self.currentTarget ) :
                    tools.append(SubToolEdgeExtrudeMulti(self.operator,self.currentTarget))
                self.SetSubTool( tools )
            elif self.currentTarget.isEmpty :
                self.SetSubTool( SubToolKnife(self.operator,self.currentTarget , self.LMBEvent.PressPos ) )   



    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if SubToolAutoQuad.Check( None , element ) :
            drawAutoQuad = SubToolAutoQuad.DrawHighlight(gizmo,element)
        else :
            drawAutoQuad = None

        if element.isEdge :
            edges , verts = gizmo.bmo.findEdgeLoop( element.element )
        else :
            edges = []

        width = gizmo.preferences.highlight_line_width
        color = gizmo.preferences.highlight_color
        def Draw() :
            if drawAutoQuad:
                drawAutoQuad()
            for edge in edges :
                vs = [ gizmo.bmo.obj.matrix_world @ v.co for v in edge.verts ] 
                draw_util.draw_lines3D( bpy.context , vs , color , width , primitiveType = 'LINES' , hide_alpha = 0.5 )        
        return Draw

    def OnDraw( self , context  ) :
        if self.LMBEvent.isPresure :
            if self.currentTarget.isNotEmpty :
                self.LMBEvent.Draw( self.currentTarget.coord )
            else:
                self.LMBEvent.Draw( None )

    def OnDraw3D( self , context  ) :
        width = self.preferences.highlight_line_width
        color = self.preferences.highlight_color        
        if self.LMBEvent.isPresure :
            color = self.preferences.makepoly_color 
        else :
            if self.currentTarget.isEdge : 
                if SubToolAutoQuad.Check( None , self.currentTarget ) :
                    drawAutoQuad = SubToolAutoQuad.DrawHighlight( self,self.currentTarget )
                    if drawAutoQuad :
                        drawAutoQuad()
        if self.currentTarget.isEdge :                    
            edges , verts = self.bmo.findEdgeLoop( self.currentTarget.element )
        else :
            edges = []
        for edge in edges :
            vs = [ self.bmo.obj.matrix_world @ v.co for v in edge.verts ] 
            draw_util.draw_lines3D( bpy.context , vs , color , width , primitiveType = 'LINES' , hide_alpha = 0.5 )        
