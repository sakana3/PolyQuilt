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

    def __init__(self , obj ) :
        super().__init__(obj)
        self.highlight = QMeshHighlight(self)

    def UpdateMesh( self ) :
        super().UpdateMesh()
        self.UpdateView( bpy.context , True )

    def UpdateView( self ,context , forced = False ):
        self.highlight.UpdateView( context , forced )

    def PickElement( self , coord , radius : float , ignore = [] , edgering = False ) -> ElementItem :

        rv3d = bpy.context.space_data.region_3d
        matrix = self.obj.matrix_world @ rv3d.perspective_matrix
        radius = radius * dpm()

        hitElement = ElementItem.Empty()

        ignoreFaces =  [ i for i in ignore if isinstance( i , bmesh.types.BMFace ) ]        

        # Hitする頂点を探す
        hitVert = ElementItem.Empty()
        ignoreVerts =  [ i for i in ignore if isinstance( i , bmesh.types.BMVert ) ]
        candidateVerts = self.highlight.CollectVerts( coord , radius , ignoreVerts , edgering )

        # Todo:ヒットするエッジを探す
        hitEdge = ElementItem.Empty()
        ignoreEdges =  [ i for i in ignore if isinstance( i , bmesh.types.BMEdge ) ]
        candidateEdges = self.highlight.CollectEdge( coord , radius , ignoreEdges )

        for vert in candidateVerts :
            # 各点からRayを飛ばす
            hitTemp = self.highlight.PickFace( vert.coord , ignoreFaces  )
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
            hitTemp = self.highlight.PickFace( edge.coord , ignoreFaces )
        
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
            hitFace = self.highlight.PickFace( coord , ignoreFaces )

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

