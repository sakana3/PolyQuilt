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

import bpy
import bmesh
import math
import copy
import mathutils
import bpy_extras
import collections
from mathutils import *
import numpy as np
from ..utils import pqutil
from ..utils.dpi import *
from .ElementItem import ElementItem

__all__ = ['QMeshHighlight']

class QMeshHighlight :
    def __init__(self,pqo) :
        self.pqo = pqo
        self.__viewPosVerts = None
        self.__viewPosEdges = None
        self.current_matrix = None

    @property
    def viewPosVerts(self):
        if self.__viewPosVerts == None :
            self.UpdateView( bpy.context , True )
        return self.__viewPosVerts

    @property
    def viewPosEdges(self):
        if self.__viewPosEdges == None :
            self.UpdateView( bpy.context , True )
        return self.__viewPosEdges

    def setDirty( self ) :
        if self.__viewPosVerts :
            del self.__viewPosVerts
        self.__viewPosVerts = None
        if self.__viewPosEdges :
            del self.__viewPosEdges
        self.__viewPosEdges = None
        self.current_matrix = None

    def UpdateViewNP( self ,context , forced = False ):
        rv3d = context.space_data.region_3d
        matrix = self.pqo.obj.matrix_world @ rv3d.perspective_matrix
        if forced == True or matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            matrix_world = self.pqo.obj.matrix_world
            perspective_matrix = rv3d.perspective_matrix

            verts = self.pqo.bm.verts

            vertCount = len(verts)
            verts_co = np.array( [ v.co for v in verts ] )
            verts_co.shape = (vertCount, 3) 
            verts_co_4d = np.ones(shape=(vertCount, 4), dtype=np.float) 
            verts_co_4d[:, :-1] = verts_co
            verts_world = np.einsum( 'ij,aj->ai' , matrix_world , verts_co_4d)
            verts_view = np.einsum( 'ij,aj->ai' , perspective_matrix , verts_world ) 
            verts_xyz = verts_view[:,[0,1,2]] 
            verts_w = verts_view[:,[3]]
            verts_proj = verts_xyz / verts_w * np.array( (halfW , halfH , 1) ) + np.array( (halfW , halfH , 0) ) 
            verts_proj_xy = verts_view[:,[0,1]] 

            viewPos = { v : ( v , Vector( p ).to_2d() ) for (v,p,w) in zip(verts , verts_proj , verts_world ) }

            edges = self.pqo.bm.edges
            edges_size = len(edges) 
