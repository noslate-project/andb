
from __future__ import print_function, division

import andb.dbg as dbg 

class Struct(dbg.Struct):
    """ represents an Structure/Class in node
    """
    pass


class Enum(dbg.Enum):
    """ represents an Enumeration in node 
    """
    pass


class Immortal(Struct):
    _typeName = "shinki::Immortal"

    _current_environ = None

    @classmethod
    def SetCurrent(cls, pyo):
        cls._current_environ = pyo

    @classmethod
    def GetCurrent(cls, pyo):
        return cls._current_environ

def LoadDwf():
    # check is shinki
    t = dbg.Type.LookupType('shinki::Immortal')
    if t is None:
        # not shinki
        return 0

    Struct.LoadAllDwf()
    Enum.LoadAllDwf()
    return 1
