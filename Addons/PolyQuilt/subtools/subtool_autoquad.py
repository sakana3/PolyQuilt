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

class SubToolAutoQuad(SubTool) :
    name = "AutoQuadTool"

    def __init__(self,op, target ) :
        super().__init__(op)
        if target.isVert :
            self.MakePolyByVert(target.element)
        elif target.isEdge :
            self.MakePolyByEdge(target.element)

    @staticmethod
    def Check( target ) :
        if target.isVert :
            edges = [ e for e in target.element.link_edges if len(e.link_faces) == 1 ]
            if len(edges) == 2 :
                if set(edges[0].link_faces) == set(edges[1].link_faces) :
                    return False
                return True
        elif target.isEdge :
            if target.element.is_boundary and len(target.element.link_faces) == 1 :
                return True
        return False

    @classmethod
    def FindBoundaryEdge( cls , edge , vert ) :
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
    def CalaTangent( cls , edge , vert ) :
        loop = edge.link_loops        
        if loop[0].vert == edge.verts[0] :
            vec = ( edge.verts[0].co - edge.verts[1].co ).normalized()
        else :
            vec = ( edge.verts[1].co - edge.verts[0].co ).normalized()

        nrm = vert.normal.cross(vec).normalized()
        return nrm

    def OnUpdate( self , context , event ) :
        return 'FINISHED'

    def MakePolyByEdge( self , edge ) :
        len = edge.calc_length()
        loop = edge.link_loops
        if loop[0].vert == edge.verts[0] :
            v0 = edge.verts[0]
            v1 = edge.verts[1]
        else :
            v0 = edge.verts[1]
            v1 = edge.verts[0]

        e0 = self.FindBoundaryEdge( edge , v0 )
        e1 = self.FindBoundaryEdge( edge , v1 )

        if e0 == None and e1 != None :
            self.MakePolyByVert( v1 )
            return
        if e0 != None and e1 == None :
            self.MakePolyByVert(  v0 )
            return

        nrm1 = self.CalaTangent(edge,v0)        
        if e0:
            x0 = e0.other_vert(v0)
        else :
            p0 = v0.co + nrm1 * len
            x0 = self.bmo.AddVertex( p0 )

        nrm2 = self.CalaTangent(edge,v1)
        if e1:
            x1 = e1.other_vert(v1)
        else :
            p1 = v1.co + nrm2 * len
            x1 = self.bmo.AddVertex( p1 )       

        self.bmo.UpdateMesh()        

        verts = [v1,v0,x0,x1]

        normal = None
        self.bmo.AddFace( verts , normal )
        QSnap.adjust_verts( self.bmo.obj , [x0,x1] , self.operator.fix_to_x_zero )  

        self.bmo.UpdateMesh()

    def MakePolyByVert( self , vert ) :
        edges = [ edge for edge in vert.link_edges if edge.is_boundary ]        
        v1 = edges[0].other_vert(vert)
        v2 = edges[1].other_vert(vert)
        c = (v1.co + v2.co) / 2.0
        p = vert.co + (c-vert.co) * 2

        v0 = self.bmo.AddVertex( p )
        self.bmo.UpdateMesh()

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
            normal = pqutil.getViewDir()

        self.bmo.AddFace( verts , normal )        
        QSnap.adjust_verts( self.bmo.obj , [v0] , self.operator.fix_to_x_zero )  
        self.bmo.UpdateMesh()
