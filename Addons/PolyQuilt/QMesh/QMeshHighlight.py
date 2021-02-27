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
from .QSnap import QSnap
import time

__all__ = ['QMeshHighlight']

class QMeshHighlight :
    __grobal_tag__ = 0

    def __init__(self,pqo) :
        self.pqo = pqo
        self.__viewPosVertsNP = None
        self.__viewPosVertsIdx = None
        self.__viewPosEdgeNP = None
        self.__viewPosEdgeIdx = None
        self.current_matrix = None
        self.__boundaryViewPosVerts = None
        self.__boundaryViewPosEdges = None
        self.__local_tag__ = 0

    @property
    def viewPosVerts(self):
        if self.__viewPosVertsNP is None :
            self.UpdateView( bpy.context , True )
        return self.__viewPosVertsNP , self.__viewPosVertsIdx

    @property
    def viewPosEdges(self):
        if self.__viewPosEdgeNP is None :
            self.UpdateView( bpy.context , True )
        return self.__viewPosEdgeNP , self.__viewPosEdgeIdx

    @property
    def boundaryViewPosVerts(self):
        self.checkDirty()
        if self.__boundaryViewPosVerts is None :
            verts = self.pqo.bm.verts            
            t = np.fromiter( [ vi for vi , vp in [ (i , verts[j]) for i,j in enumerate(self.__viewPosVertsIdx) ] if vp.is_boundary or vp.is_wire or not vp.is_manifold ] , dtype = np.int32 )
            self.__boundaryViewPosVerts = t
        return self.__boundaryViewPosVerts

    @property
    def boundaryViewPosEdges(self):
        self.checkDirty()
        if self.__boundaryViewPosEdges is None  :
            edges = self.pqo.bm.edges
            self.__boundaryViewPosEdges = np.fromiter( [ ei for ei , ep in [ (i , edges[j]) for i,j in enumerate(self.__viewPosEdgeIdx) ] if ep.is_boundary or ep.is_wire ] , dtype = np.int32 )
        return self.__boundaryViewPosEdges

    def setDirty( self ) :
        QMeshHighlight.__grobal_tag__ = QMeshHighlight.__grobal_tag__ + 1
        self.checkDirty()

    def checkDirty( self ) :
        if QMeshHighlight.__grobal_tag__ != self.__local_tag__ :
            if self.__viewPosVertsNP is None:
                del self.__viewPosVertsNP
            self.__viewPosVertsNP = None

            if self.__viewPosVertsIdx is None:
                del self.__viewPosVertsIdx
            self.__viewPosVertsIdx = None

            if self.__viewPosEdgeNP is None:
                del self.__viewPosEdgeNP
            self.__viewPosEdgeNP = None

            if self.__viewPosEdgeIdx is None:
                del self.__viewPosEdgeIdx
            self.__viewPosEdgeIdx = None

            if self.__boundaryViewPosVerts is None:
                del self.__boundaryViewPosVerts
            self.__boundaryViewPosVerts = None

            if self.__boundaryViewPosEdges is None:
                del self.__boundaryViewPosEdges
            self.__boundaryViewPosEdges = None

            self.current_matrix = None
            self.__local_tag__ = QMeshHighlight.__grobal_tag__

    def UpdateView2( self ,context , forced = False ):
        start = time.time()
        rv3d = context.region_data
        pj_matrix = rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        self.checkDirty()

        if forced == True or pj_matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0
            mat_scaleX = mathutils.Matrix.Scale( halfW , 4 , (1.0, 0.0, 0.0))
            mat_scaleY = mathutils.Matrix.Scale( halfH , 4 , (0.0, 1.0, 0.0))
            matrix = mat_scaleX @ mat_scaleY @ pj_matrix
            halfWH = Vector( (halfW,halfH) )

            def ProjVert( vt ) :
                pv = matrix @ vt.co.to_4d()
                return pv.to_2d() / pv[3] + halfWH if pv[3] > 0.0 else None

            verts = self.pqo.bm.verts
            viewPos = { p : ProjVert(p) for p in verts }
#           viewPos = compute( verts , pj_matrix , region.width , region.height )

            edges = self.pqo.bm.edges
            viewEdges = { e : [ viewPos[e.verts[0]] , viewPos[e.verts[1]] ] for e in edges if not e.hide }
