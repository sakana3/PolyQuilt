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
import bmesh
import math
import copy
import mathutils
import bpy_extras
import collections
from mathutils import *
from ..utils import pqutil

class QSnap :
    instance = None

    @classmethod
    def start( cls,context ) :
        cls.instance = cls(context)
        cls.update(context)

    @classmethod
    def exit(cls) :
        if cls.instance :
            del cls.instance

    @classmethod
    def is_active( cls ) :
        return cls.instance != None

    @classmethod
    def update(cls,context) :
        if cls.instance :
            cls.instance.__update(context)

    def __init__( self , context, snap_objects = 'Visible'  ) :
        self.objects_array = None
        self.bvh_list = None

    def __update( self , context ) :
        if context.scene.tool_settings.use_snap \
            and 'FACE' in context.scene.tool_settings.snap_elements :
                if self.bvh_list == None :
                    self.create_tree(context)
                else :
                    if set( self.bvh_list.keys() ) != set(self.snap_objects(context)) :
                        self.remove_tree()
                        self.create_tree(context)
        else :
            if self.bvh_list != None :
                self.remove_tree()

    @staticmethod
    def snap_objects( context ) :
        active_obj = context.active_object        
        objects = context.visible_objects
#           objects = context.selected_objects
        objects_array = [obj for obj in objects if obj != active_obj and obj.type == 'MESH']
        return objects_array

    def create_tree( self , context ) :
        if self.bvh_list == None :
            self.bvh_list = {}
            for obj in self.snap_objects(context):
                bvh = mathutils.bvhtree.BVHTree.FromObject(obj, context.evaluated_depsgraph_get() , epsilon = 0.0 )
                self.bvh_list[obj] = bvh

    def remove_tree( self ) :
        if self.bvh_list != None :
            for bvh in self.bvh_list.values():
                del bvh
        self.bvh_list = None


    @classmethod
    def view_adjust( cls , world_pos : mathutils.Vector ) -> mathutils.Vector :
        if cls.instance != None :
            ray = pqutil.Ray.from_world_to_screen( bpy.context , world_pos )
            location , norm , obj = cls.instance.__raycast( ray )
            if location != None :
                return location
        return world_pos

    @classmethod
    def adjust_verts( cls , obj , verts , is_fix_to_x_zero ) :
        if cls.instance != None :
            find_nearest =  cls.instance.__find_nearest
            matrix = obj.matrix_world
            for vert in verts :
                location , norm , obj = find_nearest( matrix @ vert.co )
                if location != None :
                    if is_fix_to_x_zero :
                        dist = bpy.context.scene.tool_settings.double_threshold                        
                        if abs(vert.co.x) <= dist :
                            location.x = 0.0
                            location , norm , obj = find_nearest( location )
                            location.x = 0.0
                    vert.co = location

    @classmethod
    def is_target( cls , world_pos : mathutils.Vector) -> bool :
        if cls.instance != None :
            ray = pqutil.Ray.from_world_to_screen( bpy.context , world_pos )
            location , normal , obj = cls.instance.__raycast( ray )
            if location != None :
                if (location - ray.origin).length >= (world_pos - ray.origin).length :
                    return True
                else :
                    ray_p = pqutil.Ray( world_pos , ray.vector )
                    inv_p = ray_p.invert
                    # ターゲットからビュー方向にレイを飛ばす
                    location_r , normal_r , obj_r = cls.instance.__raycast( ray_p )
                    location_i , normal_i , obj_i = cls.instance.__raycast( inv_p )
                    if obj_i != None and obj_r == None :
                        if obj_i == obj :
                            return True
                    if obj_r != None and obj_i == None :
                        if obj_r == obj :
                            return True
                    if obj_r == obj and obj_i == obj :
                        return True
                    if location_r != None and location_i != None :
                        if (location_r - world_pos).length <= (location_i - world_pos).length :
                            if obj_r == obj :
                                return True
                        else :
                            if obj_i == obj :
                                return True
                return False
        return True

    def __raycast( self , ray : pqutil.Ray ) :
        min_dist = math.inf
        location = None
        normal = None
        index = None
        if self.bvh_list :
            for obj , bvh in self.bvh_list.items():
                local_ray = ray.world_to_object( obj )
                hit = bvh.ray_cast( local_ray.origin , local_ray.vector )
                if None not in hit :
                    if hit[3] < min_dist :
                        matrix = obj.matrix_world
                        location = pqutil.transform_position( hit[0] , matrix )
                        normal = pqutil.transform_normal( hit[1] , matrix )
                        index =  hit[2]
                        min_dist = hit[3]

        return location , normal , index

    def __find_nearest( self, pos : mathutils.Vector ) :
        min_dist = math.inf
        location = None
        normal = None
        index = None
        if self.bvh_list :
            for obj , bvh in self.bvh_list.items():
                matrix = obj.matrix_world
                lp = pqutil.transform_position( pos , matrix )
                hits = bvh.find_nearest_range(lp)
                if None not in hits :
                    for hit in hits :
                        if hit[3] < min_dist :
                            location = pqutil.transform_position( hit[0] , matrix )
                            normal = pqutil.transform_normal( hit[1] , matrix )
                            index =  hit[2]
                            min_dist = hit[3]

        return location , normal , index
