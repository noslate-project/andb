# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import os
import re
import shlex

from . import dbg_select as dbg
from andb.fmt import Dwf as DwfClass
import andb.py23 as Py23
from andb.utility import Logging as log

# only support 64bits
PointerSize = 8 

# holds a tag value, smi, tag pointer or address
_tag_type = dbg.Type.LookupType('unsigned long')

def AllSubClasses(cls):
    """ get all subclesses recusive """
    #a= set(cls.__subclasses__()).union(
    #    [s for c in cls.__subclasses__() for s in AllSubClasses(c)])
   
    all_cls = {}
    ordered_cls = []

    def AddClass(cls):
        if cls not in all_cls:
            all_cls[cls] = 1
            ordered_cls.append(cls)

    def WalkClass(cls):
        subcls = cls.__subclasses__()
        for c in subcls:
            AddClass(c)
        
        # recursive
        for c in subcls:
            WalkClass(c)

    WalkClass(cls)
    return ordered_cls

class Struct(dbg.Value):
    """ represets a C++ Structure 

        Struct(memory_address) represents a C++ Structure in memory.

        eg. 
            s = Struct(0x38d0138)
            heap = s['heap_']   // s.heap_
    """

    # c++ class name
    _typeName = None

    # gdb.type for _typeName
    _S_type = None

    def __init__(self, address):
        """ accept address(int) or dbg.Value.
        """
        if isinstance(address, Py23.integer_types):
            val = dbg.Value.CreateTypedAddress(self._S_type, address)
        elif isinstance(address, dbg.Value):
            val = address.Cast(self._S_type)
        else:
            print(type(address), address)
            raise Exception
        super(Struct, self).__init__(val)

    @classmethod
    def LoadDwf(cls):
        t = dbg.Type.LookupType(cls._typeName)
        if t is None:
            log.warn("struct '%s' not found." % (cls.__name__))
            return
        cls._S_type = t.GetPointerType()
        log.verbose("loaded struct '%s'." % (cls.__name__))

    @classmethod
    def LoadAllDwf(cls):
        for c in AllSubClasses(cls):
            c.LoadDwf()

    @property
    def type(self):
        return self._S_type

    @property
    def name(self):
        return self._typeName

    @classmethod
    def IsDisabled(cls):
        """ tell whether the structure has been diabled due to dwarf absence """
        return cls._S_type is None

class Enum(object):
    """ represents a C++ Enum  
        
        InstanceType.JS_OBJECT_TYPE
        InstanceType.Name(169)
        InstanceType.
    """

    # v8 c++ type string
    _typeName = None 

    # holds gdb.type
    _E_type = None

    # cache for type to name reference
    _E_nameMap = {} 

    @classmethod
    def LoadDwf(cls):
        #if cls._typeName is None:
        #    return

        cls._E_type = dbg.Type.LookupType(cls._typeName)
        if cls._E_type is None:
            print("enum '%s' is not found." % (cls._typeName))
            return

        print("loaded enum '%s'."%(cls.__name__))
        cache = {}
        for i in cls._E_type.GetEnumMembers():
            name = i['name']
            enumval = int(i['value'])

            # add Attribute
            if hasattr(cls, name):
                v = getattr(cls, name)
                if v != enumval:
                    print("%s::%s (%d) = %d"%(cls._E_type, name, v, enumval))
            setattr(cls, name, enumval)

            # save cache
            v = int(enumval)
            if v in cache:
                cache[v].append(name)
            else:
                cache[v] = [name]
        setattr(cls, '_E_nameMap', cache) 

    @classmethod
    def LoadAllDwf(cls):
        for c in AllSubClasses(cls):
            c.LoadDwf()

    @classmethod
    def Find(cls, name):
        if hasattr(cls, name):
            return getattr(cls, name) 
        return None

    @classmethod
    def isType(cls, name, num):
        kMapType = cls.Find(name)
        if num == kMapType:
            return True
        return False

    @classmethod
    def inRange(cls, low, high, num):
        lowType = cls.Find(low)
        highType = cls.Find(high)
        if lowType == highType:
            return False
        if lowType <= num <= highType:
            return True
        return False

    @classmethod
    def getNames(cls, num):
        """ return all Enumerator names with the value """
        num = int(num)
        if not num in cls._E_nameMap:
            return []
        return cls._E_nameMap[num]

    @classmethod
    def bestName(cls, num):
        """ return the best name for the Enumerator 
            
            Enumerator lower the better,
            Enumerator should not be 'first' starts.
        """ 
        pre = "%d" % num
        for s in cls.getNames(num):
            i = s.lower()
            if i.startswith("first"):
                pre = s
                continue
            return s
        return pre

    @classmethod
    def Name(cls, num):
        """ Return the String of the Enumerator """
        return cls.bestName(num)

    @classmethod
    def CamelName(cls, num):
        """ Return name inform of Camel-case.
            e.g. PROTOTYPE_INFO_TYPE to 'PrototypeInfo'
        """
        n = cls.bestName(num)
        s = n.replace('-', '_')
       
        # type 1: XXX_YYY_ZZZ
        if s.find('_') > 0:
            y = []
            for x in s.split('_'):
                y.append(x.lower().capitalize())
            return ''.join(y)
       
        # type 2: kXxxYxxZzz
        elif re.match('^k[A-Z]', s) is not None:
            return s[1:]
 
        # type 3: kxxx_string
        elif re.match('^k[a-z_]+_string', s) is not None:
            return s[1:]
        
        # we dont' support
        return n


