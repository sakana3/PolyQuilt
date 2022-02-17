import sys
import bpy
import bmesh
import math
import mathutils
import copy
import collections
from ..utils.dpi import *
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
        self.center_verts = set()
        self.slide_guid = None

    def set_geoms( self , geoms , is_mirror = None ) :
        self.verts = {}
        self.mirror_set = {}
        self.center_verts = set()
        for geom in geoms :
            if geom != None :
                if isinstance( geom , bmesh.types.BMVert ) :
                    self.verts[geom] = geom.co.copy()
                    if self.bmo.is_x_zero_pos( geom.co ) :
                        self.center_verts.add(geom)
                elif isinstance( geom , bmesh.types.BMEdge ) :
                    for vert in geom.verts :
                        self.verts[vert] = vert.co.copy()
                    if all( self.bmo.is_x_zero_pos( v.co ) for v in geom.verts ) :
                        for vert in geom.verts :
                            self.center_verts.add(vert)
                elif isinstance( geom , bmesh.types.BMFace ) :
                    for vert in geom.verts :
                        self.verts[vert] = vert.co.copy()
                    if all( self.bmo.is_x_zero_pos( v.co ) for v in geom.verts ) :
                        for vert in geom.verts :
                            self.center_verts.add(vert)
                elif isinstance( geom , bmesh.types.BMLoop ) :
                    self.verts[geom] = geom.vert.co.copy()

        if self.bmo.check_mirror( is_mirror ) :
            self.mirror_set = { v : self.bmo.find_mirror( v , True ) for v in self.verts }
        else :
            self.mirror_set = { v : None for v in self.verts }

    def setup_slide( self , edgeloops : list ) :
        self.slide_guid = []
        for loop in self.currentTarget.element.link_loops :
            link = self.bmo.collect_loops( loop , edgeloops )
            pair = {}
            for l in link :
                pair[ l.vert ] = l.link_loop_prev.vert
                pair[ l.link_loop_next.vert ] = l.link_loop_next.link_loop_next.vert
            self.slide_guid.append( pair )

    def update_geoms( self , move : mathutils.Vector , snap_type : str = 'VIEW' ) -> bool :

        if (self.move - move).length >= sys.float_info.epsilon :
            pos_table = self.update_geoms_pos(move,snap_type)
            self.update_geoms_verts( pos_table )
            return True

        return False

    def update_geoms_verts( self , pos_table : list ) -> bool :
        for vert , mirror in self.mirror_set.items() :
            if vert and vert in pos_table :
                vert.co = pos_table[vert]
                
            if mirror and mirror in pos_table :
                mirror.co = pos_table[mirror]

    def update_geoms_pos( self , move : mathutils.Vector , snap_type : str = 'VIEW' , move_center : bool = False  ) -> bool :
        ret = {}

        if (self.move - move).length >= sys.float_info.epsilon :
            self.move = move
            wm = self.bmo.obj.matrix_world 
            im = wm.inverted()

            is_center_snap = self.bmo.is_mirror_mode or self.bmo.preferences.fix_to_x_zero
            is_fix_center = False
            if is_center_snap :
                if self.currentTarget.isEdge or self.currentTarget.isVert :
                    if self.bmo.is_x0_snap( self.start_pos + move ) :
                        is_fix_center = True

            for vert , mirror in self.mirror_set.items() :
                initial_pos = self.verts[vert]
                p = wm @ initial_pos
                p = p + move
                if QSnap.is_active() :
                    if snap_type == 'VIEW' :
                        p = QSnap.view_adjust(p)
                    elif snap_type == 'NEAR' :
                        p , _ = QSnap.adjust_point(p)
                p = im @ p

                if is_center_snap and self.bmo.is_x_zero_pos( initial_pos ) and ( move_center == False or vert not in self.center_verts ) :
                    p.x = 0.0
                elif mirror == vert :
                    p.x = 0.0
                elif is_fix_center :
                    p.x = 0.0

                if mirror :
                    m = mathutils.Vector( (-p.x,p.y,p.z) )
                    if mirror in self.verts :
                        if (self.start_pos.x >= 0 and initial_pos.x >= 0 ) or (self.start_pos.x <= 0 and initial_pos.x <= 0 ) :
                            ret[vert] = p
                            ret[mirror] = m
                    else :
                        ret[vert] = p
                        ret[mirror] = m
                else :
                    ret[vert] = p

        return ret


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

        if QSnap.is_active() :
            targetPos = self.start_pos + move
            targetPos = QSnap.view_adjust( targetPos )
            move = targetPos - self.start_pos

        if change_conponent :
            self.currentTarget.hitPosition = self.start_pos + move

        return move


    def find_slide_side( self ,  mouse_pos: mathutils.Vector ) :
        vs = self.currentTarget.element.verts
        rl = ( self.verts[vs[0]] - self.start_pos ).length / ( self.verts[vs[0]] - self.verts[vs[1]] ).length 
        rr = 1 - rl
        ray = pqutil.Ray.from_screen( bpy.context , mouse_pos )
        radius = display.dot( self.bmo.preferences.distance_to_highlight )

        r = 1000000
        side = None
        hit = None
        for slide in self.slide_guid :
            ts = [ slide[v] for v in vs ]        
            pt = [ self.verts[vs[0]] * rr + self.verts[vs[1]] * rl , ts[0].co * rr + ts[1].co * rl ]
            hp = ray.hit_to_line( pt[0] , pt[1] )
            if hp > 0.00000001 and hp < 1.00000001 :
                line = pqutil.Ray.from_line( pt[0] , pt[1] )
                q1 , q2 , d = line.distance(ray)
                if r > d :
                    p =  pt[0] + ( pt[1] -  pt[0]) * hp
                    s = pqutil.location_3d_to_region_2d( p )
                    if (mouse_pos- s).length < radius :
                        side = slide
                        r = d
                        hit = hp

        return side , hit


    def calc_slide( self ,  mouse_pos: mathutils.Vector ) :
        if not self.slide_guid :
            return None

        ray = pqutil.Ray.from_screen( bpy.context , mouse_pos )
        radius = display.dot( self.bmo.preferences.distance_to_highlight )

        hitSide , hp = self.find_slide_side( mouse_pos )

        if hitSide == None :
            return None

        side = {} 
        for v,s in hitSide.items() :
            p = self.verts[v].lerp( s.co , hp )
            if QSnap.is_active() :
                p , _ = QSnap.adjust_point(p)
            side[v] = p 

        if side :
            for vert , mirror in self.mirror_set.items() :
                
                if vert in side :
                    p = side[vert]
                    m = mathutils.Vector( (-p.x,p.y,p.z) )
                    side[mirror] = m

        return side

    @property
    def move_distance( self ) :
        return ( self.currentTarget.hitPosition - self.start_pos ).length

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


    def draw_3D( self , context , mouse_pos = None ) :
        if self.move_ray != None :
            v0 = self.move_ray.origin
            v1 = v0 + self.move_ray.vector * 10000.0 
            v2 = v0 - self.move_ray.vector * 10000.0 
            draw_util.draw_lines3D( context , (v1,v2) , self.move_color , 1.0 , 0.2 )

        if self.slide_guid :
            hitSide , hp = self.find_slide_side( mouse_pos )
            for slide in self.slide_guid :
                if hitSide == slide :
                    color = (1,1,1,1)
                    width = 2
                else :
                    color = (1,1,1,0.25)
                    width = 1
                vs = self.currentTarget.element.verts
                rl = ( self.verts[vs[0]] - self.start_pos ).length / ( self.verts[vs[0]] - self.verts[vs[1]] ).length 
                rr = 1 - rl
                ts = [ slide[v] for v in vs ]
                pt = [ self.verts[vs[0]] * rr + self.verts[vs[1]] * rl , ts[0].co * rr + ts[1].co * rl  ]

                draw_util.draw_lines3D( context , verts = pt , color = color , width = width )


    @staticmethod
    def check_move_type( target : ElementItem , move_type0  : str, move_type1 : str) -> str :
        move_type = move_type0
        if move_type1 == None :
            pass
