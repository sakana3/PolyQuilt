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
import numpy as np
from .. import handleutility
from .. import draw_util
from ..dpi import *
from .ElementItem import ElementItem
from .QMeshOperators import QMeshOperators
from .QMeshHighlight import QMeshHighlight

__all__ = ['QMesh']
        
class QMesh(QMeshOperators) :

    def __init__(self , obj , preferences) :
        super().__init__(obj, preferences)
        self.highlight = QMeshHighlight(self)

    def UpdateMesh( self ) :
        super().UpdateMesh()
        self.UpdateView( bpy.context , True )

    def UpdateView( self ,context , forced = False ):
        self.highlight.setDirty()

    def PickElement( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = False ) -> ElementItem :
        backface_culling = self.get_shading(bpy.context).show_backface_culling
        rv3d = bpy.context.space_data.region_3d
        matrix = self.obj.matrix_world @ rv3d.perspective_matrix
        radius = radius * dpm()

        hitElement = ElementItem.Empty()

        ignoreFaces =  [ i for i in ignore if isinstance( i , bmesh.types.BMFace ) ]        

        # Hitする頂点を探す
        hitVert = ElementItem.Empty()
        ignoreVerts =  [ i for i in ignore if isinstance( i , bmesh.types.BMVert ) ]
        candidateVerts = self.highlight.CollectVerts( coord , radius , ignoreVerts , edgering , backface_culling = backface_culling  )

        # Todo:ヒットするエッジを探す
        hitEdge = ElementItem.Empty()
        ignoreEdges =  [ i for i in ignore if isinstance( i , bmesh.types.BMEdge ) ]
        candidateEdges = self.highlight.CollectEdge( coord , radius , ignoreEdges , backface_culling = backface_culling )

        for vert in candidateVerts :
            # 各点からRayを飛ばす
            hitTemp = self.highlight.PickFace( vert.coord , ignoreFaces , backface_culling = False  )
            if hitTemp.isEmpty :
                # 何の面にもヒットしないなら採択
                hitVert = vert
                break
            else :
                if vert.element in hitTemp.element.verts :
                    # ヒットした面に含まれているなら採択
                    hitVert = vert
                    break
                else :
                    # ヒットしたポイントより後ろなら採択
                    v1 = matrix @ vert.hitPosition
                    v2 = matrix @ hitTemp.hitPosition
                    if v1.z <= v2.z :
                        hitVert = vert
                        break

        for edge in candidateEdges :
            hitTemp = self.highlight.PickFace( edge.coord , ignoreFaces , backface_culling = False )
        
            if hitTemp.isEmpty :
                hitEdge = edge
                break
            else:
                if edge.element in hitTemp.element.edges :
                    # ヒットした面に含まれているなら採択
                    hitEdge = edge
                    break
                else :
                    # ヒットしたポイントより後ろなら採択
                    v1 = matrix @ edge.hitPosition
                    v2 = matrix @ hitTemp.hitPosition
                    if v1.z <= v2.z :
                        hitEdge = edge
                        break


        if hitVert.isEmpty and hitEdge.isEmpty :
            # hitする面を探す
            hitFace = self.highlight.PickFace( coord , ignoreFaces , backface_culling = backface_culling  )

            # 候補頂点/エッジがないなら面を返す
            if hitFace.isNotEmpty :
                hitElement = hitFace
        elif hitVert.isNotEmpty and hitEdge.isNotEmpty :
            v1 = matrix @ hitVert.hitPosition
            v2 = matrix @ hitEdge.hitPosition
            if v1.z <= v2.z :
                hitElement = hitVert
            else :
                hitElement = hitEdge
        elif hitVert.isNotEmpty :
            hitElement = hitVert
        elif hitEdge.isNotEmpty :
            hitElement = hitEdge
        
        return hitElement

