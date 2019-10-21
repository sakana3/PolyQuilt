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
from .subtool import SubTool
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

class SubToolRelax(SubTool) :
    name = "RelaxTool"

    def __init__(self,op,startTarget,startMousePos) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.startMousePos = copy.copy(startTarget.coord)
        self.radius = self.preferences.brush_size * dpm()
        self.occlusion_tbl = {}
        self.mirror_tbl = {}

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.DoRelax( context ,self.mouse_pos )
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                self.bmo.UpdateMesh()
                return 'FINISHED'
        elif event.value == 'RELEASE' :
            self.repeat = False

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_circle2D( self.mouse_pos , self.radius , color = (1,1,1,1), fill = False , subdivide = 64 , dpi= False )
        pass

    def OnDraw3D( self , context  ) :
        pass

    def CollectVerts( self , context , coord ) :
        rv3d = context.space_data.region_3d
        region = context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        matrix_world = self.bmo.obj.matrix_world
        matrix = rv3d.perspective_matrix @ matrix_world
        half = mathutils.Vector( (halfW,halfH) )
        radius = self.radius
        bm = self.bmo.bm
        verts = bm.verts
        is_target = QSnap.is_target
        new_vec = mathutils.Vector

        select_stack = SelectStack( context , bm )

        select_stack.push()
        select_stack.select_mode(True,False,False)
        bpy.ops.view3d.select_circle( x = coord.x , y = coord.y , radius = radius , wait_for_input=False, mode='SET')
#        bm.select_flush(False)

        def ProjVert( vt ) :
            pv = matrix @ vt.co.to_4d()
            w = pv.w
            if w < 0.0 :
                return None
            p = new_vec( (pv.x * halfW , pv.y * halfH ) ) / w + half
            r = (coord - p).length
            if r > radius :
                return None

            is_occlusion = self.occlusion_tbl.get(vt)
            if is_occlusion == None :
                is_occlusion = is_target(matrix_world @ vt.co)
                self.occlusion_tbl[vt] = is_occlusion

            if not is_occlusion :
                return None

            x = (radius - r) / radius
            return [ x * x , vt.co.copy()]

        coords = { vert : ProjVert(vert) for vert in verts if vert.select and not vert.is_boundary }

        select_stack.pop()

        return { v:c for v , c in coords.items() if c != None } 

    def DoRelax( self , context , coord ) :
        coords = self.CollectVerts( context, coord  )

        bmesh.ops.smooth_vert( self.bmo.bm , verts = list( coords.keys() ) , factor = 1 ,
            mirror_clip_x = False, mirror_clip_y = False, mirror_clip_z = False, clip_dist = 0.0001 ,
            use_axis_x = True, use_axis_y = True, use_axis_z = True)
#        bmesh.ops.smooth_laplacian_vert(self.bmo.bm , verts = hits , lambda_factor = 1.0 , lambda_border = 0.0 ,
#            use_x = True, use_y = True, use_z = True, preserve_volume = False )

        matrix_world = self.bmo.obj.matrix_world
        matrix_world_inv = matrix_world.inverted()
        for v , (f,o) in coords.items() :
            p = matrix_world_inv @ QSnap.adjust_point( matrix_world @ v.co )
            v.co = o.lerp( p , f )

#        self.bmo.bm.normal_update()
#        self.bmo.obj.data.update_gpu_tag()
#        self.bmo.obj.data.update_tag()
#        self.bmo.obj.update_from_editmode()
#        self.bmo.obj.update_tag()
        bmesh.update_edit_mesh(self.bmo.obj.data , loop_triangles = False,destructive = False )
