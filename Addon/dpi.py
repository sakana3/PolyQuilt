import bpy

def dpi() :
    return bpy.context.preferences.system.dpi 

def dpc() :
    return dpi() / 2.54

def dpm() :
    return dpc() / 10
