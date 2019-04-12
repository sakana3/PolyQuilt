import bpy
import bgl
import blf
import gpu
import bmesh
import math
import copy
import mathutils
import bpy_extras
import collections
from gpu_extras.batch import batch_for_shader
from .handleutility import *
from .dpi import *


#shader2D = gpu.types.GPUShader(vertex_shader, fragment_shader)
shader2D = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
shader3D = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


def draw_circle2D( pos , radius , color = (1,1,1,1), fill = False , subdivide = 64 ):
    r = radius * dpm()
    dr = math.pi * 2 / subdivide
    vertices = [( pos[0] + r * math.cos(i*dr), pos[1] + r * math.sin(i*dr)) for i in range(subdivide+1)]

    shader2D.bind()
    shader2D.uniform_float("color", color )
    primitiveType = 'TRI_FAN' if fill else 'LINE_STRIP'
    batch = batch_for_shader(shader2D, primitiveType , {"pos": vertices} )
    batch.draw(shader2D)

def draw_donuts2D( pos , radius_out , width , rate , color = (1,1,1,1) ):
    r = radius_out * dpm()
    subdivide = 100
    t = int( max(min(rate,1),0)*subdivide)
    dr = math.pi * 2 / subdivide
    vertices = [( pos[0] + r * math.sin(i*dr), pos[1] + r * math.cos(i*dr)) for i in range(t+1)]

    draw_lines2D( vertices , (0,0,0,color[3]*0.5) , (width )* dpm()+ 1.0  )
    draw_lines2D( vertices , color , width* dpm()  )

def draw_lines2D( verts , color = (1,1,1,1) , width : float = 1.0 ):
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glLineWidth(width )    
    bgl.glEnable(bgl.GL_BLEND)
    shader2D.bind()
    shader2D.uniform_float("color", color )
    batch = batch_for_shader(shader2D, 'LINE_STRIP', {"pos": verts} )
    batch.draw(shader2D)
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_LINE_SMOOTH)    
    bgl.glDisable(bgl.GL_BLEND)

def draw_pivot2D( pos , radius , color = (1,1,1,1) , isWire = False ):
    r = radius * dpm()
    if isWire is False :
        verts = ( (-1*r + pos[0],-1*r + pos[1]) ,(1*r + pos[0] ,-1*r + pos[1]),(1*r + pos[0],1*r + pos[1]),(-1*r + pos[0],1*r + pos[1]) )
        shader2D.bind()
        shader2D.uniform_float("color", color )
        batch = batch_for_shader(shader2D, 'TRI_FAN', {"pos": verts} )
        batch.draw(shader2D)
    else :
        verts = ( (-1*r + pos[0],-1*r + pos[1]) ,(1*r + pos[0] ,-1*r + pos[1]),(1*r + pos[0],1*r + pos[1]),(-1*r + pos[0],1*r + pos[1]) , (-1*r + pos[0],-1*r + pos[1]) )
        shader2D.bind()
        shader2D.uniform_float("color", color )
        batch = batch_for_shader(shader2D, 'LINE_STRIP', {"pos": verts} )
        batch.draw(shader2D)

def draw_pivot3D( pos , radius , color = (1,1,1,1) ):
    verts = ( pos , )
    bgl.glDisable(bgl.GL_LINE_SMOOTH)        
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glPointSize(radius * dpm() * 2 )
    bgl.glDisable(bgl.GL_DEPTH_TEST)

    shader3D.bind()
    shader3D.uniform_float("color", color )
    batch = batch_for_shader(shader3D, 'POINTS', {"pos": verts} )
    batch.draw(shader3D)

    bgl.glPointSize(1 )
    bgl.glDisable(bgl.GL_BLEND)


def draw_Face2D( obj , face : bmesh.types.BMFace , color = (1,1,1,1) , isFill = True ):
    bgl.glEnable(bgl.GL_BLEND)
    if isFill :
        vs = [ location_3d_to_region_2d(obj.matrix_world @ v.vert.co) for v in face.loops ]
        polys = mathutils.geometry.tessellate_polygon( (vs,) )
        shader2D.bind()
        shader2D.uniform_float("color", color )
        batch = batch_for_shader(shader2D, 'TRIS', {"pos": vs } , indices=polys )
        batch.draw(shader2D)              
    else :
        verts = []
        for edge in face.edges :
            verts.append( location_3d_to_region_2d( obj.matrix_world @ edge.verts[0].co ) )
            verts.append( location_3d_to_region_2d( obj.matrix_world @ edge.verts[1].co ) )
        shader2D.bind()
        shader2D.uniform_float("color", color )
        batch = batch_for_shader(shader2D, 'LINES', {"pos": verts} )
        batch.draw(shader2D)
    bgl.glDisable(bgl.GL_BLEND)

