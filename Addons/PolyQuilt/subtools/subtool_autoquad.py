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
import copy
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubToolEx

class SubToolAutoQuad(SubToolEx) :
    name = "AutoQuadTool"

    def __init__(self , event , root ) :
        super().__init__(root)
        is_x_zero = self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode

        if self.currentTarget.isVert :
            verts , normal = self.MakePolyByVert( self.currentTarget.element , is_x_zero)
        elif self.currentTarget.isEdge :
            verts , normal = self.MakePolyByEdge( self.currentTarget.element , is_x_zero)
        elif self.currentTarget.isEmpty :
            verts , normal = self.MakePolyByEmpty( self.bmo , self.startMousePos )

        def makeVert( p ) :
            if isinstance( p , bmesh.types.BMVert ) :
                return p
            else :
                v = QSnap.adjust_local( self.bmo.obj.matrix_world , p , self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode )
                vt = self.bmo.AddVertex(v)
                self.bmo.UpdateMesh()
                return vt

        if verts != None :
            vs = [ makeVert(v) for v in verts ]
            vs = sorted(set(vs), key=vs.index)
            face = self.bmo.AddFace( vs , normal )
            face.select_set(True)
            self.bmo.UpdateMesh()

    @staticmethod
    def Check( root , target ) :
        if target.isVert :
            vert = target.element
            edges = [ e for e in vert.link_edges if len(e.link_loops) == 1 ]
            if len(edges) == 2 :
                n0 = (edges[0].other_vert( vert ).co - vert.co).normalized()
                n1 = (edges[1].other_vert( vert).co - vert.co).normalized()
                if n0.dot( n1 ) > -0.95 :
                    t0 = edges[0].calc_tangent(edges[0].link_loops[0])
                    t1 = edges[1].calc_tangent(edges[1].link_loops[0])
                    t = (t0+t1).normalized()
                    n = (n0+n1).normalized()
                    if n.dot( t ) < 0 :
                        return True
        elif target.isEdge :
            if target.element.is_boundary and len(target.element.link_faces) == 1 :
                return True
        elif target.isEmpty :                
            return True            
        return False

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        is_x_zero = gizmo.preferences.fix_to_x_zero or gizmo.bmo.is_mirror_mode
        if element.isVert :
            verts , normal = cls.MakePolyByVert( element.element , is_x_zero)
        elif element.isEdge :
            verts , normal = cls.MakePolyByEdge( element.element , is_x_zero)
        elif element.isEmpty :
            verts , normal = cls.MakePolyByEmpty( gizmo.bmo , gizmo.mouse_pos )
        if verts != None :
            col = gizmo.preferences.makepoly_color        
            col = (col[0],col[1],col[2],col[3] * 0.5)            
            mat = gizmo.bmo.obj.matrix_world

            def calcVert( v ) :
                if isinstance( v , mathutils.Vector ) :
                    return  QSnap.adjust_point( mat @ v , is_x_zero )
                else :
                    return mat @ v.co

            vs = [ calcVert(v) for v in verts ]
            vs.append( vs[0] )
            if gizmo.bmo.is_mirror_mode :
                inv = mat.inverted()
                rv = [ inv @ v for v in vs ]
                rv = [ mat @ mathutils.Vector( ( -v.x,v.y,v.z )) for v in rv ]
                rv.append( rv[0] )

            draw_highlight = element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.highlight_color , gizmo.preferences )

            def Draw() :
                if element.isVert :
                    draw_highlight()
                elif element.isEdge :
                    draw_highlight()
                draw_util.draw_Poly3D( bpy.context , vs , col , 0.5 )
                draw_util.draw_lines3D( bpy.context , vs , (col[0],col[1],col[2],col[3] * 1)  , 2 , 0 )
                if gizmo.bmo.is_mirror_mode :
                    draw_util.draw_Poly3D( bpy.context , rv , (col[0],col[1],col[2],col[3] * 0.25) , 0.5 )
                    draw_util.draw_lines3D( bpy.context , rv , (col[0],col[1],col[2],0.5) , 2 , 0.5 )
            return Draw
        def Dummy() :
            pass
        return Dummy

    def OnUpdate( self , context , event ) :
        return 'FINISHED'



    @classmethod
    def CalaTangent( cls , edge , vert ) :
        return -edge.calc_tangent( edge.link_loops[0] )

    @classmethod
    def is_x_zero( cls , p ) :
        return abs( p[0] ) <=  bpy.context.scene.tool_settings.double_threshold 

    @classmethod
    def check_z_zero( cls , v , p , is_x_zero ) :
        if is_x_zero :
            if cls.is_x_zero(p) :
                p.x = 0.0
                return p

            if cls.is_x_zero(v) :
                p.x = 0.0
                return p

            if ( v.x > 0 and p.x < 0 ) or ( v.x < 0 and p.x > 0 ) :
                ray = pqutil.Ray( v , p - v )            
                plane = pqutil.Plane( mathutils.Vector( (0,0,0) ) , mathutils.Vector( ( 1 , 0 , 0 ) ) )
                r = plane.intersect_ray( ray )
                return r
        return p


    @classmethod
    def FindBoundaryEdge( cls , edge , vert , is_x_zero ) :
        if is_x_zero and cls.is_x_zero( vert.co ) :
            return None

        manifolds = [ e for e in vert.link_edges if not e.link_faces and e != edge ]
        if len(manifolds) == 1 :
            nrm0 = ( vert.co - edge.other_vert(vert).co ).normalized()
            nrm1 = ( vert.co - manifolds[0].other_vert(vert).co ).normalized()
            if nrm0.angle( nrm1 ) * 57.3 < 150 :
                if cls.CalaTangent(edge,vert).dot(nrm1) < 0 :
                    return manifolds[0]

        boundary_edge = [ e for e in vert.link_edges if e.is_boundary and e != edge and edge.link_faces[0] not in e.link_faces ]
        if len( boundary_edge ) == 1 :
            nrm0 = ( vert.co - edge.other_vert(vert).co ).normalized()
            nrm1 = ( vert.co - boundary_edge[0].other_vert(vert).co ).normalized()
            if nrm0.angle( nrm1 ) * 57.3 < 150 :
                if cls.CalaTangent(edge,vert).dot(nrm1) < 0 :
                    return boundary_edge[0]
        return None

    @classmethod
    def MakePolyByEdge( cls , edge , is_x_zero ) :
        len = edge.calc_length()
        loop = edge.link_loops
        if loop[0].vert == edge.verts[0] :
            v0 = edge.verts[0]
            v1 = edge.verts[1]
        else :
            v0 = edge.verts[1]
            v1 = edge.verts[0]

        # 境界エッジを探す
        e0 = cls.FindBoundaryEdge( edge , v0 , is_x_zero )
        e1 = cls.FindBoundaryEdge( edge , v1 , is_x_zero )

        if e0 == None and e1 != None :
            return cls.Make_Isosceles_Trapezoid( edge ,e1, v1 , is_x_zero )
        if e0 != None and e1 == None :
            return cls.Make_Isosceles_Trapezoid( edge ,e0, v0 , is_x_zero )

        if e0 and e1:
            p0 = e0.other_vert(v0)
            p1 = e1.other_vert(v1)
            if p0 == p1 :
                return  [v1,v0,p0] , None
        elif not e0 and not e1:
            p0 = cls.check_z_zero( v0.co , v0.co + cls.CalaTangent(edge,v0) * len , is_x_zero )
            p1 = cls.check_z_zero( v1.co , v1.co + cls.CalaTangent(edge,v1) * len , is_x_zero )

        verts = [ v for v in [v1,v0,p0,p1] if v != None ]

        return verts , None

    @classmethod
    def Make_Isosceles_Trapezoid( cls , edge , boundary_edge , vert , is_x_zero ) :
        edge_other_vert = edge.other_vert(vert)
        boundary_other_vert = boundary_edge.other_vert(vert)

        edge_nrm = cls.CalaTangent(edge , edge_other_vert)
        edge_ray = pqutil.Ray( edge_other_vert.co , edge_nrm )
        boundary_nrm = edge_other_vert.co - vert.co
        boundary_ray = pqutil.Ray( boundary_other_vert.co , boundary_nrm.normalized() )

        Q0 , Q1 , len = edge_ray.distance( boundary_ray )
        if is_x_zero and cls.is_x_zero( boundary_other_vert.co ) :
            p = cls.check_z_zero( boundary_other_vert.co , Q1 , is_x_zero )
        else :
            p = cls.check_z_zero( edge_other_vert.co , Q1 , is_x_zero )
        verts = [ v for v in [ edge_other_vert , p , boundary_other_vert , vert ] if v != None ]

        normal = None
        if edge.link_faces :
            for loop in edge.link_faces[0].loops :
                if edge == loop.edge :
                    if loop.vert == vert :
                        verts.reverse()
                        break
        else :
            normal = pqutil.getViewDir()

        return verts , normal

    @classmethod
    def MakePolyByVert( cls , vert , is_x_zero ) :
        edges = [ edge for edge in vert.link_edges if edge.is_boundary ]        
        if len(edges) != 2 :
            return 
        v1 = edges[0].other_vert(vert)
        v2 = edges[1].other_vert(vert)
        c = (v1.co + v2.co) / 2.0
        p = vert.co + (c-vert.co) * 2
        v = vert
        z1 = cls.is_x_zero( v1.co )
        z2 = cls.is_x_zero( v2.co )
        if z1 and not z2 :
            v = v2
        elif z2 and not z1 :
            v = v1
        p = cls.check_z_zero( v.co , p , is_x_zero )

        verts = [ v for v in [v2,vert,v1,p] if v != None ]

        normal = None
        edge = edges[0]
        if edge.link_faces :
            for loop in edge.link_faces[0].loops :
                if edge == loop.edge :
                    if loop.vert == vert :
                        verts.reverse()
                        break
        else :
            normal = pqutil.getViewDir()

        return verts , normal



    @classmethod
    def MakePolyByEmpty( cls , bmo , startPos ) :
        highlight = bmo.highlight
        boundary_edges = highlight.boundaryViewPosEdges
        verts = [ [(startPos-p).length , v , p ] for v,p in highlight.boundaryViewPosVerts ]
        verts.sort(key=lambda x:x[0] , reverse=False)
        matrix = bmo.obj.matrix_world
        context =  bpy.context
        intersect_point_quad_2d = mathutils.geometry.intersect_point_quad_2d
        intersect_line_line_2d = mathutils.geometry.intersect_line_line_2d
        convex_hull_2d = mathutils.geometry.convex_hull_2d
        atan2 =  math.atan2

        def Chk( p1 , vt ) :
            v = vt[1]
            p2 = vt[2]
            if not QSnap.is_target( matrix @ v.co ) :
                return False
            for edge , (e1,e2) in boundary_edges.items() : 
                if v not in edge.verts :
                    hit = intersect_line_line_2d( e1 , e2 , p1 , p2 )
                    if hit != None :
                        v1 = matrix @ edge.verts[0].co
                        v2 = matrix @ edge.verts[1].co        
                        wp = pqutil.Ray.from_screen( context , hit ).hit_to_line_pos( v1 , v2 )                                        
                        if wp != None and QSnap.is_target( wp ) :
                            return False
            return True

        def convex_hull( points ) :
            idxs = convex_hull_2d( points )
            if len(idxs) != len(points) :
                angles = [ [ atan2( point.y - startPos.y , point.x - startPos.x ) , index ] for index , point in enumerate(points) ]
                angles.sort(key=lambda x:x[0] , reverse=False)
                return [ i for r,i in angles ]
            return idxs

        if len(verts) >= 4 :
            quad = []
            for vt in verts:
                if Chk( startPos , vt) :
                    quad.append( vt )
                    if len(quad) >= 4 :
                        idxs = convex_hull( [ q[2] for q in quad ] )
                        quad = [ quad[i] for i in idxs ]
                        if intersect_point_quad_2d( startPos , quad[0][2] , quad[1][2] , quad[2][2] , quad[3][2] ) == 0 :
                            quad.remove(vt)
                        else :
                            break

            if len(quad) >= 4 :
                return [ q[1] for q in quad ] , None

            if len(quad) >= 3 :
                if mathutils.geometry.intersect_point_tri( startPos , quad[0][2] , quad[1][2] , quad[2][2] ) :
                    return [ q[1] for q in quad ] , None

        return None , None


