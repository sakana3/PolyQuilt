import bpy
import math
import mathutils
import time
import collections
from enum import Enum , auto
from . import draw_util

__all__ = ['MBEventType','ButtonEventUtil']

class MBEventType(Enum) :
    Noting = auto()
    Click = auto()
    Drag = auto()
    Down = auto()
    Move = auto()
    LongPress = auto()
    LongClick = auto()
    LongPressDrag = auto()
    Release = auto()

class ButtonEventUtil :
    __timer_handle = None
    def __init__( self , button : str , cls , func , preferences ) :
        self.button : str = button
        self.eventFunc = func
        self.eventClass = cls
        self.Press : bool = False
        self.Presure : bool = False
        self.PressTime : float = 0.0
        self.type : MBEventType =  MBEventType.Noting
        self.mouse_pos = mathutils.Vector((0.0,0.0))
        self.event = None
        self.PressPos = mathutils.Vector((0.0,0.0))
        self.presureCompOnce = False
        self.preferences = preferences

    def __del__(self) :
        self.RemoveTimerEvent(bpy.context)

    @property
    def presureValue(self) -> float :  
        if self.Presure == False :
            return 0.0
        else :
            lpt = self.preferences.longpress_time
            cur = time.time()-self.PressTime
            t = ( cur - (lpt/3.0) ) / (lpt - lpt/3.0)
            return min( 1.0 , max( 0.0 , t ) )

    @property
    def presureComplite(self) -> bool : 
        return self.presureValue >= 1.0 

    @property
    def isPresure(self) -> bool : 
        return self.presureValue >= 0.0001 

    def Update( self , context , event  ) :
        self.mouse_pos = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))                    
        if event.type == self.button:
            if event.value == 'PRESS': 
                if self.Press is False :
                    self.Press = True
                    self.Presure = True
                    self.presureCompOnce = False
                    self.PressTime = time.time()
                    self.PressPos = self.mouse_pos
                    self.OnEvent( event , MBEventType.Down )
                    self.AddTimerEvent(context)
                else :
                    self.OnEvent( event , MBEventType.Press )
            elif event.value == 'RELEASE':
                if self.presureComplite :
                    self.presureCompOnce = True
                if self.Presure :
                    if self.presureComplite :
                        self.OnEvent( event , MBEventType.LongClick )
                    else :
                        self.OnEvent( event , MBEventType.Click )
                self.Presure = False
                self.Press = False
                self.OnEvent( event , MBEventType.Release )
                self.RemoveTimerEvent(context)
                self.PressTime  = 0.0
                self.presureCompOnce = False
        elif event.type == 'MOUSEMOVE':
            if self.Press :
                if self.presureComplite :
                    self.presureCompOnce = True
                if (time.time()-self.PressTime ) > 0.15 and (self.mouse_pos-self.PressPos ).length > 4:
                   self.Presure = False
                if self.Presure is False :
                    if self.presureCompOnce :
                       self.OnEvent( event , MBEventType.LongPressDrag )
                    else :
                       self.OnEvent( event , MBEventType.Drag )
            self.OnEvent( event , MBEventType.Move )
        elif event.type == 'TIMER':
            if self.presureComplite :
                self.presureCompOnce = True
                self.OnEvent( event , MBEventType.LongPress )
    
    def OnEvent( self ,event , type : MBEventType ) :
        self.type = type
        if self.eventFunc != None :
            self.event = event
            self.eventFunc( self.eventClass , self)
            self.event = None
        pass

    def Reset(self, context ) :
        self.Presure = False
        self.Press = False
        self.presureCompOnce = False
        self.RemoveTimerEvent(context)

    def Draw( self , coord = None , text = None ) :
        if self.presureValue > 0.001 :
            if coord != None :
                draw_util.draw_donuts2D( coord , 4 , 1 , self.presureValue, (1,1,1,self.presureValue)  )
                if self.presureComplite and text != None :
                    draw_util.DrawFont(text, 12 , coord , (0,4) )
            else:
                draw_util.draw_donuts2D( self.PressPos , 4 , 1 , self.presureValue, (1,1,1,self.presureValue)  )
                if self.presureComplite and text != None :
                    draw_util.DrawFont( text , 12 , self.PressPos , (0,4) )            
        return self.presureComplite

    def AddTimerEvent( self , context , time = 1.0 / 60.0 ) :
        if ButtonEventUtil.__timer_handle is None :
            ButtonEventUtil.__timer_handle = context.window_manager.event_timer_add( time , window = context.window)

    def RemoveTimerEvent( self , context ) :
        if ButtonEventUtil.__timer_handle is not None:
            context.window_manager.event_timer_remove(ButtonEventUtil.__timer_handle)
            ButtonEventUtil.__timer_handle = None
