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
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubTool

class SubToolEdgeSlide(SubTool) :
    name = "EdgeLoopSlideTool"

    def __init__(self,op, target : ElementItem ) :
        super().__init__(op)
        self.currentEdge = target.element
        self.edges , self.vetrs = self.bmo.findEdgeLoop( self.currentEdge )
        l2w = self.bmo.local_to_world_pos
        t = [ [ l2w( e.other_vert(v).co) for e in self.vetrs[v] ] for v in self.currentEdge.verts ]
        v0 = l2w(self.currentEdge.verts[0].co)
        v1 = l2w(self.currentEdge.verts[1].co)
        rate = ( v0 - target.hitPosition ).length / ( v0 - v1 ).length
        self.center_pos = target.hitPosition
        self.target_poss = [ t[0][i].lerp( t[1][i] , rate ) for i in range( len(self.currentEdge.link_faces) ) ]
        self.initial_poss = { v : v.co.copy() for v in self.vetrs }
        self.other_poss = { v : [ e.other_vert(v).co.copy() for e in edges] for v,edges in self.vetrs.items() }
        self.rates = [0,0]

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.rates = self.calcRate( context , self.mouse_pos )
            max_rate = max( self.rates )
            if max_rate <= sys.float_info.epsilon :
                for vert in self.vetrs :
                    vert.co = self.initial_poss[vert]
            else :
                for vert in self.vetrs :
                    edges = self.vetrs[vert]
                    for i in range( len(edges)) :
                        if self.rates[i] >= sys.float_info.epsilon and self.rates[i] == max_rate :
                            p = self.initial_poss[vert].lerp( self.other_poss[vert][i] , self.rates[i] )
                            vert.co = p
            self.bmo.UpdateMesh()

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def calcRate(  self , context , location ) :
        ray = pqutil.Ray.from_screen( context , location )        
        r = [ ray.hit_to_line( self.center_pos , p ) for p in self.target_poss ]
        return r

    def OnDraw3D( self , context  ) :
        for t in self.target_poss :
            draw_util.draw_lines3D( context , [self.center_pos,t] , width = 1 , color = self.color_create() , primitiveType = 'LINES' , hide_alpha = 1 )

        for (t,r) in zip( self.target_poss , self.rates ) :
            draw_util.draw_pivots3D( ( self.center_pos.lerp( t , r ) ,) , self.preferences.highlight_vertex_size / 2 , self.color_split(0.5) )

        lines = []
        for e in self.edges :
            lines.append( self.bmo.local_to_world_pos( e.verts[0].co ) )
            lines.append( self.bmo.local_to_world_pos( e.verts[1].co ) )
        draw_util.draw_lines3D( context , lines , width = 3 , color = self.color_highlight() , primitiveType = 'LINES' , hide_alpha = 1 )
