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
import time
import mathutils
import bmesh
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubTool
from .subtool_util import move_component_module

class SubToolMove(SubTool) :
    name = "MoveTool"

    def __init__(self,op,startTarget,startMousePos, move_type = None, mirror = None  ) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.currentTarget.set_snap_div( 0 )        
        self.snapTarget = ElementItem.Empty()
        self.target_orig = { v : v.co.copy()  for v in startTarget.verts if v != None }

        mt = move_component_module.check_move_type( startTarget , op.move_type , move_type )
        self.move_component_module = move_component_module( self.bmo , startTarget , startMousePos , mt , self.preferences.fix_to_x_zero )
        self.move_component_module.set_geoms( [startTarget.element] )

        self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )
        self.MoveTo( bpy.context , startMousePos )
        self.bmo.UpdateMesh( changeTopology = False )
        self.is_snap = False

        # ignore snap target
        self.ignoreSnapTarget = []
        if self.currentTarget.isVert :
            self.ignoreSnapTarget = [self.currentTarget.element]
#               self.ignoreSnapTarget.extend( self.currentTarget.element.link_faces )
            self.ignoreSnapTarget.extend( self.currentTarget.element.link_edges )
#                for face in self.currentTarget.element.link_faces :
#                    self.ignoreSnapTarget.extend( face.verts )
            if self.currentTarget.mirror is not None :
                self.ignoreSnapTarget.append( self.currentTarget.mirror )
                self.ignoreSnapTarget.extend( self.currentTarget.mirror.link_edges )
        elif self.currentTarget.isEdge :
            self.ignoreSnapTarget = [self.currentTarget.element ]
            self.ignoreSnapTarget.extend( self.currentTarget.element.verts[0].link_edges )
            self.ignoreSnapTarget.extend( self.currentTarget.element.verts[1].link_edges )
            for face in self.currentTarget.element.link_faces :
                self.ignoreSnapTarget.extend( face.edges )

            if self.currentTarget.mirror is not None :
                self.ignoreSnapTarget.append( self.currentTarget.mirror )

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.MoveTo( context , self.mouse_pos )

            self.is_snap = False
            if self.operator.is_snap :
                dist = self.preferences.distance_to_highlight
                if self.currentTarget.isVert and self.move_component_module.move_ray == None :# and ( self.currentTarget.element.is_manifold is False or self.currentTarget.element.is_boundary )  :
                    self.snapTarget = self.bmo.PickElement( self.mouse_pos , dist , self.ignoreSnapTarget , elements = ['VERT'] )

                    if self.snapTarget.isVert \
                            and self.currentTarget.element != self.snapTarget.element \
                            and (self.preferences.fix_to_x_zero and self.currentTarget.is_x_zero and self.snapTarget.is_x_zero is False ) is False :
                        self.is_snap = True
                        self.currentTarget.element.co = self.snapTarget.element.co
                        if self.currentTarget.mirror is not None :
                            self.currentTarget.mirror.co = self.bmo.mirror_pos(self.currentTarget.element.co)
                    else :
                        self.snapTarget = ElementItem.Empty()

                    if self.currentTarget.mirror is not None :
                        if self.bmo.check_near(self.currentTarget.element.co ,self.currentTarget.mirror.co ) :
                            x_zero = self.bmo.zero_pos(self.currentTarget.element.co)
                            self.currentTarget.element.co = x_zero
                            self.currentTarget.mirror.co = x_zero
                            self.is_snap = True
                    else :
                        if self.bmo.is_mirror_mode :
                            mp = self.bmo.mirror_pos( self.currentTarget.element.co )
                            if self.bmo.check_near(self.currentTarget.element.co , mp ) :
                                self.currentTarget.element.co = self.bmo.zero_pos(mp)
                                self.is_snap = True

                elif self.currentTarget.isEdge and self.move_component_module.move_ray == None :
                    self.snapTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreSnapTarget ) 
                    if self.snapTarget.isEdge :
                        p0 = self.bmo.local_to_2d( self.currentTarget.element.verts[0].co )
                        p1 = self.bmo.local_to_2d( self.currentTarget.element.verts[1].co )
                        t0 = self.bmo.local_to_2d( self.snapTarget.element.verts[0].co )
                        t1 = self.bmo.local_to_2d( self.snapTarget.element.verts[1].co )
                        if (p0-t0).length + (p1-t1).length < (p0-t1).length + (p1-t0).length :
                            self.currentTarget.element.verts[0].co = self.snapTarget.element.verts[0].co
                            self.currentTarget.element.verts[1].co = self.snapTarget.element.verts[1].co
                        else :
                            self.currentTarget.element.verts[0].co = self.snapTarget.element.verts[1].co
                            self.currentTarget.element.verts[1].co = self.snapTarget.element.verts[0].co
                        if self.currentTarget.mirror is not None :
                            self.currentTarget.mirror.verts[0].co = self.bmo.mirror_pos(self.currentTarget.element.verts[1].co)
                            self.currentTarget.mirror.verts[1].co = self.bmo.mirror_pos(self.currentTarget.element.verts[0].co)

                    if self.currentTarget.mirror is not None :
                        if self.bmo.is_x0_snap( self.currentTarget.hitPosition ) :
                            self.currentTarget.element.verts[0].co = self.bmo.zero_pos(self.currentTarget.element.verts[0].co)
                            self.currentTarget.element.verts[1].co = self.bmo.zero_pos(self.currentTarget.element.verts[1].co)
                            self.currentTarget.mirror.verts[0].co = self.bmo.zero_pos(self.currentTarget.mirror.verts[0].co)
                            self.currentTarget.mirror.verts[1].co = self.bmo.zero_pos(self.currentTarget.mirror.verts[1].co)
            self.bmo.UpdateMesh( changeTopology = False )

        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                threshold = bpy.context.scene.tool_settings.double_threshold
                verts = set( self.move_component_module.mirror_set.keys() ) | set( v for v in self.move_component_module.mirror_set.values() if v != None )
                if self.snapTarget.isVert :
                    verts = verts | self.bmo.find_near(self.bmo.obj.matrix_world @ self.snapTarget.element.co)
                elif self.snapTarget.isEdge : 
                    verts = verts | self.bmo.find_near(self.bmo.obj.matrix_world @ self.snapTarget.element.verts[0].co)
                    verts = verts | self.bmo.find_near(self.bmo.obj.matrix_world @ self.snapTarget.element.verts[1].co)
                if len(verts) > 1 :
                    bmesh.ops.remove_doubles( self.bmo.bm , verts = [ v for v in verts if v ] , dist = threshold )
                    self.bmo.UpdateMesh()

                return 'FINISHED'
        else :
            self.move_component_module.update(event)

        self.debugStr = str(self.snapTarget.element)
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        if self.is_snap :
            size = self.preferences.highlight_vertex_size
            pos = pqutil.location_3d_to_region_2d( self.bmo.local_to_world_pos( self.currentTarget.element.co ) )
            draw_util.draw_circle2D( pos , size + 1.5 , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        self.currentTarget.Draw( self.bmo.obj , self.color_highlight()  , self.preferences )
        if self.snapTarget.isNotEmpty :
            self.snapTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

        self.move_component_module.draw_3D( context )

    def MoveTo( self ,context ,  mouse_pos ) :
        move = self.move_component_module.move_to( mouse_pos )
        self.move_component_module.update_geoms( move )
        return

            