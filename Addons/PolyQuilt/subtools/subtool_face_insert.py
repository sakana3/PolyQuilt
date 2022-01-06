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

class SubToolFaceInsert(SubTool) :
    name = "FaceInsertTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentTarget = target
        self.slice_rate = 0.0
        self.slice_dist = 0.0
        self.hit_face = None
        self.center = None
        self.is_hit_center = None
        self.extrude_dst = 0

    @staticmethod
    def Check( root ,target ) :
        return target.isVert and len(target.element.link_faces) > 0

    def OnForcus( self , context , event  ) :
        if event.type == 'MOUSEMOVE':
            backface_culling = self.bmo.get_shading(bpy.context).show_backface_culling
            hit = self.bmo.highlight.PickFace( mathutils.Vector( (event.mouse_region_x , event.mouse_region_y) ) , [] , backface_culling )
            if hit.isFace and hit.element in self.currentTarget.element.link_faces :
                hit.setup_mirror()
                self.hit_face = hit
            else :
                self.hit_face = None
        return self.hit_face != None

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.center = None
            self.is_hit_center = False
            self.extrude_dst = 0 
            if self.hit_face != None :
                l2w = self.bmo.local_to_world_pos
                self.center = l2w( self.hit_face.element.calc_center_median() )                
                self.is_hit_center = self.hit_face.is_hit_center()
                self.extrude_dst = self.CalcInsertDistance( self.mouse_pos , self.hit_face.element , self.currentTarget.element )

        if event.type == 'RIGHTMOUSE' :
            return 'FINISHED'
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.hit_face :
                    self.DoInsert(self.hit_face.element)
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw3D( self , context  ) :
        if self.center != None :
            draw_util.draw_pivots3D( (self.center,) , 1 , self.color_split() )
        l2w = self.bmo.local_to_world_pos
        faces = [ f for f in ( self.hit_face.element , self.hit_face.mirror ) if f != None ]

        if self.is_hit_center :
            for face in faces :
                p = self.bmo.local_to_world_pos( face.calc_center_median() )
                lines = ( ( p , l2w( v.co )) for v in face.verts )
                draw_util.draw_lines3D( bpy.context, verts = sum( lines , () )  , color= self.color_split() , primitiveType='LINES' )
        elif self.extrude_dst > 0:
#   add_v3_v3v3(ab, a, b);            
 #           angle_cos = (normalize_v3(ab) != 0.0f) ? fabsf(dot_v3v3(a, ab)) : 0.0f;
 #           return (UNLIKELY(angle_cos < SMALL_NUMBER)) ? 1.0f : (1.0f / angle_cos);

            dst = self.extrude_dst
            def nor( lp ) :
                return l2w( lp.vert.co + lp.calc_tangent() * dst * self.calc_loop_length(lp) )

            for face in faces :
                lines = ( ( l2w( l.vert.co ) ,nor(l))  for l in face.loops )
                draw_util.draw_lines3D( bpy.context, verts = sum( lines , () )  , color= self.color_split() , primitiveType='LINES' )

                lines = ( ( nor(l) , nor(l.link_loop_next) ) for l in face.loops )
                draw_util.draw_lines3D( bpy.context, verts = sum( lines , () )  , color= self.color_split() , primitiveType='LINES' )

    def calc_loop_length( self , loop ) :
        prev = loop.link_loop_prev
        a = prev.edge.calc_tangent(prev)
        b = loop.edge.calc_tangent(loop)
        ab = a + b
        angle_cos = a.dot(ab.normalized()) if ab.length != 0 else 0
        d = 1.0 if angle_cos < sys.float_info.epsilon else 1 / angle_cos
        return d

    def CalcInsertDistance( self , coord , face , vert ) :
        loop = [ l for l in face.loops if l.vert == vert ][-1]
        tang = loop.calc_tangent()
        p0 = loop.vert.co
        p1 = loop.vert.co + loop.calc_tangent()
        ray = pqutil.Ray.from_screen( bpy.context , coord ).world_to_object( self.bmo.obj )
        ray2 = pqutil.Ray( p0 , (p1 - p0).normalized() )
        h0 , h1 , d = ray.distance( ray2 )
        dst = ( h0 - p0 ).length

        tmp = self.calc_loop_length( loop )

        return dst * ( 1 / tmp ) if tmp > sys.float_info.epsilon else 1

    def DoInsert( self , face ) :
        mirror = self.bmo.find_mirror( face ) if self.bmo.is_mirror_mode else None
        geom = [face] if mirror is None else [face,mirror]
        if self.is_hit_center :
            new_geoms = bmesh.ops.poke( self.bmo.bm, faces = geom , offset  = 0 , center_mode = 'MEAN' , use_relative_offset = False )
            if QSnap.is_active :
                for vert in new_geoms['verts'] :
                    vert.normal_update()
                    v = self.bmo.local_to_world_pos(vert.co)
                    n = self.bmo.local_to_world_nrm(vert.normal)
                    p , _ = QSnap.adjust_by_normal( v , n , self.preferences.fix_to_x_zero )
                    vert.co = self.bmo.world_to_local_pos( p )
                    vert.normal_update()
            self.bmo.UpdateMesh()
        elif self.extrude_dst > 0:
            new_geoms = bmesh.ops.inset_individual(self.bmo.bm, faces  = geom , thickness = self.extrude_dst , use_even_offset = True )
            if QSnap.is_active :
                for face in new_geoms['faces'] :
                    face.normal_update()
                for face in new_geoms['faces'] :
                    for vert in face.verts :
                        v = self.bmo.local_to_world_pos(vert.co)
                        n = self.bmo.local_to_world_nrm(vert.normal)
                        p , _ = QSnap.adjust_by_normal( v , n , self.preferences.fix_to_x_zero )
                        vert.co = self.bmo.world_to_local_pos( p )
                for face in new_geoms['faces'] :
                    for vert in face.verts :
                        vert.normal_update()

            #(bm, faces, thickness, depth, use_even_offset, use_interpolate, use_relative_offset)
#            bmesh.ops.inset_region(self.bmo.bm, faces  = geom , thickness = self.extrude_dst , use_even_offset = True)
            #, faces_exclude, use_boundary, use_even_offset, use_interpolate, use_relative_offset, use_edge_rail, thickness, depth, use_outset)
            self.bmo.UpdateMesh()
