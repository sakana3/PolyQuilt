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

class SubToolEdgeExtrudeMulti(SubTool) :
    name = "EdgeExtrudeTool"

    def __init__(self,op, target : ElementItem , is_loop : bool = True ) :
        super().__init__(op)
        self.l2w = self.bmo.local_to_world_pos
        self.w2l = self.bmo.world_to_local_pos

        self.currentVert = None
        self.currentEdge = None
        self.moveType = 'NORMAL'
        if target.isEdge :
            self.currentEdge = target.element
            if is_loop :
                self.edges , __ = self.bmo.findEdgeLoop( self.currentEdge  )
            else :
                self.edges = [ self.currentEdge ]

            self.verts = set()
            for e in self.edges :
                self.verts = self.verts | set( e.verts )
        elif target.isVert :
            self.moveType = 'SPREAD'
            self.currentVert = target.element
            self.edges , self.verts = self.bmo.findOutSideLoop( self.currentVert )

        self.verts = { v : self.l2w( v.co ) for v in self.verts }

        # mirror
        if self.bmo.is_mirror_mode :
            self.centerVerts = [ v for v in self.verts if self.bmo.is_x_zero_pos(v.co) ]
            if target.hitPosition.x >= 0 :
                self.plusVerts = { v : self.bmo.find_mirror( v ) for v in self.verts if v.co.x > 0 and v not in self.centerVerts }
                self.minusVerts = { v : self.bmo.find_mirror( v ) for v in self.verts if v not in self.plusVerts and v not in self.centerVerts }
            else :
                self.plusVerts = { v : self.bmo.find_mirror( v ) for v in self.verts if v.co.x < 0 and v not in self.centerVerts }
                self.minusVerts = { v : self.bmo.find_mirror( v ) for v in self.verts if v not in self.plusVerts and v not in self.centerVerts }
            self.mirrorEdges = [ e for e in self.edges if self.bmo.find_mirror( e ) in self.edges ]
        else :
            if self.preferences.fix_to_x_zero :
                self.centerVerts = [ v for v in self.verts if self.bmo.is_x_zero_pos(v.co) ]
            else :
                self.centerVerts = []
            self.plusVerts = {v : None for v in self.verts if v not in self.centerVerts }
            self.minusVerts = {}
            self.mirrorEdges = []

        self.startPos = target.hitPosition
        self.targetPos = target.hitPosition
        self.screen_space_plane = pqutil.Plane.from_screen( bpy.context , target.hitPosition )
        self.move_plane = self.screen_space_plane
        self.startMousePos = copy.copy(target.coord)
        self.snapTarget = ElementItem.Empty()
        self.is_center_snap = False

        self.ignoreVerts = set()
        self.ignoreEdges = set()
        for e in self.edges :
            for face in e.link_faces :
                self.ignoreVerts = self.ignoreVerts | set(face.verts)
                self.ignoreEdges = self.ignoreEdges | set(face.edges)

    @staticmethod
    def Check( root ,target ) :
        if target.isVert :
            return target.element.is_boundary 
        elif target.isEdge :
            return target.element.is_boundary or not target.element.is_manifold
        return False

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            rayS = pqutil.Ray.from_screen( context , self.startMousePos )
            rayG = pqutil.Ray.from_screen( context , self.mouse_pos )      
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )
            move = (vG - vS)
            self.targetPos = self.startPos + move
            dist = self.preferences.distance_to_highlight

            self.is_center_snap = False
            if self.bmo.is_mirror_mode :
                self.is_center_snap = self.bmo.is_x0_snap( self.targetPos )

            def adjustVert( vt , zero_snap ) :
                if self.is_center_snap :
                    vt.x = 0

                pt = QSnap.adjust_point( vt )
                ct = pqutil.location_3d_to_region_2d(pt)
                elm = self.bmo.PickElement( ct , dist , edgering=True , backface_culling = True , elements=['VERT'], ignore=self.ignoreVerts )
                if elm.isVert :
                    return elm.element
                if zero_snap :
                    pt = self.bmo.zero_pos_w2l( pt )
                return pt

            def calcMove( vt , mt ) :
                if self.moveType == 'SPREAD' :
                    if len( vt.link_faces ) == 2 :
                        et = [ e for e in set( vt.link_faces[0].edges ) & set( vt.link_faces[1].edges ) if vt in e.verts ]
                        if len(et) == 1 :
                            return self.l2w(vt.co) +( vt.co - et[0].other_vert(vt).co ).normalized() * mt.length
                    elif len( vt.link_faces ) == 1 :
                        loop = [ l for l in vt.link_loops if l.vert == vt ][0]
                        dr = loop.calc_tangent()
                        return self.l2w(vt.co - dr * mt.length)
                    else :
                        edges = [ e for e in vt.link_edges if len(e.link_faces) == 1 ]
                        if len( edges ) == 2 :
                            e0 = (edges[0].other_vert(vt).co - vt.co).normalized()
                            e1 = (edges[1].other_vert(vt).co - vt.co).normalized()
                            dr = ((e0 + e1) / 2).normalized()

                            others = [ e for e in vt.link_edges if len(e.link_faces) != 1 ]
                            if (edges[0].other_vert(vt).co - vt.co).normalized().dot(dr) > 0 :
                                return self.l2w(vt.co + dr * mt.length)
                            else :
                                return self.l2w(vt.co - dr * mt.length)

                return self.l2w(vt.co) + mt

            # 各頂点の移動
            for v in self.centerVerts :
                p = calcMove( v , move )
                self.verts[v] = adjustVert(p,True)

            for v in self.plusVerts :
                p = calcMove( v , move )
                self.verts[v] = adjustVert(p,False)

            for v in self.minusVerts :
                r = self.minusVerts[v]
                if r != None :
                    s = self.verts[r]
                    if isinstance( s , bmesh.types.BMVert ) :
                        t = self.bmo.find_mirror( s )
                        if t == None :
                            self.verts[v] = self.bmo.mirror_pos(self.l2w(s.co))
                        else :
                            self.verts[v] = t
                    else :
                        self.verts[v] = self.bmo.mirror_pos_w2l(s)
                else :
                    p = self.bmo.mirror_pos_w2l(self.l2w(v.co) + move)
                    self.verts[v] = adjustVert(p,False)

            # スナップする辺を探す
            self.snapTarget = ElementItem.Empty()
            if self.currentEdge and self.is_center_snap == False :
                snapTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreEdges )       
                if snapTarget.isEdge :
                    self.snapTarget = snapTarget
                    self.AdsorptionEdge( self.currentEdge , snapTarget.element )

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

        for v in self.verts :
            t = self.verts[v]
            if isinstance( t , mathutils.Vector ) :
                if not self.is_center_snap and self.bmo.is_mirror_mode and self.bmo.is_x_zero_pos_w2l( t ) :
                    pos = pqutil.location_3d_to_region_2d( t )
                    draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )
            elif isinstance( t , bmesh.types.BMVert ) :
                pos = pqutil.location_3d_to_region_2d( self.bmo.local_to_world_pos( t.co ) )
                draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

        if self.is_center_snap :
            pos = pqutil.location_3d_to_region_2d( self.bmo.zero_pos_w2l(self.targetPos) )
            draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        def v2p( e , v ) :
            if isinstance( v , mathutils.Vector ) :
                return v
            elif isinstance( v , bmesh.types.BMVert ) :
                if v not in e.verts :
                    return self.l2w( v.co )
            return None

        for e in self.edges :
            p = [ self.l2w( v.co ) for v in e.verts ]
            t = [ v2p(e, self.verts[v] ) for v in e.verts ]
            polys = [ v for v in (p[0],t[0],t[1],p[1]) if v != None ]
            draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.5), hide_alpha = 0.5  )        
            draw_util.draw_lines3D( context , polys , self.color_create(1.0) , 2 , primitiveType = 'LINE_LOOP' , hide_alpha = 0 )        
            if self.snapTarget.isEdge and None not in t :
                draw_util.draw_lines3D( context , [ t[0] , t[1] ] , (1,1,1,1) , 3 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

            if self.bmo.is_mirror_mode and e not in self.mirrorEdges :
                polys = [ self.bmo.mirror_pos_w2l(p) for p in polys ]
                draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.25), hide_alpha = 0.5  )        
                draw_util.draw_lines3D( context , polys , self.color_create(0.5) , 1 , primitiveType = 'LINE_STRIP' , hide_alpha = 0 )        
                if self.is_center_snap :            
                    draw_util.draw_lines3D( context , [ t[0] , t[1] ] , (1,1,1,1) , 2 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

    def AdsorptionEdge( self , srcEdge , snapEdge ) :
        def v2p( v ) :
            if isinstance( v , bmesh.types.BMVert ) :
                return self.l2w( v.co )
            return v

        p0 = v2p( self.l2w(srcEdge.verts[0].co) )
        p1 = v2p( self.l2w(srcEdge.verts[1].co) )

        st0 = pqutil.location_3d_to_region_2d(p0)
        st1 = pqutil.location_3d_to_region_2d(p1)
        se0 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(srcEdge.verts[0].co))
        se1 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(srcEdge.verts[1].co))
        if (st0-se0).length + (st1-se1).length > (st0-se1).length + (st1-se0).length :
            t0 = snapEdge.verts[1]
            t1 = snapEdge.verts[0]
        else :
            t0 = snapEdge.verts[0]
            t1 = snapEdge.verts[1]

        dstEdges = self.bmo.findOutSideEdgeLoop( snapEdge , t0 )        

        def other( edge , vert , edges ) :
            hits = [ e for e in edges if e != edge and vert in e.verts ]
            if len(hits) == 1 :
                return hits[0] , hits[0].other_vert(vert) 
            return None , None

        for (src , dst) in zip(srcEdge.verts , [t1,t0] ) :
            sv = src
            se = srcEdge
            dv = dst
            de = snapEdge
            while( sv != None and dv != None ) :
                if sv != None and dv != None :
                    self.verts[sv] = dv
                se , sv = other( se , sv , self.edges  )
                de , dv = other( de , dv , dstEdges  )

    def MakePoly( self ) :
        mirror = None

        for vert in self.verts :
            if isinstance( self.verts[vert] , mathutils.Vector ) :
                self.verts[vert] = self.bmo.AddVertexWorld( self.verts[vert] , False )
                self.bmo.UpdateMesh()

        for edge in self.edges :
            t = [ self.verts[v] for v in edge.verts ]
            if  t[0] == None and t[1] == None :
                continue
            verts = [ v for v in (edge.verts[0],edge.verts[1],t[1],t[0]) if v != None ]

            normal = None
            if edge.link_faces :
                for loop in edge.link_faces[0].loops :
                    if edge == loop.edge :
                        if loop.vert == edge.verts[0] :
                            verts.reverse()
            else :
                normal = pqutil.getViewDir()
            if edge in self.mirrorEdges :
                mirror = False
            else:
                mirror = None

            face = self.bmo.AddFace( verts , normal , mirror )
            self.bmo.UpdateMesh()
