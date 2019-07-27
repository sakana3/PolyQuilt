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

    @staticmethod
    def start( context ) :
        QSnap.instance = QSnap(context)
        QSnap.update(context)

    @staticmethod
    def exit() :
        if QSnap.instance :
            del QSnap.instance

    @staticmethod
    def update(context) :
        if QSnap.instance :
            QSnap.instance.__update(context)

    def __init__( self , context, snap_objects = 'Visible'  ) :
        self.objects_array = None
        self.bvh_list = None

    def __update( self , context ) :
        if context.scene.tool_settings.use_snap \
            and 'VOLUME' in context.scene.tool_settings.snap_elements :
                if self.bvh_list == None :
                    self.create_tree(context)
                else :
                    if set( self.bvh_list.keys() ) != set(self.snap_objects(context)) :
                        self.remove_tree()
                        self.create_tree(context)
        else :
            if self.bvh_list != None :
                self.remove_tree()

    def snap_objects( self , context ) :
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
            hit = cls.instance.raycast_hit( ray )
            if hit != None :
                return hit
        return world_pos

    @classmethod
    def adjust( cls , world_pos : mathutils.Vector ) -> mathutils.Vector :
        if cls.instance != None :
            ray = pqutil.Ray.from_world_to_screen( bpy.context , world_pos )
            hit = cls.instance.raycast_hit( ray )
            if hit != None :
                return hit
        return world_pos

    def raycast_hit( self , ray : pqutil.Ray ) :
        min_dist = math.inf
        location = None
        if self.bvh_list :
            for obj , bvh in self.bvh_list.items():
                local_ray = ray.world_to_object( obj )
                hit = bvh.ray_cast( local_ray.origin , local_ray.vector )
                if None not in hit :
                    if hit[3] < min_dist :
                        location = hit[0]
                        min_dist = hit[3]

        return location

    def find_near( self, pos : mathutils.Vector ) :
        return mathutils.Vector( (0,0,0) )
