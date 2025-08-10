#!/usr/bin/env python3
# File: write_aceax_compat.py
# Author: Mokka
#
# Description: Writes compat file for ACE Extended Arsenal
#
# Usage: python ./tools/write_aceax_compat.py
#
###############################################################################

# The MIT License (MIT)

# Copyright (c) 2025-2025 Mokka

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

###############################################################################

__version__ = "0.1"

import sys

if sys.version_info[0] == 2:
    print("Python 3 is required.")
    sys.exit(1)

from yapbol import PBOFile
import os
import argparse
import io
import re
import struct
from utils import binary_handler
from utils import data_rap as rap

# Set Globals
root_dir = ""
build_dir = ""
only_list = []
enable_trace = False
output_file = "XtdGearModels.hpp"

############################################################
# Utility functions
# Copyright (c) André Burgaud
# http://www.burgaud.com/bring-colors-to-the-windows-console-with-python/
if sys.platform == "win32":
    from ctypes import windll, Structure, c_short, c_ushort, byref

    SHORT = c_short
    WORD = c_ushort

    class COORD(Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("X", SHORT),
        ("Y", SHORT)]

    class SMALL_RECT(Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("Left", SHORT),
        ("Top", SHORT),
        ("Right", SHORT),
        ("Bottom", SHORT)]

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD)]

    # winbase.h
    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # wincon.h
    FOREGROUND_BLACK     = 0x0000
    FOREGROUND_BLUE      = 0x0001
    FOREGROUND_GREEN     = 0x0002
    FOREGROUND_CYAN      = 0x0003
    FOREGROUND_RED       = 0x0004
    FOREGROUND_MAGENTA   = 0x0005
    FOREGROUND_YELLOW    = 0x0006
    FOREGROUND_GREY      = 0x0007
    FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

    BACKGROUND_BLACK     = 0x0000
    BACKGROUND_BLUE      = 0x0010
    BACKGROUND_GREEN     = 0x0020
    BACKGROUND_CYAN      = 0x0030
    BACKGROUND_RED       = 0x0040
    BACKGROUND_MAGENTA   = 0x0050
    BACKGROUND_YELLOW    = 0x0060
    BACKGROUND_GREY      = 0x0070
    BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

    stdout_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo

    def get_text_attr():
      """Returns the character attributes (colors) of the console screen
      buffer."""
      csbi = CONSOLE_SCREEN_BUFFER_INFO()
      GetConsoleScreenBufferInfo(stdout_handle, byref(csbi))
      return csbi.wAttributes

    def set_text_attr(color):
      """Sets the character attributes (colors) of the console screen
      buffer. Color is a combination of foreground and background color,
      foreground and background intensity."""
      SetConsoleTextAttribute(stdout_handle, color)

