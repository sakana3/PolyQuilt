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

class SubToolBrushRelax(SubToolEx) :
    name = "RelaxBrushTool"

    def __init__(self, event ,  root) :
        super().__init__(root)
        self.radius = self.preferences.brush_size * dpm()
        self.occlusion_tbl = {}
        self.mirror_tbl = {}
        self.dirty = False
        if self.currentTarget.isEmpty or ( self.currentTarget.isEdge and self.currentTarget.element.is_boundary ) :
            self.effective_boundary = True
        else :
            self.effective_boundary = False

    @staticmethod
    def Check( root , target ) :
        return True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        def Draw() :
            radius = gizmo.preferences.brush_size * dpm()
            strength = gizmo.preferences.brush_strength  
            with draw_util.push_pop_projection2D() :
                draw_util.draw_circle2D( gizmo.mouse_pos , radius * strength , color = (1,0.25,0.25,0.25), fill = False , subdivide = 64 , dpi= False )
                draw_util.draw_circle2D( gizmo.mouse_pos , radius , color = (1,1,1,0.5), fill = False , subdivide = 64 , dpi= False )
        return Draw

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.DoRelax( context ,self.mouse_pos )
        elif event.type == self.rootTool.buttonType : 
            if event.value == 'RELEASE' :
                if self.dirty  :
                    self.bmo.UpdateMesh()
                    return 'FINISHED'
                return 'CANCELLED'
        elif event.value == 'RELEASE' :
            self.repeat = False

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        width = 2.0 if self.effective_boundary else 1.0
        draw_util.draw_circle2D( self.mouse_pos , self.radius , color = (1,1,1,1), fill = False , subdivide = 64 , dpi= False , width = width )
        pass

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
            return ( vt , x ** 2 , co.copy())

        coords = [ ProjVert(vert) for vert in verts if vert.select ]

        select_stack.pop()

        return { c[0]: [c[1],c[2]] for c in coords if c != None } 

    def MirrorVert( self , context , coords ) :
        # ミラー頂点を検出
        find_mirror = self.bmo.find_mirror
        mirrors = { vert : find_mirror( vert ) for vert , coord in coords.items() }

        # 重複する場合は
        for (vert , coord) , mirror in zip( coords.items() , mirrors.values() ) :
            if mirror != None :
                cur = coord[0]
                dst = coords[mirror][0]
                coord[0] = cur if dst <= cur else dst

        # 重複しないものを列挙
        mirrors = { vert : [coords[vert][0] , mirror.co.copy() ] for vert , mirror in mirrors.items() if mirror != None and mirror not in coords }

        coords.update(mirrors)
        return coords

    def DoRelax( self , context , coord ) :
        is_fix_zero = self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode
        coords = self.CollectVerts( context, coord  )
        if coords :
            self.dirty = True
        if self.bmo.is_mirror_mode :
            mirrors = { vert : self.bmo.find_mirror( vert ) for vert , coord in coords.items() }

        if not self.effective_boundary :
            bmesh.ops.smooth_vert( self.bmo.bm , verts = [ c for c in coords.keys() if not c.is_boundary ] , factor = self.preferences.brush_strength  ,
            mirror_clip_x = is_fix_zero, mirror_clip_y = False, mirror_clip_z = False, clip_dist = 0.0001 ,
            use_axis_x = True, use_axis_y = True, use_axis_z = True)
        else :
            boundary = { c for c in coords.keys() if c.is_boundary }

            result = {}
            for v in boundary :
                if len(v.link_faces) != 1 :
                    tv = mathutils.Vector( (0,0,0) )
                    le = [ e.other_vert( v ).co for e in v.link_edges if e.is_boundary ]
                    for te in le :
                        tv = tv + te
                    result[v] = tv * (1/ len(le) )
            for v , co in result.items() :
                v.co = co

            bmesh.ops.smooth_vert( self.bmo.bm , verts = list( coords.keys() - boundary ) , factor = self.preferences.brush_strength  ,
            mirror_clip_x = is_fix_zero, mirror_clip_y = False, mirror_clip_z = False, clip_dist = 0.0001 ,
            use_axis_x = True, use_axis_y = True, use_axis_z = True)

#        bmesh.ops.smooth_laplacian_vert(self.bmo.bm , verts = hits , lambda_factor = 1.0 , lambda_border = 0.0 ,
#            use_x = True, use_y = True, use_z = True, preserve_volume = False )

        matrix_world = self.bmo.obj.matrix_world
        is_x_zero_pos = self.bmo.is_x_zero_pos
        zero_pos = self.bmo.zero_pos
        mirror_pos = self.bmo.mirror_pos
#       matrix_world_inv = matrix_world.inverted()
        for v , (f,orig) in coords.items() :
            p = QSnap.adjust_local( matrix_world , v.co , is_fix_zero )
            s = orig.lerp( p , f )
            if is_fix_zero and is_x_zero_pos(s) :
                s = zero_pos(s)
            v.co = s

        if self.bmo.is_mirror_mode :
            for vert , mirror in mirrors.items() :
                if mirror != None :
                    if mirror in coords :
                        ms = coords[mirror][0]
                        vs = coords[vert][0]
                        if vs >= ms :
                            mirror.co = mirror_pos(vert.co)
                        else :
                            vert.co = mirror_pos(mirror.co)
                    else :
                        mirror.co = mirror_pos(vert.co)

#        self.bmo.bm.normal_update()
#        self.bmo.obj.data.update_gpu_tag()
#        self.bmo.obj.data.update_tag()
#        self.bmo.obj.update_from_editmode()
#        self.bmo.obj.update_tag()
        bmesh.update_edit_mesh(self.bmo.obj.data , loop_triangles = False,destructive = False )

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'