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

class SubToolEdgeExtrude(SubTool) :
    name = "EdgeExtrudeTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        self.currentEdge = target
        self.startPos = target.hitPosition
        self.targetPos = target.hitPosition
        self.screen_space_plane = handleutility.Plane.from_screen( bpy.context , target.hitPosition )
        self.move_plane = self.screen_space_plane
        self.startMousePos = copy.copy(target.coord)
        self.subTarget = ElementItem.Empty()
        self.subVertTarget = [ ElementItem.Empty() , ElementItem.Empty() ]
        self.is_center_snap = False
        self.is_sub_center_snaps = [False,False]

        self.ignoreVerts = []
        for face in self.currentEdge.element.link_faces :
            self.ignoreVerts.extend(face.verts)
        self.ignoreVerts = set(self.ignoreVerts )

        self.ignoreEdges = []
        for face in self.currentEdge.element.link_faces :
            self.ignoreEdges.extend(face.edges)
        self.ignoreEdges = set(self.ignoreEdges )

    @staticmethod
    def Check( target ) :
        return target.element.is_boundary or target.element.is_manifold == False

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            rayS = handleutility.Ray.from_screen( context , self.startMousePos )
            rayG = handleutility.Ray.from_screen( context , self.mouse_pos )      
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )
            move = (vG - vS)
            self.targetPos = self.startPos + move
            dist = self.preferences.distance_to_highlight

            # X=0でのスナップをチェック
            self.is_center_snap = False
            if self.bmo.is_mirror_mode :
                self.is_center_snap = self.bmo.is_x0_snap( self.targetPos )

            # スナップする辺を探す
            if self.is_center_snap == False :
                self.subTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreEdges )            
            else :
                self.subTarget = ElementItem.Empty()

            # 頂点のスナップ先を探す
            self.is_sub_center_snaps = [False,False]
            if self.subTarget.isEmpty :
                for i in range(2) :
                    p = self.bmo.local_to_world_pos( self.currentEdge.element.verts[i].co ) + move
                    if self.is_center_snap : 
                        p = self.bmo.zero_pos_w2l(p)
                    c = handleutility.location_3d_to_region_2d(p)
                    # スナップする頂点を探す
                    e = self.bmo.PickElement( c , dist , edgering=True , backface_culling = True , elements=['VERT'], ignore=self.ignoreVerts )
                    self.subVertTarget[i] = e
                    # X=０境界でのスナップをチェック
                    if self.is_center_snap == False and self.subVertTarget[i].isEmpty and self.bmo.is_mirror_mode and self.bmo.is_x0_snap( p ) :
                        self.is_sub_center_snaps[i] = True
                        self.subVertTarget[i] = ElementItem.Empty()
                # 両点がスナップするなら辺スナップに変更
                if all(self.is_sub_center_snaps) :
                    self.is_center_snap = True
                    self.is_sub_center_snaps = [False,False]
            else :
                self.subVertTarget = [ ElementItem.Empty() , ElementItem.Empty() ]
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
        size = self.preferences.highlight_vertex_size
        for vert in self.subVertTarget :
            if vert.isVert :            
                pos = handleutility.location_3d_to_region_2d( self.bmo.local_to_world_pos( vert.element.co ) )
                draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

        for i in range(2) :
            if self.is_sub_center_snaps[i] :
                move = self.targetPos - self.startPos
                p = self.bmo.local_to_world_pos( self.currentEdge.element.verts[i].co ) + move
                pos = handleutility.location_3d_to_region_2d( self.bmo.mirror_pos_w2l(p) )
                draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

        if self.is_center_snap :
            pos = handleutility.location_3d_to_region_2d( self.bmo.zero_pos_w2l(self.targetPos) )
            draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        move = self.targetPos - self.startPos
        p0 = self.bmo.local_to_world_pos(self.currentEdge.element.verts[0].co)
        p1 = self.bmo.local_to_world_pos(self.currentEdge.element.verts[1].co)
        t0 = p0 + move
        t1 = p1 + move

        if self.is_center_snap :
            t0 = self.bmo.zero_pos_w2l(t0)
            t1 = self.bmo.zero_pos_w2l(t1)

        if self.is_sub_center_snaps[0] :
            t0 = self.bmo.zero_pos_w2l(t0)
        if self.is_sub_center_snaps[1] :
            t1 = self.bmo.zero_pos_w2l(t1)

        if self.subTarget.isEdge :
            v0,v1 = self.AdsorptionEdge(t0,t1,self.subTarget.element)
            t0 = self.bmo.local_to_world_pos(v0.co)
            t1 = self.bmo.local_to_world_pos(v1.co)
            if v0 in self.currentEdge.element.verts :
                lines = (p0,t1,p1,p0)
                polys = (p0,t1,p1)
            elif v1 in self.currentEdge.element.verts :
                lines = (p0,t0,p1,p0)
                polys = (p0,t0,p1)
            else :
                lines = (p0,t0,t1,p1,p0)
                polys = (p0,t0,t1,p1)
        else :
            if self.subVertTarget[0].isVert :
                t0 = self.bmo.local_to_world_pos(self.subVertTarget[0].element.co)
            if self.subVertTarget[1].isVert :
                t1 = self.bmo.local_to_world_pos(self.subVertTarget[1].element.co)
            lines = (p0,t0,t1,p1,p0)
            polys = (p0,t0,t1,p1)

        draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.5), hide_alpha = 0.5  )        
        draw_util.draw_lines3D( context , lines , self.color_create(1.0) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 0.25 )        
        if self.subTarget.isEdge :
            draw_util.draw_lines3D( context , [ t0 , t1 ] , (1,1,1,1) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

        if self.bmo.is_mirror_mode :
            lines = [ self.bmo.mirror_pos_w2l(p) for p in lines ]
            polys = [ self.bmo.mirror_pos_w2l(p) for p in polys ]
            draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.25), hide_alpha = 0.25  )        
            draw_util.draw_lines3D( context , lines , self.color_create(1.0) , 1 , primitiveType = 'LINE_STRIP' , hide_alpha = 0.25 )        
            if self.is_center_snap :            
                draw_util.draw_lines3D( context , [ t0 , t1 ] , (1,1,1,1) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

    def AdsorptionEdge( self , p0 , p1 , edge ) :
        st0 = handleutility.location_3d_to_region_2d(p0)
        st1 = handleutility.location_3d_to_region_2d(p1)
        se0 = handleutility.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[0].co))
        se1 = handleutility.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[1].co))
        if (st0-se0).length + (st1-se1).length > (st0-se1).length + (st1-se0).length :
            t0 = self.subTarget.element.verts[1]
            t1 = self.subTarget.element.verts[0]
        else :
            t0 = self.subTarget.element.verts[0]
            t1 = self.subTarget.element.verts[1]

        return t0,t1

    def MakePoly( self ) :
        move = self.targetPos - self.startPos
        edge = self.currentEdge.element
        p0 = self.bmo.local_to_world_pos(edge.verts[0].co) + move
        p1 = self.bmo.local_to_world_pos(edge.verts[1].co) + move

        if self.is_center_snap :
            p0 = self.bmo.zero_pos_w2l(p0)
            p1 = self.bmo.zero_pos_w2l(p1)

        if self.is_sub_center_snaps[0] :
            p0 = self.bmo.zero_pos_w2l(p0)
        if self.is_sub_center_snaps[1] :
            p1 = self.bmo.zero_pos_w2l(p1)

        if self.subTarget.isEdge :
            v0,v1 = self.AdsorptionEdge(p0,p1,self.subTarget.element)
            if v0 in edge.verts :
                verts = [edge.verts[0],edge.verts[1],v1]
            elif v1 in edge.verts :
                verts = [edge.verts[0],edge.verts[1],v0]
            else :
                verts = [edge.verts[0],edge.verts[1],v1,v0]
            normal = None
        else :
            if self.subVertTarget[0].isVert :
                v0 = self.subVertTarget[0].element
            else :
                v0 = self.bmo.AddVertexWorld( p0 )

            if self.subVertTarget[1].isVert :
                v1 = self.subVertTarget[1].element
            else:
                v1 = self.bmo.AddVertexWorld( p1 )
            verts = [edge.verts[0],edge.verts[1],v1,v0]
            self.bmo.UpdateMesh()

        normal = None
        if edge.link_faces :
            for loop in edge.link_faces[0].loops :
                if edge == loop.edge :
                    if loop.vert == edge.verts[0] :
                        verts.reverse()
        else :
            normal = handleutility.getViewDir()

        face = self.bmo.AddFace( verts , normal )
        self.bmo.UpdateMesh()
