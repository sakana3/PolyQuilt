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
from .subtool import MainTool

class SubToolEdgeLoopExtrude(MainTool) :
    name = "EdgeLoop Extrude"

    def __init__(self,op,target, button) :
        super().__init__(op,target, button , no_hold = True )      
        self.l2w = self.bmo.local_to_world_pos
        self.w2l = self.bmo.world_to_local_pos

        self.currentVert = None
        self.currentEdge = None
        self.moveType = 'NORMAL'

        self.currentEdge = target.element
        self.edges , __ = self.bmo.calc_edge_loop( self.currentEdge , is_mirror = False )

        self.verts = set()
        for e in self.edges :
            self.verts = self.verts | set( e.verts )

        self.verts = { v : self.l2w( v.co ) for v in self.verts }

        self.mirror_edge = None

        # mirror
        is_symetry = False
        self.mirrorEdges = []
        if self.bmo.is_mirror_mode :
            mirror_edges = { e : self.bmo.find_mirror( e ) for e in self.edges }
            if set( self.edges ) & set(mirror_edges.values()) :
                self.centerVerts = [ v for v in self.verts if self.bmo.is_x_zero_pos(v.co) ]
                notCenterVerts = [ v for v in self.verts if v not in self.centerVerts ]
                if target.hitPosition.x >= 0 :
                    self.plusVerts = [ v for v in notCenterVerts if v.co.x > 0 ]
                else :
                    self.plusVerts = [ v for v in notCenterVerts if v.co.x < 0 ]
                self.minusVerts = { self.bmo.find_mirror( v ) : v  for v in notCenterVerts if v not in self.plusVerts }
                is_symetry = True
            else :
                self.mirrorEdges = { v : m for v , m in mirror_edges.items() if m }

        if not is_symetry :
            if self.preferences.fix_to_x_zero :
                self.centerVerts = [ v for v in self.verts if self.bmo.is_x_zero_pos(v.co) ]
            else :
                self.centerVerts = []
            self.plusVerts = {v : None for v in self.verts if v not in self.centerVerts }
            self.minusVerts = {}

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
    def Check( root , target ) :
        if target.isEdge :
            return target.element.is_boundary
        return False

    @staticmethod
    def CheckMarker( root , target : ElementItem ) :
        if target.isEdge :
            return (target.element.is_boundary or target.element.is_wire) and target.can_extrude()
        return False


    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight , edgering = True , elements = ["EDGE"] )
        if element.isEdge : 
            if not element.element.is_convex :
                return ElementItem.Empty()
        return element        

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element.isEdge :
            alpha = gizmo.preferences.highlight_face_alpha
            vertex_size = gizmo.preferences.highlight_vertex_size        
            width = gizmo.preferences.highlight_line_width
            color = gizmo.preferences.highlight_color
            return draw_util.drawElementsHilight3DFunc( gizmo.bmo.obj , element.both_loops , vertex_size ,width,alpha, color )
        return None

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            rayS = pqutil.Ray.from_screen( context , self.startMousePos )
            rayG = pqutil.Ray.from_screen( context , self.mouse_pos )      
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )
            move = (vG - vS)
            self.targetPos = self.startPos + move
            if QSnap.is_active() :
                self.targetPos = QSnap.view_adjust( self.targetPos )
            dist = self.preferences.distance_to_highlight

            self.is_center_snap = False
            if self.bmo.is_mirror_mode :
                self.is_center_snap = self.bmo.is_x0_snap( self.targetPos )

            def adjustVert( v , co , zero_snap ) :
                if self.is_center_snap or zero_snap :
                    co = self.bmo.zero_pos_w2l(co)
                pt = QSnap.adjust_point( co )
                ct = pqutil.location_3d_to_region_2d(pt)
                elm = self.bmo.PickElement( ct , dist , edgering=True , backface_culling = True , elements=['VERT'], ignore=self.ignoreVerts )
                if elm.isVert :
                    return elm.element
                if self.is_center_snap or zero_snap :
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
                self.verts[v] = adjustVert(v,p,True)

            for v in self.plusVerts :
                p = calcMove( v , move )
                self.verts[v] = adjustVert(v,p,False)

            for v,m in self.minusVerts.items() :
                p = calcMove( m , mathutils.Vector(( -move.x , move.y , move.z ))  )
                self.verts[m] = adjustVert(v,p,False)

            # スナップする辺を探す
            self.snapTarget = ElementItem.Empty()
            if self.currentEdge and self.is_center_snap == False :
                snapTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreEdges )       
                if snapTarget.isEdge :
                    self.snapTarget = snapTarget
                    self.AdsorptionEdge( self.currentEdge , snapTarget.element )
                    # スナップ結果から左右の対称補正
                    for v in self.centerVerts :
                        if isinstance( self.verts[v] , bmesh.types.BMVert ) :
                            if not self.bmo.is_x_zero_pos_w2l( self.verts[v].co ) :
                                p = calcMove( v , move )
                                self.verts[v] = adjustVert(v,p,True)

                    for v,m in self.minusVerts.items() :
                        if  m != None and v != None :
                            if isinstance( self.verts[v] , bmesh.types.BMVert ) :
                                x = self.bmo.find_mirror( self.verts[v] )
                                if x != None :
                                    self.verts[m] = x
                            else :
                                self.verts[m] = self.bmo.mirror_pos_w2l( self.verts[v] )

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                return 'FINISHED'
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
        def v2p( e , v , mirror ) :
            if mirror :
                if isinstance( v , mathutils.Vector ) :
                    return self.bmo.mirror_pos_w2l( v )
                elif isinstance( v , bmesh.types.BMVert ) and v not in e.verts :
                    return self.l2w( self.bmo.mirror_pos( v.co ) )
            else :
                if isinstance( v , mathutils.Vector ) :
                    return v
                elif isinstance( v , bmesh.types.BMVert ) and v not in e.verts :
                    return self.l2w( v.co )
            return None

        for e in self.edges :
            p = [ self.l2w( v.co ) for v in e.verts ]
            t = [ v2p(e, self.verts[v],False ) for v in e.verts ]
            polyss = [ [ v for v in (p[0],t[0],t[1],p[1]) if v != None ] ]

            if self.mirrorEdges and e in self.mirrorEdges :
                polyss.append( [ self.bmo.mirror_pos_w2l(v) for v in (p[0],t[0],t[1],p[1]) if v != None ] )

            for polys in polyss :
                draw_util.draw_Poly3D( self.bmo.obj , polys , self.color_create(0.5), hide_alpha = 0.5  )        
                draw_util.draw_lines3D( context , polys , self.color_create(1.0) , 2 , primitiveType = 'LINE_LOOP' , hide_alpha = 0 )        
                if self.snapTarget.isEdge and None not in t :
                    draw_util.draw_lines3D( context , [ t[0] , t[1] ] , (1,1,1,1) , 3 , primitiveType = 'LINE_STRIP' , hide_alpha = 1 )

    def AdsorptionEdge( self , srcEdge , snapEdge ) :
        dstEdges , __ = self.bmo.calc_edge_loop( snapEdge )        

        p0 = self.l2w( srcEdge.verts[0].co)
        p1 = self.l2w( srcEdge.verts[1].co) 
        s0 = self.l2w( snapEdge.verts[0].co) 
        s1 = self.l2w( snapEdge.verts[1].co) 

        if (p0-s0).length + (p1-s1).length > (p0-s1).length + (p1-s0).length :
            t0 = snapEdge.verts[0]
            t1 = snapEdge.verts[1]
        else :
            t0 = snapEdge.verts[1]
            t1 = snapEdge.verts[0]

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
                if sv in self.verts.keys() or dv in self.verts.items()  :
                    break
                self.verts[sv] = dv
                se , sv = other( se , sv , self.edges  )
                de , dv = other( de , dv , dstEdges  )

    def MakePoly( self ) :
        threshold = bpy.context.scene.tool_settings.double_threshold

        if (self.targetPos - self.startPos  ).length <= threshold :
            return

        for vert in self.verts :
            if isinstance( self.verts[vert] , mathutils.Vector ) :
                self.verts[vert] = self.bmo.AddVertexWorld( self.verts[vert] , False )
                self.bmo.UpdateMesh()

        newFaces = []
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

            newFaces.append( self.bmo.AddFace( verts , normal , is_mirror = (len(self.mirrorEdges) > 0 ) ) )
            self.bmo.UpdateMesh()

        newVerts = set( sum( ( tuple(f.verts) for f in newFaces ) , () ) )

        bmesh.ops.remove_doubles( self.bmo.bm , verts = list(newVerts) , dist = threshold )

        self.bmo.UpdateMesh()
