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

import sys
import bpy
import math
import mathutils
import bmesh
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import MainTool
from ..utils.dpi import *
from .subtool_seam import SubToolSeam

class SubToolSeamLoop(SubToolSeam) :
    name = "Mark Seam Loop"

    @staticmethod
    def Check( root , target ) :
        return target.isEdge

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight , elements = ["EDGE"] )        
        return element

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            preTarget = self.currentTarget
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ["VERT","EDGE"]  )
            if self.currentTarget.isEdge :
                e = self.find_seam_loop( self.bmo , self.currentTarget.element )
                self.removes = (e,[])
                self.startTarget = self.currentTarget
            else :
                self.removes = ([self.currentTarget.element],[])
        elif event.type == self.buttonType : 
            if event.value == 'RELEASE' :
                if self.currentTarget.isEdge :
                    e = self.find_seam_loop( self.bmo , self.currentTarget.element )
                    self.removes = (e,[])
                    self.startTarget = self.currentTarget
                else :
                    self.removes = ([self.currentTarget.element],[])
                self.SeamElement(self.currentTarget )
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element != None and gizmo.bmo != None :
            edges = cls.find_seam_loop( gizmo.bmo , element.element )
            if edges :
                alpha = gizmo.preferences.highlight_face_alpha
                vertex_size = gizmo.preferences.highlight_vertex_size        
                width = 5        
                if not element.element.seam :
                    color = bpy.context.preferences.themes["Default"].view_3d.edge_seam
                    color = (color[0],color[1],color[2],1)
                else :
                    color = ( 0, 0 , 0 ,1)
        
                mirrors = []
                if gizmo.bmo.is_mirror_mode :
                    mirrors = [ gizmo.bmo.find_mirror(m) for m in edges ]
                    mirrors = [ m for m in mirrors if m ]
                def func() :
                    draw_util.drawElementsHilight3D( gizmo.bmo.obj , edges , vertex_size , width , alpha , color )
                    if mirrors :
                        draw_util.drawElementsHilight3D( gizmo.bmo.obj , mirrors , vertex_size , width , alpha * 0.5 , color )        
                return func
        return None
