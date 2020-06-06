# coding: UTF-8
import os
import zipfile

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

filename = modulename + "_" + version + ".zip"

with zipfile.ZipFile(filename,'w') as myzip:
    for folder, subfolders, files in os.walk(package_folder):
        myzip.write(folder)
        for file in files:
            myzip.write(os.path.join(folder,file))
