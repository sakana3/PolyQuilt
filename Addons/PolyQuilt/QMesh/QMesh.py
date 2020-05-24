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
from .QSnap import QSnap
import numpy as np
from ..utils import pqutil
from ..utils import draw_util
from ..utils.dpi import *
from .ElementItem import ElementItem
from .QMeshOperators import QMeshOperators
from .QMeshHighlight import QMeshHighlight

__all__ = ['QMesh','SelectStack']
        
class QMesh(QMeshOperators) :

    def __init__(self , obj , preferences) :
        super().__init__(obj, preferences)
        self.highlight = QMeshHighlight(self)
        self.invalid = False

    def UpdateMesh( self , updateHighLight = True ) :
        super().UpdateMesh()
        if updateHighLight :
            self.highlight.setDirty()

    def CheckValid( self , context ) :
        val = super()._CheckValid(context)
        if val == False or self.invalid :
            self.highlight.setDirty()
            self.reload_obj(context)
            self.invalid = False
        return val

    def UpdateView( self ,context , forced = False ):
        self.highlight.UpdateView(context)

    def PickElement( self , coord , radius : float , ignore = [] , edgering = False , backface_culling = None , elements = ['FACE','EDGE','VERT'] ) -> ElementItem :
        if backface_culling == None :
            backface_culling = self.get_shading(bpy.context).show_backface_culling
        rv3d = bpy.context.region_data
        matrix = rv3d.perspective_matrix
        radius = radius * dpm()

        hitElement = ElementItem.Empty()

        ignoreFaces =  [ i for i in ignore if isinstance( i , bmesh.types.BMFace ) ]        

        # Hitする頂点を探す
        hitVert = ElementItem.Empty()
        if 'VERT' in elements :
            ignoreVerts =  [ i for i in ignore if isinstance( i , bmesh.types.BMVert ) ]
            candidateVerts = self.highlight.CollectVerts( coord , radius , ignoreVerts , edgering , backface_culling = backface_culling  )
            for vert in candidateVerts :
                # 各点からRayを飛ばす
                if QSnap.is_target( vert.hitPosition ) :
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

        # Todo:ヒットするエッジを探す
        hitEdge = ElementItem.Empty()
        if 'EDGE' in elements :
            ignoreEdges =  [ i for i in ignore if isinstance( i , bmesh.types.BMEdge ) ]
            candidateEdges = self.highlight.CollectEdge( coord , radius , ignoreEdges , backface_culling = backface_culling , edgering= edgering )

            for edge in candidateEdges :
                if QSnap.is_target( edge.hitPosition ) :                
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
            if 'FACE' in elements :            
                # hitする面を探す
                hitFace = self.highlight.PickFace( coord , ignoreFaces , backface_culling = backface_culling  )
                # 候補頂点/エッジがないなら面を返す
                if hitFace.isNotEmpty :
                    if QSnap.is_target( hitFace.hitPosition ) :                
                        hitElement = hitFace
        elif hitVert.isNotEmpty and hitEdge.isNotEmpty :
            if hitVert.element in hitEdge.element.verts :
                return hitVert
            v1 = matrix @ hitVert.hitPosition.to_4d()
            v2 = matrix @ hitEdge.hitPosition.to_4d()
            if v1.z <= v2.z :
                hitElement = hitVert
            else :
                hitElement = hitEdge
        elif hitVert.isNotEmpty :
            hitElement = hitVert
        elif hitEdge.isNotEmpty :
            hitElement = hitEdge
        
        return hitElement


class SelectStack :
    def __init__(self, context , bm) :
        self.context = context
        self.bm = bm
        self.mesh_select_mode = context.tool_settings.mesh_select_mode[0:3]

    def push( self ) :
        self.mesh_select_mode = self.context.tool_settings.mesh_select_mode[0:3]
        self.vert_selection = [ v.select for v in self.bm.verts ]
        self.face_selection = [ f.select for f in self.bm.faces ]
        self.edge_selection = [ e.select for e in self.bm.edges ]
        self.select_history = self.bm.select_history[:]
        self.mesh_select_mode = self.context.tool_settings.mesh_select_mode[0:3]

    def select_mode( self , vert , edge , face ) :
        self.context.tool_settings.mesh_select_mode = (vert , edge , face)


    def pop( self ) :
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

        self.context.tool_settings.mesh_select_mode = self.mesh_select_mode
