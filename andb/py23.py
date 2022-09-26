from __future__ import print_function, division

""" python 2 and python 3 compatible
    https://python-future.org/compatible_idioms.html
"""
import sys
import types

PY2 = (sys.version_info.major == 2)
PY3 = (sys.version_info.major == 3)

if PY3:
    string_types = str,
    integer_types = int,
    #class_types = type,
    text_type = str
    binary_type = bytes
    int64 = int

elif PY2:
    string_types = basestring,
    integer_types = (int, long)
    #class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    int64 = long

else:
    raise Exception

# get integer number from str(PY2) or bytes(PY3)
def byte2int(b):
    if PY3:
        return b
    else:
        return ord(b)

class SIC:
    """ Sign Integer Convert

        for lldb doesn't have an api for getting signed integer,
        we have to use SIC to covert unsigned integer to signed.
    """

    @staticmethod
    def toS8(uint_number):
        v = uint_number & 0xFF
        if v & 0x80:
            v = -0x100 + v
        return v

    @staticmethod
    def toS16(uint_number):
        v = uint_number & 0xFFFF
        if v & 0x8000:
            v = -0x10000 + v
        return v

    @staticmethod
    def toS32(uint_number):
        v = uint_number & 0xFFFFFFFF
        if v & 0x80000000:
            v = -0x100000000 + v
        return v

    @staticmethod
    def toS64(uint_number):
        v = uint_number & 0xFFFFFFFFFFFFFFFF
        if v & 0x8000000000000000:
            v = -0x10000000000000000 + v
        return v


class IteratorBase:
    """ Iterator compatitable for python2 and 3.
    """
    def next(self):
        return self.__next__()

