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
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubTool

class SubToolEdgeExtrude(SubTool) :
    name = "EdgeExtrudeTool"

    def __init__(self,op, target : ElementItem, is_loop : bool = False ) :
        super().__init__(op)
        self.currentEdge = target
        self.startPos = target.hitPosition.copy()
        self.targetPos = target.hitPosition.copy()
        self.screen_space_plane = pqutil.Plane.from_screen( bpy.context , target.hitPosition )
        self.move_plane = self.screen_space_plane
        self.startMousePos = copy.copy(target.coord)
        self.snapTarget = ElementItem.Empty()
        self.is_center_snap = False

        self.ignoreVerts = []
        for face in self.currentEdge.element.link_faces :
            self.ignoreVerts.extend(face.verts)
        self.ignoreVerts = set(self.ignoreVerts )

        self.ignoreEdges = []
        for face in self.currentEdge.element.link_faces :
            self.ignoreEdges.extend(face.edges)
        self.ignoreEdges = set(self.ignoreEdges )

        self.newEdge = [ self.bmo.local_to_world_pos( v.co ) for v in self.currentEdge.element.verts ]


    @staticmethod
    def Check( root ,target ) :
        return target.element.is_boundary or target.element.is_manifold == False

    def CalcFin( self , context ,edge , move ) :
        v0 = self.bmo.local_to_world_pos(edge.verts[0].co)
        v1 = self.bmo.local_to_world_pos(edge.verts[1].co)

        region = context.region
        rv3d = context.region_data
        view_matrix = rv3d.view_matrix
        view_vector = rv3d.view_rotation.to_matrix() @ mathutils.Vector((0.0, 0.0, -1.0))            

        f0 = v0 - self.startPos
        f1 = v1 - self.startPos

        if self.operator.extrude_mode != 'PARALLEL' :
            vp = [ view_matrix @ v for v in (v0,v1) ]
            vs = [ mathutils.Vector(( v.x , v.y , 0.0)) for v in vp ]
            n = (vs[1] - vs[0]).normalized()     
            perpendicular = view_vector.cross( n.xyz ).normalized()

            nm = ( view_matrix.to_3x3() @ move ).xy.normalized()

            dot = perpendicular.x * nm.x + perpendicular.y * nm.y      # dot product between [x1, y1] and [x2, y2]
            if dot < 0: 
                perpendicular = -perpendicular

            r0 = math.atan2( nm.y , nm.x )
            r1 = math.atan2( perpendicular.y , perpendicular.x )

            q0 = mathutils.Quaternion( view_vector , r0 )
            q1 = mathutils.Quaternion( view_vector , r1 )

            q = q0.rotation_difference(q1)

            if self.operator.extrude_mode == 'BEND' :
                f0 = q.to_matrix() @ f0
                f1 = q.to_matrix() @ f1
            else :
                f0 = q.to_matrix() @ q.to_matrix() @ f0
                f1 = q.to_matrix() @ q.to_matrix() @ f1

        p0 = self.targetPos + f0
        p1 = self.targetPos + f1
        p0 = QSnap.view_adjust(p0)
        p1 = QSnap.view_adjust(p1)
        return [p0,p1]

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            rayS = pqutil.Ray.from_screen( context , self.startMousePos )
            rayG = pqutil.Ray.from_screen( context , self.mouse_pos )      
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )
            move = (vG - vS)
            self.targetPos = self.startPos + move
