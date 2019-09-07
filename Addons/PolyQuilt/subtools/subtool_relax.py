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

class SubToolRelax(SubTool) :
    name = "RelaxTool"

    def __init__(self,op,startTarget,startMousePos) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.startMousePos = copy.copy(startTarget.coord)

    def OnUpdate( self , context , event ) :
        self.radius = context.tool_settings.proportional_size * 25.4
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
        draw_util.draw_circle2D( self.mouse_pos , self.radius , color = (1,1,1,1), fill = False , subdivide = 64 )
        pass

    def OnDraw3D( self , context  ) :
        pass

    def DoRelax( self , context , coord ) :
        rv3d = context.space_data.region_3d
        region = context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        matrix_world = self.bmo.obj.matrix_world
        perspective_matrix = rv3d.perspective_matrix
        half = mathutils.Vector( (halfW,halfH) )
        radius = self.radius

        def ProjVert( vt ) :
            if vt.is_boundary :
                return None

            wp = matrix_world @ vt.co
            pv = perspective_matrix @ wp.to_4d()
            w = pv.w
            if w < 0.0 :
                return None
            p = mathutils.Vector( (pv.x * halfW , pv.y * halfH ) ) / w + half
            r = (coord - p).length
            if r > radius :
                return None
            r = (radius - r) / radius
            return (p , r , vt.co.copy())

        verts = self.bmo.bm.verts
        coords = { vert : ProjVert(vert) for vert in verts }
        hits = [ v for v , c in coords.items() if c != None ]

        if True :
            bmesh.ops.smooth_vert( self.bmo.bm , verts = hits , factor = 0.25,
                mirror_clip_x = False, mirror_clip_y = False, mirror_clip_z = False, clip_dist = 0.0001 ,
                use_axis_x = True, use_axis_y = True, use_axis_z = True)
        else :
            bmesh.ops.smooth_laplacian_vert(self.bmo.bm , verts = verts, lambda_factor = 1.0 , lambda_border = 0.0 , use_x = True, use_y = True, use_z = True, preserve_volume = False )

        for v in hits :
            c = coords[v]
            v.co = c[2].lerp( v.co , c[1] )

        QSnap.adjust_verts( self.bmo.obj , hits , False )

        self.bmo.bm.normal_update()
#        self.bmo.obj.data.update_gpu_tag()
#        self.bmo.obj.data.update_tag()
#        self.bmo.obj.update_from_editmode()
#        self.bmo.obj.update_tag()
        bmesh.update_edit_mesh(self.bmo.obj.data , loop_triangles = False,destructive = False )
