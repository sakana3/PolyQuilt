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
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from ..dpi import *
from .subtool import SubTool

class SubToolEdgeSlice(SubTool) :
    name = "SliceTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentEdge = target
        self.draw_deges = []
        self.split_deges = []         
        self.endTriangles = {}    
        self.sliceRate = 0.5
        self.fixCenter = False
        self.CalcSlice(self.currentEdge)
        self.is_forcus = True

    def OnForcus( self , context , event  ) :
        self.sliceRate = self.CalcSplitRate( context ,self.mouse_pos , self.currentEdge )
        return self.is_forcus

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.sliceRate > 0 and self.sliceRate < 1 :
                    self.DoSlice(self.currentEdge , self.sliceRate )
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :

        if self.sliceRate > 0 and self.sliceRate < 1 :
            matrix = self.bmo.obj.matrix_world
            pos = self.currentEdge.verts[0].co + (self.currentEdge.verts[1].co-self.currentEdge.verts[0].co) * self.sliceRate
            pos = self.bmo.local_to_world_pos( pos )
            pos = handleutility.location_3d_to_region_2d( pos )            
            draw_util.DrawFont( '{:.2f}'.format(self.sliceRate) , 10 , pos , (0,2) )                    

    def OnDraw3D( self , context  ) :
        if self.sliceRate > 0 and self.sliceRate < 1 :
            size = self.preferences.highlight_vertex_size          
            width = self.preferences.highlight_line_width
            alpha = self.preferences.highlight_face_alpha
            draw_util.drawElementHilight3D( self.bmo.obj , self.currentEdge, size , width , alpha , self.color_split(0.25) )
            pos = self.currentEdge.verts[0].co + (self.currentEdge.verts[1].co-self.currentEdge.verts[0].co) * self.sliceRate
            pos = self.bmo.local_to_world_pos( pos )
            draw_util.draw_pivots3D( (pos,) , self.preferences.highlight_vertex_size , self.color_split(0.25) )

            if self.draw_deges :
                lines = []
                for cuts in self.draw_deges :
                    v0 = cuts[0].verts[0].co.lerp( cuts[0].verts[1].co , self.sliceRate if cuts[2] == 0 else 1.0 - self.sliceRate )
                    v1 = cuts[1].verts[0].co.lerp( cuts[1].verts[1].co , self.sliceRate if cuts[3] == 0 else 1.0 - self.sliceRate )
                    v0 = self.bmo.local_to_world_pos( v0 )
                    v1 = self.bmo.local_to_world_pos( v1 )
                    lines.append(v0)
                    lines.append(v1)
                draw_util.draw_lines3D( context , lines , self.color_split() , self.preferences.highlight_line_width , 1.0 , primitiveType = 'LINES'  )


    def CalcSplitRate( self , context ,coord , baseEdge ) :
        ray = handleutility.Ray.from_screen( context , coord ).world_to_object( self.bmo.obj )
        dist = self.preferences.distance_to_highlight* dpm()

        d = handleutility.CalcRateEdgeRay( self.bmo.obj , context , baseEdge , baseEdge.verts[0] , coord , ray , dist )

        self.is_forcus = d > 0 and d < 1

        if self.fixCenter :
            return 0.5

        return d

    def CalcSlice( self , startEdge ) :
        check_edges = []
        draw_deges = []
        split_deges = []

        startEdges = [ (startEdge,0) ]

        if self.bmo.is_mirror_mode :
            mirrorEdge = self.bmo.find_mirror(startEdge,False)
            if mirrorEdge is not None :
                if mirrorEdge != startEdge :
                    mirrorVert = self.bmo.find_mirror(startEdge.verts[0])
                    startEdges.append( (mirrorEdge, 0 if mirrorEdge.verts[0] == mirrorVert else 1 ) )
                else :
                    self.fixCenter = True


        for startEdge in startEdges :
            if len(startEdge[0].link_faces) > 2 :
                continue
            for startFace in startEdge[0].link_faces :

                vidx = startEdge[1]
                face = startFace
                edge = startEdge[0]              
                while( face != None and edge != None  ) :
                    loop = [ l for l in face.loops if l.edge == edge ][-1]
                    if edge not in check_edges :
                        check_edges.append(edge)
                        split_deges.append( (edge ,vidx ) )

                    if len( face.loops ) != 4 :
                        if len( face.loops ) == 3 :
                            if face not in self.endTriangles :
                                self.endTriangles[face] = (edge.verts[0].index,edge.verts[1].index , [ v for v in face.verts if v not in edge.verts ][0].index )
                            else :
                                self.endTriangles[face] = None
                        break

                    opposite = loop.link_loop_next.link_loop_next
                    pidx = 1 if ( loop.vert == edge.verts[vidx]) == (opposite.edge.verts[0] == opposite.vert) else 0                    
                    draw_deges.append( (loop.edge,opposite.edge ,vidx , pidx ) )
                    vidx = pidx

                    if len( opposite.edge.link_faces ) == 2 :
                        face = [ f for f in opposite.edge.link_faces if f != face ][-1]
                        edge = opposite.edge
                    else :
                        if opposite.edge not in check_edges :                        
                            split_deges.append( (opposite.edge ,vidx ) )
                            check_edges.append( opposite.edge )
                        break

                    if startEdge[0].index == edge.index :
                        break


        self.split_deges = split_deges 
        self.draw_deges = draw_deges 


    def DoSlice( self , startEdge , sliceRate ) :
        edges = []
        _slice = {}
        for split_dege in self.split_deges :
            edges.append( split_dege[0] )
            if( split_dege[1] == 0 ) :
                _slice[ split_dege[0] ] = sliceRate
            else :
                _slice[ split_dege[0] ] = 1.0 - sliceRate

        geom_inner , geom_split , geom = bmesh.ops.subdivide_edges(
             self.bmo.bm ,
             edges = edges ,
             edge_percents  = _slice ,
             smooth = 0 ,
             smooth_falloff = 'SMOOTH' ,
             use_smooth_even = False ,
             fractal = 0.0 ,
             along_normal = 0.0 ,
             cuts = 1 ,
             quad_corner_type = 'PATH' ,
             use_single_edge = False ,
             use_grid_fill=True,
             use_only_quads = True ,
             seed = 0 ,
             use_sphere = False 
        )

        self.bmo.UpdateMesh()

#bmesh.ops.smooth_vert（bm、verts、factor、mirror_clip_x、mirror_clip_y、mirror_clip_z、clip_dist、use_axis_x、use_axis_y、use_axis_z ）
