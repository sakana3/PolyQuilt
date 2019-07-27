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

class QSnap :
    instance = None

    @staticmethod
    def start( context ) :
        QSnap.instance = QSnap(context)
        QSnap.instance.update(context)

    @staticmethod
    def exit() :
        if QSnap.instance :
            del QSnap.instance


    def __init__( self , context, snap_objects = 'Visible'  ) :
        self.objects_array = None
        self.bvh_list = None

    def update( self , context ) :
        if context.scene.tool_settings.use_snap \
            and 'VOLUME' in context.scene.tool_settings.snap_elements :
                if self.bvh_list == None :
                    self.create_tree(context)
        else :
            if self.bvh_list != None :
                self.bvh_list = None

    def create_tree( self , context ) :
        if self.bvh_list == None :
            self.bvh_list = {}
            active_obj = context.active_object        
#           objects = context.visible_objects
            objects = context.selected_objects
            self.objects_array = [obj for obj in objects if obj != active_obj and obj.type == 'MESH']

            for obj in self.objects_array:
                bvh = mathu.bvhtree.BVHTree.FromObject(obj, context.evaluated_depsgraph_get())
                self.bvh_list[obj].bvh

    def raycast_hit( self , pos : mathutils.Vector , nrm : mathutils.Vector ) :
        if self.bvh_list :
            for obj , bch in self.bvh_list:
                pass

        return mathutils.Vector( (0,0,0) )

    def find_near( self, pos : mathutils.Vector ) :
        return mathutils.Vector( (0,0,0) )
