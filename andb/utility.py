from __future__ import print_function, division

from andb.config import Config
import functools
from andb.dbg import type as dbg_type
import andb.py23 as py23

def profiler(func):
    """ decorater for function profiling
    """
    from cProfile import Profile 
    from time import time
    
    def timeit(*args):
        """ show only time cost """ 
        t = time()
        rc = func(*args)
        print('{}() takes {:.3f} second(s).'.format(func.__name__, time() - t))
        return rc

    def profiler(*args):
        """ show detail profiling """
        pr = Profile()
        pr.enable()
        rc = func(*args)
        pr.disable()
        pr.print_stats(sort="cumulative")
        return rc
    
    def dummy(*args):
        """ disable profiling """
        rc = func(*args)
        return rc

    # select by cfgProfilerMode
    if Config.cfgProfilerMode == 2:
        return profiler
    elif Config.cfgProfilerMode == 1:
        return timeit
    return dummy 


def oneshot(func):
    """oneshot decorate run func one time and caches the result."""
    def FuncWrap(self):
        #print("call func %s" % func.__name__)
        v = func(self)
        def ConstWrap(*args):
            return v
        # overwrite the same Name Function
        setattr(self, func.__name__, ConstWrap)
        return v
    return FuncWrap


class CachedProperty(object):
    """ same as property decorator, but with cached.
    """
    def __init__(self, method):
        self._method = method

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self._method(inst)
        #name = self._method.__name__ if self._name is None else self._name
        setattr(inst, self._method.__name__, result)
        return result


class Logging:
    """ control the logging output
    """
   
    # non-color levels
    NOTSET = 0
    DEBUG = 10
    VERBOSE = 20
    # color levels
    INFO = 30
    WARN = 40
    ERROR = 50
    CRITICAL = 60
    
    @classmethod
    def getLevel(cls):
        return Config.cfgLoggingLevel

    @classmethod
    def _output(cls, sz, level=None, color=None, pad=0):
        # omit low priority output
        if level and level < cls.getLevel():
            return

        # workaround for gdb print('\0').
        if dbg_type == 'gdb':
            sz = sz.replace('\000', '')

        
        # ready unicode string 
        if color is None:
            if pad > 0:
                out = "%*s%s" % (pad, ' ', sz)
            else:
                out = sz 
        else:
            out = '\033[%dm' % color + sz + '\033[0m'

        """ Output
            python2 write utf8 encoded string, 
            python3 write unicode string.

            redirect print to log.print:
            print = Logging.print
        """
        if py23.PY2:
            print( out.encode('utf8') )
        else:
            print( out )

    @classmethod
    def critical(cls, sz, level=0):
        cls._output(sz, cls.CRITICAL + level, color=35)
    
    @classmethod
    def error(cls, sz, level=0):
        cls._output(sz, cls.ERROR + level, color=31)

    @classmethod
    def warn(cls, sz, level=0):
        cls._output(sz, cls.WARN + level, color=33)

    @classmethod
    def info(cls, sz, level=0):
        cls._output(sz, cls.INFO + level, color=32)

    @classmethod
    def verbose(cls, sz, level=0):
        cls._output(sz, cls.VERBOSE + level)
    
    @classmethod
    def debug(cls, sz, level=0):
        cls._output(sz, cls.DEBUG + level)

    @classmethod
    def print(cls, sz, pos=0):
        """ print is not controlled by level, always output. """
        cls._output(sz, pad=pos)

    @classmethod
    def DCHECK(cls, statement, *infos):
        if not statement:
            assert statement 


def RemovePrefix(src_string, to_remove):
    if src_string.startswith(to_remove):
        return src_string[len(to_remove):]
    return src_string


def RemoveSuffix(src_string, to_remove):
    if src_string.endswith(to_remove):
        return src_string[:-len(to_remove)]
    return src_string


def TextShort(any_str, limit=-1):
    """ limit string length for shot brief """
    if limit < 0:
        limit = Config.cfgStringShortLength

    if isinstance(any_str, py23.integer_types):
        return any_str

    def NoNewLine(src):
        return src.replace('\r', '').replace('\n', '')

    # Short string in one line
    if len(any_str) > limit:
        return NoNewLine(any_str[:limit] + '...').encode('unicode_escape')
    return NoNewLine(any_str)


def TextLimit(any_str, limit=-1):
    """ limit string for context output """
    
    if limit < 0:
        limit = Config.cfgStringLength
    
    if len(any_str) > limit:
        return any_str[:limit] + '...'
    return any_str


def DCHECK(statement, *args):
    """ debug check
    """
    assert statement, args 


def to_bool(value):
    """ convert string to bool
    """
    if str(value).lower() in ("yes", "on", "y", "true", "1"): return True
    if str(value).lower() in ("no",  "off", "n", "false", "0", "0.0", "", "none"): return False
    raise Exception('Invalid value for boolean conversion: ' + str(value)) 


