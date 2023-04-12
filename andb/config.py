# -*- coding: UTF-8 -*-
from __future__ import print_function, division

class Config:

    """ control the string length in ShortBrief """
    cfgStringShortLength = 50

    """ control the display of string length"""
    cfgStringLength = 8192

    """ control the display element of a array
    """
    cfgArrayElements = 1000

    """ control the display of map in 'v8 i/o' command 
        1 for all map property showup,
        2 for only set property showup,
    """
    cfgShowMapInspect = 1

    """ control the profiler decorator 
        0: disabled
        1: timeit, 'func() takes x seconds.'
        2: python profiler, 'function costs detail'
    """
    cfgProfilerMode = 1

    """ control the Object decode failed action
        0: raise exception, and stop the command. 
        1: drop the page, but continue next page. 
    """
    cfgObjectDecodeFailedAction = 1 

    """ control the output leves
        DEBUG >=10,
        VERBOSE >=20,
        INFO >=30,
        WARN >=40,
        ERROR >=50,
        CRITICAL >=60
    """
    cfgLoggingLevel = 11 

    """ the flag limit the string length in heapsnapshot.
        the string larger than the limit will be cut to reduce the json file size.
    """
    cfgHeapSnapshotMaxStringLength = 4096 

    """ contain FreeSpace object in heapsnapshot.
    """
    cfgHeapSnapshotShowFreeSapce = 0

    @classmethod
    def Show(cls, Key=None):
        for k in cls.__dict__:
            if not k.startswith('cfg'):
                continue
            print(k, "=", getattr(cls, k))
        
    @classmethod
    def SetValue(cls, key, value):
        v = getattr(cls, key)
        if v is None:
            return None
        setattr(cls, key, value)

