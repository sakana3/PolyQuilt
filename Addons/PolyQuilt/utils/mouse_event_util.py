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
import math
import mathutils
import time
import copy
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
    Press = auto()
    LongPress = auto()
    LongClick = auto()
    LongPressDrag = auto()
    Release = auto()

class MBEventResult(Enum) :
    Pass = auto()
    Do = auto()
    Quit = auto()
    Cancel = auto()
class ButtonEventUtil :
    def __init__( self , button : str , func , op , use_hold_lock = False , no_hold = False ) :
        self.op = op
        self.button : str = button
        self.eventFunc = func
        self.Press : bool = False
        self.Presure : bool = False
        self.PressTime : float = 0.0
        self.type : MBEventType =  MBEventType.Noting
        self.mouse_pos = mathutils.Vector((0.0,0.0))
        self.event = None
        self.PressPos = mathutils.Vector((0.0,0.0))
        self.PressPrevPos = mathutils.Vector((0.0,0.0))
        self.presureCompOnce = False
        self.preferences = op.preferences
        self.no_hold = no_hold
        self.test = 1
        self.is_avtive = True

    def copy( self , func ) :
        newEvent = copy.copy( self )
        newEvent.eventFunc = func
        return newEvent

    @property
    def presureValue(self) -> float :  
        if self.Presure == False :
            return 0.0
        else :
            lpt = self.preferences.longpress_time
            cur = time.time()-self.PressTime
            m = max( lpt / 3.0 , 0.125 )
            t = ( cur - m ) / (lpt - m )
            return min( 1.0 , max( 0.0 , t ) )

    @property
    def presureComplite(self) -> bool : 
        return self.presureValue >= 1.0 

    @property
    def isPresure(self) -> bool : 
        return self.presureValue >= 0.0001 

    @property
    def is_hold(self) -> bool :
        hold = self.presureCompOnce
        return hold

    def is_animated( self ) :
        if self.Presure and not self.presureCompOnce :
            return True
        return False

    def Update( self , context , event  ) :
        ret = self.Execute( context , event)
        if ret in [ 'QUIT' , 'CANCELLED' , 'FINISHED' ] :
            self.is_avtive = False
        return ret

    def Execute( self , context , event  ) :
        if self.is_avtive :
            self.mouse_pos = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
            result = 'RUNNING_MODAL'
            if event.type == self.button:
                if event.value == 'PRESS':
                    if self.Press is False :
                        self.PressPos = self.mouse_pos                    
                        self.PressTime = time.time()
                        if not self.no_hold :
                            self.Press = True
                            self.Presure = True
                            self.presureCompOnce = False
                            self.PressPrevPos = mathutils.Vector((event.mouse_prev_x, event.mouse_prev_y))  
                        result = self.OnEvent( event , MBEventType.Down , result )
                    else :
                        result = self.OnEvent( event , MBEventType.Press , result )
                elif event.value == 'RELEASE':
                    if not self.no_hold :                
                        if self.presureComplite :
                            self.presureCompOnce = True
                        if self.Presure :
                            if self.is_hold :
                                result = self.OnEvent( event , MBEventType.LongClick , result )
                            else :
                                result = self.OnEvent( event , MBEventType.Click , result )
                        self.Presure = False
                        self.Press = False
                    else :
                        result = self.OnEvent( event , MBEventType.Click , result )
                    self.OnEvent( event , MBEventType.Release , result )
                    self.PressTime  = 0.0
                    self.presureCompOnce = False
            elif event.type == 'MOUSEMOVE':
                drag_threshold = context.preferences.inputs.drag_threshold_mouse
                if not self.no_hold :                        
                    if self.Press :
                        if self.presureComplite :
                            self.presureCompOnce = True
                        if event.is_tablet : 
                            drag_threshold = context.preferences.inputs.drag_threshold_tablet
                        if (time.time()-self.PressTime ) > 0.15 and (self.mouse_pos-self.PressPos ).length > drag_threshold:
                            self.Presure = False
                        if self.Presure is False :
                            if self.is_hold :
                                result = self.OnEvent( event , MBEventType.LongPressDrag , result )
                            else :
                                result = self.OnEvent( event , MBEventType.Drag , result )
                else :
                    if (time.time()-self.PressTime ) > 0.15 and (self.mouse_pos-self.PressPos ).length > drag_threshold:
                        result = self.OnEvent( event , MBEventType.Drag , result )

                self.OnEvent( event , MBEventType.Move , result )
            elif event.type == 'TIMER':
                if self.presureComplite :
                    self.presureCompOnce = True
                    result = self.OnEvent( event , MBEventType.LongPress , result )
                    
            if result == MBEventResult.Quit :
                return 'QUIT'
            elif result == MBEventResult.Do :
                return 'RUNNING_MODAL'
            elif result == MBEventResult.Pass :
                return 'PASS_THROUGH'
            elif result == MBEventResult.Cancel :
                return 'CANCELLED'

        return result

    def OnEvent( self ,event , type : MBEventType , result : MBEventResult ) :
        self.type = type
        if self.eventFunc != None :
            self.event = event
            ret = self.eventFunc( self)
            self.event = None
            if ret :
                if result == None :
                    return ret
                elif result == MBEventResult.Quit :
                    return MBEventResult.Quit
                elif result == MBEventResult.Cancel :
                    return MBEventResult.Cancel
                elif result == MBEventResult.Do and ret == MBEventResult.Pass :
                    return MBEventResult.Do
                else :
                    return ret

        return MBEventResult.Do

    def Reset(self, context ) :
        self.Presure = False
        self.Press = False
        self.presureCompOnce = False

    def Draw( self , coord = None , text = None ) :
        if self.presureValue > 0.001 :
            if coord != None :
                draw_util.draw_donuts2D( coord , 3.5 , 0.75 , self.presureValue, (1,1,1,self.presureValue)  )
                if self.presureComplite and text != None :
                    draw_util.DrawFont(text, 12 , coord , (0,4) )
            else:
                draw_util.draw_donuts2D( self.PressPos , 3.5 , 0.75 , self.presureValue, (1,1,1,self.presureValue)  )
                if self.presureComplite and text != None :
                    draw_util.DrawFont( text , 12 , self.PressPos , (0,4) )            
        return self.presureComplite

