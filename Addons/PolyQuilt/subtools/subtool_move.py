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
from .subtool import SubTool

class SubToolMove(SubTool) :
    name = "MoveTool"

    def __init__(self,op,startTarget,startMousePos) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.subTarget = ElementItem.Empty()
        self.startMousePos = startMousePos
        self.mouse_pos = startMousePos
        self.startPos = startTarget.hitPosition
        p = handleutility.MovePointFromRegion( self.bmo.obj , self.currentTarget.element ,self.currentTarget.hitPosition, self.mouse_pos )
        self.currentTarget = ElementItem.FormElement( self.currentTarget.element , p )
        self.bmo.UpdateMesh()

        if startTarget.isVert :
            self.target_verts = [(startTarget.element, mathutils.Vector( startTarget.element.co) ) ]
        elif startTarget.isEdge :
            self.target_verts = [ (v, mathutils.Vector(v.co)) for v in startTarget.element.verts ]
        elif startTarget.isFace :
            self.target_verts = [ (v, mathutils.Vector(v.co)) for v in startTarget.element.verts ]
        else :
            self.target_verts = []

        self.normal_ray = handleutility.Ray( self.startPos , startTarget.normal ).to_object_space( self.bmo.obj )
        self.normal_ray.origin = self.startPos
#       print( self.move_normal )
        self.move_plane = handleutility.Plane.from_screen( bpy.context , startTarget.hitPosition )
        self.move_type = 'FREE'
        self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )        
        self.ChangeRay(op.move_type)
        self.repeat = False

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.MoveTo( context , self.mouse_pos )

            if self.currentTarget.isVert and self.move_ray == None :# and ( self.currentTarget.element.is_manifold is False or self.currentTarget.element.is_boundary )  :
                tmp = self.subTarget
                ignore = [self.currentTarget.element]
#               ignore.extend( self.currentTarget.element.link_faces )
                ignore.extend( self.currentTarget.element.link_edges )
#                for face in self.currentTarget.element.link_faces :
#                    ignore.extend( face.verts )
                self.subTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , ignore )

                if self.subTarget.isVert and self.currentTarget.element != self.subTarget.element :
                    self.currentTarget.element.co = self.subTarget.element.co
                    self.currentTarget = ElementItem.FormVert( self.currentTarget.element )                    
                else :
                    self.subTarget = ElementItem.Empty()

            self.bmo.UpdateMesh()
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.currentTarget.isVert and self.subTarget.isVert :
                    v0 = self.currentTarget.element
                    v1 = self.subTarget.element
#                   bmesh.utils.vert_splice( v0 , v1 )
                    bmesh.ops.pointmerge( self.bmo.bm , verts = ( v0 , v1 ) , merge_co = v1.co )
                    self.bmo.UpdateMesh()                    
                return 'FINISHED'
        elif event.value == 'PRESS' :
            if self.repeat == False :
                if event.type == 'X' :
                    self.ChangeRay( 'X' )
                elif event.type == 'Y' :
                    self.ChangeRay( 'Y' )
                elif event.type == 'Z' :
                    self.ChangeRay( 'Z' )
                elif event.type == 'N' :
                    self.ChangeRay( 'NORMAL' )
            self.repeat = True
        elif event.value == 'RELEASE' :
            self.repeat = False

        self.debugStr = str(self.subTarget.element)

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        self.currentTarget.Draw2D( self.bmo.obj , self.color_highlight()  , self.preferences )
        self.subTarget.Draw2D( self.bmo.obj , self.color_highlight() , self.preferences )

        if self.move_ray != None :
            v1 = self.move_ray.origin + self.move_ray.vector * 500.0 
            v2 = self.move_ray.origin - self.move_ray.vector * 500.0 
            v1 = handleutility.location_3d_to_region_2d( v1 )
            v2 = handleutility.location_3d_to_region_2d( v2 )
            draw_util.draw_lines2D( (v1,v2) , self.move_color )
    

    def ChangeRay( self , move_type ) :
        self.move_ray = None
        self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )

        if move_type == self.move_type :
            self.move_ray = None
            move_type = 'FREE'
        if move_type == 'X' :
            self.move_ray = handleutility.Ray( self.currentTarget.hitPosition , mathutils.Vector( (1,0,0) ) )
            self.move_color = ( 1.0 , 0.0 ,0.0 ,1.0  )
        elif move_type == 'Y' :
            self.move_ray = handleutility.Ray( self.currentTarget.hitPosition , mathutils.Vector( (0,1,0) ) )
            self.move_color = ( 0.0 , 1.0 ,0.0 ,1.0  )
        elif move_type == 'Z' :
            self.move_ray = handleutility.Ray( self.currentTarget.hitPosition , mathutils.Vector( (0,0,1) ) )
            self.move_color = ( 0.0 , 0.0 ,1.0 ,1.0  )
        elif move_type == 'NORMAL' :
            self.move_ray = self.normal_ray
            self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )

        self.move_type = move_type

    def MoveTo( self ,context ,  mouse_pos ) :
        move = mathutils.Vector( (0.0,0.0,0.0) )

        if self.move_ray != None :
            ray = handleutility.Ray.from_screen( context , mouse_pos )
            p0 , p1 , d = self.move_ray.distance( ray )

            move = ( p0 - self.move_ray.origin )
        elif self.move_plane != None :
            rayS = handleutility.Ray.from_screen( context , self.startMousePos )
            rayG = handleutility.Ray.from_screen( context , mouse_pos )
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )

            move = (vG - vS)

        for vert in self.target_verts :
            p =  self.bmo.obj.matrix_world @vert[1] + move
            vert[0].co = self.bmo.obj.matrix_world.inverted() @ p
#           self.bmo.set_positon( vert[0] , p )

            


