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
from .subtool import SubToolEx
from ..utils.dpi import *

class SubToolDelete(SubToolEx) :
    name = "DeleteTool"

    def __init__(self,root,currentTarget) :
        super().__init__( root )
        self.currentTarget = currentTarget
        self.startTarget = currentTarget
        self.removes = ( [ currentTarget.element ] , [] )

    @staticmethod
    def Check( root , target ) :
        return target.isNotEmpty

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            preTarget = self.currentTarget
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = [self.startTarget.type_name]  )
            if self.startTarget.element == self.currentTarget.element :
                self.startTarget = self.currentTarget

                vt = None
                if self.startTarget.isEdge :
                    vt = self.bmo.highlight.check_hit_element_vert( self.startTarget.element , self.mouse_pos , self.preferences.distance_to_highlight * dpm())
                ed = None
                if self.startTarget.isFace :
                    ed = self.bmo.highlight.check_hit_element_edge( self.startTarget.element , self.mouse_pos , self.preferences.distance_to_highlight * dpm())
                if vt :
                    e , v = self.bmo.calc_edge_loop( self.startTarget.element )
                    self.removes = (e,v)
                    self.currentTarget = self.startTarget
                elif ed :
                    self.removes = (  self.bmo.calc_loop_face(ed) , [] )
                else :
                    self.removes = ([self.startTarget.element],[])
            elif self.currentTarget.isNotEmpty and preTarget != self.currentTarget.element:
                if self.startTarget.type == self.currentTarget.type :
                    self.removes = self.calc_shortest_pass( self.bmo.bm , self.startTarget.element , self.currentTarget.element )
                else :
                    self.removes = ([self.startTarget.element],[])
            else :
                self.removes = ([self.startTarget.element],[])
        elif event.type == self.rootTool.buttonType : 
            if event.value == 'RELEASE' :
                self.RemoveElement(self.currentTarget )
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        if element != None and gizmo.bmo != None :
            return element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.delete_color , gizmo.preferences , marker = False , edge_pivot = False )
        return None

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.removes[0] :
            alpha = self.preferences.highlight_face_alpha
            vertex_size = self.preferences.highlight_vertex_size        
            width = self.preferences.highlight_line_width        
            color = self.preferences.delete_color 
            draw_util.drawElementsHilight3D( self.bmo.obj , self.removes[0] , vertex_size , width , alpha , color )
            if self.bmo.is_mirror_mode :
                mirrors = [ self.bmo.find_mirror(m) for m in self.removes[0] ]
                mirrors = [ m for m in mirrors if m ]
                if mirrors :
                    draw_util.drawElementsHilight3D( self.bmo.obj , mirrors , vertex_size , width , alpha * 0.5 , color )

        if self.startTarget.element == self.currentTarget.element :
            self.startTarget.Draw( self.bmo.obj , self.preferences.delete_color  , self.preferences , marker = False , edge_pivot = True )
        else :
            self.startTarget.Draw( self.bmo.obj , self.preferences.delete_color  , self.preferences , marker = False , edge_pivot = False )
        if self.currentTarget.isNotEmpty :
            if self.startTarget.element != self.currentTarget.element :
                self.currentTarget.Draw( self.bmo.obj , self.preferences.delete_color  , self.preferences , marker = False , edge_pivot = False )

    @classmethod
    def GetCursor(cls) :
        return 'ERASER'

    def RemoveElement( self , element ) :
        def dissolve_edges( edges ) :
            if all( e.is_boundary for e in edges ) :
                faces = set()
                for e in edges :
                    for f in e.link_faces :
                        faces.add(f)
                self.bmo.delete_faces( list(faces) )
            else :
                self.bmo.dissolve_edges( edges , use_verts = False , use_face_split = False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle )

        if element.isNotEmpty :
            if self.removes[0] and self.removes[1] :
                self.bmo.do_edge_loop_cut( self.removes[0] , self.removes[1] )
            elif element.isVert :
                edges = [ r for r in self.removes[0] if isinstance( r , bmesh.types.BMEdge )  ]
                if edges :
                    dissolve_edges( edges )
                else :
                    self.bmo.dissolve_vert( element.element , False , False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle  )
            elif element.isEdge :
                dissolve_edges( self.removes[0] )
            elif element.isFace :
                self.bmo.delete_faces( self.removes[0] )                    
            self.bmo.UpdateMesh()


    @staticmethod
    def calc_shortest_pass( bm , start : ElementItem , end : ElementItem  ) :
        if isinstance( start , bmesh.types.BMFace ) :
            for edge in start.edges :
                if end in edge.link_faces :
                    return ([start,end],[])
        elif isinstance( start , bmesh.types.BMEdge ) :
            for vert in start.verts :
                if end in vert.link_edges :
                    return ([start,end],[])
        elif isinstance( start , bmesh.types.BMVert ) :
            for edge in start.link_edges :
                if end in edge.verts :
                    return ([edge],[])

        bpy.ops.mesh.select_all(action='DESELECT')
        start.select = True
        end.select = True
        bk = bpy.context.tool_settings.mesh_select_mode[0:3]
        bpy.context.tool_settings.mesh_select_mode = ( isinstance( start , bmesh.types.BMVert ) , isinstance( start , bmesh.types.BMEdge ) , isinstance( start , bmesh.types.BMFace ) )        
        bpy.ops.mesh.shortest_path_select( edge_mode = 'SELECT' , use_face_step = False , use_topology_distance = True , use_fill = False )

        removes = []
        if isinstance( start , bmesh.types.BMFace ) :
            removes = [ f for f in bm.faces if f.select ]
        elif isinstance( start , bmesh.types.BMEdge ) :
            removes = [ f for f in bm.edges if f.select ]
        elif isinstance( start , bmesh.types.BMVert ) :
            removes = [ f for f in bm.edges if f.select ]
            if not removes :
                removes = [ f for f in bm.verts if f.select ]

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.context.tool_settings.mesh_select_mode = bk
        return ( removes , [] )
