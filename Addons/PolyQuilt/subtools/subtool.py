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
import blf
import math
import mathutils
import bmesh
from enum import Enum , auto
import bpy_extras
import collections
from ..utils import pqutil
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
import time
from ..QMesh import *

class SubToolRoot :
    name = "None"
    __timer_handle = None
   
    def __init__(self,op, button = None) :
        self.operator = op
        self.bmo : QMesh = op.bmo
        self.debugStr = ""
        self.subTool = []
        self.__enterySubTool = None
        self.step = 0
        self.mouse_pos = mathutils.Vector((0,0))
        self.preferences = op.preferences
        self.activeSubTool = None
        self.buttonType = button

    @staticmethod
    def Check( root  ,target ) :
        return True

    def Active(self) :
        return self if self.activeSubTool == None else self.activeSubTool

    @classmethod
    def GetCursor(cls) :
        return 'DEFAULT'

    def CurrentCursor( self ) :
        if self.activeSubTool is None :
            return self.GetCursor()
        return self.activeSubTool.CurrentCursor()

    def SetSubTool( self , subTool ) :
        if isinstance( subTool , list) :
            self.__enterySubTool = subTool
        else :
            self.__enterySubTool = [ subTool ]

    def OnInit( self , context ) :
        pass

    def OnExit( self ) :
        pass

    def OnForcus( self , context , event  ) :
        return True

    def OnUpdate( self , context , event ) :
        return 'FINISHED'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        pass

    def Update( self , context , event ) :

        ret = None
        self.mouse_pos = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))

        if self.__enterySubTool != None :
            self.subTool = self.__enterySubTool
            self.__enterySubTool = None
            for subTool in self.subTool :
                self.OnEnterSubTool( context , subTool)

        self.activeSubTool = None
        if self.subTool :
            for subTool in self.subTool :
                ret = subTool.Update(context , event)
                if ret == 'RUNNING_MODAL' :
                    self.activeSubTool = subTool
                    break
                elif ret == 'FINISHED' :
                    break
                elif ret == 'PASS_THROUGH' :
                    ret = None

            if ret == 'FINISHED' :
                for subTool in self.subTool :
                    subTool.OnExit()
                self.OnExitSubTool( context , subTool)

        if ret == 'PASS_THROUGH' :
            ret = 'RUNNING_MODAL'

        if ret == None :
            if self.OnForcus(context , event) :            
                ret = self.OnUpdate(context,event)
            else :
                return 'PASS_THROUGH'

        if ret != 'RUNNING_MODAL'  :
            self.subTool = []
            self.OnExit()

        self.step += 1
        return ret

    def check_animated( self , context ) :
        if self.activeSubTool :
            return self.activeSubTool.is_animated(context)
        else :
            return self.is_animated(context)
        return False

    def is_animated( self , context ) :
        return False

    def Draw2D( self , context  ) :
        if self.activeSubTool :
            self.activeSubTool.Draw2D(context )
        else :
            self.OnDraw(context)

    def Draw3D( self , context  ) :
        if self.activeSubTool :
            self.activeSubTool.Draw3D(context )
        else :
            self.OnDraw3D(context)

    def OnEnterSubTool( self ,context,subTool ):
        pass

    def OnExitSubTool( self ,context,subTool ):
        return 'RUNNING_MODAL'

    def color_highlight( self , alpha = 1.0 ) :
        col = self.preferences.highlight_color
        return (col[0],col[1],col[2],col[3] * alpha)

    def color_create( self , alpha = 1.0 ) :
        col = self.preferences.makepoly_color        
        return (col[0],col[1],col[2],col[3] * alpha)

    def color_split( self , alpha = 1.0 ) :
        col = self.preferences.split_color            
        return (col[0],col[1],col[2],col[3] * alpha)

    def color_delete( self ,alpha = 1.0 ) :
        col = self.preferences.delete_color            
        return (col[0],col[1],col[2],col[3] * alpha)

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element != None and gizmo.bmo != None :
            return element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.highlight_color , gizmo.preferences )
        return None

    @classmethod
    def UpdateHighlight( cls , gizmo , element ) :
        if gizmo.currentElement.element != element.element :
            return True
        elif element.isEdge :
            if element.coord != gizmo.currentElement.coord :
                return True
        return False

    @classmethod
    def recive_event( cls , gizmo , context , event ) :
        pass

class MainTool(SubToolRoot) :
    def __init__(self,op,currentTarget, button , no_hold = False ) :
        super().__init__(op, button)        
        self.currentTarget = currentTarget
        self.LMBEvent = ButtonEventUtil( button ,self, self.LMBEventCallback , op , True , no_hold )
        self.isExit = False

    def is_animated( self , context ) :
        return self.LMBEvent.is_animated()

    @staticmethod
    def LMBEventCallback(self , event ):
        pass

    def OnUpdate( self , context , event ) :
        if self.isExit :
            return 'FINISHED'

        self.LMBEvent.Update(context,event)

        return 'RUNNING_MODAL'

    def OnEnterSubTool( self ,context,subTool ):
        self.currentTarget = ElementItem.Empty()
        self.LMBEvent.Reset(context)

    def OnExitSubTool( self ,context,subTool ):
        self.currentTarget = ElementItem.Empty()

    def do_empty_space( self , event ) :
        if self.preferences.space_drag_op == "ORBIT" :
            bpy.ops.view3d.rotate('INVOKE_DEFAULT', use_cursor_init=True)
            return True
        elif self.preferences.space_drag_op == "PAN" :
            bpy.ops.view3d.move('INVOKE_DEFAULT', use_cursor_init=True)
            return True
        elif self.preferences.space_drag_op == "DOLLY" :
            bpy.ops.view3d.zoom('INVOKE_DEFAULT', use_cursor_init=True)
            return True
        elif self.preferences.space_drag_op == "KNIFE" :
            self.SetSubTool( SubToolKnife(self.operator,self.currentTarget , self.LMBEvent.PressPos ) )
        elif self.preferences.space_drag_op == "SELECT_BOX" :
            bpy.context.window.cursor_warp( event.PressPrevPos.x , event.PressPrevPos.y )
            bpy.ops.view3d.select_box('INVOKE_DEFAULT' ,wait_for_input=False, mode='SET')
            bpy.context.window.cursor_warp( event.event.mouse_prev_x ,event.event.mouse_prev_y )
            return True
        elif self.preferences.space_drag_op == "SELECT_LASSO" :
            bpy.context.window.cursor_warp( event.PressPrevPos.x , event.PressPrevPos.y )
            bpy.ops.view3d.select_lasso('INVOKE_DEFAULT' , path = [], mode='SET')
            bpy.context.window.cursor_warp( event.event.mouse_prev_x ,event.event.mouse_prev_y )
            return True

        return True

    @classmethod
    def UpdateHighlight( cls , gizmo , element ) :
        return True

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight )        
        element.set_snap_div( preferences.loopcut_division )
        return element


class SubTool(SubToolRoot) :
    def __init__( self, op ) :
        super().__init__(op )        

class SubToolEx(SubTool) :
    def __init__( self, root ) :
        super().__init__( root.operator )     
        self.rootTool = root
        self.currentTarget = root.currentTarget           
        self.startMousePos = root.mouse_pos.copy()



