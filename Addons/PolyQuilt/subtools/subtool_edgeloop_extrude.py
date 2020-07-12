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
from .subtool_util import move_component_module

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

        self.move_component_module = move_component_module( self.bmo , target , self.mouse_pos , 'FREE' , self.preferences.fix_to_x_zero )
        self.move_component_module.set_geoms( target.loops )

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

        self.snap_edges = {}
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
            move = self.move_component_module.move_to( self.mouse_pos )

            dist = self.preferences.distance_to_highlight

            self.is_center_snap = False
            if self.bmo.is_mirror_mode :
                self.is_center_snap = self.bmo.is_x0_snap( self.move_component_module.currentTarget.hitPosition )

            pos_tbl = self.move_component_module.update_geoms_pos( move , "NEAR" )
            for v in pos_tbl :
                if v in self.verts :
                    self.verts[v] = pos_tbl[v]

            self.snapTarget = ElementItem.Empty()
            if self.currentEdge and self.is_center_snap == False :
                snapTarget = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignoreEdges )       
                if snapTarget.isEdge :
                    self.snapTarget = snapTarget
                    self.snap_edges = self.move_component_module.snap_loop( self.currentEdge , self.currentTarget.loops  , snapTarget.element )

                    for vert , snap in self.snap_edges.items() :
                        self.verts[vert] = snap

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                return 'FINISHED'
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                self.MakePoly()
                return 'FINISHED'
        else :
            self.move_component_module.update(event)

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
            pos = pqutil.location_3d_to_region_2d( self.bmo.zero_pos_w2l( self.move_component_module.currentTarget.hitPosition ) )
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

        self.move_component_module.draw_3D(context)

    def MakePoly( self ) :
        threshold = bpy.context.scene.tool_settings.double_threshold

        if self.move_component_module.move_distance <= threshold :
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
