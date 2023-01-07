# -*- coding: UTF-8 -*-

from __future__ import print_function, division
""" type support

    there are 3 kinds of memory object in project,

    Enum, it's a C++ enumeration definition, 
    provided by Dwarf, defines various type/kind/config informations.
    eg, 
    enum 'v8::internal::IntanceType' tells the what kind of HeapObject it is.
    IntanceType.Name(169)  : tells the 'MAP_TYPE'，
    IntanceType.isMap(160) : tells the True.
    
    Struct, it's a C++ structure/class object, 
    all the fields are defined in C++ source code and can directly read by gdb,
    should be created by a memory pointer.
    eg,
    class 'v8::internal::Isoalte', Isolate is the root structure of a v8 engine.
    Isolate['heap_'], get the heap structure.

    Value, it's a v8 Object,
    v8 engine doesn't use c++ class to define objects, instead, all the v8 objects
    includes all js objects are referenced by Tagging and Layout(offset) information. 
    Value is the base abstrative class for all v8 objects, and represents a object 
    in memory, each v8 object has it's own layout setting. 
    should be created by a SMI or ObjectTag.
    eg, HeapObject, JSObject tells a v8 object in memory.
    o = HeapObject(0x69000121) : get the HeapObject for tagptr(0x69000121)
    m = o.GetMap() :  get the Map from HeapObject

    Enum and Struct are inherted from andb.andb.
    Value should be private type, please keep it only in v8.py.
"""

from .internal import *
from .enum import *
from .structure import *
from .object import *
from .iterator import *
from .frame import *
