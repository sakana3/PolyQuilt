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
from ..utils.dpi import *
from .subtool import SubTool

class SubToolFinSlice(SubTool) :
    name = "FinSliceTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentTarget = target
        self.slice_rate = 0.0
        self.slice_dist = 0.0

    def OnForcus( self , context , event  ) :
        if event.type == 'MOUSEMOVE':
            self.slice_rate , self.slice_dist = self.CalcRate(context,self.mouse_pos)
        return self.slice_rate > 0 

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE' :
            return 'FINISHED'
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.slice_rate == 1 :
                    self.DoSplit()
                elif self.slice_rate > 0 :
                    self.DoSlice()
                return 'FINISHED'
        return 'RUNNING_MODAL'


    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        self.currentTarget.Draw( self.bmo.obj , self.color_split() , self.preferences )

        for edge in self.currentTarget.element.link_edges :
            v0 = self.bmo.local_to_world_pos(edge.verts[0].co)
            v1 = self.bmo.local_to_world_pos(edge.verts[1].co)
            draw_util.draw_lines3D( context , (v0,v1) , self.color_split(0.25) , self.preferences.highlight_line_width , 1.0 , primitiveType = 'LINES'  )
            if self.slice_rate == 1.0 :
                p = self.bmo.local_to_world_pos(edge.other_vert(self.currentTarget.element).co)
                draw_util.draw_pivots3D( ( p , ) , 1 , self.color_split() )

        rate = self.slice_rate
        virts , edges = self.collect_geom( self.currentTarget.element , self.currentTarget.mirror )

        for vert in virts :
            for face in vert.link_faces :
                links = [ e for e in face.edges if e in edges ]
                if len(links) == 2 :
                    for v in virts :
                        p0 = self.bmo.local_to_world_pos(v.co)
                        if v in links[0].verts :
                            p1 = self.bmo.local_to_world_pos(links[0].other_vert(v).co)
                            v0 = p0 *(1-rate) + p1 * rate
                        if v in links[1].verts :
                            p1 = self.bmo.local_to_world_pos(links[1].other_vert(v).co)
                            v1 = p0 *(1-rate) + p1 * rate
                    draw_util.draw_lines3D( context , (v0,v1) , self.color_split() , self.preferences.highlight_line_width , 1.0 , primitiveType = 'LINES'  )

    def collect_geom( self , element , mirror ) :
        if self.bmo.is_mirror_mode and mirror is not None :
            s0 = set(element.link_edges)
            s1 = set(mirror.link_edges)
            edges = ( s0 | s1 ) - ( s0 & s1 )
            virts = [ element, mirror]
        else :
            edges = element.link_edges
            virts = [element]
        return virts , edges

    def CalcRate( self , context , coord ):
        rate = 0.0
        dist = 0.0
        ray = pqutil.Ray.from_screen( context , coord ).world_to_object( self.bmo.obj )
        d = self.preferences.distance_to_highlight* dpm()
        for edge in self.currentTarget.element.link_edges :
            r = pqutil.CalcRateEdgeRay( self.bmo.obj , context , edge , self.currentTarget.element , coord , ray , d )
            if r > rate :
                rate = r
                dist = d * (edge.verts[0].co - edge.verts[1].co).length
        return rate , dist

    def DoSplit( self ) :
        verts , edges = self.collect_geom( self.currentTarget.element , self.currentTarget.mirror )

        for vert in verts :
            for face in vert.link_faces :
                links = [ e for e in face.edges if e in edges ]
                if len(links) == 2 :
                    v0 = links[0].other_vert(vert)
                    v1 = links[1].other_vert(vert)

                    if self.bmo.bm.edges.get( (v0 , v1) ) == None :
                        bmesh.utils.face_split( face , v0  , v1 )
        self.bmo.UpdateMesh()

    def DoSlice( self ) :
        _slice = {}
        _edges = []

        def append( vert , other_vert ) :
            for edge in vert.link_edges :        
                if other_vert is not None :
                    if edge not in other_vert.link_edges :
                        _edges.append( edge )
                else :
                    _edges.append( edge )
                _slice[ edge ] = self.slice_rate if ( edge.verts[0] == vert ) else (1.0 - self.slice_rate)

        if self.bmo.is_mirror_mode and self.currentTarget.mirror is not None :
            append( self.currentTarget.element , self.currentTarget.mirror )
            append( self.currentTarget.mirror , self.currentTarget.element )
        else :
            append( self.currentTarget.element , None )

        ret = bmesh.ops.subdivide_edges(
             self.bmo.bm ,
             edges = _edges ,
             edge_percents  = _slice ,
             smooth = 0 ,
             smooth_falloff = 'SMOOTH' ,
             use_smooth_even = False ,
             fractal = 0.0 ,
             along_normal = 0.0 ,
             cuts = 1 ,
             quad_corner_type = 'STRAIGHT_CUT' ,
             use_single_edge = False ,
             use_grid_fill=False,
             use_only_quads = False ,
             seed = 0 ,
             use_sphere = False 
        )

        for e in ret['geom_inner'] :
            e.select_set(True)
        if QSnap.is_active() :
            QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_inner'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

        self.bmo.UpdateMesh()

