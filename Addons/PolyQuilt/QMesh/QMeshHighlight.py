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
        del self.__viewPosVerts
        del self.__viewPosEdges
        self.__viewPosVerts = None
        self.__viewPosEdges = None

    def UpdateView( self ,context , forced = False ):
        rv3d = context.space_data.region_3d
        matrix = self.pqo.obj.matrix_world @ rv3d.perspective_matrix
        if forced == True or matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            world_matrix = self.pqo.obj.matrix_world
            perspective_matrix = rv3d.perspective_matrix

            verts = self.pqo.bm.verts
#            mw = np.array( mw )
#            mp = numpy.array( perspective_matrix )
#            vo = numpy.array( [ (p.co.x,p.co.y,p.co.z,1.0) for p in verts] )
#            vw = mw @ (vo.T)
#            vp = mp @ (vw.T)

            def ProjVert( vt ) :
                v = vt.co
                wv = world_matrix @ v
                pv = perspective_matrix @ wv.to_4d()
                if pv.w < 0.0 :
                    return None

                t = Vector( (halfW+halfW * pv.x / pv.w , halfH+halfH * pv.y / pv.w ))

                return [ vt , t , wv ]

#           x1 = [ (v,mwp @ v.co.to_4d(),mw @ v.co) for v in verts ]
#           viewPos = [ (vs[0], Vector((halfW+halfW*vs[1].x/vs[1].w,halfH+halfH*vs[1].y/vs[1].w)),vs[2]) if vs[1].w > 0.0 else None for vs in x1 ]
            viewPos = [ ProjVert(p) for p in verts ]

            def ProjEdge( e) :
                verts = e.verts
                p0 = viewPos[ verts[0].index ]
                p1 = viewPos[ verts[1].index ]
                if p0 == None or p1 == None:
                    return None
                return ( e , p0[1] , p1[1] , p0[2] , p1[2] )

            edges = self.pqo.bm.edges
            viewPosEdge = [ ProjEdge(e) for e in edges ]
            self.__viewPosEdges = [ e for e in viewPosEdge if e is not None and e[0].hide is False ]
            self.__viewPosVerts = [ p for p in viewPos if p is not None and p[0].hide is False ]

            self.current_matrix = matrix        

                
    def CollectVerts( self , coord , radius : float , ignore = [] , edgering = False ) -> ElementItem :
        r = radius
        p = Vector( coord )
        viewPos = self.viewPosVerts
        s = [ i for i in viewPos if i[1] != None and (i[1] - p).length <= r and i[0] not in ignore ]
        if edgering :
            s = [ i for i in s if i[0].is_boundary or i[0].is_manifold == False ]
        r = sorted( s , key=lambda i:(i[1] - p).length )
        return [ ElementItem( self.pqo ,i[0] , i[1] , i[2] ) for i in r ] 

    def PickFace( self ,coord , ignore = [] ) -> ElementItem :
        ray = handleutility.Ray.from_screen( bpy.context , coord ).world_to_object( self.pqo.obj )
        pos,nrm,index,dist = self.pqo.btree.ray_cast( ray.origin , ray.vector )
        prePos = ray.origin
        while( index is not None ) :
            face =  self.pqo.bm.faces[index]
            if (prePos -pos).length < 0.00001 :
                break
            prePos = pos
            if face.hide is False and face not in ignore :
                return ElementItem( self.pqo , face , coord , self.pqo.obj.matrix_world @ pos , dist )
            pos,nrm,index,dist = self.pqo.btree.ray_cast( pos + ray_direction_obj * 0.000001 , ray_direction_obj )

        return ElementItem.Empty()


    def CollectEdge( self ,coord , radius : float , ignore = [] ) -> ElementItem :
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges
        ray = handleutility.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = handleutility.location_3d_to_region_2d
        def Conv( edge ) -> ElementItem :
            h0 , h1 , d = ray_distance( handleutility.Ray( edge[3] , (edge[3]-edge[4]) ) )
            c = location_3d_to_region_2d(h0)
            return ElementItem( self.pqo , edge[0] , c , h1 , d )

        intersect = geometry.intersect_line_sphere_2d
        r = [ Conv(i) for i in viewPosEdge if None not in intersect( i[1] ,i[2] ,p,radius ) and i[0] not in ignore ]
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
