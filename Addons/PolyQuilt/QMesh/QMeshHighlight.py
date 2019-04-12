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
        return self.__viewPosVerts

    @property
    def viewPosEdges(self):
        return self.__viewPosEdges

    def setDirty( self ) :
        self.__viewPosVerts = None
        self.__viewPosEdges = None

    def UpdateView( self ,context , forced = False ):
        rv3d = context.space_data.region_3d
        matrix = self.pqo.obj.matrix_world @ rv3d.perspective_matrix
        if forced == True or matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            mw = self.pqo.obj.matrix_world
            perspective_matrix = rv3d.perspective_matrix
            mwp = mw @ perspective_matrix

            verts = self.pqo.bm.verts
#            mw = np.array( mw )
#            mp = numpy.array( perspective_matrix )
#            vo = numpy.array( [ (p.co.x,p.co.y,p.co.z,1.0) for p in verts] )
#            vw = mw @ (vo.T)
#            vp = mp @ (vw.T)

            def ProjVert( vt ) :
                v = vt.co
                wv = mw @ v
                pv = mwp @ v.to_4d()
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
        return [ ElementItem( i[0] , i[1] , i[2] ) for i in r ] 

    def PickFace( self ,coord , ignore = [] ) -> ElementItem :
        ray_origin_obj , ray_direction_obj = handleutility.calc_object_space_ray( bpy.context , self.pqo.obj , coord )

        pos,nrm,index,dist = self.pqo.btree.ray_cast( ray_origin_obj , ray_direction_obj )
        prePos = ray_origin_obj
        while( index is not None ) :
            face =  self.pqo.bm.faces[index]
            if (prePos -pos).length < 0.00001 :
                break
            prePos = pos
            if face.hide is False and face not in ignore :
                return ElementItem( face , coord , self.pqo.obj.matrix_world @ pos , dist )
            pos,nrm,index,dist = self.pqo.btree.ray_cast( pos + ray_direction_obj * 0.000001 , ray_direction_obj )

        return ElementItem.Empty()


    def CollectEdge( self ,coord , radius : float , ignore = [] ) -> ElementItem :
        ray_origin , ray_direction = handleutility.calc_ray( bpy.context , coord )
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges

        def Conv( edge ) -> ElementItem :
            h0 , h1 , d = handleutility.RayDistAndPos( edge[3] , (edge[3]-edge[4]).normalized() , ray_origin , ray_direction )
            c = handleutility.location_3d_to_region_2d(h0)
            return ElementItem( edge[0] , c , h0 , d )

        intersect = geometry.intersect_line_sphere_2d
        r = [ Conv(i) for i in viewPosEdge if None not in intersect( i[1] ,i[2] ,p,radius ) and i[0] not in ignore ]
        s = sorted( r , key=lambda i:(i.coord - p).length )

        return s

