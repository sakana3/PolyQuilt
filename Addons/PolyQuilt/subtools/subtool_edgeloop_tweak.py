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
from ..utils.dpi import *
from .subtool import MainTool
from .subtool_util import move_component_module

class SubToolEdgeLoopTweak(MainTool) :
    name = "EdgeLoop Slide"

    def __init__(self,op,target : ElementItem , button) :        
        super().__init__(op,target, button)

        self.loop_edges = target.loops
#       self.loop_edges = self.bmo.sort_edges( target.loops )

        self.move_component_module = move_component_module( self.bmo , target , self.mouse_pos , op.move_type , self.preferences.fix_to_x_zero )
        self.move_component_module.set_geoms( self.loop_edges )

        self.snap_target = ElementItem.Empty()
        self.snap_edges = {}

#        self.ignore_edges = copy.copy(self.loop_edges)
        self.ignoreVerts = set()
        self.ignore_edges = set()
        for e in target.both_loops :
            for face in e.link_faces :
                self.ignoreVerts = self.ignoreVerts | set(face.verts)
                self.ignore_edges = self.ignore_edges | set(face.edges)

    @staticmethod
    def Check( root , target ) :
        return target.isEdge 

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            move = self.move_component_module.move_to( self.mouse_pos )

            if self.move_component_module.update_geoms(move , snap_type = 'NEAR' ) :
                self.bmo.UpdateMesh()

            # Snap 2 Edge
            dist = self.preferences.distance_to_highlight
            snap_target = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'] , ignore=self.ignore_edges )       
            if snap_target.isEdge :
                self.snap_target = snap_target
                self.snap_edges = self.move_component_module.snap_loop( self.currentTarget.element , self.loop_edges , self.snap_target.element  )
                for vert , snap in self.snap_edges.items() :
                    vert.co = snap.co

            else :
                self.snap_edges = {}
                self.snap_target = ElementItem.Empty()

            # Snap 2 Vert
            for vert in self.move_component_module.verts :
                if vert not in self.snap_edges.keys() :
                    pos =self.bmo.local_to_2d( vert.co )
                    if pos :
                        snapTarget = self.bmo.PickElement( pos , dist , edgering=True , backface_culling = True , elements=['VERT'] , ignore=self.ignoreVerts )
                        if snapTarget.isVert :
                            vert.co = snapTarget.element.co
                            self.snap_edges[vert] = snapTarget.element

        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'RELEASE' :
                for v,c in self.move_component_module.verts.items() :
                    v.co = c
                self.bmo.UpdateMesh()                
                return 'FINISHED'
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.snap_edges :
                    threshold = bpy.context.scene.tool_settings.double_threshold
                    elem = list(self.snap_edges.keys()) + list(self.snap_edges.values())
                    bmesh.ops.remove_doubles( self.bmo.bm , verts = list(elem) , dist = threshold )
                    self.bmo.UpdateMesh()
                return 'FINISHED'
        else :
            self.move_component_module.update(event)

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        size = self.preferences.highlight_vertex_size
        for snap in self.snap_edges :
            pos = pqutil.location_3d_to_region_2d( snap.co )
            if pos :
                draw_util.draw_circle2D( pos , size , (1,1,1,1) , False )

    def OnDraw3D( self , context  ) :
        alpha = self.preferences.highlight_face_alpha
        vertex_size = self.preferences.highlight_vertex_size        
        width = self.preferences.highlight_line_width
        color = self.preferences.highlight_color
        draw_util.drawElementsHilight3D( self.bmo.obj , self.loop_edges , vertex_size ,width,alpha, color )

        self.move_component_module.draw_3D(context)