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
import bgl
import blf
import gpu
import bmesh
import math
import copy
import mathutils
import bpy_extras
import collections
import numpy
from mathutils import *

dpi = bpy.context.preferences.system.dpi / 100

class Plane :
    def __init__( self , origin , vector ) :
        self.origin = Vector( origin )
        self.vector = Vector( vector )
        self.vector.normalize()

    @staticmethod
    def from_screen( context , origin ) :
        rv3d = context.region_data
        vector = -rv3d.view_matrix.inverted().col[2].xyz
        vector.normalize()
        return Plane( origin , vector )

    def from_screen_slice( context , startPos , endPos ) :
        rv3d = context.region_data   
        region = context.region
#       pc = region_2d_to_origin_3d(region, rv3d, startPos)
        no = region_2d_to_vector_3d(region, rv3d, startPos)
        p0 = region_2d_to_location_3d(region, rv3d, startPos, no)
        p1 = region_2d_to_location_3d(region, rv3d, endPos, no)
        p2 = region_2d_to_location_3d(region, rv3d, endPos, no * 2)
        t0 = (p1-p2)
        t1 = (p0-p1)
        t =  t0.cross( t1 )

        return Plane( p0 , t )

    #RayとPlaneの交点を求める
    def intersect_ray( self , ray ) :
        d = self.origin.dot( -self.vector )
        t = -(d + ray.origin.z * self.vector.z + ray.origin.y * self.vector.y + ray.origin.x * self.vector.x) / (ray.vector.z * self.vector.z + ray.vector.y * self.vector.y + ray.vector.x * self.vector.x)
        x = ray.origin + ray.vector * t
        return x

    def intersect_line( self , p0 :Vector , p1 : Vector ) :
        origin = self.origin
        vector = self.vector
        v = mathutils.geometry.intersect_line_plane( p0 , p1 , origin , vector , False )

        if v == None :
            return None

        epsilon = 0.001
        d0 = mathutils.geometry.distance_point_to_plane(p0 , origin , vector )
        d1 = mathutils.geometry.distance_point_to_plane(p1 , origin , vector )

        if ( d0 > epsilon and d1 > epsilon ) or ( d0 < -epsilon and d1 < -epsilon ):
            return None

        return  v

    def distance_point( self , pt :Vector ) :
        d = mathutils.geometry.distance_point_to_plane(pt , self.origin , self.vector )
        return  d

    def world_to_object( self , obj ) :
        matrix = obj.matrix_world
        origin_obj = matrix.inverted() @ self.origin
        vector_obj = matrix.transposed().to_3x3() @ self.vector
        return Plane( origin_obj , vector_obj )

    def object_to_world( self , obj ) :
        matrix = obj.matrix_world
        origin_obj = matrix @ self.origin
        vector_obj = matrix.inverted().transposed().to_3x3() @ self.vector
        return Plane( origin_obj , vector_obj )

    def reverse( sefl ) :
        self.vector = -self.vector

    def reversed( sefl ) :
        return Plane( self.origin , - self.vector )

    def x_mirror(self) :
        self.origin = Vector( (-self.origin.x,self.origin.y,self.origin.z) )
        self.vector = Vector( (-self.vector.x,self.vector.y,self.vector.z) )

class Ray :
    def __init__( self , origin : mathutils.Vector , vector  : mathutils.Vector ) :
        self.origin = origin.copy()
        self.vector = vector
        self.vector.normalize()

    @staticmethod
    def from_screen( context , coord : mathutils.Vector) :
        rv3d = context.region_data   
        region = context.region
        origin = region_2d_to_origin_3d(region, rv3d, coord)
        vector = region_2d_to_vector_3d(region, rv3d, coord)
        return Ray(origin,vector)

    @staticmethod
    def from_world_to_screen( context , world_pos : mathutils.Vector ) :
        coord = location_3d_to_region_2d(world_pos)
        if coord == None :
            return None
        return Ray.from_screen( context , coord)

    def world_to_object( self , obj ) :
        matrix_inv = obj.matrix_world.inverted()
        target = self.origin + self.vector
        ray_origin_obj = matrix_inv @ self.origin
        ray_target_obj = matrix_inv @ target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        return Ray( ray_origin_obj , ray_direction_obj )

    def object_to_world( self , obj ) :
        matrix = obj.matrix_world
        target = self.origin + self.vector
        ray_origin_obj = matrix @ self.origin
        ray_target_obj = matrix @ target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        return Ray( ray_origin_obj , ray_direction_obj )

    # RayとRayの一番近い距離
    def distance( self , ray ) :
        if self.vector.cross(ray.vector).length_squared < 0.000001 :
            return None,None, ray.origin.cross(self.origin).length

        Dv = self.vector.dot(ray.vector)
        D1 = (ray.origin-self.origin).dot(self.vector)
        D2 = (ray.origin-self.origin).dot(ray.vector)

        t1 = ( D1 - D2 * Dv ) / ( 1.0 - Dv * Dv )
        t2 = ( D2 - D1 * Dv ) / ( Dv * Dv - 1.0 )

        Q1 = self.origin + self.vector * t1
        Q2 = ray.origin + ray.vector * t2

        return Q1,Q2,(Q2 - Q1).length

    def hit_to_line( self , v0 , v1 ) :
        h0 , h1 , d = self.distance( Ray( v0 , (v1-v0) ) )

        dt =  (v0-v1).length
        d0 = (v0-h1).length
        d1 = (v1-h1).length
        if d0 > d1 and d0 >= dt :
            return 1.0
        elif d1 >= dt :
            return 0.0

        return max( 0 , min( 1 , d0 / dt ))        

    def hit_to_line_pos( self , v0 , v1 ) :
        h0 , h1 , d = self.distance( Ray( v0 , (v1-v0) ) )
        if h0 == None :
            return None
        dt =  (v0-v1).length
        d0 = (v0-h1).length
        d1 = (v1-h1).length
        if d0 > d1 and d0 >= dt :
            val =  1.0
        elif d1 >= dt :
            val =  0.0
        else :
            val = d0 / dt
        
        return v0 + (v1-v0) * val


    @property
    def invert( self ) :
        return Ray( self.origin , -self.vector )

    @property
    def x_zero( self ) :
        return Ray( self.origin , mathutils.Vector( (0 , self.vector.y , self.vector.z )) )


