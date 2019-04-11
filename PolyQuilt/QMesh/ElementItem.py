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