def color(color):
    """Set the color. Works on Win32 and normal terminals."""
    if sys.platform == "win32":
        if color == "green":
            set_text_attr(FOREGROUND_GREEN | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
        elif color == "yellow":
            set_text_attr(FOREGROUND_YELLOW | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
        elif color == "red":
            set_text_attr(FOREGROUND_RED | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
        elif color == "blue":
            set_text_attr(FOREGROUND_BLUE | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
        elif color == "magenta":
            set_text_attr(FOREGROUND_MAGENTA | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
        elif color == "reset":
            set_text_attr(FOREGROUND_GREY | get_text_attr() & 0x0070)
        elif color == "grey":
            set_text_attr(FOREGROUND_GREY | get_text_attr() & 0x0070)
    else :
        if color == "green":
            sys.stdout.write('\033[92m')
        elif color == "red":
            sys.stdout.write('\033[91m')
        elif color == "blue":
            sys.stdout.write('\033[94m')
        elif color == "reset":
            sys.stdout.write('\033[0m')

def print_error(msg):
    color("red")
    print ("ERROR: {}".format(msg))
    color("reset")

def print_warning(msg):
    color("yellow")
    print ("WARNING: {}".format(msg))
    color("reset")

def print_trace(msg):
    if (not enable_trace):
        return
    color("magenta")
    print ("TRACE: {}".format(msg))
    color("reset")

def print_green(msg):
    color("green")
    print(msg)
    color("reset")

def print_blue(msg):
    color("blue")
    print(msg)
    color("reset")
############################################################

class ClassRef:
    def __init__(self, classname, data):
        self.classname = classname
        self.data = data

    def __repr__(self):
        return "ClassRef(classname={}, data={})".format(self.classname, self.data)

    def __str__(self):
        return "class {}: {}".format(self.classname, self.data)

class ModelRef:
    def __init__(self,name,data):
        self.name = name

        for d in data:
            data[d] = list(set(data[d]))
            data[d].sort()

        self.data = data

    def __repr__(self):
        return "ModelRef(name={}, data={})".format(self.name,self.data)

    def __str__(self):
        options = ""
        data_str = ""
        keys = self.data.keys()
        for idx, k in enumerate(keys):
            options = options + '"{}"'.format(k)
            if (idx < (len(keys) - 1)):
                options = options + ", "

            data_str = data_str + "\n\t\t\tclass {} {{\n\t\t\t\tchangeingame = 0;\n\t\t\t\tvalues[] = {{".format(k)
            for idy, o in enumerate(self.data[k]):
                data_str = data_str + '"{}"'.format(o)
                if (idy < (len(self.data[k]) - 1)):
                    data_str = data_str + ", "
            data_str = data_str + "};\n"
            for o in self.data[k]:
                data_str = data_str + '\n\t\t\t\tclass {0} {{ label = "{1}"; }};'.format(o.replace(" ","_"),o)
            data_str = data_str + "\n\t\t\t};\n"


        return '\t\tclass {} {{\n\t\t\tlabel = "";\n\t\t\tauthor = "MokTech Industries";\n\t\t\toptions[] = {{{}}};\n{}\t\t}};'.format(self.name,options,data_str)

class ConfigBin:
    def __init__(self, data, prefix, addon, path):
        self.data = data
        self.prefix = prefix
        self.addon = addon

        if os.name != 'nt':
            self.path = path.replace('\\','/')
        else:
            self.path = path

    def __repr__(self):
        return "ConfigBin(data={}, prefix={}, addon={}, path={})".format(self.data, self.prefix, self.addon, self.path)


def find_build_dir(pwd):
    # check if we find the .hemttout folder here, otherwise try one directory further up
    print_trace("Searching for .hemttout in {}".format(pwd))
    hemttout_dir = os.path.join(pwd,'.hemttout')
    if (os.path.isdir(hemttout_dir)):
        print_trace("Searching for build dir in {}".format(hemttout_dir))
        build_dir = os.path.join(hemttout_dir,'build')
        if (os.path.isdir(build_dir)):
            print_trace("HEMTT build dir found: {}".format(build_dir))
            return build_dir
        else:
            raise Exception("NoBuildDir","HEMTT build output directory could not be found!")
    else:
        return find_build_dir(os.path.join(pwd,'..'))

def grab_built_pbos(dir):
    # return all built pbos as PBOFile objects
    addons_dir = os.path.join(dir,'addons')
    print_trace("grabbing pbo files from addons dir: {}".format(addons_dir))
    addons_pbos = next(os.walk(addons_dir), (None, None, []))[2]
    print_trace("pbo files returned: {}".format(addons_pbos))

    pbos = []

    for file in addons_pbos:
        print_trace("reading pbo file: {}".format(file))
        pbo = PBOFile.read_file(os.path.join(addons_dir,file))
        pbos.append([file,pbo])

    return pbos

def get_config_prefix(cfg, searchprefix):
    cfg_patches = next(entry for entry in cfg.body.entries if entry.type == rap.RAP.EntryType.CLASS and (entry.name.lower() == "cfgpatches"))
    prefix = cfg_patches.body.entries[0].name.lower() if len(cfg_patches.body.entries) > 0 else None
    print_trace("found config prefix: {}".format(prefix))
    return prefix

def read_pbo_config_bin(pbo):
    # grab pboprefix to find root path
    pboprefix = pbo.pbo_header.header_extension.strings[1].lower()
    searchprefix = pboprefix.split('\\')[1]
    print_trace("found pboprefix as {}, searchprefix as {}".format(pboprefix,searchprefix))

    # grab all files within the data directory and the config.bin
    config_bin = []
    for file in pbo:
        #print_trace("checking file {}".format(file.filename))
        filename = "\\" + pboprefix + "\\" + file.filename.lower()

        if "config.bin" in filename:
            cfg = rap.RAP_Reader.read_raw(io.BufferedReader(io.BytesIO(file.data)))
            prefix = get_config_prefix(cfg, searchprefix)
            addon = file.filename.split('\\')[0].lower()
            if "config.bin" in addon:
                addon = addon.replace("config.bin", "")
            path = os.path.join(root_dir, '\\'.join(pboprefix.split('\\')[-2:]), addon)
            c_bin = ConfigBin(cfg, searchprefix, prefix, path)
            config_bin.append(c_bin)
            print_trace("found config.bin: {}".format(c_bin))

    if (len(config_bin) == 0):
        print_error("PBO does not contain a config.bin!")
    
    return config_bin

def get_classes_from_config(config):
    cfg_root = config.data.body
    cfg_glasses = next((entry for entry in cfg_root.entries if entry.type == rap.RAP.EntryType.CLASS and (entry.name.lower() == "cfgglasses")), None)
    cfg_weapons = next((entry for entry in cfg_root.entries if entry.type == rap.RAP.EntryType.CLASS and (entry.name.lower() == "cfgweapons")), None)
    cfg_vehicles = next((entry for entry in cfg_root.entries if entry.type == rap.RAP.EntryType.CLASS and (entry.name.lower() == "cfgvehicles")), None)

    if not cfg_glasses is None:
        print_trace("----\nrecursing CfgGlasses\n----")
        classes_facewear = recurse_classes_from_config(cfg_glasses.body,config.prefix)
    else:
        classes_facewear = []

    if not cfg_weapons is None:
        print_trace("----\nrecursing CfgWeapons\n----")
        classes_weapons = recurse_classes_from_config(cfg_weapons.body,config.prefix)
    else:
        classes_weapons = []

    if not cfg_vehicles is None:
        print_trace("----\nrecursing CfgVehicles\n----")
        classes_vehicles = recurse_classes_from_config(cfg_vehicles.body,config.prefix)
    else:
        classes_vehicles = []

    print_trace("found facewear classes {}".format(classes_facewear))
    print_trace("found weapon classes {}".format(classes_weapons))
    print_trace("found vehicle classes {}".format(classes_vehicles))
    return (classes_facewear, classes_weapons, classes_vehicles)

def recurse_classes_from_config(cfg,searchprefix,parent="root",level=0):
    print_trace("recurse level {}".format(level))
    classes = []
    if (level > 1):
        return classes # don't traverse past the first level here
    for entry in cfg.entries:
        if entry.type == rap.RAP.EntryType.CLASS:
            print_trace("checking {} with searchprefix {}".format(entry.name,searchprefix))
            if (entry.name.find(searchprefix) == 0):
                print_trace("{} in searchprefix".format(entry.name))
                classes.extend(get_classref_from_entry(entry,searchprefix))
            classes.extend(recurse_classes_from_config(entry.body,searchprefix, entry.name,level + 1))

    return classes

def get_classref_from_entry(entry,searchprefix):
    # look for XtdGearInfo
    xtdgearinfo = next((e for e in entry.body.entries if e.type == rap.RAP.EntryType.CLASS and (e.name.lower() == "xtdgearinfo")), None)
    if (xtdgearinfo is None):
        return []

    if (len(xtdgearinfo.body.entries) == 0):
        return []

    compat_data = {}
    for e in xtdgearinfo.body.entries:
        compat_data.update({e.name: e.value})

    class_ref = ClassRef(entry.name, compat_data)
    return [class_ref]

def get_models_from_classes(classes):
    models = {}
    for c in classes:
        model = ""
        options = {}
        for x in c.data:
            if x == "model":
                model = c.data[x]
            else:
                options[x] = c.data[x]
        if model != "":
            print_trace("iterating options in model {}: {}".format(model,options))
            all_options = models.get(model, {})
            for o in options:
                p = all_options.get(o, [])
                p.append(options[o])
                all_options[o] = p
            models[model] = all_options
    print_trace("found models {}".format(models))

    out = []
    for m in models:
        out.append(ModelRef(m,models[m]))

    return out

def write_compat_to_file(classes_facewear, classes_weapons, classes_vehicles, path,addon):
    if not os.path.exists(path):
        print_warning("Directory does not exist: {}".format(path))
        return False
    xtdgearmodels = os.path.join(path, output_file)

    try:
        with open(xtdgearmodels, 'w', encoding='utf-8') as f:
            f.write("// This file is automatically generated by write_aceax_compat.py\n")
            f.write("// Do not edit this file manually!\n\n")
            f.write("class XtdGearModels {\n")
            if (len(classes_facewear) > 0):
                models = get_models_from_classes(classes_facewear)
                f.write("\tclass CfgGlasses {\n")
                for m in models:
                    f.write("{}\n".format(m))
                f.write("\t};\n")
            if (len(classes_weapons) > 0):
                models = get_models_from_classes(classes_weapons)
                f.write("\tclass CfgWeapons {\n")
                for m in models:
                    f.write("{}\n".format(m))
                f.write("\t};\n")
            if (len(classes_vehicles) > 0):
                models = get_models_from_classes(classes_vehicles)
                f.write("\tclass CfgVehicles {\n")
                for m in models:
                    f.write("{}\n".format(m))
                f.write("\t};\n")
            f.write("};\n")


    except OSError as e:
        print_error("An error occurred while writing to file {}: {}".format(xtdgearmodels, e))
        return False

    return True

def main(argv):
    print_blue("## write_aceax_compat.py, version {} ##\n".format(__version__))

    # parse args
    parser = argparse.ArgumentParser(description="This script checks all local classes in the output of this project's HEMTT build.")
    parser.add_argument('directory',nargs='?',help='directory to operate on',default='.')
    parser.add_argument('-v', '--verbose',help='enables tracel-level logging',action='store_true')
    parser.add_argument('-o','--only',help='only run the path checks on the following addon',nargs='+')
    args = parser.parse_args()
    global enable_trace
    enable_trace = args.verbose

    global root_dir
    root_dir = os.path.abspath(args.directory)
    print_trace("setting root_dir to {}".format(root_dir))

    global only_list
    only_list = args.only
    print_trace("setting only_list to {}".format(only_list))

    # preliminary stuffs
    global build_dir
    try:
        build_dir = find_build_dir(root_dir)
    except:
        print_error("An exception occurred while attempting to find the build directory!")
        sys.exit(1)

    pbos = grab_built_pbos(build_dir)

    classes = []
    errors = []
    config_bins = {}
    for (file,pbo) in pbos:
        skip = False
        if (not only_list is None):
            skip = True
            for it in only_list:
                if (it in file):
                    skip = False
        if (skip):
            print_trace("{} not in only_list, skipping".format(file))
            continue

        print_trace("reading data files from pbo {}".format(file))
        config_bins[file] = read_pbo_config_bin(pbo)

    for config_files in config_bins.values():
        for config in config_files:
            classes_facewear, classes_weapons, classes_vehicles = get_classes_from_config(config)
            if (len(classes_facewear) == 0 and len(classes_weapons) == 0 and len(classes_vehicles) == 0):
                print_blue("No vehicle/weapon/facewear classes found in config.bin for addon: {}".format(config.addon))
                continue

            result = write_compat_to_file(classes_facewear, classes_weapons, classes_vehicles, config.path, config.addon)

            if (result):
                print_blue("Wrote {} facewear classes, {} weapon classes and {} vehicle classes to file: {}".format(len(classes_facewear), len(classes_weapons), len(classes_vehicles), os.path.join(config.path,output_file)))
            else:
                print_error("Failed to write to file: {}".format(os.path.join(config.path,output_file)))
                errors.append(config.addon)



    if (len(errors) == 0):
        print_green("{} files successfully written!".format(output_file))
        sys.exit(0)
    else:
        print_error("Writing {} for one or more addons has failed: {}".format(output_file, errors))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)

