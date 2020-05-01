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
import blf
import math
import mathutils
import bmesh
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubTool

class SubToolKnife(SubTool) :
    name = "KnifeTool2"

    def __init__(self,op, currentElement : ElementItem ,startPos) :
        super().__init__(op)
        if currentElement.isNotEmpty and not currentElement.isFace :
            self.startPos = currentElement.coord
        else :
            self.startPos = startPos
        self.endPos = self.startPos
        self.cut_edges = {}
        self.cut_edges_mirror = {}
        self.startElement = currentElement
        self.goalElement = ElementItem.Empty()

    def OnUpdate( self , context , event ) :
        self.goalElement = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight, elements = ['EDGE','VERT'] )   
        if self.goalElement.isNotEmpty and not self.goalElement.isFace :
            self.goalElement.set_snap_div( self.preferences.loopcut_division )
            self.endPos = self.goalElement.coord
        else :
            self.endPos = self.mouse_pos
        
        if event.type == 'MOUSEMOVE':
            if( self.startPos - self.endPos ).length > 2 :
                self.CalcKnife( context,self.startPos,self.endPos )
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.cut_edges or self.cut_edges_mirror  :
                    self.DoKnife(context,self.startPos,self.endPos)
                    self.bmo.UpdateMesh()                
                    return 'FINISHED'
                return 'CANCELLED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_lines2D( (self.startPos,self.endPos) , self.color_delete() , self.preferences.highlight_line_width )

    def OnDraw3D( self , context  ) :
        if self.goalElement.isNotEmpty :
            self.goalElement.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

        if self.cut_edges :
            draw_util.draw_pivots3D( list(self.cut_edges.values()) , 1 , self.color_delete() )
        if self.cut_edges_mirror :
            draw_util.draw_pivots3D( list(self.cut_edges_mirror.values()) , 1 , self.color_delete(0.5) )

    def CalcKnife( self ,context,startPos , endPos ) :
        slice_plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
        self.cut_edges = self.calc_slice( slice_plane , plane0 , plane1  )
        if self.bmo.is_mirror_mode :
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()
            self.cut_edges_mirror = self.calc_slice( slice_plane , plane0 , plane1 )

    def make_slice_planes( self , context,startPos , endPos ):
        slice_plane_world = pqutil.Plane.from_screen_slice( context,startPos , endPos )
        slice_plane_object = slice_plane_world.world_to_object( self.bmo.obj )

        ray0 = pqutil.Ray.from_screen( context , startPos ).world_to_object( self.bmo.obj )
        vec0 = slice_plane_object.vector.cross(ray0.vector).normalized()
        ofs0 = vec0 * 0.001
        plane0 = pqutil.Plane( ray0.origin - ofs0 , vec0 )
        ray1 = pqutil.Ray.from_screen( context ,endPos ).world_to_object( self.bmo.obj )
        vec1 = slice_plane_object.vector.cross(ray1.vector).normalized()
        ofs1 = vec1 * 0.001
        plane1 = pqutil.Plane( ray1.origin + ofs1 , vec1 )

        return slice_plane_object , plane0 , plane1

    def calc_slice( self ,slice_plane , plane0 , plane1 ) :
        edges = [ edge for edge in self.bmo.edges if edge.hide is False ]
        slice_plane_intersect_line = slice_plane.intersect_line
        plane0_distance_point = plane0.distance_point
        plane1_distance_point = plane1.distance_point
        epsilon = sys.float_info.epsilon
        
        def chk( edge ) :        
            p0 = edge.verts[0].co
            p1 = edge.verts[1].co
            p = slice_plane_intersect_line( p0 , p1 )

            if p != None :
                a0 = plane0_distance_point( p )
                a1 = plane1_distance_point( p )
                if (a0 > epsilon and a1 > epsilon ) or (a0 < -epsilon and a1 < -epsilon ):
                    return None
            return p

        matrix = self.bmo.obj.matrix_world
        cut_edges = { edge : chk( edge ) for edge in edges }
        cut_edges = { e : matrix @ p for e,p in cut_edges.items() if p != None }
#        for add_edge in add_edges :
#            cut_edges[add_edge] = slice_plane_intersect_line( add_edge.verts[0].co , add_edge.verts[1].co )
        return cut_edges

    def DoKnife( self ,context,startPos , endPos ) :
        bm = self.bmo.bm
        threshold = bpy.context.scene.tool_settings.double_threshold
        plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
        faces = [ face for face in self.bmo.faces if not face.hide ]
#        if self.startElement.isVert  :
#            for edge in self.startElement.element.link_edges :
 #               self.cut_edges[edge] = self.startElement.coord
 #       if self.goalElement.isVert :
  #          for edge in self.goalElement.element.link_edges :
  #              self.cut_edges[edge] = self.goalElement.coord
        elements = list(self.cut_edges.keys()) + faces

        ret = bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= plane.origin ,plane_no= plane.vector ,use_snap_center=True,clear_outer=False,clear_inner=False)
        for e in ret['geom_cut'] :
            e.select_set(True)
        if QSnap.is_active() :
            QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

        if self.bmo.is_mirror_mode :
            slice_plane , plane0 , plane1 = self.make_slice_planes(context,startPos , endPos)
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()
            self.bmo.UpdateMesh()
            cut_edges_mirror = self.calc_slice( slice_plane , plane0 , plane1 )
            if cut_edges_mirror :
                faces = [ face for face in self.bmo.faces if face.hide is False ]          
                elements = list(cut_edges_mirror.keys()) + faces[:]
                ret = bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= slice_plane.origin ,plane_no= slice_plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)
                for e in ret['geom_cut'] :
                    e.select_set(True)
                    if QSnap.is_active() :
                        QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

    @classmethod
    def GetCursor(cls) :
        return 'KNIFE'
