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
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from .utils import pqutil
import bmesh
import mathutils

class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a new Empty Mesh Object"""
    bl_idname = "mesh.add_empty_mesh_object"
    bl_label = "Add Empty Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context , event):
        mesh = bpy.data.meshes.new(name="New Empty Mesh")
        object_data_add(context, mesh, operator=self)
        return {'FINISHED'}

def add_object_button(self, context):
    self.layout.operator(
        OBJECT_OT_add_object.bl_idname,
        text="Empty Mesh Object",
        icon='EMPTY_DATA')

class MESH_OT_PolyQuilt_Gpenci_Tools(Operator) :
    """PolyQuilt Gpencil Tool """
    bl_idname = "mesh.polyquilt_gpencil_tool"
    bl_label = "Add X Tomography"
    bl_options = {'REGISTER', 'UNDO'}

    type : bpy.props.EnumProperty(
        name="Type",
        description="Type",
        options = {'HIDDEN'} ,
        items=[('NEW' , "NEW", "" , "COLLECTION_NEW" , 0),
               ('ADD_TOMOGRAPHY' , "", "" , "ADD" , 1 ),
               ('ADD_BOUNDARY' , "", "" , "ADD" , 2 ),
               ('ADD_PITS_AND_PEAKS' , "", "" , "ADD" , 3 ),
               ('REMOVE' , "REMOVE", "" , "REMOVE" , 4 ) ],
        default='NEW',
    )

    def invoke(self, context , event):
        if self.type == 'REMOVE' :
            gp = context.scene.grease_pencil            
            if gp:
                layer = self.get_gp_layer( context , "PolyQuilt_GPencil" )
                gp.layers.remove( layer )
                layer = self.get_gp_layer( context , None )

        else :
            layer = self.get_gp_layer( context , "PolyQuilt_GPencil" )
            frame = self.get_gp_frame( layer )

            layer.color = (0.2,0.2,0.5)
            layer.annotation_opacity = 0.5
            layer.thickness = 2

            # Get Frame
            if self.type == 'NEW' :
                for stroke in list( frame.strokes ) :
                    frame.strokes.remove(stroke)

            if self.type == 'ADD_TOMOGRAPHY' :
                self.add_tomography(context , frame)

            if self.type == 'ADD_BOUNDARY' :
                self.add_boundary(context , frame)

            if self.type == 'ADD_PITS_AND_PEAKS' :
                self.add_pits_and_peaks(context , frame)

        return {'FINISHED'}

    def add_tomography(self , context , frame ) :
        lines = self.get_lines( context )

        for line in lines :
            stroke = frame.strokes.new()
            stroke.points.add( len(line) )
            for sp , lp in zip( stroke.points , line ) :
                sp.co = lp
            stroke.points.update()

    def add_boundary(self , context , frame ) :
        lines = self.get_boundary( context )
        self.draw_lines( frame , lines )

    def add_pits_and_peaks(self , context , frame ) :
        lines = self.get_pits_and_peaks( context , 170 )
        self.draw_lines( frame , lines )

    def draw_lines( self , frame , lines ) :
        for line in lines :
            stroke = frame.strokes.new()
            stroke.points.add( len(line) )
            for sp , lp in zip( stroke.points , line ) :
                sp.co = lp
            stroke.points.update()

    @staticmethod
    def get_gp_layer( context , layer_name = "PolyQuilt_GPencil" ) :
        gp = context.scene.grease_pencil
        if not gp:
            gp = bpy.data.grease_pencils.new("GP")
            context.scene.grease_pencil = gp

        layer = None
        if not layer_name :
            if gp.layers.active :
                layer = gp.layers.active
            elif len(gp.layers) > 0 :
                layer = gp.layers[0]
                gp.layers.active = layer
        else :
            if any( layer_name in l.info for l in  gp.layers ) :
                for l in gp.layers :
                    if layer_name in l.info : 
                        layer = l
                        break
            else :
                layer = gp.layers.new(layer_name , set_active = gp.layers.active == None )
                gp.layers.active = layer

        return layer

    def get_gp_frame( self , layer ) :
        if len(layer.frames) == 0 :
            layer.frames.new( 1 , active = True )
        frame = layer.active_frame 
        return frame

    def get_lines( self, context ) :
        active_obj = context.active_object        
        visible_objects = context.visible_objects
#           objects = context.selected_objects
        objects = [obj for obj in visible_objects if obj != active_obj and obj.type == 'MESH']
        depsgraph = context.evaluated_depsgraph_get()
        loops = []
        for obj in objects:
            # make planes
            plane = pqutil.Plane( mathutils.Vector( (0,0,0) ) , mathutils.Vector( (1,0,0) ) )

            bm = bmesh.new()
            bm.from_object(obj ,depsgraph )
            ret = bmesh.ops.bisect_plane( bm , geom=bm.verts[:] + bm.edges[:] + bm.faces[:] ,dist=0.00000001,plane_co= plane.origin ,plane_no= plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)

            edges = [ e for e in ret['geom_cut'] if isinstance( e , bmesh.types.BMEdge ) ]
            # serch egde groups
            groups = pqutil.grouping_loop_edge( edges )
            for group in groups :
                le , lv = pqutil.sort_edgeloop( group )
                loops.append( [ obj.matrix_world @ v.co for v in lv ] )

            del ret
            del edges
            bm.free()

        return loops

    def get_boundary( self, context ) :
        active_obj = context.active_object        
        visible_objects = context.visible_objects
#           objects = context.selected_objects
        objects = [obj for obj in visible_objects if obj != active_obj and obj.type == 'MESH']
        depsgraph = context.evaluated_depsgraph_get()
        loops = []
        for obj in objects:
            # make planes

            bm = bmesh.new()
            bm.from_object(obj ,depsgraph )

            edges = [ e for e in bm.edges if e.is_boundary ]
            # serch egde groups
            groups = pqutil.grouping_loop_edge( edges )
            for group in groups :
                le , lv = pqutil.sort_edgeloop( group )
                loops.append( [ obj.matrix_world @ v.co for v in lv ] )

            del edges
            bm.free()

        return loops

    def get_pits_and_peaks( self, context , angle ) :
        radian = angle / 57.29577951308232
        active_obj = context.active_object        
        visible_objects = context.visible_objects
#           objects = context.selected_objects
        objects = [obj for obj in visible_objects if obj != active_obj and obj.type == 'MESH']
        depsgraph = context.evaluated_depsgraph_get()
        loops = []
        for obj in objects:
            # make planes

            bm = bmesh.new()
            bm.from_object(obj ,depsgraph )

            edges = [ e for e in bm.edges if (1 - e.calc_face_angle(0)) * 180 < angle ]
            # serch egde groups
            groups = pqutil.grouping_loop_edge( edges )
            for group in groups :
                le , lv = pqutil.sort_edgeloop( group )
                loops.append( [ obj.matrix_world @ v.co for v in lv ] )

            del edges
            bm.free()

        return loops

class MESH_OT_GPencil_2_Edge(Operator) :
    """Covert GP 2 Edge """
    bl_idname = "mesh.gpencil_to_edge"
    bl_label = "Covert GP 2 Edge"
    bl_options = {'REGISTER', 'UNDO'}

    segment_length : bpy.props.FloatProperty(
        name="Segment length",
        description="Segment length",
        default=0,
        min=0,
        max=5)


    def invoke(self, context , event ):
        self.strokes = None
        return self.execute(context )

    def execute(self, context ):
        gp = context.scene.grease_pencil
        if not gp:
            return {'CANCELLED'}
        obj = context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)                        

        preferences = context.preferences.addons[__package__].preferences
        segment = self.segment_length
        if self.segment_length == 0 :
            segment = preferences.line_segment_length
            self.segment_length = segment

        if self.strokes == None :
            self.strokes = []
            for layer in gp.layers :
                if "PolyQuilt" in layer.info :
                    if layer.active_frame != None :
                        for stroke in layer.active_frame.strokes :
                            points =  [ p.co for p in stroke.points ] 
                            self.strokes.append( points )

        newVerts = []
        for points in self.strokes :
            distances = [ (p1 - p2).length for p1 , p2 in zip( points[0:-1] , points[1:] ) ]
            isLoop =  (points[0] - points[-1]).length < bpy.context.scene.tool_settings.double_threshold
            total = sum(distances)
            if isLoop:
                num = max( 4 , int( total / segment + 0.5 ) )
            else :
                num = max( 1 , int( total / segment + 0.5 ) )
            seg = total / num
            point_num = num + 1
            length = 0
            newPoints = [ points[0] ]
            for p1, p2 , dst in zip( points[0:-1] , points[1:] , distances ) :
                if dst == 0 :
                    continue
                pre = length
                length += dst
                while length >= seg :
                    if length > sys.float_info.epsilon :
                        p1 = p1.lerp( p2 , ( seg - pre ) / length )
                    else :
                        p1 = p2
                    newPoints.append(p1)
                    if len(newPoints) >= point_num :
                        break
                    ratio = (seg - pre) / dst
                    pre = 0
                    dst = (p1-p2).length
                    length -= seg
                if len(newPoints) >= point_num :
                    break

            if len(newPoints) < point_num :
                newPoints.append( points[-1] )

#            if isLoop :
#                newPoints.append( points[0] )
            newPoints[-1] =  points[-1]
            verts = []
            for pts in newPoints :
                for v in newVerts :
                    if ( obj.matrix_world @ v.co - pts ).length <= sys.float_info.epsilon :
                        vert = v
                        break
                else :
                    vert = bm.verts.new( obj.matrix_world.inverted() @ pts )
                newVerts.append( vert )
                verts.append( vert )
                vert.select_set( True )

            edges = [ bm.edges.new( (p1,p2) ) for p1,p2 in zip( verts[0:-1] , verts[1:] ) if p1 != p2 ]
            for edge in edges :
                edge.select_set( True )
  

        bm.select_flush(True)
        bm.verts.index_update()
        bm.normal_update()
        mesh.update_gpu_tag()
        mesh.update_tag()
        mesh.update_tag()
        bmesh.update_edit_mesh( mesh , loop_triangles = True ,destructive = True )

#        for layer in list( gp.layers ) :
#            if "PolyQuilt" in layer.info :
#                gp.layers.remove( layer )

        return {'FINISHED'}
