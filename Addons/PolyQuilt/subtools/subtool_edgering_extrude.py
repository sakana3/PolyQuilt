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

class SubToolEdgeRingExtrude(MainTool) :
    name = "EdgeRing Extrude"

    def __init__(self,op,target, button) :
        super().__init__(op,target, button , no_hold = True )      

        l2wp = self.bmo.local_to_world_pos
        w2lp = self.bmo.world_to_local_nrm        
        l2wn = self.bmo.local_to_world_nrm
        w2ln = self.bmo.world_to_local_nrm

        self.edges = target.both_rings
        self.mirrorEdges = target.mirror_rings

        self.startPos = target.hitPosition
        self.startNrm = -l2wn(target.element.calc_tangent( target.element.link_loops[0] )).normalized()

        self.startRay = pqutil.Ray( self.startPos , self.startNrm )

        self.verts = {}
        for edge in self.edges :
            for v in edge.verts :
                if v not in self.verts :
                    nrm = None
                    links = [ e for e in self.edges if v in e.verts ]
                    if len(links) == 2 :
                        n0 =  links[0].calc_tangent( links[0].link_loops[0] )
                        n1 =  links[1].calc_tangent( links[1].link_loops[0] )
                        r0 = pqutil.Ray( v.co + n0 , v.co - links[0].other_vert(v).co )
                        r1 = pqutil.Ray( v.co + n1 , v.co - links[1].other_vert(v).co )
                        q0 , q1 , t = r0.distance(r1)
                        if q0 and q1 :
                            rt = pqutil.Ray( v.co , -( n0 + n1 ).normalized() )
                            nrm = v.co - rt.closest_point(  (q0 + q1) / 2 )
                        else :
                            nrm = -( n0 + n1 ).normalized()
                    elif len(links) == 1 :
                        nrm = -links[0].calc_tangent( links[0].link_loops[0] )

                    if nrm :
                        if self.bmo.is_mirror_mode :
                            if self.bmo.is_x_zero_pos( v.co ) :
                                nrm = self.bmo.zero_vector( nrm  )
                        self.verts[v] = -l2wn(nrm)

        self.rate = 0.0
        self.result_verts = {}
        for v in self.verts :
            self.result_verts[v] = v.co

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
            return draw_util.drawElementsHilight3DFunc( gizmo.bmo.obj  , gizmo.bmo.bm, element.both_loops , vertex_size ,width,alpha, color )
        return None

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            ray = pqutil.Ray.from_screen( context , self.mouse_pos )
            q0 , q1 , d = self.startRay.distance(ray)
            self.rate = ( self.startRay.origin - q0 ).length
            for v,n in self.verts.items() :
                self.result_verts[v] = v.co + n * self.rate
                if QSnap.is_active() :
                    self.result_verts[v] , _ = QSnap.adjust_point(self.result_verts[v])
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                return 'FINISHED'
        elif event.type == 'SPACE' :
                self.snap_lock = { v : s for v , s in self.verts.items() if isinstance( s , bmesh.types.BMVert  ) }
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                self.MakePoly()
                return 'FINISHED'

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        l2wp = self.bmo.local_to_world_pos

        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width
        color = self.preferences.highlight_color

        for e in self.edges :
            v0 = e.verts[0]
            v1 = e.verts[1]
            p0 = l2wp(self.result_verts[v0])
            p1 = l2wp(self.result_verts[v1])

            draw_util.draw_Poly3D( context , [ l2wp(v0.co),p0,p1,l2wp(v1.co)] , self.color_create(0.5) , 0.2 )
            draw_util.draw_lines3D( context , [p0,p1]  , self.color_create(1.0) , width , primitiveType = 'LINE_LOOP' , hide_alpha = 0.2 )

        for v , n in self.verts.items() :   
            p0 = l2wp(v.co)
            p1 = l2wp(self.result_verts[v])
            draw_util.draw_lines3D( context , [p0,p1]  , self.color_create(1.0) , width , primitiveType = 'LINE_LOOP' , hide_alpha = 0.2 )

    def MakePoly( self ) :
        make_verts = {}
        for vert in self.verts :
            make_verts[vert] = self.bmo.AddVertexWorld( self.bmo.local_to_world_pos( self.result_verts[vert] ) , False )
        self.bmo.UpdateMesh()

        for edge in self.edges :
            p0 = make_verts[edge.verts[0]]
            p1 = make_verts[edge.verts[1]]
            verts = [ edge.verts[0] , p0 , p1, edge.verts[1] ]
            self.bmo.AddFace( verts , pqutil.getViewDir() , is_mirror = False )
        self.bmo.UpdateMesh()