class CommandsDispatcher(object):
    """ for lldb doesn't support sub commands under python SDK,
        we have to implement a command dispatcher.

        [v8] : _is_prefix
          + version
          + inspect
          + isolate
            + guess
          + heap
            + walk 
            + snapshot 
            + page
        [shinki] : _is_prefix
          ...
        [node] : _is_prefix
          ...

        for gdb:
            class MyCommand(gdb.Command):
                def __init__(self):
                    gdb.Command.__init__(self, "v8", COMMAND_USER)
                def invoke(self, arg, tty):
                    print arg
    
        for lldb:
            class MyCommand(object):
                def __init__(self, debugger, unused):
                    pass
                def __call__(self, debugger, command, exe_ctx, result):
                    pass
                
            in __lldb_init_module(debugger, unused):
                debugger.HandleCommand('command script add -c <module>.MyCommand v8')

        so we need a "prefix" class to register to debugger's command line.
        dispatch any sub commands in 'invoke' or '__call__' function.
         
    """
    _I_top = [None, {}]

    @classmethod
    def WalkSubCommands(cls, ds):
        for key in ds[1]:
            cmd = ds[1][key][0]
            yield key,cmd

    @classmethod
    def ShowCommandHelp(cls, ds):
        if ds[0] is not None:
            print(ds[0].Help())

        if len(ds[1]) > 0:
            print("Subcommands,")
            for key,cmd in cls.WalkSubCommands(ds):
                if cmd is None:
                    title = "See '... %s ?'" % key
                else:
                    title = cmd.Title()
                print("  %-12s -- %s" % (key, title))

    @classmethod
    def ShowCommandList(cls, ds, word = ''):
        out = []
        for key in ds[1]:
            if key.startswith(word):
                out.append(key)
        print(" ".join(out))

    @classmethod
    def Register(cls, pyo_cmd):
        """ register command object to tree.
            ds[0] holds the command object, 
            ds[1] are subcommands in dict().
        """
        cxy = pyo_cmd._cxpr.split(' ')
        ds = cls._I_top
        for i in cxy:
            if i not in ds[1]:
                ds[1][i] = [None, {}]
            ds = ds[1][i]
        ds[0] = pyo_cmd
        print("command '%s' registered." % (pyo_cmd._cxpr))
 
    @classmethod
    def Dispatch(cls, prefix, command):
        """ find the command object match the input,
            dispatch the input to user invoke function,
            or an error message poped if not found.

            always return None
        """
        argv = shlex.split(command)

        # find ds by prefix
        cxy = prefix.split(' ')
        ds = cls._I_top
        for i in cxy:
            if i not in ds[1]:
                raise Exception
            ds = ds[1][i]

        last = 0
        for i in range(len(argv)):
            word = argv[i]
            conf = []

            # '?' give the user all sub commands
            if word == '?':
                cls.ShowCommandHelp(ds)
                return

            # parse the word
            for a in ds[1]:
                if a == word:
                    ds = ds[1][a]
                    last = i+1
                    break
                elif a.startswith(word):
                    conf.append([ds[1][a], i+1])

            # what we find only match 
            if len(conf) == 1:
                ds = conf[0][0]
                last = conf[0][1]

            # more than 1
            elif len(conf) > 1:
                print("'%s' is an ambiguous command, candidate list:" % (word))
                cls.ShowCommandList(ds, word)
                return
       
        if ds[0] is not None:
            cmd = ds[0]
            cmd.invoke(argv[last:])
        else:
            print("error: '%s' is not a valid command." % command)

    @classmethod
    def Complete(cls, prefix, text):
        """ complete function, only work in gdb.
            return keywords list or []
        """
        args = text.split(" ")
        ds = cls._I_top[1][prefix]
        mat = []
        for i in args:
            for a in ds[1]:
                if a == i:
                    ds = ds[1][a]
                    break
                elif a.startswith(i):
                    mat.append(a)
        return mat