#           viewEdges = { e : [ viewPos[v1] , viewPos[v2] ] for e , (v1,v2) in [ (e , e.verts) for e in edges if not e.hide ] }

            self.__viewPosEdges = { e : v for e , v in viewEdges.items() if None not in v }
            self.__viewPosVerts = { v : p for v,p in viewPos.items() if p and not v.hide }
            self.__boundaryViewPosEdges = None
            self.__boundaryViewPosVerts = None

            self.current_matrix = pj_matrix

            elapsed_time = time.time() - start
            print ("elapsed_time:{0}".format(elapsed_time) + "[sec]")       

    def UpdateView( self ,context , forced = False ):
        start = time.time()

        rv3d = context.region_data
        pj_matrix = rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        self.checkDirty()

        if forced == True or pj_matrix != self.current_matrix :
            region = context.region
            halfW = region.width / 2.0
            halfH = region.height / 2.0

            vts = self.pqo.bm.verts
            vlen = len(vts)

            vco = np.fromiter( [x for v in vts for x in v.co], dtype=np.float32, count = vlen*3)  

            coords = np.empty((vlen, 4), dtype=np.float32 )
            coords[:,3] = 1.0
            coords[:,:-1] = vco.reshape((vlen, 3))
            coords = np.dot( coords , np.array( pj_matrix, dtype=np.float32 ).transpose() )

            coords = coords[:,:-1] / coords[:,3:4]
            coords = coords * np.array((halfW,halfH,1), dtype=np.float32) +  np.array((halfW,halfH,0), dtype=np.float32)

#            verts = self.pqo.bm.verts
#            viewPos = { p : Vector( c[:2] ) for p,c in zip(verts , coords) }

            edges = self.pqo.bm.edges
#            viewEdges = { e : [ viewPos[e.verts[0]] , viewPos[e.verts[1]] ] for e in edges if not e.hide }
#           viewEdges = { e : [ viewPos[v1] , viewPos[v2] ] for e , (v1,v2) in [ (e , e.verts) for e in edges if not e.hide ] }

            elen = len(edges)
            eds = np.fromiter( [v.index for e in edges for v in e.verts ], dtype=np.int32, count = elen *2)

            css = coords.reshape(vlen,3)
            eds = css[eds].reshape(elen,2,3)
            vidxs = np.where( coords[:,2].reshape(vlen) < 1.0 )
            self.__viewPosVertsNP = coords[vidxs][:,:2]
            self.__viewPosVertsIdx = vidxs[0]

            insight = np.all( ( eds[:,:,2] < 1.0 ).reshape(elen,2) , axis = -1 )
            eidxs = np.where( insight )
            self.__viewPosEdgeIdx = eidxs[0]
            self.__viewPosEdgeNP =  eds[eidxs][:,:,0:2]

#            self.__viewPosEdges = { e : v for e , v in viewEdges.items() if None not in v }
#            self.__viewPosVerts = { v : p for v,p in viewPos.items() if p and not v.hide }
            self.__boundaryViewPosEdges = None
            self.__boundaryViewPosVerts = None

            self.current_matrix = pj_matrix            

            self.find_quad2( (0,0) )

#            elapsed_time = time.time() - start
#            print ("__elapsed_time:{0}".format(elapsed_time) + "[sec]")            

    def CollectVerts2( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = True ) -> ElementItem :

        p = Vector( coord )
        viewPos = self.viewPosVerts
        rr = Vector( (radius,0) )
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

    def CollectVerts( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = True ) -> ElementItem :
        viewPosVerts , viewPosVertIdx = self.viewPosVerts

#        start = time.time()        
        co = np.array( coord , dtype = np.float32 )
        verts = self.pqo.bm.verts

        rt = np.linalg.norm( viewPosVerts - co , axis=-1 )
 
        ri = np.where( rt <= radius )
        vts = [ [verts[ viewPosVertIdx[i] ] , viewPosVerts[i] ] for i in ri[0] ]

        if edgering :
            vts = [ v for v in vts if v[0].is_boundary or v[0].is_manifold == False ]

        if backface_culling :
            ray = pqutil.Ray.from_screen( bpy.context , coord ).world_to_object( self.pqo.obj )
            vts = [ v for v in vts if v[0].is_manifold == False or v[0].is_boundary or v[0].normal.dot( ray.vector ) < 0 ]

        vts = [ v for v in vts if not v[0].hide and v[0] not in ignore ]

        vts = sorted( vts , key=lambda i: np.linalg.norm(i[1] - co) )
        matrix_world = self.pqo.obj.matrix_world

