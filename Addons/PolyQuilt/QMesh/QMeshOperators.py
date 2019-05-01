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
from .. import handleutility
from .. import draw_util
from .ElementItem import *
from ..dpi import *

class QMeshOperators :
    def __init__(self,obj , preferences) :
        self.obj = obj
        self.mesh = obj.data
        self.bm = bmesh.from_edit_mesh(self.mesh)
        self.current_matrix = None
        self.__btree = None
        self.__kdtree = None
        self.preferences = preferences        

    @property
    def btree(self):
        if self.__btree == None :
            self.__btree = bvhtree.BVHTree.FromBMesh(self.bm)
        return self.__btree

    @property
    def kdtree(self):
        if self.__kdtree == None :
            size = len(self.bm.verts)
            self.__kdtree = mathutils.kdtree.KDTree(size)
            for i, v in enumerate(self.bm.verts):
                self.__kdtree.insert(v.co, i)
            self.__kdtree.balance()
        return self.__kdtree

    @property
    def verts(self): 
        return self.bm.verts

    @property
    def faces(self) :
        return self.bm.faces

    @property
    def edges(self):
        return self.bm.edges

    @property
    def is_mirror(self) :
        return self.mesh.use_mirror_x

    def check_mirror(self , is_mirror ) :
        r = self.is_mirror if is_mirror is None else is_mirror
        return r

    def local_to_world_pos(  self ,pos : Vector ) :
        return self.obj.matrix_world @ pos

    def world_to_local_pos(  self ,pos : Vector ) :
        return self.obj.matrix_world.inverted() @ pos

    @staticmethod
    def mirror_pos( pos : Vector ) :
        return Vector( (-pos[0],pos[1],pos[2]) )

    @staticmethod
    def zero_pos( pos : Vector ) :
        return Vector( (0,pos[1],pos[2]) )

    @staticmethod
    def is_x_zero_pos( pos : Vector ) :
        dist = bpy.context.scene.tool_settings.double_threshold
        return abs(pos[0]) < dist

    def mirror_world_pos( self , world_pos ) :
        pos = self.obj.matrix_world.inverted() @ world_pos
        rpos = self.mirror_pos(pos)
        wpos = self.obj.matrix_world @ rpos
        return wpos

    def mirror_world_poss( self , poss ) :
        return [ self.mirror_world_pos(pos) for pos in poss ]

    def check_near( self , v0 , v1 ) :
        c0 = handleutility.location_3d_to_region_2d( self.obj.matrix_world @ v0 )
        c1 = handleutility.location_3d_to_region_2d( self.obj.matrix_world @ v1 )        
        radius = self.preferences.distance_to_highlight * dpm()      
        return (c0-c1).length <= radius 


    def CheckValid( self ) :
        if not self.bm.is_valid :
            self.bm = bmesh.from_edit_mesh(self.mesh)

    def UpdateMesh( self ) :
        self.CheckValid()
        # ensure系は一応ダーティフラグチェックしてるので無暗に呼んでいいっぽい？
        self.bm.faces.ensure_lookup_table()
        self.bm.verts.ensure_lookup_table()
        self.bm.edges.ensure_lookup_table()
        self.bm.normal_update()        
        bmesh.update_edit_mesh(self.mesh , loop_triangles = True,destructive = True )
        if self.__btree :
            del self.__btree
            self.__btree = None
        if self.__kdtree :
            del self.__kdtree
            self.__kdtree = None

    def AddVertex( self , local_pos : Vector , is_mirror = None ) :
        vert = self.bm.verts.new( local_pos )
        if self.check_mirror(is_mirror) and self.is_x_zero_pos(local_pos) is False :
            mirror = self.bm.verts.new( self.mirror_pos(local_pos) )

        return vert

    def AddVertexWorld( self , world_pos : Vector , is_mirror = None ) :
        p = self.obj.matrix_world.inverted() @ world_pos
        vert = self.AddVertex( p , is_mirror )
        return vert

    def AddFace( self , verts , normal = None , is_mirror = None ) :
        face = self.bm.faces.new( verts )
        if normal != None :
            face.normal_update()
            dp = face.normal.dot( normal )
            if dp > 0.0 :
                bmesh.utils.face_flip(face)
                face.normal_update()           
                verts = verts[::-1] 

        if self.check_mirror(is_mirror) :
            mirror = [ self.find_mirror(v,False) for v in verts[::-1] ]
            if all(mirror) :
                if set(verts) ^ set(mirror) :
                    face = self.bm.faces.new( mirror )

        return face

    def add_edge( self , v0 , v1 , is_mirror = None ) :
        edge = self.bm.edges.get( (v0,v1) )        
        if edge is None :
            edge = self.bm.edges.new( (v0,v1) )

        if self.check_mirror(is_mirror) :
            m0 = self.find_mirror( v0 , False )
            m1 = self.find_mirror( v1 , False )
            if m0 is not None and m1 is not None :
                if m0 == v0 and m1 == v1 :
                    pass
                else :
                    self.add_edge( m0 , m1 , False )

        return edge

    def Remove( self , geom , is_mirror = None ) :
        geoms = (geom,)
        if self.check_mirror(is_mirror) :
            mirror = self.find_mirror(geom)
            if mirror is not None :
                geoms = (geom,mirror)
        if isinstance( geom , bmesh.types.BMVert ) :
            bmesh.ops.delete( self.bm , geom = geoms , context = 'VERTS' )
        elif isinstance( geom , bmesh.types.BMFace ) :
            bmesh.ops.delete( self.bm , geom = geoms , context = 'FACES' )
        elif isinstance( geom , bmesh.types.BMEdge ) :
            bmesh.ops.delete( self.bm , geom = geoms , context = 'EDGES' )

    # BMesh Operators

    def dissolve_vert( self , vert  , use_verts = False , use_face_split = False , use_boundary_tear = False, is_mirror = None  ) :
        if vert.is_manifold == False :
            self.Remove( vert , is_mirror )
        else :
            verts = [vert,]
            if self.check_mirror(is_mirror) :
                mirror = self.find_mirror( vert )
                if mirror != None :
                    verts.append(mirror)
            bmesh.ops.dissolve_verts( self.bm , verts  = verts , use_face_split = use_face_split , use_boundary_tear = use_boundary_tear )

    def dissolve_edge( self , edge , use_verts = False , use_face_split = False, is_mirror = None  ) :
        if len( edge.link_faces ) <= 1 :
            self.Remove( edge , is_mirror )
        else :
            self.dissolve_edges( edges = (edge,) , use_verts = use_verts , use_face_split = use_face_split, is_mirror = is_mirror )

    def dissolve_edges( self , edges , use_verts = False , use_face_split = False, is_mirror = None ) :
        if self.check_mirror(is_mirror) :
            mirror_edges = [self.find_mirror(edge) for edge in edges ]
            mirror_edges = {edge for edge in mirror_edges if edge is not None }
            edges = list( set(edges) | mirror_edges )

        bmesh.ops.dissolve_edges( self.bm , edges = edges , use_verts = use_verts , use_face_split = use_face_split )

    def dissolve_faces( self , fades , use_verts = False ) :
        return bmesh.ops.dissolve_faces( self.bm , fades = fades , use_verts = use_verts )

    def face_split( self , face , v0 , v1 , coords = () , use_exist=True, example=None, is_mirror = None  ) :
        """Face split with optional intermediate points."""
        if self.check_mirror(is_mirror) :
            mirror_face = self.find_mirror(face , False)
            mirror_v0 = self.find_mirror(v0 , False)
            mirror_v1 = self.find_mirror(v1 , False)
            if None not in ( mirror_face , mirror_v0 , mirror_v1 ) :
                if (mirror_v0 == v0 and mirror_v1 == v1) or (mirror_v0 == v1 and mirror_v1 == v0) :
                    pass
                else :
                    new_face , new_edge = bmesh.utils.face_split( mirror_face , mirror_v0  , mirror_v1 , coords , use_exist )
                    if (v0 not in face.verts or v1 not in face.verts ) and (v0 not in new_face.verts or v1 not in new_face.verts ):
                        return
                    if v0 in new_face.verts and v1 in new_face.verts :
                        return bmesh.utils.face_split( new_face , v0  , v1 , coords , use_exist )
            
        return bmesh.utils.face_split( face , v0  , v1 , coords , use_exist )

    def __calc_split_fac( self , edge , refPos ) :
        fac = 0.5
        d0 = (edge.verts[0].co - refPos ).length
        d1 = (edge.verts[1].co - refPos ).length
        fac = d0 / (d0 + d1)
        return fac

    def edge_split_from_position( self , edge , refPos , is_mirror = None):
        mirror_edge = None
        if self.check_mirror(is_mirror) and self.is_x_zero_pos( refPos ) is False :
            mirror_edge = self.find_mirror( edge , False )

        fac = self.__calc_split_fac( edge , refPos )
        new_edge , new_vert = bmesh.utils.edge_split( edge , edge.verts[0] , fac )

        if mirror_edge is not None :
            if new_edge is mirror_edge :
                if set(edge.verts) & set(mirror_edge.verts) :
                    mirror_edge = new_edge
            rfac = self.__calc_split_fac( mirror_edge , self.mirror_pos(refPos) )
            bmesh.utils.edge_split( mirror_edge , mirror_edge.verts[0] , rfac )

        return new_edge , new_vert


    def weld( self , targetmap ) :
        bmesh.ops.weld_verts(self.bm,targetmap)

    def set_positon( self , geom , pos , is_world = True ) :            
        if is_world :
            pos = self.obj.matrix_world.inverted() @ pos   
        geom.co = pos

    def test_mirror( self , v0 , v1 ) :
        dist = bpy.context.scene.tool_settings.double_threshold
        p0 = Vector((-v0[0],v0[1],v0[2]))
        p1 = v1
        return (p0 - p1).length <= dist

    def test_mirror_geom( self , geom0 , geom1 ) :
        if type(geom0) == type(geom1) :
            if isinstance( geom0 , bmesh.types.BMVert ) :
                return self.test_mirror( geom0.co , geom1.co )
            elif isinstance( geom0 , bmesh.types.BMFace ) or isinstance( geom0 , bmesh.types.BMEdge ):
                for vert0 in geom0.verts :
                    if not any( [ self.test_mirror(vert0.co,vert1.co) for vert1 in geom1.verts] ) :
                        break
                else :
                    return True
        return False


    def find_mirror( self , geom , check_same = True ) :
        result = None
        dist = bpy.context.scene.tool_settings.double_threshold

        if isinstance( geom , bmesh.types.BMVert ) :
            co = self.mirror_pos( geom.co )

            hits = self.kdtree.find_range(co, dist )

            if hits != None :
                if len(hits) == 1 :
                    result = self.bm.verts[hits[0][1]] 
                elif len(hits) > 0 :
                    hits = sorted( hits , key=lambda x:x[2])
                    result = self.bm.verts[ hits[0][1] ] 
                    for h in hits :
                        hitV = self.bm.verts[h[1]]
                        for edge in geom.link_edges :
                            if not any( [ self.test_mirror_geom(edge,e) for e in hitV.link_edges ]):
                                break
                        else :
                            result = hitV
                            break
        elif isinstance( geom , bmesh.types.BMFace ) or isinstance( geom , bmesh.types.BMEdge ):
            mirror_cos = [ self.mirror_pos( v.co ) for v in geom.verts ]

            hits = self.kdtree.find_range(mirror_cos[0], dist )
            if hits != None :
                for hit in hits :
                    hitvert = self.bm.verts[hit[1]]                    
                    links = hitvert.link_edges if isinstance( geom , bmesh.types.BMEdge ) else hitvert.link_faces
                    for link in links :
                        if self.test_mirror_geom( link , geom ) :
                            result = link
                            break
                    else :
                        continue
                    break

        if check_same and result is not None and result.index == geom.index :
            return None

        return result
