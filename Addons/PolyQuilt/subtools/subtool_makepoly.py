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
from ..mouse_event_util import ButtonEventUtil, MBEventType
from .subtool import SubTool
from ..dpi import *

class SubToolMakePoly(SubTool) :
    name = "MakePolyTool"

    def __init__(self,op,startElement , mouse_pos ) :
        super().__init__(op)        
        self.mekePolyList = []

        if self.operator.plane_pivot == 'OBJ' :
            self.pivot = self.bmo.obj.location
        elif self.operator.plane_pivot == '3D' :
            self.pivot = bpy.context.scene.cursor.location
        elif self.operator.plane_pivot == 'Origin' :
            self.pivot = (0,0,0)

        if startElement.isEmpty :
            vert = self.bmo.AddVertexFromRegionCoord( mouse_pos , self.pivot )
            self.currentTarget = ElementItem( vert , mouse_pos , vert.co , 0 ); 
            self.bmo.UpdateMesh()
        elif startElement.isEdge :
            edge , vert = self.bmo.edge_split_from_position( startElement.element , startElement.hitPosition )
            self.currentTarget = ElementItem( vert , mouse_pos , vert.co , 0 )
            self.bmo.UpdateMesh()
        else :            
            self.currentTarget = startElement
        self.mekePolyList.append( self.currentTarget.element )
        self.targetElement = None
        self.isEnd = False
        self.LMBEvent = ButtonEventUtil('LEFTMOUSE' , self , SubToolMakePoly.LMBEventCallback , op.preferences )
        self.mode = op.geometry_type
        self.EdgeLoops = None
        if self.mode == 'VERT' :
            self.isEnd = True

    @staticmethod
    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Down :
            pass
        elif event.type == MBEventType.Release :
            if self.currentTarget.element == self.mekePolyList[-1] :
                self.isEnd = True
            else :
                if self.EdgeLoops != None :
                    self.DoEdgeLoopsRemove( self.EdgeLoops )
                    self.isEnd = True       
                elif self.currentTarget.isEdge :
                    edge , vert = self.bmo.edge_split_from_position( self.currentTarget.element , self.currentTarget.hitPosition )
                    self.currentTarget = ElementItem( vert , self.mouse_pos , vert.co , 0 )
                    self.isEnd = self.AddVert(self.currentTarget.element ) == False
                elif self.currentTarget.isEmpty :
                    pivot = self.pivot
                    if self.mekePolyList :
                        pivot = self.bmo.obj.matrix_world @ self.mekePolyList[-1].co
                    addVert = self.bmo.AddVertexFromRegionCoord( self.mouse_pos , pivot )
                    self.currentTarget = ElementItem( addVert , self.mouse_pos , addVert.co , 0.0 )
                    self.bmo.UpdateMesh()
                if self.currentTarget.isVert :
                    if self.currentTarget.element not in self.mekePolyList :
                        self.isEnd = self.AddVert(self.currentTarget.element ) == False
        elif event.type == MBEventType.Click :            
            pass
        elif event.type == MBEventType.LongPress :
            if len(self.mekePolyList) <= 1 and self.currentTarget.isVert and self.mekePolyList[-1] != self.currentTarget.element :
                edge = self.bmo.edges.get( (self.mekePolyList[0] , self.currentTarget.element) )
                if edge != None :
                    self.EdgeLoops = self.SelectEdgeLoops( edge )
        elif event.type == MBEventType.LongClick :
            if len(self.mekePolyList) <= 1 :
                self.mode = 'EDGE'
        elif event.type == MBEventType.Move :
            tmp = self.currentTarget
            ignore = []
            if isinstance( self.targetElement , bmesh.types.BMFace ) :
                ignore = self.targetElement.edges
            elif isinstance( self.targetElement , bmesh.types.BMEdge ):
                ignore = [ self.targetElement ]
            self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , ignore=ignore )
            if tmp != self.currentTarget :
                self.EdgeLoops = None
            if (self.currentTarget.isVert or self.currentTarget.isEdge ) is False :
                self.currentTarget = ElementItem.Empty()

    def OnUpdate( self , context , event ) :
        self.LMBEvent.Update( context , event )

        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE' :
            self.isEnd = True

        if self.isEnd == True :
            return 'FINISHED'

        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        l = len(self.mekePolyList)
        vs = [ i.region for i in handleutility.TransformBMVerts(self.bmo.obj,self.mekePolyList) ]
        lp = self.mouse_pos if self.currentTarget.isEmpty else self.currentTarget.coord
        vs.append( lp )

        color = self.color_create()
        if l == 1:
            text = None
            same_edges , same_faces = self.CheckSameFaceAndEdge( self.mekePolyList[0] , self.currentTarget.element )
            if same_edges :
                if len(same_faces) > 1 :
                    if self.LMBEvent.presureComplite :
                        color = self.color_delete()
                    else :
                        color = self.color_delete()
                    text = "Edge Loop"
            elif same_faces :
                color = self.color_split()
            else :
                text = "Line"                    
            draw_util.draw_lines2D( vs , color , self.preferences.highlight_line_width  )
            if text != None :
                self.LMBEvent.Draw( self.currentTarget.coord , text )
        elif l > 1:
            vs.append( vs[0] )
            draw_util.draw_lines2D( vs , self.color_create() , self.preferences.highlight_line_width  )

        if self.currentTarget.isNotEmpty :
            self.currentTarget.Draw2D( self.bmo.obj , self.color_highlight() , self.preferences )

            draw_util.draw_pivot2D( lp , self.preferences.highlight_vertex_size , color )

            if self.currentTarget.element == self.mekePolyList[-1] :
                draw_util.draw_pivot2D(  lp , self.preferences.highlight_vertex_size * 1.5 , self.color_create() , True )
            elif self.currentTarget.element in self.mekePolyList:
                draw_util.draw_pivot2D(  lp , self.preferences.highlight_vertex_size * 1.5 , self.color_delete() , True )
        else :
            draw_util.draw_pivot2D( lp , self.preferences.highlight_vertex_size , self.color_create() )

        draw_util.drawElementsHilight( self.bmo.obj , self.mekePolyList , self.preferences.highlight_vertex_size , self.color_create() )

        if self.EdgeLoops != None :
            draw_util.drawElementsHilight( self.bmo.obj , self.EdgeLoops , self.preferences.highlight_vertex_size , self.color_delete() )

    def AddVert( self , vert ) :
        ret = True
        if vert not in self.mekePolyList :
            self.mekePolyList.append(vert)
            ret = True
            pts = len( self.mekePolyList )

            # 既に存在する辺ならExit
            if pts > 2 :
                edge = self.bmo.edges.get( ( self.mekePolyList[0] , self.mekePolyList[-1] ) )
                if edge != None :
                    ret = False
            if pts == 2 :
                same_edges , same_faces = self.CheckSameFaceAndEdge(self.mekePolyList[-2] , self.mekePolyList[-1])

                if same_edges :
                    if len(same_faces) > 1 :
