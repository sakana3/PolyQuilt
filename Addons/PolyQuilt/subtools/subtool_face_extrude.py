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

        ret = bmesh.ops.extrude_discrete_faces( op.bmo.bm , faces = [startTarget.element], use_normal_flip = True , use_select_history = False )        
        op.bmo.UpdateMesh()

        newFace = ElementItem( op.bmo , element = ret['faces'][0] , coord = startTarget.coord , hitPosition = startTarget.hitPosition )

        super().__init__(op,newFace,startMousePos,'NORMAL')
