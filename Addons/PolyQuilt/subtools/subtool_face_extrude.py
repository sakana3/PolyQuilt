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
from .subtool_move import SubToolMove

class SubToolFaceExtrude(SubToolMove) :
    name = "Extrud&MoveTool"

    def __init__(self,op,startTarget,startMousePos) :
        newMirror = None
        faces = [startTarget.element]
        region = False
        if op.bmo.is_mirror_mode :
            mirror = op.bmo.find_mirror( startTarget.element  )
            if mirror != None and mirror != startTarget.element:
                faces = [startTarget.element , mirror ]
                if op.preferences.fix_to_x_zero or startTarget.normal.dot(mirror.normal) > 0.999999999 :
                    region = True

        verts = [ [v for v in f.verts] for f in faces ]
        is_convex = all( [ len( e.link_faces ) > 1 for e in startTarget.element.edges ] )

        if region :
            ret = bmesh.ops.extrude_face_region( op.bmo.bm , geom  = faces, use_normal_flip = False , use_select_history = False )        
            ret = [ g for g in ret['geom'] if isinstance( g , bmesh.types.BMFace ) ] 
        else :
            ret = bmesh.ops.extrude_discrete_faces( op.bmo.bm , faces = faces, use_normal_flip = True , use_select_history = False )        
            ret = ret['faces']

        if not is_convex:
            for vs in verts :
                op.bmo.AddFace( reversed(vs) , normal = None , is_mirror = False )

        op.bmo.UpdateMesh()

        newFace = ElementItem( op.bmo , element = ret[0] , coord = startTarget.coord , hitPosition = startTarget.hitPosition )
        if op.bmo.is_mirror_mode :
            if len(faces) > 1 :
                newMirror = ret[1]
            else :
                newMirror = ret[0]
            newFace.setup_mirror(newMirror)
    
        super().__init__(op,newFace,startMousePos,'NORMAL',newMirror)
