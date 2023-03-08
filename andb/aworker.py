
from __future__ import print_function, division

import andb.dbg as dbg 
import andb.stl as stl

def IsAworker():
    """Return True if the binary is a aworker"""
    t = dbg.Type.LookupType('aworker::Immortal')
    if t is None:
        # not shinki
        return False
    return True

class Struct(dbg.Struct):
    """ represents an Structure/Class in node
    """
    pass


class Enum(dbg.Enum):
    """ represents an Enumeration in node 
    """
    pass


class Metadata(Struct):
    _typeName = "aworker::Metadata"

    def Flatten(self):
        out = {}

        out['versions'] = {}
        for i in ('aworker', 'v8', 'uv', 'zlib'):
            v = stl.String(self[i])
            out['versions'][i] = v.toString()
        
        arch = stl.String(self['arch']).toString() 
        platform = stl.String(self['platform']).toString() 
        out['arch'] = arch
        out['platform'] = platform
        return out 


class Immortal(Struct):
    _typeName = "aworker::Immortal"

    _current_environ = None

    @classmethod
    def SetCurrent(cls, pyo):
        cls._current_environ = pyo

    @classmethod
    def GetCurrent(cls, pyo):
        return cls._current_environ

def LoadDwf():
    # check is shinki
    if not IsAworker():
        # not shinki
        return 0

    Struct.LoadAllDwf()
    Enum.LoadAllDwf()
    return 1
