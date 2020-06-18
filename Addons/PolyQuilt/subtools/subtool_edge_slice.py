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
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubTool

class SubToolEdgeSlice(SubTool) :
    name = "SliceTool"

    def __init__(self,op, target , mouse_pos ) :
        super().__init__(op)
        self.currentTarget = target
        self.currentEdge = target.element
        l0 = (self.bmo.local_to_world_pos(target.element.verts[0].co) - target.hitPosition).length
        l1 = (self.bmo.local_to_world_pos(target.element.verts[1].co) - target.hitPosition).length
        self.reference_point = 0 if l0 > l1 else 1
        self.fixCenter = False
        self.split_deges , self.draw_deges , self.endTriangles , self.fixCenter = self.CalcSlice( self.bmo , self.currentEdge)
        self.is_forcus = True
        self.sliceRate = self.CalcSplitRate( bpy.context , mouse_pos , self.currentEdge )

    def Check( root , target ) :
        if target.isEdge :
            if ( target.world_co[0] - target.world_co[1] ).length <= sys.float_info.epsilon :
                return False
            co = target.world_co
            sliceRate = ( co[0] - target.hitPosition ).length / ( co[0] - co[1] ).length
            if sliceRate >= 0.02 and sliceRate < 0.98 :
                return True

        return False

    @classmethod
    def DrawHighlight( cls , gizmo , target : ElementItem ) :
        mode = gizmo.get_attr("loopcut_mode")

        if target != None and gizmo.bmo != None :
            split_deges , draw_deges , endTriangles , fixCenter = cls.CalcSlice( gizmo.bmo , target.element )
            co = target.world_co

            l0 = (gizmo.bmo.local_to_world_pos(target.element.verts[0].co) - target.hitPosition).length
            l1 = (gizmo.bmo.local_to_world_pos(target.element.verts[1].co) - target.hitPosition).length
            reference_point = 0 if l0 > l1 else 1

            sliceRate = ( co[0] - target.hitPosition ).length / ( co[0] - co[1] ).length
            func = cls.DrawFunc( gizmo.bmo , target , draw_deges , sliceRate , gizmo.preferences , mode , reference_point )
            def draw() :
                func()           
                with draw_util.push_pop_projection2D() :
                    draw_util.DrawFont( '{:.2f}'.format(sliceRate) , 10 , target.coord , (0,2) )           
            return draw

        return None

    @classmethod
    def DrawFunc( cls , bmo , currentEdge , cut_deges , sliceRate : float , preferences , mode , reference_point ) :
        if sliceRate > 0 and sliceRate < 1 :
            def color_split( alpha = 1.0 ):
                col = preferences.split_color            
                return (col[0],col[1],col[2],col[3] * alpha )
            def calc_slice_rate( edge , refarence , rate ) :
                return SubToolEdgeSlice.calc_slice_rate( currentEdge.element , reference_point , edge , refarence , rate , mode )

            size = preferences.highlight_vertex_size          
            width = preferences.highlight_line_width
            alpha = preferences.highlight_face_alpha
            pos = currentEdge.verts[0].co + ( currentEdge.verts[1].co- currentEdge.verts[0].co) * sliceRate
            pos = bmo.local_to_world_pos( pos )

            lines = []
            for cuts in cut_deges :
                v0 = cuts[0].verts[0].co.lerp( cuts[0].verts[1].co , calc_slice_rate( cuts[0] , cuts[2] , sliceRate ) )
                v1 = cuts[1].verts[0].co.lerp( cuts[1].verts[1].co , calc_slice_rate( cuts[1] , cuts[3] , sliceRate ) )
                v0 = bmo.local_to_world_pos( v0 )
                v1 = bmo.local_to_world_pos( v1 )
                lines.append(v0)
                lines.append(v1)
            
            snaps = []
            for i in range( preferences.loopcut_division ) :
                r = (i+1.0) / ( preferences.loopcut_division + 1.0)
                snaps.append( bmo.local_to_world_pos( currentEdge.verts[0].co.lerp( currentEdge.verts[1].co , r) ) )

            def Draw() :
                draw_util.draw_pivots3D( (pos,) , preferences.highlight_vertex_size , color_split(0.5) )
                if lines :
                    draw_util.draw_lines3D( bpy.context , lines , color_split() , preferences.highlight_line_width , 1.0 , primitiveType = 'LINES'  )
                if snaps :
                    draw_util.draw_pivots3D( snaps , 0.75 , color_split(0.25) )

            return Draw

        def Noting() :
            pass
        return Noting


    def OnForcus( self , context , event  ) :
        if event.type == 'MOUSEMOVE':        
            self.sliceRate = self.CalcSplitRate( context ,self.mouse_pos , self.currentEdge )
        return self.is_forcus

    def OnUpdate( self , context , event ) :
        if event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.sliceRate > 0 and self.sliceRate < 1 :
                    self.DoSlice(self.currentEdge , self.sliceRate )
                    return 'FINISHED'
                return 'CANCELLED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.DrawFont( '{:.2f}'.format(self.sliceRate) , 10 , self.mouse_pos , (0,2) )                   

    def OnDraw3D( self , context  ) :
        if self.currentTarget.isEdge :
            func = SubToolEdgeSlice.DrawFunc( self.bmo , self.currentTarget , self.draw_deges , self.sliceRate , self.preferences , self.operator.loopcut_mode , self.reference_point )
            func()
    @staticmethod
    def calc_slice_rate( currentEdge , reference_point , edge , refarence , rate , mode ) :
        if mode == 'EVEN' :
            len0 = currentEdge.calc_length()
            len1 = edge.calc_length()
            if reference_point == 0 :
                rate = 1 - max( min( ( (len0 / len1) * (1-rate) ) , 1.0 ) , 0.0 )
            else :
                rate = max( min( ( len0 / len1 * rate ) , 1.0 ) , 0.0 )
        return rate if refarence == 0 else 1.0 - rate

    def CalcSplitRate( self , context ,coord , baseEdge ) :
        p0 = baseEdge.verts[0].co
        p1 = baseEdge.verts[1].co
        val = None
        dst = 10000000
        for i in range(self.preferences.loopcut_division ) :
            r = (i+1.0) / (self.preferences.loopcut_division + 1.0)
            v = self.bmo.local_to_2d( p0.lerp( p1 , r ) )
            l = ( coord - v ).length
            if l <= self.preferences.distance_to_highlight* dpm() :
                if dst > l :
                    dst = l
                    val = r
        if val :
            return val

        ray = pqutil.Ray.from_screen( context , coord ).world_to_object( self.bmo.obj )
        dist = self.preferences.distance_to_highlight* dpm()
        d = pqutil.CalcRateEdgeRay( self.bmo.obj , context , baseEdge , baseEdge.verts[0] , coord , ray , dist )

        self.is_forcus = d > 0 and d < 1

        if self.fixCenter :
            return 0.5

        return d

    @classmethod
    def CalcSlice( cls , bmo , currentEdge ) :
        check_edges = []
        draw_deges = []
        split_deges = []
        endTriangles = {}
        fixCenter = False

        startEdges = [ (currentEdge,0) ]

        if bmo.is_mirror_mode :
            mirrorEdge = bmo.find_mirror(currentEdge,False)
            if mirrorEdge is not None :
                if mirrorEdge != currentEdge :
                    mirrorVert = bmo.find_mirror(currentEdge.verts[0])
                    startEdges.append( (mirrorEdge, 0 if mirrorEdge.verts[0] == mirrorVert else 1 ) )
                else :
                    fixCenter = True

        for startEdge in startEdges :
            if len(startEdge[0].link_faces) > 2 :
                continue
            for startFace in startEdge[0].link_faces :

                vidx = startEdge[1]
                face = startFace
                edge = startEdge[0]
                for i in range(0,4096) :              
                    if( face == None or edge == None  ) :
                        break

                    if edge.index not in check_edges :
                        check_edges.append(edge.index)
                        split_deges.append( (edge ,vidx ) )

                    if len( face.loops ) != 4 :
                        if len( face.loops ) == 3 :
                            if face not in endTriangles :
                                endTriangles[face] = (edge.verts[0].index,edge.verts[1].index , [ v for v in face.verts if v not in edge.verts ][0].index )
                            else :
                                endTriangles[face] = None
                        break

                    loop = [ l for l in face.loops if l.edge == edge ][-1]
                    opposite = loop.link_loop_next.link_loop_next
                    pidx = 1 if ( loop.vert == edge.verts[vidx]) == (opposite.edge.verts[0] == opposite.vert) else 0                    
                    draw_deges.append( (loop.edge,opposite.edge ,vidx , pidx ) )
                    vidx = pidx

                    if len( opposite.edge.link_faces ) == 2 :
                        face = [ f for f in opposite.edge.link_faces if f != face ][-1]
                        edge = opposite.edge
                    else :
                        if opposite.edge.index not in check_edges :                        
                            split_deges.append( (opposite.edge ,vidx ) )
                            check_edges.append( opposite.edge.index )
                        break

                    if startEdge[0].index == edge.index :
                        break
               

        return split_deges , draw_deges , endTriangles , fixCenter

    def DoSlice( self , startEdge , sliceRate ) :
        edges = []
        _slice = {}
        for split_dege in self.split_deges :
            edges.append( split_dege[0] )
            _slice[ split_dege[0] ] = SubToolEdgeSlice.calc_slice_rate( self.currentEdge ,self.reference_point, split_dege[0] , split_dege[1] , sliceRate , self.operator.loopcut_mode )

        ret = bmesh.ops.subdivide_edges(
             self.bmo.bm ,
             edges = edges ,
             edge_percents  = _slice ,
             smooth = 0 ,
             smooth_falloff = 'SMOOTH' ,
             use_smooth_even = False ,
             fractal = 0.0 ,
             along_normal = 0.0 ,
             cuts = 1 ,
             quad_corner_type = 'PATH' ,
             use_single_edge = False ,
             use_grid_fill=True,
             use_only_quads = True ,
             seed = 0 ,
             use_sphere = False 
        )

        bpy.ops.mesh.select_all(action='DESELECT')
        for e in ret['geom_inner'] :
            e.select_set(True)

        if QSnap.is_active() :
            QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_inner'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

        if  bpy.context.scene.tool_settings.use_mesh_automerge or True :
            verts = set()

            for e in ret['geom'] :
                if isinstance( e, bmesh.types.BMVert ) :
                    verts.add( e )
                elif isinstance( e, bmesh.types.BMEdge ) :
                    verts.add( e.verts[0] )
                    verts.add( e.verts[1] )
            bmesh.ops.remove_doubles( self.bmo.bm , verts =  list(verts) , dist = bpy.context.scene.tool_settings.double_threshold )

        self.bmo.UpdateMesh()

#bmesh.ops.smooth_vert（bm、verts、factor、mirror_clip_x、mirror_clip_y、mirror_clip_z、clip_dist、use_axis_x、use_axis_y、use_axis_z ）
