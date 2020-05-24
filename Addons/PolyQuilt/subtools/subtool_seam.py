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
from .subtool import MainTool
from ..utils.dpi import *

class SubToolSeam(MainTool) :
    name = "SeamTool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = True )        

        self.currentTarget = currentTarget
        self.startTarget = currentTarget
        self.removes = ( [ currentTarget.element ] , [] )

    @staticmethod
    def Check( root , target ) :
        return target.isEdge or target.isVert

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight , elements = ["EDGE","VERT"] )        
        return element

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            preTarget = self.currentTarget
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ["VERT","EDGE"]  )
            if self.currentTarget.isNotEmpty :
                vt = None
                if self.startTarget.isEdge :
                    vt = self.bmo.highlight.check_hit_element_vert( self.startTarget.element , self.mouse_pos , self.preferences.distance_to_highlight * dpm())
                ed = None
                if self.startTarget.isFace :
                    ed = self.bmo.highlight.check_hit_element_edge( self.startTarget.element , self.mouse_pos , self.preferences.distance_to_highlight * dpm())
                if vt :
                    if self.startTarget.isEdge and self.startTarget.element.seam :
                        e = self.find_seam_loop( self.startTarget.element )
                        v = []
                    else :
                        def check_func( edge , vert ) :
                            return any( [ e.seam for e in vert.link_edges if e != edge ] ) == False

                        e , v = self.bmo.calc_edge_loop( self.startTarget.element , check_func )
                    self.removes = (e,v)
                    self.currentTarget = self.startTarget
                elif ed :
                    self.removes = (  self.bmo.calc_loop_face(ed) , [] )
                elif self.startTarget.element != self.currentTarget.element :
                    self.removes = self.bmo.calc_shortest_pass( self.bmo.bm , self.startTarget.element , self.currentTarget.element )
                else :
                    self.removes = ([self.startTarget.element],[])
            else :
                self.removes = ([self.startTarget.element],[])
        elif event.type == self.buttonType : 
            if event.value == 'RELEASE' :
                self.SeamElement(self.currentTarget )
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element != None and gizmo.bmo != None :
            color = bpy.context.preferences.themes["Default"].view_3d.edge_seam
            return element.DrawFunc( gizmo.bmo.obj , (color[0],color[1],color[2],1) , gizmo.preferences , marker = False , edge_pivot = False , width = 5 )
        return None

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.removes[0] :
            alpha = self.preferences.highlight_face_alpha
            vertex_size = self.preferences.highlight_vertex_size        
            width = 5        
            color = bpy.context.preferences.themes["Default"].view_3d.edge_seam
            color = (color[0],color[1],color[2],1)
            draw_util.drawElementsHilight3D( self.bmo.obj , self.removes[0] , vertex_size , width , alpha , color )
            if self.bmo.is_mirror_mode :
                mirrors = [ self.bmo.find_mirror(m) for m in self.removes[0] ]
                mirrors = [ m for m in mirrors if m ]
                if mirrors :
                    draw_util.drawElementsHilight3D( self.bmo.obj , mirrors , vertex_size , width , alpha * 0.5 , color )

        if self.startTarget.element == self.currentTarget.element :
            self.startTarget.Draw( self.bmo.obj , self.preferences.highlight_color  , self.preferences , marker = False , edge_pivot = True )
        else :
            self.startTarget.Draw( self.bmo.obj , self.preferences.highlight_color  , self.preferences , marker = False , edge_pivot = False )
        if self.currentTarget.isNotEmpty :
            if self.startTarget.element != self.currentTarget.element :
                self.currentTarget.Draw( self.bmo.obj , self.preferences.highlight_color  , self.preferences , marker = False , edge_pivot = False )

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'

    def SeamElement( self , element ) :
        edges = [ e for e in self.removes[0] if isinstance( e , bmesh.types.BMEdge ) ]
        seam = True
        if all( [ e.seam for e in edges] ) :
            seam = False 

        for edge in edges :
            edge.seam = seam
            if self.bmo.is_mirror_mode :
                mirror = self.bmo.find_mirror( edge )
                if mirror :
                    mirror.seam = True
        self.bmo.UpdateMesh()

    def find_seam_loop( self , edge ) :
        loop = [edge]

        def find_loop( start , head ) :
            while(True) :
                link_seams = [ e for e in head.link_edges if e != start and e.seam ]
                if len( [ e for e in link_seams ] ) != 1 :
                    return
                start =  link_seams[0]
                if start in loop :
                    break
                loop.append( start )
                head = start.other_vert(head)

        find_loop( edge , edge.verts[0] )
        find_loop( edge , edge.verts[1] )

        return loop
