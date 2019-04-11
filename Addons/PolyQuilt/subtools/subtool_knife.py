import sys
import bpy
import blf
import math
import mathutils
import bmesh
import bpy_extras
import collections
from .. import handleutility
from .. import draw_util
from ..QMesh import *
from .subtool import SubTool

class SubToolKnife(SubTool) :
    name = "KnifeTool2"

    def __init__(self,op,startPos) :
        super().__init__(op)
        self.startPos = startPos
        self.endPos = startPos
        self.CutEdgePos = []

    def OnUpdate( self , context , event ) :
        self.endPos = self.mouse_pos
        if event.type == 'MOUSEMOVE':
            if( self.startPos - self.endPos ).length > 2 :
                self.CalcKnife( context,self.startPos,self.endPos )
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if len(self.CutEdgePos) > 0 :
                    self.DoKnife(context,self.startPos,self.endPos)
                    self.bmo.UpdateMesh()                
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_lines2D( (self.startPos,self.endPos) , self.color_delete() , self.preferences.highlight_line_width )

        for pos in self.CutEdgePos :
            draw_util.draw_pivot2D( pos , 1 , self.color_delete() )
    
    def CalcKnife( self ,context,startPos , endPos ) :
        edges = self.bmo.highlight.viewPosEdges
        intersect = mathutils.geometry.intersect_line_line_2d        
        self.CutEdgePos = [ intersect( edge[1], edge[2] , startPos, endPos) for edge in edges ]
        self.CutEdgePos = [ p for p in self.CutEdgePos if p != None ]

    def DoKnife( self ,context,startPos , endPos ) :
        rv3d = context.space_data.region_3d    
        region = context.region

        pc = handleutility.region_2d_to_origin_3d(region, rv3d, startPos)
        no = handleutility.region_2d_to_vector_3d(region, rv3d, startPos)
        p0 = handleutility.region_2d_to_location_3d(region, rv3d, startPos, no)
        p1 = handleutility.region_2d_to_location_3d(region, rv3d, endPos, no)
        p2 = handleutility.region_2d_to_location_3d(region, rv3d, endPos, no * 2)
        t0 = (p1-p2)
        t1 = (p0-p1)
        t =  t0.cross( t1 )
        pn = t.normalized()

        bm = self.bmo.bm
        edges = self.bmo.highlight.viewPosEdges
        intersect = mathutils.geometry.intersect_line_line_2d
        cutEdge = [ edge[0] for edge in edges if intersect( edge[1], edge[2] , startPos, endPos) is not None ]

        co , no = handleutility.calc_object_space( self.bmo.obj , p0 , pn )        

        elements = cutEdge[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm,geom=elements,dist=0.00000001,plane_co=co,plane_no=no ,use_snap_center=False,clear_outer=False,clear_inner=False)
            