#                       bmesh.utils.vert_separate( vert , same_edges )
                        self.bmo.dissolve_edges( edges = same_edges , use_verts = False , use_face_split = False )
                        self.bmo.UpdateMesh()
                        self.mekePolyList = [ self.mekePolyList[-1] ] 
                elif same_faces:
                    for face in same_faces :
                        self.bmo.face_split( face , self.mekePolyList[-2] , self.mekePolyList[-1] )
                        self.bmo.UpdateMesh()
                    self.mekePolyList = [ self.mekePolyList[-1] ]                        
                else :
                    edge = self.bmo.edges.get( (self.mekePolyList[-2],self.mekePolyList[-1]) )
                    edge = edge if edge != None else self.bmo.AddEdge( self.mekePolyList[-2] , self.mekePolyList[-1] )
#                    edge.select = True
                    self.targetElement = edge
                    self.bmo.UpdateMesh()
            elif pts == 3 :
                face = self.bmo.AddFace( self.mekePolyList , handleutility.getViewDir() )
#                face.select = True
                self.bmo.UpdateMesh()
                self.targetElement = face
            elif pts > 3:
#               self.bmo.Remove( self.targetElement )
                edge = self.bmo.edges.get( ( self.mekePolyList[0] , self.mekePolyList[-2] ) )
                if edge != None :
                    self.bmo.Remove( edge )
                self.targetElement = self.bmo.AddFace( self.mekePolyList, handleutility.getViewDir()  )
                self.bmo.UpdateMesh()
#            edge = self.bm.edges.get( (self.mekePolyList[0], self.mekePolyList[-2] ))
#            if edge is not None :
#                self.targetElement = bmesh.utils.edge_split(edge, edge.verts[0] , 0.5)[0]
#                bmesh.update_edit_mesh(self.mesh)

        if self.mode == 'TRI' and pts == 3 :
            ret = False

        if self.mode == 'QUAD' and pts == 4 :
            ret = False

        if self.mode == 'EDGE' :
            self.mekePolyList = [ self.mekePolyList[-1] ]

        return ret

    def CheckSameFaceAndEdge( self , v0 , v1 ) :
        same_edges = []
        same_faces = []
        if isinstance( v0,bmesh.types.BMVert ) :
            if isinstance( v1,bmesh.types.BMVert ) :
                same_edges = list( set(v0.link_edges) & set(v1.link_edges) )
                same_faces = list( set(v0.link_faces) & set(v1.link_faces) )
            elif  isinstance( v1,bmesh.types.BMEdge ) :
#               same_edges = [] if v1 in v0.link_edges else [v1]
                same_faces = list( set(v0.link_faces) & set(v1.link_faces) )
        return same_edges , same_faces

    def SelectEdgeLoops( self , startEdge ) :
        results = [startEdge]
        for vert in startEdge.verts :
            preEdge = startEdge
            currentV = vert
            while len(currentV.link_faces) == 4 :
                fs = { i for i in currentV.link_faces}.intersection( { i for i in preEdge.link_faces } )
                ff = list( { i for i in currentV.link_faces}.difference(fs) )
                if len(ff) != 2 and currentV not in ff:
                    break
                nexE = list({ i for i in ff[0].edges }.intersection( {i for i in ff[1].edges} ))
                if len(nexE) != 1 :
                    break
                preEdge = nexE[0]
                currentV = preEdge.other_vert(currentV)
                if preEdge in results:
                    break
                results.append(preEdge)

        return results

    def DoEdgeLoopsRemove( self , edges ) :
        self.bmo.dissolve_edges( edges = edges , use_verts = True , use_face_split = True )        
        self.bmo.UpdateMesh()             
        self.currentTarget = ElementItem.Empty()
        