# coding: UTF-8
import os
import re
import zipfile
import shutil

modulename = "PolyQuilt"
package_folder = os.getcwd() + "/Addons/PolyQuilt"

version = "0.0.0"
with open( package_folder + "/__init__.py", encoding= "utf-8" ) as f:
    line = f.readline()
    while line :
        if "\"version\"" in line :
            vtext =  line.split('(')[-1].split(')')[0]
            vtext = [ v.replace(" ","") for v in vtext.split(',') ]
            version =  '.'.join(vtext)
        line = f.readline()

filename = modulename + "_v" + version 

shutil.make_archive( filename , 'zip', root_dir= package_folder )

