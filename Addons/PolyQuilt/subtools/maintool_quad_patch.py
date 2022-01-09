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
import bmesh
import bpy_extras
import collections
import copy

from ..utils.dpi import display
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *
from .subtool_select_boundary_edge import SubToolSelectBoundaryEdge
from .subtool_draw_patch import SubToolDrawPatch
from .subtool_cooper import SubToolCooper
class MainToolQuadPatch(MainTool) :
    name = "QuadPatch Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = False )        
        self.callback = { 
            MBEventType.Release         : [] ,
            MBEventType.Down            : [ [ SubToolSelectBoundaryEdge.Check , SubToolSelectBoundaryEdge ] ],
            MBEventType.Click           : [],
            MBEventType.LongPress       : [ [SubToolCooper.Check , SubToolCooper ] ] ,
            MBEventType.LongPressDrag   : [ [SubToolCooper.Check , SubToolCooper ] ] ,
            MBEventType.Drag            : [ [SubToolDrawPatch.Check , SubToolDrawPatch ] ] ,
        }
        if self.currentTarget.isEmpty :
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ["EDGE"], edgering = True  )
        self.activeTarget = ElementItem.Empty()
        self.singleton = False 

    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Release :
            self.isExit = True

        if event.type in self.callback.keys() :
            subtools = self.callback[event.type]
            for i in range( 0 , len( subtools ) ) :
                subtool = subtools[i]
                if subtool :
                    if subtool[0]( self , self.currentTarget ) :
                        newtool = subtool[1]( self , self.currentTarget , self.buttonType )
                        self.SetSubTool( newtool , replace = True )
                        subtools[i] = None
#
    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        def check( target ) :
            if target.isVert :
                return target.element.select == False
            return True
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['SELECT','VERT','EDGE'] , edgering = True , check_func = check )        
        return element

    @staticmethod
    def Check( root , target ) :
        return True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        funcs = SubToolSelectBoundaryEdge.DrawHighlight( gizmo , element ) 

        if not funcs :
            color = gizmo.preferences.makepoly_color
            funcs = []
            funcs.append( element.DrawFunc( gizmo.bmo.obj , color , gizmo.preferences , marker = False, edge_pivot = False ) ) 

        return funcs

    def OnDraw( self , context  ) :
        if self.LMBEvent.isPresure :
            if self.currentTarget.isNotEmpty :
                self.LMBEvent.Draw( self.currentTarget.coord )
            else:
                self.LMBEvent.Draw( None )

        if self.currentTarget.isEdge and self.LMBEvent.is_hold :
            loop = self.currentTarget.loops
            le , vt =  pqutil.sort_edgeloop( loop )
            verts = [ pqutil.location_3d_to_region_2d( v.co ) for v in vt ]
            draw_util.draw_dot_lines2D( verts , self.color_highlight(0.5) , display.dot( self.preferences.highlight_line_width ) )

    def OnDraw3D( self , context  ) :
        self.currentTarget.Draw( self.bmo.obj , self.preferences.highlight_color , self.preferences , marker = False, edge_pivot = False )    
        pass

    def OnExit( self ) :
        pass

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'