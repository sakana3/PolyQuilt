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

import sys
import bpy
import math
import mathutils
import bmesh
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubTool
from ..utils.dpi import *
from ..utils.mouse_event_util import MBEventType , MBEventResult

class SubToolSelectBoundaryEdge(SubTool) :
    name = "Select boundary edge"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op)        
        self.buttonType = button
        self.shortest_path = [ ]
        self.shortest_path_Verts = []
        self.loops = []

    @staticmethod
    def Check( root , target ) :
        return True

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight , elements = ["EDGE"] , edgering = True )        
        return element

    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Drag :
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ["EDGE"], edgering = True  )

            if self.startTarget.isEdge and self.currentTarget.isEdge and self.currentTarget.element != self.startTarget.element :
                self.shortest_path = self.bmo.calc_shortest_pass( self.bmo.bm , self.startTarget.element , self.currentTarget.element , boundaryOnly = True )[0]
                self.shortest_path , self.shortest_path_Verts =  pqutil.sort_edgeloop( self.shortest_path )
                if self.shortest_path and self.shortest_path_Verts[0] not in self.startTarget.element.verts :
                    self.shortest_path.reverse()
                    self.shortest_path_Verts.reverse()
            else :
                self.shortest_path =  []

        elif event.type == MBEventType.LongPress :
            selected = [ edge for edge in self.bmo.bm.edges if edge.select and (edge.is_boundary or edge.is_wire) ]
            if set(selected) == set(self.startTarget.loops) :
                self.loops = self.startTarget.rings
            else :            
                self.loops = self.startTarget.loops

        elif event.type == MBEventType.LongClick :
            if self.loops :
                if not SubToolSelectBoundaryEdge.check_connect_of_loop( self.currentTarget.element ) :
                    self.bmo.select_flush()
                self.bmo.select_components( self.loops , True )
                self.bmo.select_component( self.startTarget.element , True )
                self.bmo.UpdateMesh()
            return MBEventResult.Quit

        elif event.type == MBEventType.Click :                
            if self.currentTarget.isEdge :
                edge = self.currentTarget.element
                if not edge.select :
                    if not SubToolSelectBoundaryEdge.check_connect_of_loop(edge) :
                        self.bmo.select_flush()
                    self.bmo.select_component( edge , True )
#                       self.bmo.bm.select_flush(True)
                else :
                    if SubToolSelectBoundaryEdge.check_end_of_loop( edge ) :
                        self.bmo.select_component( edge , False )
                    elif not SubToolSelectBoundaryEdge.check_connect_of_loop(edge) :
                        self.bmo.select_flush()
                        self.bmo.select_component( edge , True )

                self.bmo.UpdateMesh()
            else :
                self.bmo.select_flush()
                self.bmo.UpdateMesh()                    

            self.isExit = True
            return MBEventResult.Quit

        elif event.type == MBEventType.Release :
            if self.shortest_path and self.currentTarget.isEdge :
                start = self.startTarget.element                
                end = self.currentTarget.element                
                if SubToolSelectBoundaryEdge.check_connect_of_loop(start) :
                    self.bmo.select_components( self.shortest_path , True )
                elif SubToolSelectBoundaryEdge.check_end_of_loop( start ) and end.select :
                    self.bmo.select_components( self.shortest_path , False )
                    self.bmo.bm.select_flush(True)
                else :                    
                    self.bmo.select_flush()
                    self.bmo.select_components( self.shortest_path , True )
                self.bmo.UpdateMesh()                    

            self.isExit = True
            return MBEventResult.Quit

        return MBEventResult.Do

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'

        return super().OnUpdate(context , event)  


    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        funcs = []
        color = gizmo.preferences.highlight_color

#        def func() :
#            for edge in gizmo.bmo.bm.select_history :
 #               if  type( edge ) == bmesh.types.BMEdge :
 #                   verts = [ v.co for v in edge.verts ]
 #                   draw_util.draw_lines3D( bpy.context , verts , color = gizmo.preferences.highlight_color , width = display.dot( gizmo.preferences.highlight_line_width ) )                    
  #      funcs.append( func )

        if element.isEdge and element.element.select :
            if SubToolSelectBoundaryEdge.check_end_of_loop( element.element ):
                color = ( 0 , 0 , 0.3 , 1 )

        funcs.append( element.DrawFunc( gizmo.bmo.obj , color , gizmo.preferences , marker = False, edge_pivot = False ) )

        return funcs

    def OnDraw( self , context  ) :
        if self.shortest_path :
            vertex_size = self.preferences.highlight_vertex_size        
            width = display.dot( self.preferences.highlight_line_width + 1)
            color = self.preferences.highlight_color
            if ( self.check_end_of_loop(self.startTarget.element) and self.currentTarget.element.select ) or ( self.check_end_of_loop(self.currentTarget.element) and not self.startTarget.element.select )  :
                color = ( 0.25 , 0.1 , 0.1 , 1 )
            verts = [ self.bmo.local_to_2d( v.co ) for v in self.shortest_path_Verts  ]
            draw_util.draw_dot_lines2D( verts , color , width , pattern= (2,1) )
        else :
            if self.LMBEvent.isPresure :
                if self.currentTarget.isNotEmpty :
                    self.LMBEvent.Draw( self.currentTarget.coord )
                else:
                    self.LMBEvent.Draw( None )

            if self.currentTarget.isEdge and self.LMBEvent.is_hold :
                loop = self.loops
                le , vt =  pqutil.sort_edgeloop( loop )
                verts = [ self.bmo.local_to_2d( v.co ) for v in vt ]
                draw_util.draw_dot_lines2D( verts , self.color_highlight(0.5) , display.dot( self.preferences.highlight_line_width + 1 ) , pattern= (2,1)  )

    def OnDraw3D( self , context  ) :
        if not self.shortest_path :
            color = self.preferences.highlight_color
            if self.currentTarget.isEdge :
                if SubToolSelectBoundaryEdge.check_end_of_loop( self.currentTarget.element ):
                    color = ( 0 , 0 , 0.3 , 1 )
            self.currentTarget.Draw( self.bmo.obj , color  , self.preferences , marker = False, edge_pivot = False )    

    @staticmethod
    def check_end_of_loop( edge ) :
        return edge.select and any( not any( e.select and e != edge and ( e.is_wire or e.is_boundary ) for e in v.link_edges ) for v in edge.verts )

    @staticmethod
    def check_connect_of_loop( edge ) :
        v1=  any( e.select and e != edge and ( e.is_wire or e.is_boundary ) for e in edge.verts[0].link_edges )
        v2=  any( e.select and e != edge and ( e.is_wire or e.is_boundary ) for e in edge.verts[1].link_edges )
        return not edge.select and (v1 != v2)

#                    if any( not any( e.select and e != edge and ( e.is_wire or e.is_boundary ) for e in v.link_edges ) for v in verts ) :

    @classmethod
    def GetCursor(cls) :
        return 'DEFAULT'
