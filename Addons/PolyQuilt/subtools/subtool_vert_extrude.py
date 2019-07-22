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
import mathutils
import copy
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from ..dpi import *
from .subtool import SubTool

class SubToolVertExtrude(SubTool) :
    name = "VertExtrudeTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentVert = target
        self.startPos = target.hitPosition
        self.targetPos = target.hitPosition
        self.screen_space_plane = handleutility.Plane.from_screen( bpy.context , target.hitPosition )
        self.move_plane = self.screen_space_plane
        self.startMousePos = copy.copy(target.coord)
        self.subTarget = ElementItem.Empty()
        self.ignore = []
        for face in self.currentVert.element.link_faces :
            self.ignore.extend(face.verts)
        self.ignore = set(self.ignore )

    @staticmethod
    def Check( target ) :
        edges = [ e for e in target.element.link_edges if len(e.link_faces) == 1 ]
        if len(edges) == 2 :
            if set(edges[0].link_faces) == set(edges[1].link_faces) :
                return False
            return True
        return False

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            rayS = handleutility.Ray.from_screen( context , self.startMousePos )
            rayG = handleutility.Ray.from_screen( context , self.mouse_pos )      
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )
            move = (vG - vS) 
            self.targetPos = self.startPos + move
            self.subTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , edgering=True , backface_culling = True , elements=['VERT'] , ignore = self.ignore )      

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                self.MakePoly()
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        if self.subTarget.isVert :            
            size = self.preferences.highlight_vertex_size
            pos = handleutility.location_3d_to_region_2d( self.bmo.local_to_world_pos( self.subTarget.element.co ) )
            draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        vert = self.currentVert.element
        edges = [ edge for edge in vert.link_edges if edge.is_boundary ]

        p0 = self.bmo.local_to_world_pos(vert.co)
        p1 = self.bmo.local_to_world_pos(edges[0].other_vert(vert).co)
        if self.subTarget.isVert :
            p2 = self.bmo.local_to_world_pos(self.subTarget.element.co)
        else :
            move = self.targetPos - self.startPos
            p2 = p0 + move
        p3 = self.bmo.local_to_world_pos(edges[1].other_vert(vert).co)

        lines = (p0,p1,p2,p3,p0)
        polys = (p0,p1,p2,p3)

        draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.5), hide_alpha = 0.25  )        
        draw_util.draw_lines3D( context , lines , self.color_create(1.0) , 1 , primitiveType = 'LINE_STRIP' , hide_alpha = 0.25 )        

    def MakePoly( self ) :
        vert = self.currentVert.element        
        edges = [ edge for edge in vert.link_edges if edge.is_boundary ]        
        if self.subTarget.isVert :        
            v0 = self.subTarget.element    
        else :
            move = self.targetPos - self.startPos        
            p0 = self.bmo.local_to_world_pos(vert.co) + move        
            v0 = self.bmo.AddVertexWorld( p0 )       
        v1 = edges[0].other_vert(vert)
        v2 = edges[1].other_vert(vert)

        verts = [v2,vert,v1,v0]

        normal = None
        edge = edges[0]
        if edge.link_faces :
            for loop in edge.link_faces[0].loops :
                if edge == loop.edge :
                    if loop.vert == vert :
                        verts.reverse()
                        break
        else :
            normal = handleutility.getViewDir()

        self.bmo.AddFace( verts , normal )        
        self.bmo.UpdateMesh()
