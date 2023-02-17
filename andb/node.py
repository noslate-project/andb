
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

    def PrettyPrint(self):
        arch = stl.String(self['arch']) 
        print(arch)

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
