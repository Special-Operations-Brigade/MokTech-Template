#!/usr/bin/env python3
# File: check_paths.py
# Author: Mokka
#
# Description: Checks local file paths referenced in hiddenSelectionsTexture[]
#
# Usage: python ./tools/check_paths.py
#
###############################################################################

# The MIT License (MIT)

# Copyright (c) 2024-2024 Mokka

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

__version__ = "0.2"

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
from utils import data_rap as rap
from utils import binary_handler

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

class PathRef:
    def __init__(self, path, parent, entry_name):
        self.path = path.lower()
        self.parent = parent.lower()
        self.entry_name = entry_name.lower()

    def __str__(self):
        return "{} (class {} >> '{}')".format(self.path, self.parent, self.entry_name)

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        return iter((self.path, self.parent, self.entry_name))

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

def is_local_path(path,prefix):
    # check if the path is a valid local path
    return (path.find(prefix) == 0)

def get_paths_from_config(config):
    cfg_root = config.data.body
    paths = recurse_paths(cfg_root, config.prefix)
    #print_trace("found paths: {}".format(paths))
    return list(set(paths))  # remove duplicates

def recurse_paths(cfg, searchprefix, parent="root"):
    classes = []
    for entry in cfg.entries:
        if entry.type == rap.RAP.EntryType.CLASS:
            #print_trace("found class: {}".format(entry.name))
            classes.extend(recurse_paths(entry.body,searchprefix,entry.name))
        elif entry.type == rap.RAP.EntryType.ARRAY:
            for subentry in entry.body.elements:
                classes.extend(parse_path_from_entry(subentry, searchprefix, parent, entry.name))
        elif entry.type == rap.RAP.EntryType.SCALAR:
            classes.extend(parse_path_from_entry(entry, searchprefix, parent))

    return classes

def parse_path_from_entry(entry, searchprefix, parent, entry_name=None):
    if entry_name is None:
        entry_name = entry.name

    # parse a class ref from an entry name
    if (entry.subtype != rap.RAP.EntrySubType.STRING):
        return []

    if (is_local_path(entry.value, searchprefix)):
        print_trace("found path: {} in {} at {}".format(entry.value, entry_name, parent))
        return [PathRef(entry.value.lower(), parent.lower(), entry_name.lower())]
    else:
        return []

def read_pbo_data_files(pbo):
    # grab pboprefix to find root path
    pboprefix = pbo.pbo_header.header_extension.strings[1].lower()
    modroot = "\\" + pboprefix.split('\\')[0]+ "\\" + pboprefix.split('\\')[1] + "\\"
    print_trace("found pboprefix as {}".format(pboprefix))

    # grab all files within the data directory and the config.bin
    config_bin = []
    data_files = []
    for file in pbo:
        filename = "\\" + pboprefix + "\\" + file.filename.lower()
        if (not ".hpp" in filename):
            print_trace("found data file {}".format(filename))
            data_files.append(filename)

        if "config.bin" in filename:
            print_trace("found config.bin")
            config_bin.append(ConfigBin(rap.RAP_Reader.read_raw(io.BufferedReader(io.BytesIO(file.data))), modroot))

    if (config_bin is []):
        print_error("PBO does not contain a config.bin!")
        return ([], [])

    if (len(data_files) == 0):
        print_warning("PBO does not contain data files")

    return (data_files, config_bin)

def check_pbo_paths(pbo,config_bin,data_files):
    # checks paths in the pbo
    if config_bin is []:
        return False
    # read the config.bin for all paths in config
    texture_paths = []
    for cfg in config_bin:
        texture_paths.extend(get_paths_from_config(cfg))
    #print_trace("found paths in config: {}".format(texture_paths))

    # iterate through texture_paths from config and see if they are a) local to current addon and b) if they exist in data_files
    errors = []
    pboprefix = pbo.pbo_header.header_extension.strings[1].lower()
    modroot = "\\" + pboprefix.split('\\')[0]+ "\\" + pboprefix.split('\\')[1] + "\\"
    print_trace("modroot is {}".format(modroot))
    for path in texture_paths:
        if (modroot in path.path):
            print_trace("{} is local path".format(path.path))
            if (path.path in data_files):
                print_trace("{} exists in data_files".format(path.path))
            else:
                print_warning("File {} could not be found!".format(path))
                errors.append(path)
        else:
            print_trace("{} is not local path, skipping".format(path))
            continue

    return (len(errors) == 0)


def main(argv):
    print_blue("## check_paths.py, version {} ##\n".format(__version__))

    # parse args
    parser = argparse.ArgumentParser(description="This script checks all local paths referenced in hiddenSelectionsTextures[] entries in the output of this project's HEMTT build.")
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

    # actually run the checks
    errors = []
    data_files = []
    config_bins = {}
    for (file,pbo) in pbos:
        # first pass, read all data files from all pbos to match cross-refs
        print_trace("reading data files from pbo {}".format(file))
        pbo_files = read_pbo_data_files(pbo)
        data_files += pbo_files[0]
        config_bins[file] = pbo_files[1]

    data_files = list(set(data_files))  # remove duplicates

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

        print_blue("Checking paths in {}...".format(file))
        success = check_pbo_paths(pbo,config_bins[file],data_files)
        if (success):
            print_blue("Paths in {} are valid!".format(file))
        else:
            print_error("Paths in {} contain errors!".format(file))
            errors.append(file)
        print('')

    if (len(errors) == 0):
        print_green("Validation of all addons' paths succeeded!")
        sys.exit(0)
    else:
        print_error("Validation of one or more addons' paths failed: {}".format(errors))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)

