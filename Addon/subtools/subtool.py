import bpy
import blf
import math
import mathutils
import bmesh
from enum import Enum , auto
import bpy_extras
import collections
from ..QMesh.QMesh import *
import time


class SubTool :
    name = "None"
    __timer_handle = None
   
    def __init__(self,op) :
        self.operator = op
        self.bmo : QMesh = op.bmo
        self.debugStr = ""
        self.subTool = None
        self.__enterySubTool = None
        self.step = 0
        self.mouse_pos = mathutils.Vector((0,0))
        self.preferences = op.preferences

    def Active(self) :
        return self if self.subTool == None else self.subTool

    def GetCursor(self) :
        return 'DEFAULT'

    def SetSubTool( self , subTool ) :
        self.__enterySubTool = subTool 

    def OnInit( self , context ) :
        pass

    def OnExit( self ) :
        pass

    def OnUpdate( self , context , event ) :
        return 'FINISHED'

    def OnDraw( self , context  ) :
        pass

    def Update( self , context , event ) :

        ret = 'FINISHED'
        self.mouse_pos = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))

        if self.__enterySubTool != None :
            self.subTool = self.__enterySubTool
            self.__enterySubTool = None
            self.OnEnterSubTool( context , self.subTool)

        if self.subTool != None :
            ret = self.subTool.Update(context , event)
            if ret == 'FINISHED' :
                self.subTool.OnExit()
                ret = self.OnExitSubTool( context , self.subTool)
                self.subTool = None
        else :
            ret = self.OnUpdate(context,event)

        if ret == 'FINISHED' :
            self.OnExit()

        self.step += 1
        return ret

    def Draw( self , context  ) :
        if self.subTool != None :
            self.subTool.Draw(context )
        else :
            self.OnDraw(context)
        pass

    def OnEnterSubTool( self ,context,subTool ):
        pass

    def OnExitSubTool( self ,context,subTool ):
        return 'RUNNING_MODAL'

    def AddTimerEvent( self , context , time = 1.0 / 60.0 ) :
        if SubTool.__timer_handle is not None :
            SubTool.__timer_handle = context.window_manager.event_timer_add( time , window = context.window)

    def RemoveTimerEvent( self , context ) :
        if SubTool.__timer_handle is not None:
            context.window_manager.event_timer_remove(SubTool.__timer_handle)
            SubTool.__timer_handle = None
        
    def color_highlight( self , alpha = 1.0 ) :
        return (1,1,0.2,alpha)

    def color_create( self , alpha = 1.0 ) :
        return (0.4,0.7,0.9,alpha)

    def color_split( self , alpha = 1.0 ) :
        return (0.1,1.0,0.25,alpha)

    def color_edgeloop( self , alpha = 1.0 ) :
        return (0.1,1.0,0.25,alpha)

    def color_delete( self ,alpha = 1.0 ) :
        return (1,0.1,0.1,alpha)

