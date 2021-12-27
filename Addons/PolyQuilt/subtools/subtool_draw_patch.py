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

class SubToolDrawPatch(SubTool) :
    name = "DrawPatch Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op)        

        self.plane = self.default_plane

        self.stroke2D = [self.operator.start_mouse_pos]

        if QSnap.is_active() :
            coord = QSnap.screen_adjust(self.operator.start_mouse_pos)
        else :
            ray = pqutil.Ray.from_screen( bpy.context , self.operator.start_mouse_pos )
            coord = self.plane.intersect_ray( ray )

        self.stroke3D = [coord]

        self.activeTarget = ElementItem.Empty()
        self.firstVert =  None if not currentTarget.isVert else currentTarget.element
        self.lastVert = None

    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.activeTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ['VERT'] )

            self.stroke2D.append( self.mouse_pos )
            ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
            coord = self.plane.intersect_ray( ray )
            if coord :
                if QSnap.is_active() :
                    coord = QSnap.view_adjust(coord)
                self.stroke3D.append( coord )
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                self.MakeQuad()
                return 'FINISHED'
        elif event.type == 'RIGHTMOUSE': 
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    @staticmethod
    def pick_element( qmesh , location , preferences ) :
        def check( target ) :
            if target.isVert :
                return target.element.select == False
            return True
        element = qmesh.PickElement( location , preferences.distance_to_highlight, elements = ['VERT','EDGE'] , edgering = True , check_func = check )        
        return element

    @staticmethod
    def Check( root , target ) :
        return target.isEmpty or target.isVert

    @classmethod
    def DrawHighlight( cls , gizmo , element ) :
        return []

    def OnDraw( self , context  ) :
        if self.stroke2D :
            draw_util.draw_dot_lines2D( self.stroke2D , self.color_create() , 4 , pattern=(2,1) )        

    def OnDraw3D( self , context  ) :
#        self.activeTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )
        if self.startTargte.isVert :
            self.startTargte.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

#        draw_util.draw_lines3D( context , self.stroke3D  )

    def OnExit( self ) :
        pass

    def MakeQuad( self ) :
        targetLoops = self.FindTargetLoops()

        if len(targetLoops.keys()) != 1 :
            self.report_message = ("ERROR" , "Choose one boundary edge loop first.(loop count = %d )" %  len(targetLoops.keys()) )
            return

        targetLoop = list(targetLoops.values())[0]
        targetLoop, targetVerts = pqutil.sort_edgeloop(targetLoop)

        if (targetVerts[0].co - self.stroke3D[0]).length > (targetVerts[0].co - self.stroke3D[-1]).length :
            targetLoop.reverse()
            targetVerts.reverse()

        targetLengths = [ (e.verts[0].co-e.verts[1].co).length for e in targetLoop ]
        targetTotal = sum( targetLengths )
        targetRatio = [ t / targetTotal  for t in targetLengths ]

        divide = len(targetLoop)

        p1 =self.stroke3D[0]
        totalLen = 0
        for i in range(1,len(self.stroke3D)) :
            totalLen = totalLen + (p1 - self.stroke3D[i] ).length
            p1 =self.stroke3D[i]

        if ( totalLen <= 0.01 ) :
            return

        self.bmo.select_flush()

        targetSegment = 0
        segmentLen = targetRatio[0] * totalLen
        segment = 0
        newVerts = []
        if self.firstVert :
            newVerts.append( self.firstVert )
        else :
            newVerts.append( self.make_vert( targetVerts[0].co , self.stroke3D[0] ) )

        p1 =self.stroke3D[0]
        for i in range(1,len(self.stroke3D)) :
            p2 =self.stroke3D[i]
            length = (p1 - p2 ).length
            tmp = segment
            segment += length
            while segment >= segmentLen :
                t = ( segmentLen - tmp ) / length
                p1 = p2 * t + p1 * (1-t)
                if len(newVerts) >= divide and self.lastVert :
                    break
                newVerts.append( self.make_vert( targetVerts[targetSegment+1].co , p1 ) )
                tmp = 0
                length = (p1-p2).length
                segment -= segmentLen
                targetSegment += 1
                if targetSegment >= len(targetRatio) :
                    break
                segmentLen = targetRatio[targetSegment] * totalLen
            p1 =self.stroke3D[i]

        if len( newVerts ) <= divide :
            if self.lastVert :
                newVerts.append( self.lastVert )
            else :                
                newVerts.append( self.make_vert( targetVerts[-1].co , self.stroke3D[-1] ) )

        v1 = newVerts[0]
        newEdges = []
        for  i in range(1,len(newVerts)) :
            edge = self.bmo.add_edge( v1 , newVerts[i]  )
            self.bmo.select_component(edge)
            newEdges.append( edge )
            v1 = newVerts[i]

        self.bridge_loops(newEdges , targetLoop )

    #       self.bmo.select_components( newEdges , True )
        self.bmo.select_components( newVerts , True )
        self.bmo.UpdateMesh()

    def make_vert( self , src , tar ) :
        if not QSnap.is_active() :
            pl = pqutil.Plane.from_screen( bpy.context , src )
            pr = pqutil.Ray.from_world_to_screen( bpy.context , tar )
            pt = pl.intersect_ray( pr )
        else :
            pt = tar
        v = self.bmo.AddVertexWorld( pt )
        return v

    def bridge_loops( self , edge1 , edge2 ) :

        loopPair = copy.copy(edge1)
        loopPair.extend( edge2 )

        newFaces = bmesh.ops.grid_fill(self.bmo.bm, edges = loopPair, mat_nr = 0, use_smooth = False, use_interp_simple = False)
        if newFaces['faces'] :
            if QSnap.is_active() :
                vertsets = set()
                facesets = []
                for face in newFaces['faces'] :
                    facesets.append(face)
                    for vert in face.verts :
                        vertsets.add(vert)
#                bmesh.ops.join_triangles(self.bmo, faces = facesets)                        
                for vert in vertsets :
                    vert.normal_update()
                for vert in vertsets :
                    QSnap.adjust_by_normal( self.bmo.world_to_local_pos(vert.co) , self.bmo.world_to_local_nrm(vert.normal) )
#                    QSnap.adjust_point( self.bmo.world_to_local_pos(vert.co) )
        else :
            bmesh.ops.bridge_loops(self.bmo.bm, edges = loopPair, use_pairs = False, use_cyclic = False, use_merge = False, merge_factor = 0.0 , twist_offset = 0.0 )



    def FindTargetLoops( self) :
        selected ={ edge : -1 for edge in self.bmo.bm.edges if edge.select and (edge.is_boundary or edge.is_wire) }

        index = 0
        for edge in list( selected.keys() ) :
            if selected[edge] == -1 :
                selected[edge] = index
                for vert in edge.verts :
                    tar = edge
                    while tar :
                        boundarys = [ e for e in vert.link_edges if e != tar and e in selected.keys() and selected[e] == -1 ]
                        if len(boundarys) == 1 :
                            tar = boundarys[0]
                            vert = tar.other_vert(vert)
                            selected[tar] = index
                        else :
                            tar = None
                index += 1

        select_loops = {}
        for edge , idx in selected.items() :
            if idx not in select_loops.keys() :
                select_loops[idx] = []
            select_loops[idx].append(edge)

        return select_loops

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'