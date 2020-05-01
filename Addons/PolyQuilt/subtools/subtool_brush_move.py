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

class SubToolBrushMove(SubToolEx) :
    name = "MoveBrushTool"

    def __init__(self, event ,  root ) :
        super().__init__( root )
        self.radius = self.preferences.brush_size * dpm()
        self.strength = self.preferences.brush_strength
        self.mirror_tbl = {}
        matrix = self.bmo.obj.matrix_world        
        self.verts = self.CollectVerts( bpy.context , self.startMousePos )

        if self.bmo.is_mirror_mode :
            self.mirrors = { vert : self.bmo.find_mirror( vert ) for vert in self.verts }
        else :
            self.mirrors = {}

    @staticmethod
    def Check( root , target ) :
        return True

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.UpdateVerts(context)
        elif event.type == self.rootTool.buttonType : 
            if event.value == 'RELEASE' :
                if self.verts :
                    self.bmo.UpdateMesh()
                    return 'FINISHED'
                return 'CANCELLED'
        elif event.value == 'RELEASE' :
            self.repeat = False

        return 'RUNNING_MODAL'

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        def Draw() :
            radius = gizmo.preferences.brush_size * dpm()
            strength = gizmo.preferences.brush_strength  
            with draw_util.push_pop_projection2D() :
                draw_util.draw_circle2D( gizmo.mouse_pos , radius * strength , color = (1,0.25,0.25,0.25), fill = False , subdivide = 64 , dpi= False )
                draw_util.draw_circle2D( gizmo.mouse_pos , radius , color = (1,1,1,0.5), fill = False , subdivide = 64 , dpi= False )
        return Draw

    def OnDraw( self , context  ) :
        radius = self.preferences.brush_size * dpm()
        strength = self.preferences.brush_strength  

        draw_util.draw_circle2D( self.mouse_pos , radius * strength , color = (1,0.25,0.25,0.25), fill = False , subdivide = 64 , dpi= False )
        draw_util.draw_circle2D( self.startMousePos , self.radius , color = (0.75,0.75,1,1), fill = False , subdivide = 64 , dpi= False , width = 1.0 )

    def OnDraw3D( self , context  ) :
        pass

    def CollectVerts( self , context , coord ) :
        rv3d = context.region_data
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

        is_target = QSnap.is_target
        new_vec = mathutils.Vector
        pw = (self.strength * self.strength ) * 8

        def ProjVert( vt ) :
            co = vt.co
            if not is_target(matrix_world @ co) :
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
            r = (1-x) ** pw
            return ( p , r , matrix_world @ co , co )

        coords = { vert : ProjVert(vert) for vert in verts if vert.select }

        select_stack.pop()

        return { v : x for v,x in coords.items() if x }

    def UpdateVerts( self , context ) :
        is_fix_zero = self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode        
        region = context.region
        rv3d = context.region_data
        move = self.mouse_pos - self.startMousePos
        matrix = self.bmo.obj.matrix_world         
        matrix_inv = self.bmo.obj.matrix_world.inverted()         
        region_2d_to_location_3d = pqutil.region_2d_to_location_3d
        is_x_zero_pos = self.bmo.is_x_zero_pos
        zero_pos = self.bmo.zero_pos
        mirror_pos = self.bmo.mirror_pos

        for v,(p,r,co,orig) in self.verts.items() :
            coord = p + move
            x = region_2d_to_location_3d( region = region , rv3d = rv3d , coord = coord , depth_location = co)
            x = co.lerp( x , 1 - r )
            x = QSnap.adjust_point( x )
            x = matrix_inv @ x
            if is_fix_zero and is_x_zero_pos(orig) :
                x.x = 0 
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

    @classmethod
    def GetCursor(cls) :
        return 'SCROLL_XY'