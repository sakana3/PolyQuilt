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

class display :

    @staticmethod
    def inch() :
        return bpy.context.preferences.system.dpi

    @staticmethod
    def cm() :
        return bpy.context.preferences.system.dpi / 2.54

    @staticmethod
    def mm() :
        return bpy.context.preferences.system.dpi / 25.4

    @staticmethod
    def scale() :
        return bpy.context.preferences.system.ui_scale

    @staticmethod
    def pixel_size() :
        return bpy.context.preferences.system.pixel_size

    @staticmethod
    def scale( val ) :
        return bpy.context.preferences.system.dpi / 25.4 / bpy.context.preferences.system.ui_scale * bpy.context.preferences.system.pixel_size * val

    @staticmethod
    def dot( val ) :
        return bpy.context.preferences.system.dpi / 25.4 * bpy.context.preferences.system.pixel_size * val

    def dot_to_mm( val ) :
        return val / (bpy.context.preferences.system.dpi / 25.4 * bpy.context.preferences.system.pixel_size)

        