class Command(dbg.intf.Command):
    
    _is_prefix = False 

    @classmethod
    def RegisterAll(cls):
        all_cmds = sorted(AllSubClasses(cls), key=lambda c: c._cxpr)
        for c in all_cmds:
            CommandsDispatcher.Register(c())

    @classmethod
    def Register(cls):
        CommandsDispatcher.Register(cls())

    def __init__(self):
        pass


class CommandPrefix(dbg.Command):
   
    _is_prefix = True 

    @classmethod
    def RegisterAll(cls):
        all_cmds = sorted(AllSubClasses(cls), key=lambda c: c._cxpr)
        for c in all_cmds:
            c.Register()

    def Dispatch(self, command):
        CommandsDispatcher.Dispatch(self._cxpr, command)

    def Complete(self, text):
        return CommandsDispatcher.Complete(self._cxpr, text)


""" Slot/Slots is for quick get Pointers in [start_address, end_address).
    for Value().Dereference() is more expensive.
"""

def Slot(address):
    #t = dbg.Type.LookupType('unsigned long').GetPointerType()
    #v = dbg.Value.CreateTypedAddress(t, address)
    v = dbg.Target.ReadInt(address)
    return v

class Slots:
    """ return ptrs in slots between start_address and end_address.
        end_address is not inclueded.

        start_address 0x00 : [ slot 0 ]
                      0x08 : [ slot 1 ]
                      0x10 : [ slot 2 ]
                      0x18 : [ slot 3 ]
          end_address 0x20 :

        example,
            for tag in Slots(0, 0x20):
                print(tag)
    """
    def __init__(self, start_address, end_address):
        """ start_address : int or Value
            end_address : int or Value
        """
        addr = int(start_address)
        addr_end = int(end_address)
        slots = (addr_end - addr) // 8

        self._next_slot = 0
        self._max_slot = slots
        self._start_addr = addr

    def __iter__(self):
        return self

    def __next__(self):
        """ iter.next for py3"""
        if self._next_slot < self._max_slot:
            addr = self._start_addr + (self._next_slot * 8)
            v = dbg.Target.ReadInt(addr)
            #print(addr, v, type(v))
            self._next_slot += 1
            return v
        raise StopIteration 

    def next(self):
        """ iter.next for py2 """
        return self.__next__()


class BitField22222(int):
    """ helper for define Flags.
    """

    @classmethod
    def Bit(cls, val, pos):
        return (val >> pos) & 1

    @classmethod
    def Bits(cls, val, start, end):
        size = end - start + 1
        return cls.BitSize(val, start, size)

    @classmethod
    def BitSize(cls, val, pos, size):
        v = 0
        x = val
        x = x >> pos
        for i in range(size):
            if x & 0x1:
                v |= (1 << i)
            x = x >> 1
        return v

