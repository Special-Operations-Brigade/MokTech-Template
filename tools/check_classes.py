#!/usr/bin/env python3
# File: check_classes.py
# Author: Mokka
#
# Description: Checks addon classes in built pbos
#
# Usage: python ./tools/check_classes.py
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

############################################################
# rap-related functions for binary file reading
# many thanks to MrClock (https://github.com/MrClock8163/)
def rap_read_paths(stream, count):
    paths = []
    for i in range(count):
        if binary_handler.read_byte(stream) != 0:
            print_warning("Non-ASCIIZ value encountered in array")
            break

        paths.append(binary_handler.read_asciiz(stream).lower())

    return paths
############################################################

class ClassRef:
    def __init__(self, classname, path, source):
        self.classname = classname
        self.path = path
        self.source = source

    def __repr__(self):
        return "ClassRef(classname={}, path={}, source={})".format(self.classname, self.path, self.source)

    def __str__(self):
        return "{} (class {} >> '{}')".format(self.classname, self.path, self.source)

class ConfigBin:
    def __init__(self, data, prefix):
        self.data = data
        self.prefix = prefix

    def __repr__(self):
        return "ConfigBin(data={}, prefix={})".format(self.data, self.prefix)


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

def read_pbo_config_bin(pbo):
    # grab pboprefix to find root path
    pboprefix = pbo.pbo_header.header_extension.strings[1].lower()
    searchprefix = pboprefix.split('\\')[1]
    print_trace("found pboprefix as {}, searchprefix as {}".format(pboprefix,searchprefix))

    # grab all files within the data directory and the config.bin
    config_bin = []
    for file in pbo:
        print_trace("checking file {}".format(file.filename))
        filename = "\\" + pboprefix + "\\" + file.filename.lower()

        if "config.bin" in filename:
            config_bin.append(ConfigBin(rap.RAP_Reader.read_raw(io.BufferedReader(io.BytesIO(file.data))), searchprefix))
            print_trace("found config.bin: {}".format(config_bin))

    if (len(config_bin) == 0):
        print_error("PBO does not contain a config.bin!")
    
    return config_bin

def get_classes_from_config(config):
    cfg_root = config.data.body
    classes = recurse_classes_from_config(cfg_root,config.prefix)
    print_trace("found classes: {}".format(classes))
    return list(set(classes))  # return unique classes

def recurse_classes_from_config(cfg,searchprefix,parent="root"):
    classes = []
    for entry in cfg.entries:
        if entry.type == rap.RAP.EntryType.CLASS:
            if (entry.name.find(searchprefix) == 0):
                classes.append(entry.name.lower())
            classes.extend(recurse_classes_from_config(entry.body,searchprefix, entry.name))

    return classes

def get_class_refs_from_config(config):
    cfg_root = config.data.body
    class_refs = recurse_class_refs_from_config(cfg_root,config.prefix)
    #print_trace("found class refs: {}".format(class_refs))
    return list(set(class_refs))  # return unique class refs

def recurse_class_refs_from_config(cfg,searchprefix,parent="root"):
    classes = []
    if (parent == "CfgPatches" and skip_cfgpatches):
        return classes  # skip CfgPatches if requested
    for entry in cfg.entries:
        if entry.type == rap.RAP.EntryType.CLASS:
            #print_trace("found class: {}".format(entry.name))
            classes.extend(recurse_class_refs_from_config(entry.body,searchprefix,entry.name))
        elif entry.type == rap.RAP.EntryType.ARRAY:
            for subentry in entry.body.elements:
                classes.extend(parse_class_ref_from_entry(subentry, searchprefix, parent, entry.name))
        elif entry.type == rap.RAP.EntryType.SCALAR:
            classes.extend(parse_class_ref_from_entry(entry, searchprefix, parent))

    return classes

def parse_class_ref_from_entry(entry, searchprefix, parent, entry_name=None):
    if entry_name is None:
        entry_name = entry.name
    # parse a class ref from an entry name
    if (entry.subtype != rap.RAP.EntrySubType.STRING):
        return []

    if (entry.value.find(searchprefix) == 0):
        # handle functions
        if ("_fnc_" in entry.value):
            return []
        #print_trace("found class ref: {} with {} at {}".format(entry_name, entry.value, parent))
        return [ClassRef(entry.value.lower(), parent.lower(), entry_name.lower())]
    else:
        return []

def check_pbo_class_refs(pbo,config_bin,classes):
    # checks paths in the pbo
    if config_bin is None:
        return False
    # read the config.bin for all paths in hiddenSelectionsTextures[]
    class_refs = []
    for cfg in config_bin:
        class_refs.extend(get_class_refs_from_config(cfg))
    print_trace("found class refs in config: {}".format(class_refs))

    # iterate through class_refs from config and see if they are a) local to current addon and b) if they exist in classes
    errors = []
    pboprefix = pbo.pbo_header.header_extension.strings[1].lower()
    searchprefix = pboprefix.split('\\')[1]
    for cls in class_refs:
        if (searchprefix in cls.classname):
            print_trace("{} is local class".format(cls.classname))
            if (cls.classname in classes):
                print_trace("{} exists in classes".format(cls.classname))
            else:
                print_warning("Class {} could not be found!".format(cls))
                errors.append(cls.classname)
        else:
            print_trace("{} is not local class, skipping".format(cls.classname))
            continue

    return (len(errors) == 0)


def main(argv):
    print_blue("## check_classes.py, version {} ##\n".format(__version__))

    # parse args
    parser = argparse.ArgumentParser(description="This script checks all local classes in the output of this project's HEMTT build.")
    parser.add_argument('directory',nargs='?',help='directory to operate on',default='.')
    parser.add_argument('-v', '--verbose',help='enables tracel-level logging',action='store_true')
    parser.add_argument('--enable-cfgpatches',help='enables checking units/weapons array in CfgPatches',action='store_true')
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

    global skip_cfgpatches
    skip_cfgpatches = not args.enable_cfgpatches
    print_trace("setting skip_cfgpatches to {}".format(skip_cfgpatches))

    # preliminary stuffs
    global build_dir
    try:
        build_dir = find_build_dir(root_dir)
    except:
        print_error("An exception occurred while attempting to find the build directory!")
        sys.exit(1)

    pbos = grab_built_pbos(build_dir)

    # actually run the checks
    errors = []
    classes = []
    config_bins = {}
    # first pass, read all classes from all pbos to match cross-refs
    for (file,pbo) in pbos:
        print_trace("reading data files from pbo {}".format(file))
        config_bins[file] = read_pbo_config_bin(pbo)
        for config in config_bins[file]:
            classes.extend(get_classes_from_config(config))

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

        print_blue("Checking classes in {}...".format(file))
        success = check_pbo_class_refs(pbo,config_bins[file],classes)
        if (success):
            print_blue("Classes in {} are valid!".format(file))
        else:
            print_error("Classes in {} contain errors!".format(file))
            errors.append(file)
        print('')

    if (len(errors) == 0):
        print_green("Validation of all addons' classes succeeded!")
        sys.exit(0)
    else:
        print_error("Validation of one or more addons' classes failed: {}".format(errors))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)

