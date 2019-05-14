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
from .. import handleutility
from ..dpi import *
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

    def UpdateView( self ,context , forced = False ):
        rv3d = context.space_data.region_3d
        matrix = self.pqo.obj.matrix_world @ rv3d.perspective_matrix
        if forced == True or matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            matrix_world = self.pqo.obj.matrix_world
            perspective_matrix = rv3d.perspective_matrix

#https://blender.stackexchange.com/questions/139511/multiply-4x4-matrix-and-array-of-3d-vectors-using-numpy/139517#139517
            verts = self.pqo.bm.verts

            def ProjVert( vt ) :
                v = vt.co
                wv = matrix_world @ v
                pv = perspective_matrix @ wv.to_4d()
                if pv.w < 0.0 :
                    return None

                t = Vector( (halfW+halfW * pv.x / pv.w , halfH+halfH * pv.y / pv.w ))

                return ( vt , t , wv )

            viewPos = { p : ProjVert(p) for p in verts }

            edges = self.pqo.bm.edges
            self.__viewPosEdges = [ (e, p1[1] , p2[1] , p1[2] , p2[2] ) for e,p1,p2 in [ (e, viewPos[e.verts[0]], viewPos[e.verts[1]]) for e in edges ]  if p1 and p2 and not e.hide ]
            self.__viewPosVerts = [ p for p in viewPos.values() if p and not p[0].hide ]

            self.current_matrix = matrix        


    def CollectVerts( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = True ) -> ElementItem :
        r = radius
        p = Vector( coord )
        viewPos = self.viewPosVerts
        s = [ i for i in viewPos if (i[1] - p).length <= r and i[0] not in ignore ]
        if edgering :
            s = [ i for i in s if i[0].is_boundary or i[0].is_manifold == False ]

        if backface_culling :
            ray = handleutility.Ray.from_screen( bpy.context , coord )
            s = [ i for i in s if i[0].is_manifold == False or i[0].is_boundary or i[0].normal.dot( ray.vector ) < 0 ]

        r = sorted( s , key=lambda i:(i[1] - p).length )
        return [ ElementItem( self.pqo ,i[0] , i[1] , i[2] ) for i in r ] 

    def PickFace( self ,coord , ignore = []  , backface_culling = True ) -> ElementItem :
        ray = handleutility.Ray.from_screen( bpy.context , coord ).world_to_object( self.pqo.obj )
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


    def CollectEdge( self ,coord , radius : float , ignore = [] , backface_culling = True ) -> ElementItem :
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges
        ray = handleutility.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = handleutility.location_3d_to_region_2d
        def Conv( edge , v1, v2 ) -> ElementItem :
            h0 , h1 , d = ray_distance( handleutility.Ray( v1 , (v1-v2) ) )
            c = location_3d_to_region_2d(h0)
            return ElementItem( self.pqo , edge , c , h1 , d )

        intersect = geometry.intersect_line_sphere_2d
        r = [ Conv(e,v1,v2) for e,p1,p2,v1,v2 in viewPosEdge if None not in intersect( p1 , p2 ,p,radius ) and e not in ignore ]

        if backface_culling :
            r = [ i for i in r
                if  i.element.is_manifold == False or i.element.is_boundary or
                    i.element.verts[0].normal.dot( ray.vector ) < 0 or i.element.verts[1].normal.dot( ray.vector ) < 0 ]
        
        s = sorted( r , key=lambda i:(i.coord - p).length )

        return s


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
