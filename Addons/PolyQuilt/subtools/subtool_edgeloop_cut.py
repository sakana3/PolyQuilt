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
import bpy_extras
import collections
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from ..dpi import *
from .subtool import SubTool

class SubToolEdgeloopCut(SubTool) :
    name = "SliceTool"

    def __init__(self,op, target : ElementItem ) :
        super().__init__(op)
        self.currentEdge = target
        self.is_forcus = False
        self.EdgeLoops = None
        self.VertLoops = None

    def Check( target : ElementItem ) :
        if len( target.element.link_faces ) == 2 :
            return True
        return False

    def OnForcus( self , context , event  ) :
        if event.type == 'MOUSEMOVE':
            self.is_forcus = False
            p0 = self.bmo.local_to_2d( self.currentEdge.element.verts[0].co )
            p1 = self.bmo.local_to_2d( self.currentEdge.element.verts[1].co )
            if self.bmo.is_snap2D( self.mouse_pos , p0 ) or self.bmo.is_snap2D( self.mouse_pos , p1 ) :
                self.is_forcus = True
                if self.EdgeLoops == None :
                    self.EdgeLoops , self.VertLoops = self.SelectEdgeLoops( self.currentEdge.element )
        return self.is_forcus

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.EdgeLoops != None :
                    self.DoEdgeLoopCut( self.EdgeLoops , self.VertLoops )
                    self.bmo.UpdateMesh()                    
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.EdgeLoops != None :
            alpha = self.preferences.highlight_face_alpha
            vertex_size = self.preferences.highlight_vertex_size        
            width = self.preferences.highlight_line_width
            color = self.color_delete()
            draw_util.drawElementsHilight3D( self.bmo.obj , self.EdgeLoops , vertex_size ,width,alpha, color )

    def SelectEdgeLoops( self , startEdge ) :
        edges = []
        verts = []

        def append( lst , geom ) :
            if geom not in lst :
                lst.append(geom)
                if self.bmo.is_mirror_mode :
                    mirror =self.bmo.find_mirror( geom )
                    if mirror :
                        lst.append( mirror )

        for vert in startEdge.verts :
            preEdge = startEdge
            currentV = vert
            while currentV != None :
                append(edges , preEdge)

                if currentV.is_boundary :
                    if len( currentV.link_faces )== 2 :
                        if not any( [ len(f.verts) == 3 for f in currentV.link_faces ] ):
                            if currentV not in verts :
                                append(verts , currentV)
                    break

                if len(currentV.link_faces) == 4 :
                    faces = set(currentV.link_faces ) ^ set(preEdge.link_faces )
                    if len( faces ) != 2 :
                        break
                    faces = list(faces)
                    share_edges = set(faces[0].edges) & set(faces[1].edges) & set(currentV.link_edges )
                    if len(share_edges) != 1 :
                        print(share_edges)                    
                        break
                    preEdge = list(share_edges)[0]

                    if currentV not in verts :
                        append(verts , currentV)

                elif len(currentV.link_faces) == 2 :
                    share_edges = [ e for e in currentV.link_edges if e != preEdge ]
                    if len(share_edges) != 1 :
                        break
                    preEdge = share_edges[0]
                else :
                    break
                currentV = preEdge.other_vert(currentV)
                if currentV == vert:
                    break
        return edges , verts


    def DoEdgeLoopCut( self , edges , verts ) :
        bmesh.ops.dissolve_edges( self.bmo.bm , edges = edges , use_verts = False , use_face_split = False )  
        vs = [ v for v in verts if v.is_valid ]
        bmesh.ops.dissolve_verts( self.bmo.bm , verts = vs , use_face_split = True , use_boundary_tear = False )        
        self.currentTarget = ElementItem.Empty()        

#bmesh.ops.smooth_vert（bm、verts、factor、mirror_clip_x、mirror_clip_y、mirror_clip_z、clip_dist、use_axis_x、use_axis_y、use_axis_z ）