#        elapsed_time = time.time() - start
#        print ("_elapsed_time:{0}".format(elapsed_time) + "[sec]")        

        return [ ElementItem( self.pqo , v , Vector(t) , matrix_world @ v.co ) for v,t in vts ] 


    def CollectEdge( self ,coord , radius : float , ignore = [] , backface_culling = True , edgering = False ) -> ElementItem :
        viewPosEdges , viewPosEdgesIdx = self.viewPosEdges

        co = np.array( coord , dtype = np.float32 )
        edges = self.pqo.bm.edges
        p = Vector( coord )
        ray = pqutil.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = pqutil.location_3d_to_region_2d
        matrix_world = self.pqo.obj.matrix_world      

        edgeNum = viewPosEdges.shape[0]
        a = viewPosEdges[:,0:1].reshape(edgeNum,2)
        b = viewPosEdges[:,1:2].reshape(edgeNum,2)

        ab = a - b
        ba = -ab
        pa = co - a 
        pb = co - b

        t0 = (ba[:,None,:] @ pa[...,None]).ravel()
        t1 = (ab[:,None,:] @ pb[...,None]).ravel()

        dist = np.abs( np.cross( ba , pa ) / np.linalg.norm( ba , axis=-1 ) )

        hit = (t0 > 0) & (t1 > 0) & (dist < radius)
        hit = [ edges[h] for h in viewPosEdgesIdx[np.where(hit)] ]

        def Conv( edge ) -> ElementItem :
            v1 = matrix_world @ edge.verts[0].co
            v2 = matrix_world @ edge.verts[1].co
            h0 , h1 , d = ray_distance( pqutil.Ray( v1 , (v1-v2) ) )
            c = location_3d_to_region_2d(h1)
            return ElementItem( self.pqo , edge , c , h1 , d )

        if edgering :        
            r = [ Conv(e) for e in hit if not e.hide and len(e.link_faces) <= 1 and e not in ignore ]
        else :
            r = [ Conv(e) for e in hit if not e.hide and e not in ignore ]

        if backface_culling :
            ray2 = ray.world_to_object( self.pqo.obj )
            r = [ i for i in r
                if not i.element.is_manifold or i.element.is_boundary or
                    i.element.verts[0].normal.dot( ray.vector ) < 0 or i.element.verts[1].normal.dot( ray2.vector ) < 0 ]
        
        s = sorted( r , key=lambda i:(i.coord - p).length_squared )

        return s


    def CollectEdge2( self ,coord , radius : float , ignore = [] , backface_culling = True , edgering = False ) -> ElementItem :
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges
        ray = pqutil.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = pqutil.location_3d_to_region_2d
        intersect_line_sphere_2d = geometry.intersect_line_sphere_2d
        intersect_sphere_sphere_2d = geometry.intersect_sphere_sphere_2d
        intersect_point_line = geometry.intersect_point_line
        matrix_world = self.pqo.obj.matrix_world      
        rr = Vector( (radius,0) )

        def Conv( edge ) -> ElementItem :
            v1 = matrix_world @ edge.verts[0].co
            v2 = matrix_world @ edge.verts[1].co
            h0 , h1 , d = ray_distance( pqutil.Ray( v1 , (v1-v2) ) )
            c = location_3d_to_region_2d(h1)
            return ElementItem( self.pqo , edge , c , h1 , d )

        def intersect( p1 , p2 ) :
            hit , pt = intersect_point_line( p , p1 , p2 )
            if pt > 0 and pt < 1 :
                if hit - p <= rr :
                    return True

            return False
        edges = self.pqo.bm.edges
        if edgering :        
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if len(e.link_faces) <= 1 and intersect( p1 , p2 ) and e not in ignore ]
        else :
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if intersect( p1 , p2 ) and e in edges and e not in ignore ]

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


    def find_quad2( self , coord ) :
        co = np.array( coord , dtype = np.float32 )   
        verts = self.pqo.bm.verts
        vpos = self.__viewPosVertsNP[ self.boundaryViewPosVerts ]
        vids = self.__viewPosVertsIdx[ self.boundaryViewPosVerts ]
        epos = self.__viewPosEdgeNP[ self.boundaryViewPosEdges ]
        eids = self.__viewPosEdgeIdx[ self.boundaryViewPosEdges ]
        matrix = self.pqo.obj.matrix_world

        st = np.argsort( np.linalg.norm( vpos - co , axis=-1 ) )

        T = np.array([[0, -1], [1, 0]])

        l0 = epos[:,0]
        l1 = epos[:,1]

        def convex_hull( points ) :
            idxs = mathutils.geometry.convex_hull_2d( points )
            if len(idxs) != len(points) :
                angles = [ [  math.atan2( point[1] - coord[1] , point[0] - coord[0] ) , index ] for index , point in enumerate(points) ]
                angles.sort(key=lambda x:x[0] , reverse=False)
                return [ i for r,i in angles ]
            return idxs

        def Check( vp ) :
            da = np.atleast_2d( vp - co )
            db = np.atleast_2d( l1 - l0 )
            dp = np.atleast_2d( co - l0 )

            dap = np.dot( da , T )
            denom = np.sum(dap * db, axis=1)
            num = np.sum(dap * dp, axis=1)
            t = np.atleast_2d(num / denom).T * db + l1

            d = np.linalg.norm( l0 - l1, axis=-1  )

            dist = np.linalg.norm( vp - co, axis=-1 )