#            if target.is_hit_center() :
#                move_type = 'NORMAL'
        else :
            move_type = move_type1

        return move_type

    def snap_loop( self , sorce_edge : bmesh.types.BMEdge , sorce_loop  , snap_edge : bmesh.types.BMEdge ) :
        snap_loop , __ = self.bmo.calc_edge_loop( snap_edge )        

        p0 = self.bmo.local_to_world_pos( sorce_edge.verts[0].co)
        p1 = self.bmo.local_to_world_pos( sorce_edge.verts[1].co) 
        s0 = self.bmo.local_to_world_pos( snap_edge.verts[0].co) 
        s1 = self.bmo.local_to_world_pos( snap_edge.verts[1].co)
        if (p0-s0).length + (p1-s1).length > (p0-s1).length + (p1-s0).length :
            t0 = snap_edge.verts[0]
            t1 = snap_edge.verts[1]
        else :
            t0 = snap_edge.verts[1]
            t1 = snap_edge.verts[0]

        def other( edge , vert , edges ) :
            hits = [ e for e in edges if e != edge and vert in e.verts ]
            if len(hits) == 1 :
                return hits[0] , hits[0].other_vert(vert) 
            return None , None

        pair_verts = {}
        for (src , dst) in zip(sorce_edge.verts , [t1,t0] ) :
            sv = src
            se = sorce_edge
            dv = dst
            de = snap_edge
            while( sv != None and dv != None ) :
                if sv in pair_verts.keys() or dv in pair_verts.items()  :
                    break
                pair_verts[sv] = dv
                se , sv = other( se , sv , sorce_loop  )
                de , dv = other( de , dv , snap_loop  )

        return pair_verts


    def find_snap_vert( self , vert_dic , ignoreVerts ) :
        snaps = {}
        dist = self.bmo.preferences.distance_to_highlight
        for vert in self.verts :
            if vert in vert_dic :
                tar = vert_dic[vert]
                if not isinstance( tar , bmesh.types.BMVert ) :
                    pos =self.bmo.local_to_2d( vert_dic[vert] )
                    if pos :
                        snapTarget = self.bmo.PickElement( pos , dist , edgering=True , backface_culling = True , elements=['VERT'] , ignore= ignoreVerts )
                        if snapTarget.isVert :
                            if self.bmo.is_mirror_mode :
                                mirror = self.bmo.find_mirror( snapTarget.element , None )
                                if mirror and self.mirror_set[vert] :
                                    m =  self.mirror_set[vert]
                                    snaps[m] = mirror

                            snaps[vert] = snapTarget.element

        return snaps


