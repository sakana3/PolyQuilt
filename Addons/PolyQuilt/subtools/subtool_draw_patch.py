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
import copy
import itertools

from ..utils.dpi import display
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.mouse_event_util import MBEventType, MBEventResult
from .subtool import *
class SubToolDrawPatch(SubTool) :
    name = "DrawPatch Tool"

    def __init__(self,op,currentTarget, button) :
        super().__init__(op)        

        self.plane = self.default_plane

        self.stroke2D = [self.operator.start_mouse_pos]

        if QSnap.is_active() :
            coord = QSnap.screen_adjust(self.operator.start_mouse_pos)
            if not coord :
                ray = pqutil.Ray.from_screen( bpy.context , self.operator.start_mouse_pos )
                coord = self.plane.intersect_ray( ray )
        else :
            ray = pqutil.Ray.from_screen( bpy.context , self.operator.start_mouse_pos )
            coord = self.plane.intersect_ray( ray )

        self.stroke3D = [coord]

        self.currentTarget = ElementItem.Empty()

        self.connected_loop_1st = None
        self.connected_loop_2nd = None
        if self.startTarget.isVert :
            self.connected_loop_1st = self.fine_connected_loop( self.startTarget.element )
        self.is_loop_stroke = None

        self.view_vector = -bpy.context.region_data.view_matrix.inverted().col[2].xyz
        self.view_vector.normalize()

    def LMBEventCallback(self , event ):
        if event.type == MBEventType.Drag :
            if not self.is_loop_stroke :
                def check( target ) :
                    if target.isVert :
                        return target.element.select == False
                    return True
                self.currentTarget = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight , elements = ['VERT'] , check_func=check )
                if self.currentTarget.isVert :
                    self.connected_loop_2nd = self.fine_connected_loop( self.currentTarget.element )
                else :
                    self.connected_loop_2nd = None

                self.stroke2D.append( self.mouse_pos )
                ray = pqutil.Ray.from_screen( bpy.context , self.mouse_pos )
                coord = self.plane.intersect_ray( ray )
                if coord :
                    if QSnap.is_active() :
                        hit = QSnap.view_adjust(coord)
                        if hit :
                            coord = hit
                            self.plane = pqutil.Plane.from_screen( bpy.context , coord )
                    self.stroke3D.append( coord )
                if self.is_loop_stroke == None :
                    if (self.stroke2D[0] - self.stroke2D[-1] ).length > self.preferences.distance_to_highlight * 4 :
                        self.is_loop_stroke = False
                elif (self.stroke2D[0] - self.stroke2D[-1] ).length < self.preferences.distance_to_highlight * 2 :
                        self.stroke2D.append( self.stroke2D[0] )
                        self.stroke3D.append( self.stroke3D[0] )
                        self.is_loop_stroke = True
        elif event.type == MBEventType.Release :
            div , loop = self.MakeQuad( bpy.context , self.preferences.line_segment_length )
            self.operator.edge_divide = div if div != None else 0
            self.operator.redo_info = [ self.execute , [ x for x , t in zip( ['edge_divide' , 'edge_offset' ] ,[ div != None , loop ] ) if t ] ]
            return MBEventResult.Quit
        return MBEventResult.Do



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
            draw_util.draw_dot_lines2D( self.stroke2D , self.color_create() , 4 , pattern=(3,2) )       

        if self.connected_loop_1st : 
            draw_util.draw_dot_lines2D( [ self.bmo.local_to_2d( v.co ) for v in  self.connected_loop_1st ] , self.color_create(0.5) , 4 , pattern=(3,2) )       

        if self.connected_loop_2nd : 
            draw_util.draw_dot_lines2D( [ self.bmo.local_to_2d( v.co ) for v in  self.connected_loop_2nd ] , self.color_create(0.5) , 4 , pattern=(3,2) )       

        if self.is_loop_stroke :
            draw_util.draw_circle2D( self.stroke2D[0] , self.preferences.distance_to_highlight / 2 )

    def OnDraw3D( self , context  ) :
#        self.activeTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )
        if self.startTarget.isVert :
            self.startTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

        if self.currentTarget.isVert :
            self.currentTarget.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