#            g = ( np.linalg.norm( co - t, axis=-1 ) < dist ) & (np.linalg.norm(l0 - t, axis=-1 ) > d) & ( np.linalg.norm(l1 - t, axis=-1 ) > d )
            g = ( np.linalg.norm( co - t, axis=-1 ) < dist )

            hits = t[g]
            hits = hits[ np.argsort( np.linalg.norm( hits - co , axis=-1 ) ) ]
            return hits

        def Check2( vp ) :
            for l in epos :
                hit = mathutils.geometry.intersect_line_line_2d( co , vp , l[0], l[1] )
                if hit != None and (hit - Vector(vp) ).length > 0.001 :
                    return True
            return False

        geom = []
        for s in st :
            vi = vids[s]
            vo = verts[vi]

            # オブジェクト表面か？
            if not QSnap.is_target( matrix @ vo.co ) :       
                continue

            vp = vpos[s]
            line = np.array( (co,vp) ).reshape( 2,2 )

            #ライン交差
            if Check2(vp) :
                continue

            geom.append( (vo,vp) )

            if len(geom) >= 3 :
                geom = [ geom[i] for i in convex_hull( [ p for v,p in geom ] ) ]

            if( len(geom) >= 4 ) :
                break
                
        return [ v for v,p in geom]

    @classmethod
    def find_quad( cls , bmo , startPos ) :
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
                return [ q[1] for q in quad ]

            if len(quad) >= 3 :
                if mathutils.geometry.intersect_point_tri( startPos , quad[0][2] , quad[1][2] , quad[2][2] ) :
                    return [ q[1] for q in quad ]

        return None


    def check_hit_element_vert( self , element , mouse_pos ,radius = None ) :
        if radius == None :
            self.preferences.distance_to_highlight * dpm()

        rv3d = bpy.context.region_data
        region = bpy.context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        mat_scaleX = mathutils.Matrix.Scale( halfW , 4 , (1.0, 0.0, 0.0))
        mat_scaleY = mathutils.Matrix.Scale( halfH , 4 , (0.0, 1.0, 0.0))
        matrix = mat_scaleX @ mat_scaleY @ rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        halfWH = Vector( (halfW,halfH) )        
        def ProjVert( vt ) :
            pv = matrix @ vt.co.to_4d()
            return pv.to_2d() / pv[3] + halfWH if pv[3] > 0.0 else None

        for v in element.verts :
            co = ProjVert( v )
            if ( mouse_pos - co ).length <= radius :
                return v

        return None

    def check_hit_element_edge( self , element , mouse_pos ,radius ) :
        rv3d = bpy.context.region_data
        region = bpy.context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        mat_scaleX = mathutils.Matrix.Scale( halfW , 4 , (1.0, 0.0, 0.0))
        mat_scaleY = mathutils.Matrix.Scale( halfH , 4 , (0.0, 1.0, 0.0))
        matrix = mat_scaleX @ mat_scaleY @ rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        halfWH = Vector( (halfW,halfH) )        
        def ProjVert( vt ) :
            pv = matrix @ vt.co.to_4d()
            return pv.to_2d() / pv[3] + halfWH if pv[3] > 0.0 else None

        intersect_point_line = geometry.intersect_point_line
        rr = Vector( (radius,0) )
        def intersect( p1 , p2 ) :
            hit , pt = intersect_point_line( mouse_pos , p1 , p2 )
            if pt > 0 and pt < 1 :
                if hit - mouse_pos <= rr :
                    return True

        for e in element.edges :
            co0 = ProjVert( e.verts[0] )
            co1 = ProjVert( e.verts[1] )
            if intersect(co0,co1) :
                return e

        return None
