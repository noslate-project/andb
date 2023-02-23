
from __future__ import print_function, division

import andb.dbg as dbg 
import andb.stl as stl

""" Base Classes
"""
class Struct(dbg.Struct):
    """ represents an Structure/Class in node
    """
    pass


class Enum(dbg.Enum):
    """ represents an Enumeration in node 
    """
    pass


class ContextEmbedderIndex(Enum):
    _typeName = "node::ContextEmbedderIndex"

    kEnvironment = 32 

class Metadata(Struct):
    """node::Metadata was first introduced by node-v12.
    """
    _typeName = "node::Metadata"

    def Flatten(self):
        out = {}

        out['versions'] = {}
        versions = self['versions']
        for i in ('node', 'v8', 'uv', 'zlib', 'napi'):
            v = stl.String(versions[i])
            out['versions'][i] = v.toString()
        
        arch = stl.String(self['arch']).toString() 
        platform = stl.String(self['platform']).toString() 
        out['arch'] = arch
        out['platform'] = platform
        return out 

class Environment(Struct):
    _typeName = "node::Environment"

    _current_environ = None

    @classmethod
    def SetCurrent(cls, pyo):
        cls._current_environ = pyo

    @classmethod
    def GetCurrent(cls):
        return cls._current_environ


def LoadDwf():
    # check is node
    t = dbg.Type.LookupType('node::Environment')
    if t is None:
        # not node 
        return 0

    Struct.LoadAllDwf()
    Enum.LoadAllDwf()
    return 1
