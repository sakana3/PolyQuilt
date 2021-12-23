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
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import *
from .subtool_edgeloop_cut import *
from .subtool_edgeloop_dissolve import *
from .subtool_edgeloop_extrude import SubToolEdgeLoopExtrude
from .subtool_edgeloop_slide import SubToolEdgeSlide
from .subtool_edgeloop_tweak import SubToolEdgeLoopTweak
from .subtool_edgering_extrude import SubToolEdgeRingExtrude

class MainToolQuadPatch(MainTool) :
    name = "QuadPatch Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op,currentTarget, button , no_hold = False )        

        self.plane = self.default_plane

        self.stroke2D = [self.mouse_pos]
        ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
        self.stroke3D = [self.plane.intersect_ray( ray )]

        selected = [ edge for edge in self.bmo.bm.edges if edge.select ]

    @staticmethod
    def LMBEventCallback(self , event ):
        self.debugStr = str(event.type)


        if event.type == MBEventType.LongClick :                
            if self.currentTarget.isEdge :
                self.bmo.dissolve_edges( self.currentTarget.both_loops , use_verts = False , use_face_split = False , dissolve_vert_angle=self.preferences.vertex_dissolve_angle )
                self.bmo.UpdateMesh()
                self.isExit = True

        elif event.type == MBEventType.Click :                
            if self.currentTarget.isEdge :
                self.bmo.select_flush()
                self.bmo.select_components( self.currentTarget.both_loops , True )
                self.bmo.UpdateMesh()
                self.isExit = True
        elif event.type == MBEventType.Drag :
            self.stroke2D.append( self.mouse_pos )
            ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
            coord = self.plane.intersect_ray( ray )
            if coord :
                self.stroke3D.append( coord )

        elif event.type == MBEventType.Release :
            self.MakeQuad()
            self.isExit = True

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['EDGE'] , edgering = True )        
        return element

    @staticmethod
    def Check( root , target ) :
        if target.isEdge :
            return True
        return True

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        funcs = []
        funcs.append( element.DrawFunc( gizmo.bmo.obj , gizmo.preferences.highlight_color , gizmo.preferences , True ) )

        if element.isEdge :
            alpha = gizmo.preferences.highlight_face_alpha
            vertex_size = gizmo.preferences.highlight_vertex_size        
            width = gizmo.preferences.highlight_line_width
            color = gizmo.preferences.highlight_color
            if element.can_extrude() :
                color = gizmo.preferences.makepoly_color
                width = gizmo.preferences.highlight_line_width + 1
            funcs.append( draw_util.drawElementsHilight3DFunc( gizmo.bmo.obj , gizmo.bmo.bm, element.both_loops , vertex_size ,width,alpha, color ) )
            return funcs
        return None

    def OnDraw( self , context  ) :
        if self.stroke2D :
            draw_util.draw_dot_lines2D( self.stroke2D , self.color_create() , self.preferences.highlight_line_width )        

    def OnDraw3D( self , context  ) :
        pass

    def OnExit( self ) :
        pass

    def MakeQuad( self , divide = 5 ) :
        p1 =self.stroke3D[0]
        totalLen = 0
        for i in range(1,len(self.stroke3D)) :
            totalLen = totalLen + (p1 - self.stroke3D[i] ).length
            p1 =self.stroke3D[i]

        if ( totalLen <= 0.01 ) :
            return

        segmentLen = totalLen / (divide-1)
        segment = 0
        newVerts = []
        newVerts.append( self.bmo.AddVertexWorld( self.stroke3D[0] ) )
        p1 =self.stroke3D[0]
        for i in range(1,len(self.stroke3D)) :
            p2 =self.stroke3D[i]
            length = (p1 - p2 ).length
            tmp = segment
            segment += length
            while segment >= segmentLen :
                t = ( segmentLen - tmp ) / length
                p1 = p2 * t + p1 * (1-t)
                newVerts.append( self.bmo.AddVertexWorld( p1 ) )
                tmp = 0
                length = (p1-p2).length
                segment -= segmentLen
            p1 =self.stroke3D[i]

        newVerts.append( self.bmo.AddVertexWorld( self.stroke3D[-1] ) )

        v1 = newVerts[0]
        for  i in range(1,len(newVerts)) :
            edge = self.bmo.add_edge( v1 , newVerts[i]  )
            self.bmo.select_component(edge)
            v1 = newVerts[i]

#        bmesh.ops.bridge_loops(self.bmo.bm, edges = edges, use_pairs = False, use_cyclic = False, use_merge = False, merge_factor = 0.0 , twist_offset = 0.0 )

        self.bmo.select_flush()
        self.bmo.select_components( newVerts , True )

        self.bmo.UpdateMesh()

    @classmethod
    def GetCursor(cls) :
        return 'DEFAULT'