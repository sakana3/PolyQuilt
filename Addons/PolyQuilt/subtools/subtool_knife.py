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
import numpy as np
import collections

from ..utils.dpi import display
from ..utils import pqutil
from ..utils import draw_util
from ..utils import np_math
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
        draw_util.draw_dot_lines2D( (self.startPos,self.endPos) , self.color_delete() , display.dot(self.preferences.highlight_line_width) )

    def OnDraw3D( self , context  ) :
        if self.goalElement.isNotEmpty :
            self.goalElement.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

        if self.cut_edges :
            draw_util.draw_pivots3D( self.cut_edges.values() , 1 , self.color_delete() )
            
        if self.cut_edges_mirror :
            draw_util.draw_pivots3D( list(self.cut_edges_mirror.values()) , 1 , self.color_delete(0.5) )

    def CalcKnife( self ,context, p0 , p1 ) :
        epos , eids = self.bmo.highlight.viewPosEdges

        hits = np_math.IntersectLine2DLines2D( np.array( (p0,p1) , dtype = np.float32 ) , epos , isRetPoint= False )

        edges = self.bmo.edges
        edges = [ edges[i] for i in eids[hits] ]
        plane_intersect_line = pqutil.Plane.from_screen_slice( context,p0 , p1 ).world_to_object( self.bmo.obj ).intersect_line
        matrix = self.bmo.obj.matrix_world
        self.cut_edges = { e : matrix @ plane_intersect_line(e.verts[0].co,e.verts[1].co) for e in edges }

        if self.bmo.is_mirror_mode :
            find_mirror = self.bmo.find_mirror
            mirror_pos = self.bmo.mirror_pos
            mirrors =  [ (find_mirror( e , False ) , mirror_pos(v),e ) for e , v in self.cut_edges.items() ]
            self.cut_edges_mirror = { x : y for x,y,e in mirrors if x is not None }


    def DoKnife( self ,context,startPos , endPos ) :
        bm = self.bmo.bm
        threshold = bpy.context.scene.tool_settings.double_threshold
        plane , plane0 , plane1 = pqutil.make_slice_planes(context,startPos , endPos)
        plane = plane.world_to_object(self.bmo.obj)
        faces = [ face for face in self.bmo.faces if not face.hide ]

        elements = list(self.cut_edges.keys()) + faces

        ret = bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= plane.origin ,plane_no= plane.vector ,use_snap_center=True,clear_outer=False,clear_inner=False)
        for e in ret['geom_cut'] :
            e.select_set(True)
        if QSnap.is_active() :
            QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

        if self.bmo.is_mirror_mode and self.cut_edges_mirror :
            slice_plane , plane0 , plane1 = pqutil.make_slice_planes(context,startPos , endPos)
            slice_plane = plane.world_to_object(self.bmo.obj)
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()

            faces = [ face for face in self.bmo.faces if not face.hide ]         
            elements = list( set( list( self.cut_edges_mirror.keys()) + faces[:] + ret['geom_cut'] + ret['geom'] ) )
            ret = bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= slice_plane.origin ,plane_no= slice_plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)
            for e in ret['geom_cut'] :
                e.select_set(True)
                if QSnap.is_active() :
                    QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

            self.bmo.UpdateMesh()

    @classmethod
    def GetCursor(cls) :
        return 'KNIFE'
