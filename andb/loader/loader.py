#!/usr/bin/env python

""" alinode debugger loader,
      is part of alinode andb project.

    http://xxxx
"""

from __future__ import print_function

import os
import sys
import argparse


# add andb library
directory, file = os.path.split(__file__)
directory       = os.path.expanduser(directory)
directory       = os.path.abspath(directory)

#fmt_dir = "%s/andb/fmt" % directory

#if not fmt_dir in sys.path:
#    sys.path.insert(0, fmt_dir)
#print(sys.path)

loader_desc = """
Alinode Debugger Loader

A better experience for any node.js developers.

1) auto download binary (but not start a debugger session)
   andb can auto download the matched binary and typ file from remote. 
     
    andb -c core

2) debug only a corefile using lldb
   (imply auto download binary, if found)
    andb -l -c core

3) debug a corefile with local binary
    andb -l node -c core

4) start a new process
    andb -l node

5) debug a live process
    andb -l -p <pid>

choose your favourite debugger:
  andb -g or --gdb     : request a gdb console.
  andb -l or --lldb    : request a lldb console.

"""

parser = argparse.ArgumentParser(description=loader_desc, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-g', '--gdb', action='store_true', help='using gdb as debugger.')
parser.add_argument('-l', '--lldb', action='store_true', help='using lldb as debugger. (default)')
parser.add_argument('-p', '--pid', nargs=1, type=int, help='the process id to attach to.')
parser.add_argument('-c', '--core', nargs="?", type=str, help='path to corefile')
parser.add_argument('binary', nargs="?", type=str, help='node or shinki binaray')
#parser.add_argument('opts', nargs="*", help='debugger options')

args, dbg_opts = parser.parse_known_args()

print(os.path.abspath(__file__))
dirname, filename = os.path.split(__file__)
dirname = os.path.expanduser(dirname)
andb_dir = os.path.abspath(dirname)

#if not andb_dir in sys.path:
#    sys.path.insert(0, andb_dir)

#print('gdb:', args.gdb, 'lldb:', args.lldb,
#  'core:', args.core, 'binary:', args.binary, 'opts:', args.opts)

binary = None

if args.binary:
    """ use specified binary
    """
    binary = args.binary

elif args.core:
    """ only corefile
    """
    from myloader import CorefileAuxiliaryDownloader, Corefile
    corepath = args.core
    corefileFmt = Corefile()
    corefileFmt.Load(corepath)
    buildId = corefileFmt.GetBuildId()
    print('build-id:', buildId)

    corefileAuxiliaryDownloader = CorefileAuxiliaryDownloader()
    info = corefileAuxiliaryDownloader.Download(buildId)

    os.environ['ANDB_TYP'] = info['typ']

    if 'bin' in info:
        binary = info['bin']


if args.lldb:
    """ start lldb
    """
    opts = ['lldb', 
            '-x',  # no any .lldbinit
            '-o "com sc im %s/lldbinit.py"' % andb_dir,  # lldbinit python script
            '-s %s/lldbinit.cmd' % andb_dir,  # lldbinit command
           ]
    if binary:
        opts.append(binary)
    if args.core:
        opts.extend(["-c", args.core])
    if args.pid:
        opts.append("-p %d" % args.pid[0])

    print(" ".join(opts))
    os.system(" ".join(opts))

elif args.gdb:
    """ start gdb 
    """
    opts = ['gdb', 
            '--nh',  # no ~/.gdbinit
            '--nx',  # no .gdbinit 
            '-x %s/gdbinit.py' % andb_dir  # gdbinit python script
           ]
    if binary:
        opts.append(binary)
    if args.core:
        opts.append(args.core)
    if args.pid:
        opts.append("-p %d" % args.pid[0])
    if dbg_opts:
        opts.extend(dbg_opts)

    print(" ".join(opts))
    os.system(" ".join(opts)) 
