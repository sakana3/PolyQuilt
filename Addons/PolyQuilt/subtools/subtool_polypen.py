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
        self.startData = [ self.CalcHead( target.verts ) ]
        self.endData = None

    @staticmethod
    def Check( root ,target ) :
        return target.isEdge and target.can_extrude()
 
    def OnUpdate( self , context , event ) :
        if event.type == 'MOUSEMOVE':
            dist = self.preferences.distance_to_highlight            
            hitEdge = self.bmo.PickElement( self.mouse_pos , dist , edgering=True , backface_culling = True , elements=['EDGE'], ignore=[self.startEdge] )
            if hitEdge.isEdge :
                self.endData = self.AdsorptionEdge(  self.startData[-1].WorldPos[0] , self.startData[-1].WorldPos[1] , hitEdge.element )
            else :
                while( True ) :
                    sd = self.startData[-1]
                    v = ( self.mouse_pos - sd.Center )
                    pos = sd.Center + v.normalized() * min( sd.Witdh , v.length )
                    self.endData = self.CalcEnd( pos )
                    self.ReCalcFin(pos)
                    if self.startData != None and self.endData != None :
                        if v.length >= sd.Witdh :
                            self.MakePoly()
                            continue
                    break
 
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'PRESS' :
                pass
            elif event.value == 'RELEASE' :
                pass
        elif event.type == 'LEFTMOUSE' :
            if event.value == 'RELEASE' :
                if self.endData != None :
                    if (self.startData[-1].Center - self.mouse_pos).length / self.startData[-1].Witdh > 0.2 :
                        self.MakePoly() 
                return 'FINISHED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        pass

    def OnDraw3D( self , context  ) :
        startData = self.startData[-1]
        if startData != None and self.endData != None :
            alpha = (startData.Center - self.mouse_pos).length / startData.Witdh
            if alpha >= 0.2 :
                verts = [ startData.WorldPos[0] , startData.WorldPos[1] , self.endData.WorldPos[1] , self.endData.WorldPos[0] ]
                draw_util.draw_Poly3D( context , verts , color = self.color_create(alpha / 2) )
                verts.append( verts[-1] )
                draw_util.draw_lines3D(  context , verts , color = self.color_create(alpha ) , width = 2 )

    def CalcHead( self , verts , center = None ) :
        wpos = [ self.bmo.obj.matrix_world @ v.co for v in verts ]
        planes = [ pqutil.Plane.from_screen( bpy.context , v ) for v in wpos ]
        vpos = [ pqutil.location_3d_to_region_2d(v) for v in wpos ]
        if center == None :
            center = ( vpos[0] + vpos[1] ) / 2        
        vec = ( vpos[0] - vpos[1] )
        width = vec.length
        nrm = vec.normalized()

        perpendicular = mathutils.Vector( (0,0,1) ).cross( mathutils.Vector( (nrm.x,nrm.y,0) ) ).normalized()

        Ret = namedtuple('Ret', ('Verts','WorldPos', 'Plane' , 'ViewPos' , 'Center' , 'Witdh', 'Perpendicular' ))
        ret = Ret(Verts=verts[:],WorldPos=wpos,Plane=planes, ViewPos = vpos , Center = center , Witdh = width , Perpendicular = perpendicular  )
        return ret

    def CalcEnd( self , mouse_pos ) :
        Ret = namedtuple('Ret', ('WorldPos', 'ViewPos' , 'Center', 'Verts'  ))

        start = self.startData[-1]
        context = bpy.context

        q = self.CalcRot( start , mouse_pos )

        f = [ v - start.Center for v in start.ViewPos ]
        ft = [ q.to_matrix() @ v.to_3d() for v in f ]
        pt = [ mouse_pos + v.xy for v in ft ]
        rt = [ pqutil.Ray.from_screen( context , v ) for v in pt ]
        vt = [ p.intersect_ray( r ) for r,p in zip(rt , start.Plane) ]
        vt = [ QSnap.view_adjust( p ) for p in vt ]

        ret = Ret(WorldPos = vt , ViewPos = pt , Center = mouse_pos , Verts = [None,None] )
        return ret


    def ReCalcFin( self , mouse_pos ) :
        if len( self.startData ) < 2 :
            return
        context = bpy.context
        finP = self.startData[-2]
        fin1 = self.startData[-1]

        q = self.CalcRot( finP , self.endData.Center )

        f = [ v - finP.Center for v in finP.ViewPos ]
        ft = [ q.to_matrix() @ v.to_3d() for v in f ]
        pt = [ fin1.Center + v.xy for v in ft ]
        rt = [ pqutil.Ray.from_screen( context , v ) for v in pt ]
        vt = [ p.intersect_ray( r ) for r,p in zip(rt , finP.Plane) ]
        vt = [ QSnap.view_adjust( p ) for p in vt ]

        for v , p in zip( fin1.Verts , vt ) :
            if self.bmo.is_mirror_mode :
                mirror = self.bmo.find_mirror(v)

            self.bmo.set_positon( v , p , is_world = True )

            if self.bmo.is_mirror_mode and mirror != None :
                self.bmo.set_positon( mirror , self.bmo.mirror_world_pos( p ) , is_world = True )
            self.bmo.UpdateMesh()

        self.startData[-1] = self.CalcHead( fin1.Verts , fin1.Center )

    def MakePoly( self ) :
        startData = self.startData[-1]        
        verts = [ startData.Verts[0] , startData.Verts[1] ]
        nv = []

        for p , vt in zip( self.endData.WorldPos[::-1] , self.endData.Verts[::-1] ) :
            if vt != None :
                v = vt
            else :
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
        self.startData.append( self.CalcHead( nv[::-1] ) )
        self.endData = None


    def AdsorptionEdge( self , p0 , p1 , edge ) :
        Ret = namedtuple('Ret', ('WorldPos', 'ViewPos' , 'Center' , 'Verts' ))

        st0 = pqutil.location_3d_to_region_2d(p0)
        st1 = pqutil.location_3d_to_region_2d(p1)
        se0 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[0].co))
        se1 = pqutil.location_3d_to_region_2d(self.bmo.local_to_world_pos(edge.verts[1].co))
        if (st0-se0).length + (st1-se1).length > (st0-se1).length + (st1-se0).length :
            wp = [ edge.verts[1] , edge.verts[0] ]
        else :
            wp = [ edge.verts[0] , edge.verts[1] ]

        vp = [ pqutil.location_3d_to_region_2d(v.co) for v in wp ]

        ret = Ret(WorldPos = [ self.bmo.obj.matrix_world @ v.co for v in wp] , ViewPos = vp , Center = (vp[0]+vp[1]) / 2 , Verts = wp )

        return ret

    def CalcRot( self , start , v0 ) :
        vec = (v0 - start.Center )
        nrm = vec.normalized()

        r0 = math.atan2( nrm.x , nrm.y )
        if nrm.dot(start.Perpendicular) > 0 :
            r1 = math.atan2( start.Perpendicular.x , start.Perpendicular.y )
        else :
            r1 = math.atan2( -start.Perpendicular.x , -start.Perpendicular.y )

        q0 = mathutils.Quaternion( mathutils.Vector( (0,0,1) ) , r0 )
        q1 = mathutils.Quaternion( mathutils.Vector( (0,0,1) ) , r1 )            

        q = q0.rotation_difference(q1)

        return q