#           self.targetPos = QSnap.view_adjust(self.targetPos)
#           move = self.targetPos - self.startPos

            dist = self.preferences.distance_to_highlight

            self.newEdge = self.CalcFin( context , self.currentEdge.element , move )

            if self.operator.is_snap :
                # X=0でのスナップをチェック
                self.is_center_snap = False
                if self.bmo.is_mirror_mode :
                    if not self.currentEdge.is_straddle_x_zero :
                        self.is_center_snap = self.bmo.is_x0_snap( self.targetPos )
                        if self.bmo.is_x0_snap( self.targetPos ) :
                            self.newEdge = [ self.bmo.zero_pos_w2l(p) for p in self.newEdge ]
                    else :
                        l0 = self.bmo.world_to_local_pos( self.newEdge[0] )
                        l1 = self.bmo.world_to_local_pos( self.newEdge[1] )
                        max = abs(l0.x) if abs(l0.x) > abs(l1.x) else abs(l1.x)
                        l0.x = max if self.currentEdge.element.verts[0].co.x > 0 else -max
                        l1.x = max if self.currentEdge.element.verts[1].co.x > 0 else -max
                        self.newEdge = [ self.bmo.local_to_world_pos(l0) , self.bmo.local_to_world_pos(l1) ]

                # スナップする辺を探す
                if self.is_center_snap == False :
                    self.snapTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreEdges )         
                    if self.bmo.is_mirror_mode and self.snapTarget.isEdge and self.currentEdge.is_straddle_x_zero :
                        if not self.snapTarget.is_straddle_x_zero :
                            self.snapTarget = ElementItem.Empty()                        
                    if self.snapTarget.isEdge :
                        self.newEdge = self.AdsorptionEdge( self.newEdge[0] , self.newEdge[1] ,  self.snapTarget.element )
                else :
                    self.snapTarget = ElementItem.Empty()

                # 頂点のスナップ先を探す
                if self.snapTarget.isEmpty :
                    for i in range(2) :
                        p = self.newEdge[i]
                        # スナップする頂点を探す
                        c = pqutil.location_3d_to_region_2d(p)
                        e = self.bmo.PickElement( c , dist , edgering=True , backface_culling = True , elements=['VERT'], ignore=self.ignoreVerts )
                        if e.isVert :
                            self.newEdge[i] = e.element
                        # X=０境界でのスナップをチェック
                        if not self.is_center_snap and e.isEmpty and self.bmo.is_mirror_mode and self.bmo.is_x0_snap( p ) and not self.currentEdge.is_straddle_x_zero :
                            self.newEdge[i] = self.bmo.zero_pos_w2l(self.newEdge[i])

                    if self.bmo.is_mirror_mode and self.currentEdge.is_straddle_x_zero :
                        if isinstance( self.newEdge[0] , bmesh.types.BMVert ) and isinstance( self.newEdge[1] , bmesh.types.BMVert ) :
                            if self.currentEdge.element.verts[0].co.x > self.currentEdge.element.verts[1].co.x :
                                mirror = self.bmo.find_mirror( self.newEdge[0] )
                                if mirror != None :
                                    self.newEdge[1] = mirror                        
                            else :
                                mirror = self.bmo.find_mirror( self.newEdge[1] )
                                if mirror != None :
                                    self.newEdge[0] = mirror                        
                        elif isinstance( self.newEdge[0] , bmesh.types.BMVert ) and isinstance( self.newEdge[1] , mathutils.Vector ) :
                            self.newEdge[1] = self.bmo.local_to_world_pos( self.bmo.mirror_pos( self.newEdge[0].co ) )
                            mirror = self.bmo.find_mirror( self.newEdge[0] )
                            if mirror != None :
                                self.newEdge[1] = mirror
                        elif isinstance( self.newEdge[1] , bmesh.types.BMVert ) and isinstance( self.newEdge[0] , mathutils.Vector ) :
                            self.newEdge[0] = self.bmo.local_to_world_pos( self.bmo.mirror_pos( self.newEdge[1].co ) )
                            mirror = self.bmo.find_mirror( self.newEdge[1] )
                            if mirror != None :
                                self.newEdge[0] = mirror

                    # 両点がスナップするなら辺スナップに変更
                    if isinstance( self.newEdge[0] , bmesh.types.BMVert ) and isinstance( self.newEdge[1] , bmesh.types.BMVert ) :
                        self.is_center_snap = True
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
        for vert in self.newEdge :
            if isinstance( vert , mathutils.Vector ) :
                if not self.is_center_snap and self.bmo.is_mirror_mode and self.bmo.is_x_zero_pos_w2l( vert ) :
                    pos = pqutil.location_3d_to_region_2d( vert )
                    draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )
            elif isinstance( vert , bmesh.types.BMVert ) :       
                pos = pqutil.location_3d_to_region_2d( self.bmo.local_to_world_pos( vert.co ) )
                draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

        if self.is_center_snap :
            pos = pqutil.location_3d_to_region_2d( self.bmo.zero_pos_w2l(self.targetPos) )
            draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        p0 = self.bmo.local_to_world_pos(self.currentEdge.element.verts[0].co)
        p1 = self.bmo.local_to_world_pos(self.currentEdge.element.verts[1].co)

        t = [p0,p1]
        for i in range(2) :
            if isinstance( self.newEdge[i] , mathutils.Vector ) :
                t[i] = self.newEdge[i]
            elif isinstance( self.newEdge[i] , bmesh.types.BMVert ) :
                if self.newEdge[i] in self.currentEdge.element.verts :
                    t[i] = None
                else :
                    t[i] = self.bmo.local_to_world_pos(self.newEdge[i].co)

        lines = [ v for v in (p0,t[0],t[1],p1,p0) if v != None ]
        polys = [ v for v in (p0,t[0],t[1],p1) if v != None ]

        draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.5), hide_alpha = 0.5  )        
        draw_util.draw_lines3D( context , lines , self.color_create(1.0) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 0 )        
        if self.snapTarget.isEdge and None not in t :
            draw_util.draw_lines3D( context , [ t[0] , t[1] ] , (1,1,1,1) , 3 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

        if self.bmo.is_mirror_mode and not self.currentEdge.is_straddle_x_zero:
            lines = [ self.bmo.mirror_pos_w2l(p) for p in lines ]
            polys = [ self.bmo.mirror_pos_w2l(p) for p in polys ]
            draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.25), hide_alpha = 0.25  )        
            draw_util.draw_lines3D( context , lines , self.color_create(1.0) , 1 , primitiveType = 'LINE_STRIP' , hide_alpha = 0 )        
            if self.is_center_snap :            
                draw_util.draw_lines3D( context , [ t[0] , t[1] ] , (1,1,1,1) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

    def AdsorptionEdge( self , p0 , p1 , edge ) :
        st0 = pqutil.location_3d_to_region_2d(p0)
        st1 = pqutil.location_3d_to_region_2d(p1)
        se0 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[0].co))
        se1 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[1].co))
        if (st0-se0).length + (st1-se1).length > (st0-se1).length + (st1-se0).length :
            t0 = edge.verts[1]
            t1 = edge.verts[0]
        else :
            t0 = edge.verts[0]
            t1 = edge.verts[1]

        return t0,t1

    def MakePoly( self ) :
        edge = self.currentEdge.element
        mirror = False if self.currentEdge.is_straddle_x_zero else None

        t = [None,None]
        for i in range(2) :
            if isinstance( self.newEdge[i] , mathutils.Vector ) :
                t[i] = self.bmo.AddVertexWorld( self.newEdge[i] , mirror )
                self.bmo.UpdateMesh()
            elif isinstance( self.newEdge[i] , bmesh.types.BMVert ) :
                if self.newEdge[i] in self.currentEdge.element.verts :
                    t[i] = None
                else :
                    t[i] = self.newEdge[i]

        if  t[0] == None and t[1] == None :
            return

        verts = [ v for v in (edge.verts[0],edge.verts[1],t[1],t[0]) if v != None ]

        normal = None
        if edge.link_faces :
            for loop in edge.link_faces[0].loops :
                if edge == loop.edge :
                    if loop.vert == edge.verts[0] :
                        verts.reverse()
        else :
            normal = pqutil.getViewDir()

        face = self.bmo.AddFace( verts , normal , mirror )
        self.bmo.UpdateMesh()