class vert_array_util :
    def __init__(self , qmesh ) :
        self.qmesh = qmesh
        self.verts_list = []
        self.face_count = 0
        self.edge_count = 0

    def get( self , index : int ) :
        return self.verts[index]

    def add( self , vert ) :
        world = self.qmesh.local_to_world_pos( vert.co )
        screen = pqutil.location_3d_to_region_2d( world )
        self.verts_list.append( [vert,vert.index,vert.co.copy(),world,screen] )
        self.qmesh.bm.select_history.discard(vert)
        self.qmesh.bm.select_history.add(vert)
        vert.select_set(True)

    def add_face( self , face ) :
        self.qmesh.bm.select_history.discard(face)
        self.qmesh.bm.select_history.add(face)
        self.face_count = self.face_count + 1

    def add_edge( self , edge ) :
        self.qmesh.bm.select_history.discard(edge)
        self.qmesh.bm.select_history.add(edge)
        self.edge_count = self.edge_count + 1

    def add_line( self , vert ) :
        self.add( vert )
        edge = self.qmesh.add_edge( self.get(-2) , self.get(-1) )          
        self.add_edge( edge )
        self.qmesh.UpdateMesh()                      
        return edge

    def clear_verts( self ) :
        self.verts_list = []

    def reset_verts( self ) :
        self.verts_list = [ self.verts_list[-1] ]

    @property
    def vert_count( self ) :
        return len(self.verts_list)

    @property
    def verts( self ) :
        if len(self.verts_list) == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMVert) ][-len(self.verts_list):]

    @property
    def faces( self ) :
        if self.face_count == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMFace) ][-self.face_count:]

    @property
    def last_vert( self ) :
        return self.verts[-1]

    @property
    def last_edge( self ) :
        return self.edges[-1]

    @property
    def last_face( self ) :
        return self.faces[-1]

    @property
    def edges( self ) :
        if self.edge_count == 0 :
            return []
        return [ h for h in self.qmesh.bm.select_history if isinstance(h,bmesh.types.BMEdge) ][-self.edge_count:]

    def clear_faces( self ) :
        self.face_count = 0

    def clear_edges( self ) :
        self.edge_count = 0

    @property
    def cos( self ) :
        return [ i[1] for i in self.verts_list ]

    @property
    def world_positions( self ) :
        return [ i[3] for i in self.verts_list ]

    @property
    def screen_positions( self ) :
        return [ i[4] for i in self.verts_list ]
