import sys
import bpy
import math
import mathutils
import bmesh
import bpy_extras
import collections
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from .subtool import SubTool

class SubToolMove(SubTool) :
    name = "MoveTool"

    def __init__(self,op,startTarget,startMousePos) :
        super().__init__(op)
        self.currentTarget = startTarget
        self.subTarget = ElementItem.Empty()
        self.mouse_pos = startMousePos
        self.startPos = startTarget.hitPosition
        p = handleutility.MovePointFromRegion( self.bmo.obj , self.currentTarget.element ,self.currentTarget.hitPosition, self.mouse_pos )
        self.currentTarget = ElementItem.FormElement( self.currentTarget.element , p )
        self.bmo.UpdateMesh()

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            p = handleutility.MovePointFromRegion( self.bmo.obj , self.currentTarget.element ,self.currentTarget.hitPosition, self.mouse_pos )
            self.currentTarget = ElementItem.FormElement( self.currentTarget.element , p )

            if self.currentTarget.isVert and ( self.currentTarget.element.is_manifold is False or self.currentTarget.element.is_boundary )  :
                tmp = self.subTarget
                ignore = [self.currentTarget.element]
                ignore.extend( self.currentTarget.element.link_faces )
                ignore.extend( self.currentTarget.element.link_edges )
                self.subTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , ignore , edgering= True )
                if self.subTarget.isVert and self.currentTarget.element != self.subTarget.element :
                    self.currentTarget.element.co = self.subTarget.element.co
                    self.currentTarget = ElementItem.FormVert( self.currentTarget.element )                    
                else :
                    if tmp.isVert :
                        self.currentTarget.element.co = self.startPos
                        p = handleutility.MovePointFromRegion( self.bmo.obj , self.currentTarget.element , self.startPos, self.mouse_pos )
                        self.currentTarget = ElementItem.FormVert( self.currentTarget.element )
                    self.subTarget = ElementItem.Empty()

            self.bmo.UpdateMesh()
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.currentTarget.isVert and self.subTarget.isVert :
                    bmesh.utils.vert_splice( self.currentTarget.element , self.subTarget.element )
                    self.bmo.UpdateMesh()                    
                return 'FINISHED'

        self.debugStr = str(self.subTarget.element)

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        self.currentTarget.Draw2D( self.bmo.obj , self.color_highlight() , self.preferences )
    
