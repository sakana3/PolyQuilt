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

class QMeshOperators :
    def __init__(self,obj) :
        self.obj = obj
        self.mesh = obj.data
        self.bm = bmesh.from_edit_mesh(self.mesh)
        self.current_matrix = None
        self.__btree = None

    @property
    def btree(self):
        if self.__btree == None :
            self.__btree = bvhtree.BVHTree.FromBMesh(self.bm)
        return self.__btree


    @property
    def verts(self): 
        return self.bm.verts

    @property
    def faces(self) :
        return self.bm.faces

    @property
    def edges(self):
        return self.bm.edges

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
        self.__btree = None

    def AddVertexFromRegionCoord( self ,coord , pivot : Vector ):
        p = handleutility.CalcPositionFromRegion( coord , pivot )
        return self.AddVertexWorld(p)

    def AddVertex( self , local_pos : Vector  ) :
        vert = self.bm.verts.new( local_pos )
        return vert

    def AddVertexWorld( self , world_pos : Vector  ) :
        p = self.obj.matrix_world.inverted() @ world_pos
        vert = self.bm.verts.new( p )
        return vert

    def AddFace( self , verts , normal ) :
        face = self.bm.faces.new( verts )
        if normal != None :
            face.normal_update()
            dp = face.normal.dot( normal )
            if dp > 0.0 :
                bmesh.utils.face_flip(face)
                face.normal_update()            
        return face

    def AddEdge( self , v0 , v1 ) :
        edge = self.bm.edges.new( (v0,v1) )
        return edge

    def Remove( self , element ) :
        if isinstance( element , bmesh.types.BMVert ) :
            bmesh.ops.delete( self.bm , geom = (element,) , context = 'VERTS' )
        elif isinstance( element , bmesh.types.BMFace ) :
            bmesh.ops.delete( self.bm , geom = (element,) , context = 'FACES' )
        elif isinstance( element , bmesh.types.BMEdge ) :
            bmesh.ops.delete( self.bm , geom = (element,) , context = 'EDGES' )

    def world_to_object_position( self , pos ) :
        return self.obj.matrix_world.inverted() @ pos

    def object_to_world_position( self , pos ) :
        return self.obj.matrix_world @ pos

    # BMesh Operators

    def dissolve_vert( self , vert  , use_verts = False , use_face_split = False , use_boundary_tear = False ) :
        if len( vert.link_faces ) == 0 and len( vert.link_edges ) <= 1 :
            self.Remove( vert)
        else :
            bmesh.ops.dissolve_verts( self.bm , verts  = (vert,) , use_face_split = use_face_split , use_boundary_tear = use_boundary_tear )

    def dissolve_edge( self , edge , use_verts = False , use_face_split = False ) :
        if len( edge.link_faces ) <= 1 :
            self.Remove( edge )
        else :
            bmesh.ops.dissolve_edges( self.bm , edges = (edge,) , use_verts = use_verts , use_face_split = use_face_split )

    def dissolve_edges( self , edges , use_verts = False , use_face_split = False ) :
        return bmesh.ops.dissolve_edges( self.bm , edges = edges , use_verts = use_verts , use_face_split = use_face_split )

    def dissolve_faces( self , fades , use_verts = False ) :
        return bmesh.ops.dissolve_faces( self.bm , fades = fades , use_verts = use_verts )

    def face_split( self , face , v0 , v1 , coords = () , use_exist=True, example=None ) :
        """Face split with optional intermediate points."""
        if example == None :
            return bmesh.utils.face_split( face , v0  , v1 , coords , use_exist )
        else :
            return bmesh.utils.face_split( face , v0  , v1 , coords , use_exist , example )

    def edge_split_from_position( self , edge , refPos ):
        refPos = self.world_to_object_position(refPos)
        fac = 0.5
        d0 = (edge.verts[0].co - refPos ).length
        d1 = (edge.verts[1].co - refPos ).length
        fac = d0 / (d0 + d1)
        return self.edge_split( edge , fac )

    def edge_split( self , edge , fac ):
        return bmesh.utils.edge_split( edge , edge.verts[0] , fac )

    def weld( self , targetmap ) :
        bmesh.ops.weld_verts(self.bm,targetmap)

    def fine_mirror( ElementItem geom )
        hit = None
        dist = bpy.context.scene.tool_settings.double_threshold
        if geon.isVert :
            co = geom.element.co
            rco = Vector( (-co.x , co.y , co.z) )

            for vert in bm.verts :
                po = vert.co
                len = (co - po).length
                if len <= dist
                    hit = vert
                    break
        return hit

    def set_positon( vert , pos , is_world = True ) :            
        if is_world :
            pos = self.bmo.obj.matrix_world.inverted() @ pos   
        vert.co = pos

        self.bmo.mesh.use_mirror_x





