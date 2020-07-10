import sys
import bpy
import bmesh
import math
import mathutils
import copy
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *

class move_component_module :
    def __init__( self , qmesh : QMesh , startTarget : ElementItem , startMousePos : mathutils.Vector , move_type : str, fix_to_x_zero : bool  ) :
        self.bmo = qmesh
        self.currentTarget = startTarget
        self.fix_to_x_zero = fix_to_x_zero
        self.start_mouse_pos = copy.copy(startTarget.coord)
        self.start_pos = startTarget.hitPosition.copy()
        self.mouse_pos = startMousePos.copy()

        self.normal_ray = pqutil.Ray( self.start_pos , self.bmo.local_to_world_nrm( startTarget.normal ) )
        self.normal_ray.origin = self.start_pos

        self.screen_space_plane = pqutil.Plane.from_screen( bpy.context , startTarget.hitPosition )
        self.move_plane = self.screen_space_plane
        self.move_ray = None

        self.set_move_type(move_type)
        self.repeat = False
        self.verts = {}
        self.mirror_set = {}
        self.move = mathutils.Vector( (0,0,0) )

    def set_geoms( self , geoms , is_mirror = None ) :
        self.verts = {}
        self.mirror_set = {}
        for geom in geoms :
            if geom != None :
                if isinstance( geom , bmesh.types.BMVert ) :
                    self.verts[geom] = geom.co.copy()
                elif isinstance( geom , bmesh.types.BMEdge ) :
                    for vert in geom.verts :
                        self.verts[vert] = vert.co.copy()
                elif isinstance( geom , bmesh.types.BMFace ) :
                    for vert in geom.verts :
                        self.verts[vert] = vert.co.copy()
                elif isinstance( geom , bmesh.types.BMLoop ) :
                    self.verts[geom] = geom.vert.co.copy()

        if self.bmo.check_mirror( is_mirror ) :
            self.mirror_set = { v : self.bmo.find_mirror( v , False ) for v in self.verts }
        else :
            self.mirror_set = { v : None for v in self.verts }

    def update_geoms( self , move : mathutils.Vector ) -> bool :

        if (self.move - move).length >= sys.float_info.epsilon :
            self.move = move
            wm = self.bmo.obj.matrix_world 
            im = wm.inverted()

            for vert , mirror in self.mirror_set.items() :
                initial_pos = self.verts[vert]
                p = wm @ initial_pos
                p = p + move
                p = QSnap.view_adjust(p)
                p = im @ p

                if self.fix_to_x_zero and self.bmo.is_x_zero_pos( initial_pos ) :
                    p.x = 0.0
                if mirror == vert :
                    p.x = 0.0

                if mirror :
                    m = mathutils.Vector( (-p.x,p.y,p.z) )
                    if mirror in self.verts :
                        if (self.start_pos.x >= 0 and initial_pos.x >= 0 ) or (self.start_pos.x <= 0 and initial_pos.x <= 0 ) :
                            vert.co , mirror.co = p , m
                    else :
                        vert.co , mirror.co = p , m
                else :
                    vert.co = p

            return True
        return False

    def update( self , event ) :
        if event.type == 'WHEELUPMOUSE' :
            a = { 'FREE' : 'X' , 'X' : 'Y'  , 'Y' : 'Z' , 'Z' : 'NORMAL' , 'NORMAL' : 'FREE' }
            self.set_move_type( a[self.move_type] )
        elif event.type == 'WHEELDOWNMOUSE' :
            a = { 'FREE' : 'NORMAL' , 'X' : 'FREE' , 'Y' : 'X' , 'Z' : 'Y' , 'NORMAL' : 'Z' }
            self.set_move_type( a[self.move_type] )
        elif event.value == 'PRESS' :
            if self.repeat == False :
                if event.type == 'X' :
                    self.set_move_type( 'X' )
                elif event.type == 'Y' :
                    self.set_move_type( 'Y' )
                elif event.type == 'Z' :
                    self.set_move_type( 'Z' )
                elif event.type == 'N' :
                    self.set_move_type( 'NORMAL'  )
                elif event.type == 'T' :
                    self.set_move_type( 'TANGENT'  )
            self.repeat = True
        elif event.value == 'RELEASE' :
            self.repeat = False

    def set_move_type( self ,move_type : str) :
        self.move_type = move_type
        self.change_ray(self.move_type)

    def move_to( self ,  mouse_pos: mathutils.Vector , change_conponent = True ) -> mathutils.Vector :
        move = mathutils.Vector( (0.0,0.0,0.0) )

        if self.move_ray != None :
            ray = pqutil.Ray.from_screen( bpy.context , mouse_pos )
            p0 , p1 , d = self.move_ray.distance( ray )

            move = ( p0 - self.move_ray.origin )
        elif self.move_plane != None :
            rayS = pqutil.Ray.from_screen( bpy.context , self.start_mouse_pos )
            rayG = pqutil.Ray.from_screen( bpy.context , mouse_pos )
            vS = self.move_plane.intersect_ray( rayS )
            vG = self.move_plane.intersect_ray( rayG )

            move = (vG - vS)

        if change_conponent :
            self.currentTarget.hitPosition = self.start_pos + move

        return move

    def change_ray( self , move_type : str ) :
        self.move_plane = None
        self.move_ray = None
        self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )

        if self.fix_to_x_zero and self.currentTarget.is_x_zero:
            plane = pqutil.Plane( mathutils.Vector((0,0,0) ) ,  mathutils.Vector((1,0,0) ) ).object_to_world( self.bmo.obj )
            plane.origin = self.start_pos

        if move_type == 'FREE' :
            self.move_plane = self.screen_space_plane
        elif move_type == 'X' :
            self.move_ray = pqutil.Ray( self.start_pos , mathutils.Vector( (1,0,0) ) )
            self.move_color = ( 1.0 , 0.0 ,0.0 ,1.0  )
        elif move_type == 'Y' :
            self.move_ray = pqutil.Ray( self.start_pos , mathutils.Vector( (0,1,0) ) )
            self.move_color = ( 0.0 , 1.0 ,0.0 ,1.0  )
        elif move_type == 'Z' :
            self.move_ray = pqutil.Ray( self.start_pos , mathutils.Vector( (0,0,1) ) )
            self.move_color = ( 0.0 , 0.0 ,1.0 ,1.0  )
        elif move_type == 'NORMAL' :
            self.move_ray = self.normal_ray
            self.move_color = ( 1.0 , 1.0 ,1.0 ,1.0  )
        elif move_type == 'TANGENT' :
            self.move_plane = pqutil.Plane( self.start_pos , self.normal_ray.vector )

    def draw_3D( self , context  ) :
        if self.move_ray != None :
            v0 = self.move_ray.origin
            v1 = v0 + self.move_ray.vector * 10000.0 
            v2 = v0 - self.move_ray.vector * 10000.0 
            draw_util.draw_lines3D( context , (v1,v2) , self.move_color , 1.0 , 0.2 )


    @staticmethod
    def check_move_type( target : ElementItem , move_type0  : str, move_type1 : str) -> str :
        move_type = move_type0
        if move_type1 == None :
            if target.is_hit_center() :
                move_type = 'NORMAL'
        else :
            move_type = move_type1

        return move_type
