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
import mathutils
import copy
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from ..utils.dpi import *
from .subtool import SubTool
from collections import namedtuple

class SubToolPolyPen(SubTool) :
    name = "PolyPenTool"

    def __init__(self , op , target : ElementItem ) :
        super().__init__(op)
        self.currentEdge = target
        self.startPos = target.hitPosition.copy()
        self.targetPos = target.hitPosition.copy()
        self.startMousePos = copy.copy(target.coord)

        self.startEdge = target.element
        self.startData = self.CalcStart( target.verts )
        self.endData = None

    @staticmethod
    def Check( root ,target ) :
        return target.isEdge and target.can_extrude() and False
 
    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            self.endData = self.CalcEnd( self.mouse_pos )
            if self.startData != None and self.endData != None :
#                print(( self.startData.Center - self.endData.Center ).length)
                if ( self.startData.Center - self.endData.Center ).length > self.startData.Witdh :
                    self.MakePoly()
 
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        if self.startData != None and self.endData != None :
            verts = [ self.startData.WorldPos[0] , self.startData.WorldPos[1] , self.endData.WorldPos[0] , self.endData.WorldPos[1] ]
            draw_util.draw_Poly3D( context , verts , color = self.color_create(0.5) )
            verts.append( verts[-1] )
            draw_util.draw_lines3D(  context , verts , color = self.color_create() , width = 2 )

    def CalcStart( self , verts ) :
        startVerts = verts[:]
        startWPs = [ self.bmo.obj.matrix_world @ v.co for v in startVerts ]
        startPlane = [ pqutil.Plane.from_screen( bpy.context , v ) for v in startWPs ]
        startPos = [ pqutil.location_3d_to_region_2d(v) for v in startWPs ]
        startCenetr = ( startPos[0] + startPos[1] ) / 2        
        width = ( startPos[0] - startPos[1] ).length

        Ret = namedtuple('Ret', ('Verts','WorldPos', 'Plane' , 'ViewPos' , 'Center' , 'Witdh'))
        ret = Ret(Verts=startVerts,WorldPos=startWPs,Plane=startPlane, ViewPos = startPos , Center = startCenetr , Witdh = width  )
        return ret

    def CalcEnd( self , mouse_pos ) :
        if (self.startData.Center - mouse_pos).length <= sys.float_info.epsilon :
            return None

        context = bpy.context
        start = self.startData 
        p0 = mouse_pos + start.ViewPos[0] - start.Center
        p1 = mouse_pos + start.ViewPos[1] - start.Center
        lengh = (p0-mouse_pos).length
        vec = mathutils.Matrix.Rotation(math.radians(90.0), 2, 'Z') @ (mouse_pos - start.Center).normalized()
        nrm = (start.ViewPos[0]-mouse_pos).normalized()

        if  vec.dot(nrm) < 0 :
            p0 = mouse_pos + vec * lengh
            p1 = mouse_pos - vec * lengh
        else :
            p0 = mouse_pos - vec * lengh
            p1 = mouse_pos + vec * lengh

        r0 = pqutil.Ray.from_screen( bpy.context , p0 )
        r1 = pqutil.Ray.from_screen( bpy.context , p1 )
        v0 = start.Plane[0].intersect_ray( r0 )
        v1 = start.Plane[1].intersect_ray( r1 )

        Ret = namedtuple('Ret', ('WorldPos', 'ViewPos' , 'Center' ))
        ret = Ret(WorldPos = [v0,v1]  , ViewPos = [p0,p1] , Center = mouse_pos  )
        return ret

    def MakePoly( self ) :
        verts = [ self.startData.Verts[0] , self.startData.Verts[1] ]
        nv = []
        for p in self.endData.WorldPos :
            v = self.bmo.AddVertexWorld( p )
            verts.append( v )
            nv.append( v )

        normal = pqutil.getViewDir()

        face = self.bmo.AddFace( verts , normal )
        face.normal_update()
        self.bmo.UpdateMesh()

        for e in face.edges :
            if set( e.verts ) == set( nv ) :
                self.startEdge = e
        self.startData = self.CalcStart( nv ) 
        self.endData = None