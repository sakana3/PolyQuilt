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
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubToolEx
from ..utils.dpi import *

class SelectStack :
    def __init__(self, context , bm) :
        self.context = context
        self.bm = bm

    def push( self ) :
        self.mesh_select_mode = self.context.tool_settings.mesh_select_mode[0:3]
        self.vert_selection = [ v.select for v in self.bm.verts ]
        self.face_selection = [ f.select for f in self.bm.faces ]
        self.edge_selection = [ e.select for e in self.bm.edges ]
        self.select_history = self.bm.select_history[:]

    def select_mode( self , vert , face , edge ) :
        self.context.tool_settings.mesh_select_mode = (vert , face , edge)


    def pop( self ) :
        self.context.tool_settings.mesh_select_mode = self.mesh_select_mode

        for select , v in zip( self.vert_selection , self.bm.verts ) :
            v.select = select
        for select , f in zip( self.face_selection , self.bm.faces ) :
            f.select = select
        for select , e in zip( self.edge_selection , self.bm.edges ) :
            e.select = select

        self.bm.select_history = self.select_history

        del self.vert_selection
        del self.face_selection
        del self.edge_selection

class SubToolBrushMove(SubToolEx) :
    name = "MoveBrushTool"

    def __init__(self, root ) :
        super().__init__( root )
        self.radius = self.preferences.brush_size * dpm()
        self.mirror_tbl = {}
        matrix = self.bmo.obj.matrix_world        
        self.occlusion_tbl = {}
        self.verts = self.CollectVerts( bpy.context , self.startMousePos )

        if self.bmo.is_mirror_mode :
            self.mirrors = { vert : self.bmo.find_mirror( vert ) for vert in self.verts }
        else :
            self.mirrors = {}

    @staticmethod
    def Check( root , target ) :
        if root.preferences.brush_type == 'MOVE' :
            return True
        return False

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.UpdateVerts(context)
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                self.bmo.UpdateMesh()
                return 'FINISHED'
        elif event.value == 'RELEASE' :
            self.repeat = False

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_circle2D( self.startMousePos , self.radius , color = (0.75,0.75,1,1), fill = False , subdivide = 64 , dpi= False , width = 1.0 )

    def OnDraw3D( self , context  ) :
        pass


    def CollectVerts( self , context , coord ) :
        rv3d = context.space_data.region_3d
        region = context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        matrix_world = self.bmo.obj.matrix_world
        matrix = rv3d.perspective_matrix @ matrix_world
        radius = self.radius
        bm = self.bmo.bm
        verts = bm.verts

        select_stack = SelectStack( context , bm )

        select_stack.push()
        select_stack.select_mode(True,False,False)
        bpy.ops.view3d.select_circle( x = coord.x , y = coord.y , radius = radius , wait_for_input=False, mode='SET' )
#        bm.select_flush(False)

        occlusion_tbl_get = self.occlusion_tbl.get
        is_target = QSnap.is_target
        new_vec = mathutils.Vector
        def ProjVert( vt ) :
            co = vt.co
            is_occlusion = occlusion_tbl_get(vt)
            if is_occlusion == None :
                is_occlusion = is_target(matrix_world @ co)
                self.occlusion_tbl[vt] = is_occlusion

            if not is_occlusion :
                return None

            pv = matrix @ co.to_4d()
            w = pv.w
            if w < 0.0 :
                return None
            p = new_vec( (pv.x * halfW / w + halfW , pv.y * halfH / w + halfH ) )
            r = (coord - p).length
            if r > radius :
                return None

            x = (radius - r) / radius
            return ( p , (1-x) ** 2 , matrix_world @ co )

        coords = { vert : ProjVert(vert) for vert in verts if vert.select }

        select_stack.pop()

        return { v : x for v,x in coords.items() if x }

    def UpdateVerts( self , context ) :
        is_fix_zero = self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode        
        region = context.region
        rv3d = context.space_data.region_3d
        move = self.mouse_pos - self.startMousePos
        matrix = self.bmo.obj.matrix_world         
        matrix_inv = self.bmo.obj.matrix_world.inverted()         
        region_2d_to_location_3d = bpy_extras.view3d_utils.region_2d_to_location_3d
        is_x_zero_pos = self.bmo.is_x_zero_pos
        zero_pos = self.bmo.zero_pos
        mirror_pos = self.bmo.mirror_pos

        for v,(p,r,co) in self.verts.items() :
            coord = p + move
            x = region_2d_to_location_3d( region = region , rv3d = rv3d , coord = coord , depth_location = co)
            x = co.lerp( x , 1 - r )
            x = QSnap.adjust_point( x )
            x = matrix_inv @ x
            if is_fix_zero and is_x_zero_pos(co) :
                x = zero_pos(x)
            v.co = x

        if self.bmo.is_mirror_mode :
            for vert , mirror in self.mirrors.items() :
                if mirror != None :
                    if mirror in self.verts.keys() :
                        ms = self.verts[mirror][1]
                        vs = self.verts[vert][1]
                        if vs <= ms :
                            mirror.co = mirror_pos(vert.co)
                        else :
                            vert.co = mirror_pos(mirror.co)
                    else :
                        mirror.co = mirror_pos(vert.co)

        self.bmo.UpdateMesh()        

