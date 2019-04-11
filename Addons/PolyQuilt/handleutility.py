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

        out = Vector(((2.0 * coord[0] / region.width) - 1.0,
                      (2.0 * coord[1] / region.height) - 1.0,
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
    rv3d = bpy.context.space_data.region_3d
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
    Item = collections.namedtuple('Item', ('vert', 'region' ))
    region = bpy.context.region
    rv3d = bpy.context.space_data.region_3d    

    halfW = region.width / 2.0
    halfH = region.height / 2.0
    matrix = rv3d.perspective_matrix @ obj.matrix_world

    def Proj2( vt ) :
        v = matrix @ Vector((vt.co[0], vt.co[1], vt.co[2], 1.0))
        t = None if v.w < 0 else Vector( (halfW+halfW*(v.x/v.w) , halfH+halfH*(v.y/v.w) , ))
        return Item( vert = vt , region = t )

    vp = [ Proj2(p) for p in verts ]

    return vp

#RayとPlaneの交点を求める
def IntersectPlaneToRay( planeP : Vector  , planeN : Vector , rayP: Vector  ,rayD : Vector ) :
    d = planeP.dot( -planeN )
    t = -(d + rayP.z * planeN.z + rayP.y * planeN.y + rayP.x * planeN.x) / (rayD.z * planeN.z + rayD.y * planeN.y + rayD.x * planeN.x)
    x = rayP + rayD * t

    return x

def getViewDir() :
    rv3d = bpy.context.space_data.region_3d
    view_dir = -rv3d.view_matrix.inverted().col[2].xyz
    view_dir.normalize()
    return view_dir

# ビューポート平面上の点を計算する
def CalcPositionFromRegion( pos , pivot : Vector ):
    region = bpy.context.region
    rv3d = bpy.context.space_data.region_3d

    view_dir = -rv3d.view_matrix.inverted().col[2].xyz
    view_dir.normalize()
#   ray_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, pos)
#   ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, pos)
    ray_vector = region_2d_to_vector_3d(region, rv3d, pos)
    ray_origin = region_2d_to_origin_3d(region, rv3d, pos)
    
    p = IntersectPlaneToRay( pivot , -view_dir , ray_origin , ray_vector )

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

def calc_object_space( obj , origin , vector ) :
    matrix = obj.matrix_world
    origin_obj = matrix.inverted() @ origin
    vector_obj = matrix.transposed().to_3x3() @ vector
    return origin_obj , vector_obj


def calc_ray( context , coord ) :
    rv3d = context.space_data.region_3d    
    region = context.region

#   view_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
#   ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    view_vector = region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = region_2d_to_origin_3d(region, rv3d, coord)

    return ray_origin , view_vector


def calc_object_space_ray( context , obj , coord ) :
    ray_origin , view_vector = calc_ray(context,coord)
    return calc_object_space(obj,ray_origin,view_vector)


# 点Pと線(AB)の距離
# # https://tokibito.hatenablog.com/entry/20121227/1356581559
def Distance_P2L_NP( P : Vector , A : Vector , B : Vector ) :
    u = numpy.array([B.x - A.x, B.y - A.y])
    v = numpy.array([P.x - A.x, P.y - A.y])
    L = abs(numpy.cross(u, v) / numpy.linalg.norm(u))
    return L

def Distance_P2L( P : Vector , A : Vector , B : Vector ) ->float :
    a = B - A
    t = A - P
    r = a.length_squared
    tt = -a.dot(t)
    if tt < 0 :
        return t.length_squared
    elif tt > r :
        return (B-P).length_squared

    f = a.x - a.y
    return (f*f)/r


# RayとRayの一番近い距離
# https://stackoverflow.com/questions/29188686/finding-the-intersect-location-of-two-rays
# http://marupeke296.com/COL_3D_No19_LinesDistAndPos.html
def RayDistAndPos( p1 : Vector , v1 : Vector  , p2 : Vector  , v2 : Vector  ) :
    if v1.cross(v2).length_squared < 0.000001 :
        return None,None, p1.cross(p2).length

    Dv = v1.dot(v2)
    D1 = (p2-p1).dot(v1)
    D2 = (p2-p1).dot(v2)

    t1 = ( D1 - D2 * Dv ) / ( 1.0 - Dv * Dv )
    t2 = ( D2 - D1 * Dv ) / ( Dv * Dv - 1.0 )

    Q1 = p1 + v1 * t1
    Q2 = p2 + v2 * t2

    return Q1,Q2,(Q2 - Q1).length