#        draw_util.draw_lines3D( context , self.stroke3D  )

    def OnExit( self ) :
        pass

    def execute( self , context ) :
        self.bmo.CheckValid( context )
        self.startTarget.CheckValid( self.bmo )
        self.currentTarget.CheckValid( self.bmo )
        if self.startTarget.isVert :
            self.connected_loop_1st = self.fine_connected_loop( self.startTarget.element )
        if self.currentTarget.isVert :
            self.connected_loop_2nd = self.fine_connected_loop( self.currentTarget.element )
        self.MakeQuad( context , self.preferences.line_segment_length , divide = self.operator.edge_divide ,  offset = self.operator.edge_offset/ 100   )
        return 'FINISHED'

    def MakeStrokeLine( self , stroke ) :
        pass

    def MakeQuad( self , context , segment = 0.1 , divide = None , offset = 0 ) :
        div = None

        targetLoop, targetVerts , num = SubToolDrawPatch.find_target_loop( self.bmo.bm )
        if num > 1 :
            self.operator.report_message = ("WARNING" , "Choose one boundary edge path first." )
            return None , None

        if num == 0 :
            isLoop = self.is_loop_stroke
            loop = self.stroke3D
            if divide != None :
                div = divide
            else :            
                ttl = sum( (e1-e2).length for e1,e2 in zip( loop[ 0 : len(loop) - 1 ] , loop[ 1 : len(loop) ] ) )
                div = max( 1 , int( ttl / segment + 0.5 ) )
            div = max( 3 if isLoop else 1 , div )            
            pts = SubToolDrawPatch.make_loop_by_stroke( loop , [1] * div , offset = offset )
        else :
            isLoop = targetVerts[0] == targetVerts[-1]
            pts = SubToolDrawPatch.calc_new_points( self.stroke3D ,targetLoop ,targetVerts, offset )

        if isLoop :
            if len(pts) < 4 :
                return None , None
            pts = pts[0:-1]

        newVerts = []

        start = 0
        if not isLoop and self.startTarget.isVert :
            newVerts.append( self.startTarget.element )
            start = 1

        end = len(pts)
        endVert = None
        if not isLoop and self.currentTarget.isVert :
            end = len(pts) - 1
            endVert = self.currentTarget.element

        for p in pts[ start : end ] :
            v = self.make_vert( p , p )
            newVerts.append( v )

        if endVert :
            newVerts.append( endVert )

        if isLoop :
            newVerts.append( newVerts[0] )

        self.bmo.select_flush()
        newEdges = []
        for  v1,v2 in zip( newVerts[0: -1] , newVerts[1:len(newVerts)] ) :
            edge = self.bmo.add_edge( v1 , v2 )
            newEdges.append( edge )

        self.bmo.select_components(newEdges , True)
        self.bmo.select_components(newVerts , True)
        self.bmo.bm.select_flush(True)
        
        if num == 1 :
            if not isLoop :
                if self.connected_loop_1st and not self.currentTarget.isVert :
                    _ , self.connected_loop_2nd = self.add_auxiliary_Edge( self.connected_loop_1st , targetVerts , newVerts )
                elif self.connected_loop_2nd and not self.startTarget.isVert :
                    _ , self.connected_loop_1st  = self.add_auxiliary_Edge( self.connected_loop_2nd , targetVerts , newVerts )
            div = SubToolDrawPatch.bridge_loops( self.bmo , 
                newEdges , targetLoop , self.connected_loop_1st , self.connected_loop_2nd , 
                view_vector= self.view_vector, segment = segment , divide= divide )

        self.bmo.select_components( newEdges , True )
        self.bmo.bm.select_flush(True)
        self.bmo.UpdateMesh()
        return div , isLoop

    def add_auxiliary_Edge( self , connected_loop ,targetVerts , newVerts ) :
        '''
        補助線を足す
        '''

        if newVerts[0] in connected_loop :
            s = self.stroke3D[-1]
            e = targetVerts[-1] if targetVerts[0] == connected_loop[-1] else targetVerts[0]
            pts = [newVerts[-1]]
        else :
            s = self.stroke3D[0]
            e = targetVerts[0] if targetVerts[-1] == connected_loop[-1] else targetVerts[-1]
            pts = [newVerts[0]]

        l2w = self.bmo.local_to_world_pos
        w2l = self.bmo.world_to_local_pos

        lengths = [ ( l2w(p1.co)-l2w(p2.co)).length for p1, p2 in zip(connected_loop[0:-1] , connected_loop[1:len(connected_loop)])  ]
        total = sum(lengths)
        ratios = [ l / total for l in lengths]
        num = len(connected_loop) - 1
        ratio = 0
        for i,l in zip( range( 1 , num ) , ratios ) :
            ratio = ratio + l
            x = s.lerp( e.co , ratio)
            t = self.bmo.AddVertex( w2l(x) )
            pts.append( t )
        pts.append( e )

        ret = []
        for p1 , p2 in zip( pts[ 0 : len(pts) - 1 ] ,pts[ 1 : len(pts) ] ) :
            ret.append( self.bmo.add_edge( p1 , p2 ) )
        return ret , pts

    def make_vert( self , src , tar ) :
        if not QSnap.is_active() :
            pl = pqutil.Plane.from_screen( bpy.context , src )
            pr = pqutil.Ray.from_world_to_screen( bpy.context , tar )
            pt = pl.intersect_ray( pr )
        else :
            pt = tar
        v = self.bmo.AddVertexWorld( pt )
        return v

    def check_connnected_loop( self , startVert , targetVerts ) :
        def find( edge , vert ) :
            cur_edge = edge
            cur_vert = vert
            ret = []
            while( cur_edge and cur_edge not in ret ) :
                ret.append(cur_edge)
                cur_vert = cur_edge.other_vert(cur_vert)
                if cur_vert in targetVerts :
                    break
                candidate = [ e for e in cur_vert.link_edges if e != cur_edge and ((cur_edge.is_boundary and e.is_boundary) or (cur_edge.is_wire and e.is_wire)) ]
                if len(candidate) == 1 :
                    cur_edge = candidate[0]
                else :
                    cur_edge = None
            else :
                return []
            return ret

        loops = [ find( e , startVert ) for e in startVert.link_edges ]
        loops = { len(e) : e for e in loops if e }
        loops = sorted( loops.items() )
        if len(loops) :
            return loops[0][1]

        return None

    def fine_connected_loop( self , vert ) :
        targetLoop, targetVerts , num = SubToolDrawPatch.find_target_loop( self.bmo.bm )     
        connected_loop = None
        if num == 1 :
            connected_loop = self.check_connnected_loop( vert , targetVerts )
            if connected_loop:
                _ , connected_loop = pqutil.sort_edgeloop(connected_loop )
                if connected_loop[0] in targetVerts :
                        connected_loop.reverse()
        return connected_loop        

    @staticmethod
    def adjust_faces_normal( bmo , faces , view_vector ) :
        cnt = 0
        for face in faces :
            face.normal_update()
            normal = face.normal
            if QSnap.is_active() :
                center = face.calc_center_median()
                snappos , snapnrm = QSnap.adjust_by_normal( bmo.local_to_world_pos(center) , bmo.local_to_world_nrm(normal) )
                cnt = cnt + (1 if snapnrm.dot(normal) > 0 else -1)
            elif view_vector != None :
                cnt = cnt - (1 if view_vector.dot(normal) > 0 else -1)
        if cnt < 0 :
            for face in faces :
                face.normal_flip()

    @staticmethod
    def bridge_loops( bmo , edge1 , edge2 , connect1 = None , connect2 = None , view_vector = None , segment = None, divide = None ) :
        bmo.bm.edges.index_update()
        loopPair = copy.copy(edge1)
        loopPair.extend( edge2 )

        is_wire = all( e.is_wire for e in edge1 + edge2 + (connect1 if connect1 != None else []) + (connect2 if connect2 != None else [])  )