def transform_position( vec : mathutils.Vector , matrix : mathutils.Matrix ) :
    return matrix @ vec

def transform_normal( vec : mathutils.Vector , matrix : mathutils.Matrix ) :
    return matrix.transposed().to_3x3() @ vec


def region_2d_to_vector_3d(region, rv3d, coord):
    """
    Return a direction vector from the viewport at the specific 2d region
    coordinate.

    :arg region: region of the 3D viewport, typically bpy.context.region.
    :type region: :class:`bpy.types.Region`
    :arg rv3d: 3D region data, typically bpy.context.space_data.region_3d.
    :type rv3d: :class:`bpy.types.RegionView3D`
    :arg coord: 2d coordinates relative to the region:
       (event.mouse_region_x, event.mouse_region_y) for example.
    :type coord: 2d vector
    :return: normalized 3d vector.
    :rtype: :class:`mathutils.Vector`
    """
    from mathutils import Vector

    viewinv = rv3d.view_matrix.inverted()
    if rv3d.is_perspective:
        persinv = rv3d.perspective_matrix.inverted()
        width = region.width
        height = region.height

        out = Vector(((2.0 * coord[0] / width) - 1.0,
                      (2.0 * coord[1] / height) - 1.0,
                      -0.5
                      ))

        w = out.dot(persinv[3].xyz) + persinv[3][3]

        view_vector = ((persinv @ out) / w) - viewinv.translation
    else:
        view_vector = -viewinv.col[2].xyz

    view_vector.normalize()

    return view_vector


def region_2d_to_origin_3d(region, rv3d, coord, clamp=None):
    """
    Return the 3d view origin from the region relative 2d coords.

    .. note::

       Orthographic views have a less obvious origin,
       the far clip is used to define the viewport near/far extents.
       Since far clip can be a very large value,
       the result may give with numeric precision issues.

       To avoid this problem, you can optionally clamp the far clip to a
       smaller value based on the data you're operating on.

    :arg region: region of the 3D viewport, typically bpy.context.region.
    :type region: :class:`bpy.types.Region`
    :arg rv3d: 3D region data, typically bpy.context.space_data.region_3d.
    :type rv3d: :class:`bpy.types.RegionView3D`
    :arg coord: 2d coordinates relative to the region;
       (event.mouse_region_x, event.mouse_region_y) for example.
    :type coord: 2d vector
    :arg clamp: Clamp the maximum far-clip value used.
       (negative value will move the offset away from the view_location)
    :type clamp: float or None
    :return: The origin of the viewpoint in 3d space.
    :rtype: :class:`mathutils.Vector`
    """
    viewinv = rv3d.view_matrix.inverted()

    if rv3d.is_perspective:
        origin_start = viewinv.translation.copy()
    else:
        persmat = rv3d.perspective_matrix.copy()
        dx = (2.0 * coord[0] / region.width) - 1.0
        dy = (2.0 * coord[1] / region.height) - 1.0
        persinv = persmat.inverted()
        origin_start = ((persinv.col[0].xyz * dx) +
                        (persinv.col[1].xyz * dy) +
                        persinv.translation)

        if clamp != 0.0:
            if rv3d.view_perspective != 'CAMERA':
                # this value is scaled to the far clip already
                origin_offset = persinv.col[2].xyz
                if clamp is not None:
                    if clamp < 0.0:
                        origin_offset.negate()
                        clamp = -clamp
                    if origin_offset.length > clamp:
                        origin_offset.length = clamp

                origin_start -= origin_offset

    return origin_start


