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
import collections
from mathutils import *
from .. import handleutility
from .. import draw_util

__all__ = ['ElementItem']

class ElementItem :
    def __init__(self , element : bmesh.types.BMVert , coord : Vector, hitPosition : Vector , dist = 0 ) :
        self.__element = element
        self.__hitPosition: Vector = hitPosition
        self.__coord: Vector = coord
        self.__dist: float = dist

    @property
    def element(self):
        return self.__element

    @property
    def hitPosition(self) -> Vector :
        return self.__hitPosition

    @property
    def coord(self) -> Vector :
        return self.__coord

    @property
    def normal(self) -> Vector :
        if self.isVert :
            return self.__element.normal
        if self.isEdge :
            return ( self.__element.verts[0].normal + self.__element.verts[1].normal ) * 0.5
        if self.isFace :
            return self.__element.normal

        return Vector(1,0,0)

    @property
    def dist(self) -> float:
        return self.__dist

    @property
    def isEmpty(self) -> bool:
        return self.__element is None

    @property
    def isNotEmpty(self) -> bool :
        return self.__element is not None

    @property
    def isVert(self) -> bool :
        return self.type == bmesh.types.BMVert

    @property
    def isEdge(self) -> bool :
        return self.type == bmesh.types.BMEdge

    @property
    def isFace(self) -> bool :
        return self.type == bmesh.types.BMFace

    @property
    def type(self):
        return type(self.__element)

    @staticmethod
    def Empty():
        return ElementItem( None , None , None , 0.0 )

    @staticmethod
    def FormVert( v ):
        p = handleutility.location_3d_to_region_2d( v.co )
        return ElementItem( v , p , v.co , 0.0 )

    def FormElement( e , co ):
        p = handleutility.location_3d_to_region_2d( co )
        return ElementItem( e , p , co , 0.0 )

    def Draw( self , obj , color , preferences ) :
        if self.isNotEmpty :
            size = preferences.highlight_vertex_size
            width = preferences.highlight_line_width
            alpha = preferences.highlight_face_alpha
            draw_util.drawElementHilight3D( obj , self.element , size , width ,alpha, color )
            if self.isEdge :
                draw_util.draw_pivot3D( self.hitPosition , 0.75 , color )

    def Draw2D( self , obj , color , preferences ) :
        if self.isNotEmpty :
            size = preferences.highlight_vertex_size
            width = preferences.highlight_line_width
            alpha = preferences.highlight_face_alpha
            draw_util.drawElementHilight( obj , self.element , size , color )
            if self.isEdge :
                draw_util.draw_pivot2D( self.hitPosition , 0.75 , color )