#        is_loop = edge1[0].verts[0] in edge1[-1].verts or edge1[0].verts[1] in edge1[-1].verts

        hides = []
        if connect1 != None and connect2 != None :
            verts = set()
            allverts = set( itertools.chain( connect1 if connect1 != None else [] , connect2 if connect2 != None else [] ) )
            for e in itertools.chain( edge1 , edge2) :
                allverts.update( tuple(e.verts) )
            for v in allverts :
                for t in [ e.other_vert( v ) for e in  v.link_edges ] :
                    if not t.hide and t not in verts :
                        t.hide_set(True)
                        hides.append(t)

        newGeoms = bmesh.ops.grid_fill( bmo.bm, edges = loopPair, mat_nr = 0, use_smooth = False, use_interp_simple = True)
        newFaces = newGeoms['faces']

        if not newFaces and connect1 and connect2 :
            connect1 = [ bmo.bm.edges.get( (v1 , v2)) for v1 , v2 in zip( connect1[0 : -1] , connect1[1 : ] ) ]
            connect2 = [ bmo.bm.edges.get( (v1 , v2)) for v1 , v2 in zip( connect2[0 : -1] , connect2[1 : ] ) ]
            loopPair1 = copy.copy(connect1)
            loopPair1.extend( connect2 )
            newGeoms = bmesh.ops.grid_fill( bmo.bm, edges = loopPair1, mat_nr = 0, use_smooth = False, use_interp_simple = True)
            newFaces = newGeoms['faces']

        for hide in hides :
            hide.hide_set(False)

        if newFaces :
            if QSnap.is_active() :
                vertsets = set()
                facesets = []
                for face in newFaces :
                    facesets.append(face)
                    for vert in face.verts :
                        vertsets.add(vert)
