# -*- coding: UTF-8 -*-

from __future__ import print_function, division

def isGDB():
    try:
        import gdb
        print(gdb.VERSION)
        return True
    except:
        return False

def isLLDB():
    try:
        import lldb
        if not lldb.target is None:
            print(lldb.target)
            return True
        return False
    except:
        return False

type = 'unknown'
if isLLDB():
    from .dbg_lldb import *
    type = "lldb"
elif isGDB():
    from .dbg_gdb import *
    type = "gdb"
else:
    raise Exception

