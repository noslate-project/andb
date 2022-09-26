 # -*- coding: UTF-8 -*-
from __future__ import print_function
import os

""" andb.dbg : support gdb/lldb platform
"""
import os

from .dbg_select import * 
from .base import *
from .dwf import * 

import sys
sys.setrecursionlimit(2000)


""" Functions
"""
def LoadDwf():
    # get binary's typ file
        
    if os.environ.get('ANDB_TYP'):
         dwf_file = os.environ.get('ANDB_TYP')
    elif os.path.exists('shinki.typ'):
         dwf_file = 'shinki.typ'
    else:
         dwf_file = 'node.typ'

    print("load Dwf", dwf_file)
 
    # add to debugger
    Target.AddDwfFile(dwf_file)

    # load dwf 
    Dwf.Load(dwf_file)