#                bmesh.ops.join_triangles(self.bmo, faces = facesets)                        
                for vert in vertsets :
                    vert.normal_update()
                for vert in vertsets :
                    wp , _ = QSnap.adjust_by_normal( bmo.local_to_world_pos(vert.co) , bmo.local_to_world_nrm(vert.normal) )
                    vert.co = bmo.world_to_local_pos(wp)
                if is_wire :
                    SubToolDrawPatch.adjust_faces_normal( bmo , newFaces , view_vector )
        else :
            Geom = bmesh.ops.bridge_loops(bmo.bm, edges = loopPair, use_pairs = False, use_cyclic = False, use_merge = False, merge_factor = 0.0 , twist_offset = 0 )
            newFaces = Geom['faces']
            if segment != None and divide == None :
                lengths = [ ( bmo.local_to_world_pos( e.verts[0].co ) - bmo.local_to_world_pos( e.verts[1].co )).length for e in Geom['edges'] ]
                avarage = sum(lengths) / len(lengths)
                divide = max( 0 , int( avarage / segment ) )
            if is_wire :
                SubToolDrawPatch.adjust_faces_normal( bmo , newFaces , view_vector )

            if divide :
                #bmesh.ops.subdivide_edges(bm, edges, smooth, smooth_falloff, fractal, along_normal, cuts, seed, custom_patterns, edge_percents, quad_corner_type, use_grid_fill, use_single_edge, use_only_quads, use_sphere, use_smooth_even
                div = bmesh.ops.subdivide_edges( bmo.bm , edges = Geom['edges'] , smooth = 1.0 , cuts = divide , use_grid_fill=True )
                newFaces = [ f for f in div['geom_split'] if isinstance( f , bmesh.types.BMFace ) ]
                if QSnap.is_active() :
                    vs = [ t for t in div['geom_inner'] if isinstance( t , bmesh.types.BMVert ) ]
                    for v in vs  :
                        v.normal_update()
                    for v in vs  :
                        wp , _ = QSnap.adjust_by_normal( bmo.local_to_world_pos(v.co) , bmo.local_to_world_nrm(v.normal) )
                        v.co = bmo.world_to_local_pos(wp)

        return divide

    @staticmethod
    def find_target_loop( bm ) :
        selected = [ edge for edge in bm.edges if edge.select and (edge.is_boundary or edge.is_wire) ]
        targetLoops = pqutil.grouping_loop_edge( selected )

        if len(targetLoops) != 1 :
            return None , None , len(targetLoops)

        targetLoop = targetLoops[0]
        targetLoop, targetVerts = pqutil.sort_edgeloop(targetLoop)

        return  targetLoop, targetVerts , 1

    @staticmethod
    def calc_new_points( stroke , edges , verts, offset =0 ) :
        '''
        新しいポイントを作る
        '''
        isLoop = verts[0] == verts[-1]
        if isLoop :
            # 一番近い点に移動する
            lens = [ (s-verts[0].co).length for s in stroke ]
            idx = lens.index( min(lens) )
            for i in range(0,idx) :
                t = stroke[0]
                stroke.pop(0)
                stroke.append( t )
            stroke.append( stroke[0] )

            loop = [ e.calc_length() for e in edges ]
            pts1 = SubToolDrawPatch.make_loop_by_stroke( stroke , loop , offset )
            pts2 = SubToolDrawPatch.make_loop_by_stroke( list(reversed(stroke)) , loop , offset )

            if ( pts1[1] - verts[1].co ).length < ( pts2[1] - verts[1].co ).length :
                pts = pts1
            else :
                pts = pts2
        else :
            if (verts[0].co - stroke[0]).length > (verts[0].co - stroke[-1]).length :
                edges.reverse()
                verts.reverse()
            pts = SubToolDrawPatch.make_loop_by_stroke( stroke , [ ( e.verts[0].co - e.verts[1].co ).length for e in edges ] , offset )

        return pts


    @staticmethod
    def make_loop_by_stroke( stroke , targets , offset = 0 ) :
        isLoop = (stroke[0] - stroke[-1]).length <= sys.float_info.epsilon

        stroke_length = [ ( s - e ).length for s,e in zip( stroke[0: -1] , stroke[1: ] ) ]

        stroke_total  = sum( stroke_length )
        targets_total = sum( targets )
        segments = [ t / targets_total * stroke_total for t in targets ]

        if isLoop :
            stroke = stroke[0:] + stroke[1 : ]
            stroke_length = stroke_length + stroke_length[1 : ]

        offset =  ((offset % 1.0) + 1.0) % 1.0
        offset = offset * stroke_total
        retPositions = []
        cur = 0
        segment = - offset
        segmentLen = 0
        for pre ,pos , length in zip( stroke[0:-1] , stroke[1:] , stroke_length ) :
            tmp = segment
            segment = segment + length
            while segment >= segmentLen :
                if length > sys.float_info.epsilon :
                    pre = pre.lerp( pos , ( segmentLen - tmp ) / length )
                else :
                    pre = pos
                retPositions.append(pre)
                segment = segment - segmentLen
                tmp = 0
                length = (pre-pos).length
                segmentLen = segments[cur % len(segments) ]
                cur += 1
            if cur > len(segments) :
                break

        if len(retPositions) < len(targets) + 1 :
            retPositions.append( stroke[-1] )
        return retPositions


    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'