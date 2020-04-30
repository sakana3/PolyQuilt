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
import os
import bpy.utils.previews

__all__ = ['register_icons','unregister_icons','custom_icon']

icons = [   "icon_geom_vert" , "icon_geom_edge" , "icon_geom_triangle" , "icon_geom_quad" , "icon_geom_polygon" , 
            "icon_move_free" , "icon_move_x" , "icon_move_y" , "icon_move_z" , "icon_move_normal", "icon_move_tangent" ,
            "icon_opt_backcull" , "icon_opt_mirror" , "icon_opt_x0" ,
            "icon_brush_move" , "icon_brush_relax", "icon_brush_delete" ]

custom_icons = {}

def register_icons():
    global custom_icons
    custom_icons = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    for icon in icons :
       custom_icons.load( icon , os.path.join(my_icons_dir, icon + ".png" )  , 'IMAGE')

def unregister_icons():
    global custom_icons    
    bpy.utils.previews.remove(custom_icons)
    custom_icons = None

def custom_icon( name ) :
    global custom_icons
    return custom_icons[ name].icon_id

def custom_icon_t( name ) :
    global custom_icons
    return custom_icons[ name]
