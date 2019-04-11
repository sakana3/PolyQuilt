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
from .subtool import SubTool

class SubToolEdgeSlice(SubTool) :
    name = "SliceTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentEdge = target
        self.sliceEdges = []
        self.sliceCuts = []
        self.sliceRate = 0
        self.CalcSlice(self.currentEdge)

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.sliceRate = self.CalcSplitRate( context ,self.mouse_pos , self.currentEdge )
            pass
        elif event.type == 'RIGHTMOUSE' :
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

            draw_util.drawElementHilight( self.bmo.obj , self.currentEdge, 4 , self.color_split(0.25) )
            pos = self.currentEdge.verts[0].co + (self.currentEdge.verts[1].co-self.currentEdge.verts[0].co) * self.sliceRate
            pos = self.bmo.object_to_world_position( pos )
            pos = handleutility.location_3d_to_region_2d( pos )
            draw_util.draw_pivot2D( pos , self.preferences.highlight_vertex_size , self.color_split(0.25) )

            for sliceCut in self.sliceCuts :
                for cuts in sliceCut :
                    v0 = cuts[0].verts[0].co.lerp( cuts[0].verts[1].co , self.sliceRate if cuts[2] == 0 else 1.0 - self.sliceRate )
                    v1 = cuts[1].verts[0].co.lerp( cuts[1].verts[1].co , self.sliceRate if cuts[3] == 0 else 1.0 - self.sliceRate )
                    v0 = handleutility.location_3d_to_region_2d( matrix @ v0)
                    v1 = handleutility.location_3d_to_region_2d( matrix @ v1)
                    draw_util.draw_lines2D( (v0,v1) , self.color_split() , self.preferences.highlight_line_width  )
            draw_util.DrawFont( '{:.2f}'.format(self.sliceRate) , 10 , pos , (0,2) )                    

    def CalcSplitRate( self , context ,coord , baseEdge ) :
        ray_origin , ray_direction = handleutility.calc_object_space_ray( context , self.bmo.obj , coord )
        v0 = baseEdge.verts[0].co
        v1 = baseEdge.verts[1].co
        h0 , h1 , d = handleutility.RayDistAndPos( v0 , (v1-v0).normalized() , ray_origin , ray_direction )
        dt =  (v0-v1).length
        d0 = (v0-h0).length
        d1 = (v1-h0).length
        if d0 > dt :
            return 1.0
        elif d1 > dt :
            return 0.0
        else :
            return max( 0 , min( 1 , d0 / dt ))

    def CalcSlice( self , startEdge ) :
        self.sliceCuts = []
        for face in startEdge.link_faces :
            if len(face.loops) == 4 :
                if len( [cut for cut in self.sliceCuts if cut[-1][1] in face.edges ] ) == 0 :
                    sliceCuts = self.__calc_slice( startEdge ,face )
                    self.sliceCuts.append( sliceCuts )

    def __calc_slice( self , startEdge ,startFace ) :
        edge_pairs = []
        edge = startEdge
        face = startFace
        vidx = 0
        while( face != None and len(face.loops) == 4 ) :
            loop = [ l for l in face.loops if l.edge == edge ][-1]
            pair = loop.link_loop_next.link_loop_next
            if loop.vert == edge.verts[vidx] :
                pidx = 1 if pair.edge.verts[0] == pair.vert else 0
            else :
                pidx = 0 if pair.edge.verts[0] == pair.vert else 1
            edge_pairs.append( (loop.edge,pair.edge,vidx , pidx ) )
            edge = pair.edge
            vidx = pidx
            if len(edge.link_faces) != 2 :
                break
            if edge == startEdge :
                break
            face = [ f for f in pair.edge.link_faces if f != face ][-1]

        return edge_pairs 

    def DoSlice( self , startEdge , sliceRate ) :
        edges = [startEdge]
        _slice = {startEdge:sliceRate}
        for sliceCut in self.sliceCuts :
            for cuts in sliceCut :
                if cuts[1] != startEdge:
                    edges.append( cuts[1] )
                    if( cuts[3] == 0 ) :
                        _slice[ cuts[1] ] = sliceRate
                    else :
                        _slice[ cuts[1] ] = 1.0 - sliceRate

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
             use_only_quads = False ,
             seed = 0 ,
             use_sphere = False 
        )

        self.bmo.UpdateMesh()                

#bmesh.ops.smooth_vert（bm、verts、factor、mirror_clip_x、mirror_clip_y、mirror_clip_z、clip_dist、use_axis_x、use_axis_y、use_axis_z ）