def region_2d_to_location_3d(region, rv3d, coord, depth_location):
    """
    Return a 3d location from the region relative 2d coords, aligned with
    *depth_location*.

    :arg region: region of the 3D viewport, typically bpy.context.region.
    :type region: :class:`bpy.types.Region`
    :arg rv3d: 3D region data, typically bpy.context.space_data.region_3d.
    :type rv3d: :class:`bpy.types.RegionView3D`
    :arg coord: 2d coordinates relative to the region;
       (event.mouse_region_x, event.mouse_region_y) for example.
    :type coord: 2d vector
    :arg depth_location: the returned vectors depth is aligned with this since
       there is no defined depth with a 2d region input.
    :type depth_location: 3d vector
    :return: normalized 3d vector.
    :rtype: :class:`mathutils.Vector`
    """
    from mathutils import Vector

    coord_vec = region_2d_to_vector_3d(region, rv3d, coord)
    depth_location = Vector(depth_location)

    origin_start = region_2d_to_origin_3d(region, rv3d, coord)
    origin_end = origin_start + coord_vec

    if rv3d.is_perspective:
        from mathutils.geometry import intersect_line_plane
        viewinv = rv3d.view_matrix.inverted()
        view_vec = viewinv.col[2].copy()
        return intersect_line_plane(origin_start,
                                    origin_end,
                                    depth_location,
                                    view_vec, 1,
                                    )
    else:
        from mathutils.geometry import intersect_point_line
        return intersect_point_line(depth_location,
                                    origin_start,
                                    origin_end,
                                    )[0]



def location_3d_to_region_2d( coord ) :
    region = bpy.context.region
    rv3d = bpy.context.region_data
    perspective_matrix = rv3d.perspective_matrix

    prj = perspective_matrix @ Vector((coord[0], coord[1], coord[2], 1.0))
    if prj.w > 0.0:
        width_half = region.width / 2.0
        height_half = region.height / 2.0 

        return Vector((width_half + width_half * (prj.x / prj.w),
                       height_half + height_half * (prj.y / prj.w),
                       ))
    else:
        return None

def TransformBMVerts( obj , verts ) : 
    Item = collections.namedtuple('Item', ('vert', 'region' , 'world' ))
    region = bpy.context.region
    rv3d = bpy.context.region_data    

    halfW = region.width / 2.0
    halfH = region.height / 2.0
    matrix_world = obj.matrix_world
    perspective_matrix = rv3d.perspective_matrix

    def Proj2( vt ) :
        w = matrix_world @ vt.co 
        v = perspective_matrix @ Vector((w[0], w[1], w[2], 1.0))
        t = None if v.w < 0 else Vector( (halfW+halfW*(v.x/v.w) , halfH+halfH*(v.y/v.w) , ))
        return Item( vert = vt , region = t , world = w )

    vp = [ Proj2(p) for p in verts ]

    return vp


def getViewDir() :
    rv3d = bpy.context.region_data
    view_dir = -rv3d.view_matrix.inverted().col[2].xyz
    view_dir.normalize()
    return view_dir

# ビューポート平面上の点を計算する
def CalcPositionFromRegion( pos , pivot : Vector ):
    plane = Plane.from_screen( bpy.context , pivot )
    ray = Ray.from_screen( bpy.context , pos )
    p = plane.intersect_ray( ray )
    return p

def MovePointFromRegion( obj , element , orig , pos ):
    p = CalcPositionFromRegion( pos , orig ) - orig

    if isinstance( element , bmesh.types.BMVert ) :
        v = obj.matrix_world @ element.co + p
        element.co = obj.matrix_world.inverted() @ v
    elif isinstance( element , bmesh.types.BMFace ) :
        for vert in element.verts :
            v = obj.matrix_world @ vert.co + p
            vert.co = obj.matrix_world.inverted() @ v
    elif isinstance( element , bmesh.types.BMEdge ) :
        for vert in element.verts :
            v = obj.matrix_world @ vert.co + p
            vert.co = obj.matrix_world.inverted() @ v

    return orig + p
    
def MakePointFromRegion( obj , bm , pos , pivot : Vector ):
    p = CalcPositionFromRegion( pos , pivot )
    p = obj.matrix_world.inverted() @ p

    vert = bm.verts.new( p )

    return vert


def CalcRateEdgeRay( obj , context , edge , vert , coord , ray , dist ) :
    matrix = obj.matrix_world        
    v0 = vert.co
    v1 = edge.other_vert(vert).co
    p0 = location_3d_to_region_2d( matrix @ v0)
    p1 = location_3d_to_region_2d( matrix @ v1)
    intersects = mathutils.geometry.intersect_line_sphere_2d( p0 , p1 , coord , dist )
    if any(intersects) == False:
        return 0.0

    ray = Ray.from_screen( context , coord ).world_to_object( obj )
    h0 , h1 , d = ray.distance( Ray( v0 , (v1-v0) ) )

    dt =  (v0-v1).length
    d0 = (v0-h1).length
    d1 = (v1-h1).length
    if d0 > dt :
        return 1.0
    elif d1 > dt :
        return 0.0
    else :
        return max( 0 , min( 1 , d0 / dt ))        