#           edges_verts = [ (e.verts[0].index,e.verts[1].index) for e in edges ]
#           self.__viewPosEdges = [ (e , verts_xyz[e[0]] , verts_xyz[e[1]] ) for e in edges_verts ]

            self.__viewPosEdges = { e : [ p1[1] , p2[1] ] for e,p1,p2 in [ (e, viewPos[e.verts[0]], viewPos[e.verts[1]]) for e in edges ]  if p1 and p2 and not e.hide }
            self.__viewPosVerts = [ p for p in viewPos.values() if p and not p[0].hide ]

            self.current_matrix = matrix        

    def UpdateView( self ,context , forced = False ):
        rv3d = context.space_data.region_3d
        matrix = self.pqo.obj.matrix_world @ rv3d.perspective_matrix
        if forced == True or matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            matrix = rv3d.perspective_matrix @ self.pqo.obj.matrix_world

            verts = self.pqo.bm.verts

            def ProjVert( vt ) :
                pv = matrix @ vt.co.to_4d()
                w = pv[3]
                return Vector( (pv.x * halfW / w + halfW , pv.y * halfH / w + halfH ) )  if w > 0.0 else None

            viewPos = { p : ProjVert(p) for p in verts }

            edges = self.pqo.bm.edges

            self.__viewPosEdges = { e : [ p1 , p2 ] for e,p1,p2 in [ (e, viewPos[e.verts[0]], viewPos[e.verts[1]]) for e in edges ]  if p1 and p2 and not e.hide }
            self.__viewPosVerts = { v : p for v,p in viewPos.items() if p and not v.hide }

            self.current_matrix = copy.copy(matrix)

    def CollectVerts( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = True ) -> ElementItem :
        r = radius
        p = Vector( coord )
        viewPos = self.viewPosVerts
        rr = Vector( (r,0) )
        verts = self.pqo.bm.verts
        s = [ [v,s] for v,s in viewPos.items() if s - p <= rr and v in verts ]
        if edgering :
            s = [ i for i in s if i[0].is_boundary or i[0].is_manifold == False ]

        if backface_culling :
            ray = pqutil.Ray.from_screen( bpy.context , coord ).world_to_object( self.pqo.obj )
            s = [ i for i in s if i[0].is_manifold == False or i[0].is_boundary or i[0].normal.dot( ray.vector ) < 0 ]

        s = [ i for i in s if i[0] not in ignore ]

        r = sorted( s , key=lambda i:(i[1] - p).length_squared )
        matrix_world = self.pqo.obj.matrix_world
        return [ ElementItem( self.pqo ,i[0] , i[1] , matrix_world @ i[0].co ) for i in r ] 


    def CollectEdge( self ,coord , radius : float , ignore = [] , backface_culling = True , edgering = False ) -> ElementItem :
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges
        ray = pqutil.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = pqutil.location_3d_to_region_2d
        matrix_world = self.pqo.obj.matrix_world      

        def Conv( edge ) -> ElementItem :
            v1 = matrix_world @ edge.verts[0].co
            v2 = matrix_world @ edge.verts[1].co
            h0 , h1 , d = ray_distance( pqutil.Ray( v1 , (v1-v2) ) )
            c = location_3d_to_region_2d(h1)
            return ElementItem( self.pqo , edge , c , h1 , d )

        intersect = geometry.intersect_line_sphere_2d
        edges = self.pqo.bm.edges
        if edgering :        
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if len(e.link_faces) <= 1 and None not in intersect( p1 , p2 ,p,radius ) and e not in ignore ]
        else :
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if None not in intersect( p1 , p2 ,p,radius ) and e in edges and e not in ignore ]

        if backface_culling :
            ray2 = ray.world_to_object( self.pqo.obj )
            r = [ i for i in r
                if not i.element.is_manifold or i.element.is_boundary or
                    i.element.verts[0].normal.dot( ray.vector ) < 0 or i.element.verts[1].normal.dot( ray2.vector ) < 0 ]
        
        s = sorted( r , key=lambda i:(i.coord - p).length_squared )

        return s


    def PickFace( self ,coord , ignore = []  , backface_culling = True ) -> ElementItem :
        ray = pqutil.Ray.from_screen( bpy.context , coord ).world_to_object( self.pqo.obj )
        pos,nrm,index,dist = self.pqo.btree.ray_cast( ray.origin , ray.vector )
        prePos = ray.origin
        while( index is not None ) :
            face =  self.pqo.bm.faces[index]
            if (prePos -pos).length < 0.00001 :
                break
            prePos = pos
            if face.hide is False and face not in ignore :
                if backface_culling == False or face.normal.dot( ray.vector ) < 0 :
                    return ElementItem( self.pqo , face , coord , self.pqo.obj.matrix_world @ pos , dist )
                else :
                    return ElementItem.Empty()
            ray.origin = ray.origin + ray.vector * 0.00001
            pos,nrm,index,dist = self.pqo.btree.ray_cast( ray.origin , ray.vector )

        return ElementItem.Empty()



    def find_view_range( self , coord , radius ) :
#       xray = bpy.context.space_data.shading.show_xray 
#       select_mode = bpy.context.tool_settings.mesh_select_mode

        #bpy.context.tool_settings.mesh_select_mode = [True,True,True] 

        #bpy.ops.ed.undo_push(message="For find nearest") 
        bpy.ops.view3d.select_circle( x = coord.x , y = coord.y , radius = radius ) 

        rv = [ v for v in  bm.verts if v.select ]
        re = [ e for e in  bm.edges if e.select ] 
        rf = [ f for f in  bm.faces if f.select ] 

        #bpy.ops.ed.undo_redo() 

#       bpy.ops.action.select_all( 'DESELECT' ) 
        #bpy.context.tool_settings.mesh_select_mode = select_mode 
#       bpy.context.space_data.shading.show_xray = xray 

        return rv , re , rf 

def find_view_range( coord , radius ) :
    bpy.ops.view3d.select_circle( x = coord.x , y = coord.y , radius = radius ) 

    rv = [ v for v in  bm.verts if v.select ]
    re = [ e for e in  bm.edges if e.select ] 
    rf = [ f for f in  bm.faces if f.select ] 

    bpy.ops.action.select_all( 'DESELECT' ) 

    return rv , re , rf 