def draw_Face3D( obj , face : bmesh.types.BMFace , color = (1,1,1,1) , isFill = True ):
    bgl.glEnable(bgl.GL_BLEND)

    if isFill :
        vs = [ obj.matrix_world @ v.vert.co for v in face.loops ]
        polys = mathutils.geometry.tessellate_polygon( (vs,) )
        shader3D.bind()
        shader3D.uniform_float("color", color )
        batch = batch_for_shader(shader3D, 'TRIS', {"pos": vs } , indices=polys )
        batch.draw(shader3D)  
    else :
        verts = []
        for edge in face.edges :
            verts.append( obj.matrix_world @ edge.verts[0].co )
            verts.append( obj.matrix_world @ edge.verts[1].co )
        shader3D.bind()
        shader3D.uniform_float("color", color )
        batch = batch_for_shader(shader3D, 'LINES', {"pos": verts} )
        batch.draw(shader3D)
    bgl.glDisable(bgl.GL_BLEND)


def draw_Edge2D( obj , edge : bmesh.types.BMEdge , color = (1,1,1,1) ):
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glLineWidth(2.5)    
    bgl.glEnable(bgl.GL_BLEND)
    verts = ( 
        location_3d_to_region_2d( obj.matrix_world @ edge.verts[0].co ) , 
        location_3d_to_region_2d( obj.matrix_world @ edge.verts[1].co ) )

    shader2D.bind()
    shader2D.uniform_float("color", color )
    batch = batch_for_shader(shader2D, 'LINES', {"pos": verts} )
    batch.draw(shader2D)
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_LINE_SMOOTH)    
    bgl.glDisable(bgl.GL_BLEND)

def draw_Edge3D( obj , edge : bmesh.types.BMEdge , color = (1,1,1,1) , width = 1 ):
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glLineWidth(width)    
    bgl.glEnable(bgl.GL_BLEND)
    verts = ( obj.matrix_world @ edge.verts[0].co ,  obj.matrix_world @ edge.verts[1].co )

    shader3D.bind()
    shader3D.uniform_float("color", color )
    batch = batch_for_shader(shader3D, 'LINES', {"pos": verts} )
    batch.draw(shader3D)
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_LINE_SMOOTH)    
    bgl.glDisable(bgl.GL_BLEND)

def drawElementHilight( obj , element, radius , color = (1,1,1,1) ) :
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDisable(bgl.GL_DEPTH_TEST)

    if isinstance( element , bmesh.types.BMVert ) :
        v = obj.matrix_world @ element.co
        pos = location_3d_to_region_2d(v)
        draw_pivot2D( pos , radius , color )
    elif isinstance( element , bmesh.types.BMFace ) :
        draw_Face2D(obj,element, (color[0],color[1],color[2],color[3] * 0.25) )
    elif isinstance( element , bmesh.types.BMEdge ) :
        draw_Edge2D(obj,element,color)

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDisable(bgl.GL_BLEND)        


def drawElementsHilight3D( obj , elements, radius,width ,alpha, color = (1,1,1,1) ) :
    for element in elements :
        drawElementHilight(obj , element, radius ,width,alpha, color)

def drawElementHilight3D( obj , element, radius ,width , alpha, color = (1,1,1,1) ) :
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDisable(bgl.GL_DEPTH_TEST)

    if isinstance( element , bmesh.types.BMVert ) :
        v = obj.matrix_world @ element.co
        draw_pivot3D( v , radius , color )
    elif isinstance( element , bmesh.types.BMFace  ) :
        draw_Face3D(obj,element, (color[0],color[1],color[2],color[3] * alpha) )
    elif isinstance( element , bmesh.types.BMEdge ) :
        draw_Edge3D(obj,element,color,width)

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDisable(bgl.GL_BLEND)  


def drawElementsHilight( obj , elements, radius , color = (1,1,1,1) ) :
    for element in elements :
        drawElementHilight(obj , element, radius , color)


def DrawFont( text , size , positon , offset = (0,0) ) :
    font_id = 0
    blf.size(font_id, size, dpi() )
    w,h = blf.dimensions(font_id, text )
    blf.position(font_id, positon[0] - w / 2 + offset[0] * dpm() , positon[1] + h + offset[1] * dpm() , 0)
    blf.draw(font_id, text )

