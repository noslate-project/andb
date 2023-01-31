# -*- coding: UTF-8 -*-
from __future__ import print_function

import lldb
from . import intf_dbg as intf
import andb.py23 as py23
import struct

debugger = lldb.debugger
target = debugger.GetSelectedTarget()
process = target.process

print("lldb.target: ", target)
print("lldb.process: ", process)

class BasicTypes:

    ptr_t = target.FindFirstType('void').GetPointerType()
    
    u8_t = target.FindFirstType('unsigned char')
    u16_t = target.FindFirstType('unsigned short')
    u32_t = target.FindFirstType('unsigned int')
    u64_t = target.FindFirstType('unsigned long')
    
    s8_t = target.FindFirstType('char')
    s16_t = target.FindFirstType('short')
    s32_t = target.FindFirstType('int')
    s64_t = target.FindFirstType('long')

    u8p_t = u8_t.GetPointerType()
    u16p_t = u16_t.GetPointerType()
    u32p_t = u32_t.GetPointerType()
    u64p_t = u64_t.GetPointerType()
 
    s8p_t = s8_t.GetPointerType()
    s16p_t = s16_t.GetPointerType()
    s32p_t = s32_t.GetPointerType()
    s64p_t = s64_t.GetPointerType()

    double_t = target.FindFirstType('double')
    p_double = double_t.GetPointerType() 

    @classmethod
    def GetType(cls, typ):
        return Type(typ)


class Command(intf.Command):

    _cxpr = None

    @classmethod
    def Register(cls):
        mod = cls.__module__
        name = cls.__name__
        cmd = "command script add -c %s.%s %s" % (mod, name, cls._cxpr)
        #print(cmd)
        debugger.HandleCommand(cmd)

    def __init__(self, debugger=None, unused=None):
        pass

    def __call__(self, debugger, command, result, internal_dict):
        
        # workaround for new SBAddress, https://reviews.llvm.org/D80848
        lldb.target = target
        lldb.process = process

        child_fn = getattr(self, 'Dispatch')
        child_fn(command)

    def get_short_help(self):
        return self.Title()

    def get_long_help(self):
        return self.Help() 

class Block(intf.Block):
    """ Block 
    """
    # what we read from this _address.
    _address = None

    @property
    def address(self):
        return self._address

    def LoadPtr(self, off):
        error = lldb.SBError()
        return process.ReadUnsignedFromMemory(self._address + off, 8, error)

    def LoadU64(self, off):
        error = lldb.SBError()
        return process.ReadUnsignedFromMemory(self._address + off, 8, error)

    def LoadU32(self, off):
        error = lldb.SBError()
        return process.ReadUnsignedFromMemory(self._address + off, 4, error)

    def LoadU16(self, off):
        error = lldb.SBError()
        return process.ReadUnsignedFromMemory(self._address + off, 2, error)

    def LoadU8(self, off):
        error = lldb.SBError()
        return process.ReadUnsignedFromMemory(self._address + off, 1, error)

    def LoadDouble(self, off):
        address = self.address + off
        return Target.ReadDouble(address)

    """ String
    """ 
    def GetCString(self):
        return Target.ReadCStr(self.address)
    
    def LoadCString(self, off, length = -1):
        address = self.address + off
        return Target.ReadCStr(address, length)

    def LoadUString(self, off, length = -1):
        address = self.address + off
        return Target.ReadUStr(address, length)


class Value(intf.Value):
    """ Represent the Value of a variable, a register or an expression.

        create:
            isolate = Value()

        reference:
            heap = isolate['heap_']
    """
    # holds the lldb.Value()
    _I_value = None

    """ saved address value for lldb optimization
    """
    _I_is_pointer = None
    _I_address = None

    # holds the SBError, some of lldb apis referenced.
    _I_error = lldb.SBError()

    def __init__(self, pyo_value = None):
        # holds the internal Value
        if pyo_value is None:
            self._I_value = None
        elif isinstance(pyo_value, Value):
            self._I_value = pyo_value._I_value
            self._I_address = pyo_value._I_address
            self._I_is_pointer = pyo_value._I_is_pointer
        elif isinstance(pyo_value, lldb.SBValue):
            self._I_value = pyo_value
        else:
            raise Exception

    def __getitem__(self, member_name_or_index):
        if isinstance(member_name_or_index, int):
            v = self._I_value.GetChildAtIndex(
                    member_name_or_index, lldb.eNoDynamicValues, True)
        elif isinstance(member_name_or_index, str):
            v = self._I_value.GetChildMemberWithName(member_name_or_index)
        else:
            raise Exception
        
        "lldb use Synthetic to format pretty print, here get the raw value"
        if v.IsSynthetic():
            #print("IsSynthetic", v)
            v = v.GetNonSyntheticValue()
            #print(v)

        return Value(v) 

    @classmethod
    def CreateTypedAddress(cls, pyo_type, address):
        # only for 64b
        a = lldb.SBData.CreateDataFromInt(address, size=8, target=target, ptr_size=8)
        v = target.CreateValueFromData('_z', a, pyo_type._I_type)
        o = Value(v)
        o._I_address = int(address)
        o._I_is_pointer = True 
        return o 

    @classmethod
    def CreateFromString(cls, type_name, address):
        print(cls.__name__, type_name, address)
        t = Type.LookupType(type_name)
        if t is None:
            return None
        return cls.CreateTypedAddress(t, address) 

    def Cast(self, pyo_type):
        return Value(self._I_value.Cast(pyo_type._I_type))

    @property
    def is_pointer(self):
        if self._I_is_pointer is not None:
            return self._I_is_pointer
        self._I_is_pointer = self._I_value.TypeIsPointerType()
        return self._I_is_pointer

    @property
    def address(self):
        if self._I_address is not None:
            return self._I_address
        if self.is_pointer:
            self._I_address = int(self._I_value.unsigned)
        else:
            self._I_address = int(self._I_value.addr)
        #print(self._I_value, ", address: 0x%x" % self._I_address)
        return self._I_address

    @property
    def size(self):
        return int(self._I_value.size)

    def GetType(self):
        return Type(self._I_value.GetType())

    def has(self, name):
        try:
            x = self[name]
            #print ("has (%s) = %s, %s" % (name, x.size > 0, x))
            return x.size > 0 
        except:
            return False

    def AddressOf(self):
        """ return a pointer value if valid.
        """
        o = self._I_value.AddressOf()
        if o.IsValid():
            return Value(o)
        return None

    def Dereference(self):
        """ return reference value if valid.
        """
        o = self._I_value.Dereference()
        if o.IsValid(): 
            return Value(o)
        return None

    def LoadType(self, off, typ):
        """ Load 'type' value from offset 

            return: Value()

            e.g. iso.LoadType(38176, 'v8::internal::Heap')
        """
        v = Value.CreateFromString(typ, self.address + off)
        return v

    def GetCString(self):
        return Target.ReadCStr(self.address)
    
    def LoadCString(self, off, length = -1):
        address = self.address + off
        return Target.ReadCStr(address, length)

    def LoadUString(self, off, length = -1):
        address = self.address + off
        return Target.ReadUStr(address, length)

    def LoadIntValue(self, off, size=1, is_signed = True):
        e = lldb.SBError()
        addr = self.address + off
        v = process.ReadUnsignedFromMemory(addr, size, e)
        return int(v)

    def LoadPtr(self, off):
        return self.LoadIntValue(off, 8, is_signed=False)
 
    def LoadU8(self, off):
        return self.LoadIntValue(off, 1, is_signed=False)

    def LoadU16(self, off):
        return self.LoadIntValue(off, 2, is_signed=False)

    def LoadU32(self, off):
        return self.LoadIntValue(off, 4, is_signed=False)
   
    def LoadU64(self, off):
        return self.LoadIntValue(off, 8, is_signed=False)

    def LoadS8(self, off):
        return self.LoadIntValue(off, 1, is_signed=True)

    def LoadS16(self, off):
        return self.LoadIntValue(off, 2, is_signed=True)
    
    def LoadS32(self, off):
        return self.LoadIntValue(off, 4, is_signed=True)
   
    def LoadS64(self, off):
        return self.LoadIntValue(off, 8, is_signed=True)

    def LoadDouble(self, off):
        addr = self.address + off
        return Target.ReadDouble(addr)

    def __int__(self):
        """ return int of the Value (address)
        """
        if self.is_pointer:
            return self.address
        elif self._I_value.GetByteSize() <= 8:
            return int(self._I_value.unsigned)
        #print("andb.error: Cannot convert Value to int.")
        raise Exception

    def __add__(self, other):
        if self.is_pointer and isinstance(other, py23.integer_types):
            type = self.GetType()
            new_address = self.address + (other * type.SizeOf())
            return self.CreateTypedAddress(type, new_address)
        return int(self) + int(other)

    def __sub__(self, other):
        if self.is_pointer and isinstance(other, py23.integer_types):
            type = self.GetType()
            new_address = self.address - (other * type.SizeOf())
            return self.CreateTypedAddress(type, new_address)
        return int(self) - int(other)

    def __str__(self):
        return str(self._I_value)

class Type(intf.Type):
    """ Represent a data type.
    """

    # holds the lldb.Type()
    _I_type = None

    def __init__(self, pyo_type = None):
        # holds the internal Type
        if pyo_type is None:
            self._I_type = None
        elif isinstance(pyo_type, Type):
            self._I_type = pyo_type._I_type
        elif isinstance(pyo_type, lldb.SBType):
            self._I_type = pyo_type
        else:
            raise Exception

    @classmethod
    def LookupType(cls, type_name):
        ts = target.FindTypes(type_name)
        for t in ts:
            return Type(t)
        return None 
 
    def GetPointerType(self):
        """ return a pointer type to self
        """
        return Type(self._I_type.GetPointerType()) 

    def GetArrayType(self, size):
        """ returns a array type with the given constant size 
        """
        # fix <float> to <int>
        size = int(size)
        return Type(self._I_type.GetArrayType(size))

    def SizeOf(self):
        """ return the type size
        """
        return int(self._I_type.GetByteSize())

    def GetEnumMembers(self):
        """ get enum values from the type 
        """
        array = self._I_type.get_enum_members_array()
        out_list = []
        for i in array:
            out_list.append({"name": i.name, "value": i.unsigned})
        return out_list

    def GetTemplateArgument(self, index):
        return Type(self._I_type.GetTemplateArgumentType(index))

    def __str__(self):
        """ return short string
        """
        return self._I_type.GetDisplayTypeName()

class Dwf:

    @classmethod
    def LoadConst(cls, typ, name):
        # TBD: lldb can't read const variable in class.
        return None 

    @classmethod
    def LoadInternalConst(cls, name):
        # TBD: lldb can't read const variable in class.
        return None 

class Thread(intf.Thread):

    def GetFrameTop(self):
        return Frame(self._I_thread.frame[0]) 

    @classmethod
    def BacktraceCurrent(cls, parser):
        thread = process.GetSelectedThread()
        print(thread)
        num_frames = thread.GetNumFrames() 
        for i in range(0, num_frames):
            frame = Frame(thread.GetFrameAtIndex(i))
            v8f = parser(frame)
            if v8f:
                print(" #%-02d %s" % (i, v8f.Description()))
            else:
                print(" #%-02d %s" % (i, frame.Description()))


class Symval(intf.Symval):
    pass


class Frame(intf.Frame):

    def GetSP(self):
        return int(self._I_frame.GetSP())

    def GetPC(self):
        return int(self._I_frame.GetSP())

    def GetFP(self):
        return int(self._I_frame.GetFP())

    def GetFunctionName(self):
        return self._I_frame.name

    def GetArgs(self):
        out = []
        args = self._I_frame.args
        if args is None:
            return [] 
        
        for i in args:
            out.append(Symval(i.name, i.value)) 
        return out 

    def GetPosition(self):
        line_entry = self._I_frame.line_entry
        return (line_entry.file, line_entry.line)


class MemoryRegionInfo(intf.MemoryRegionInfo):
    pass


class MemoryRegions(intf.MemoryRegions):

    @classmethod
    def LoadMemoryRegions(cls):
        mrl = process.GetMemoryRegions()
        size = mrl.GetSize()
        for i in range(size):
            mri = lldb.SBMemoryRegionInfo()
            mrl.GetMemoryRegionAtIndex(i, mri)

            v = 0
            if mri.IsExecutable(): v |= MemoryRegionInfo.EXECUTE
            if mri.IsReadable(): v |= MemoryRegionInfo.READ
            if mri.IsWritable(): v |= MemoryRegionInfo.WRITE

            pyo = MemoryRegionInfo()
            pyo._I_mode = v
            pyo._I_start_address = int(mri.GetRegionBase())
            pyo._I_end_address = int(mri.GetRegionEnd())

            # lldb didn't support region name, use a auto index name
            pyo._I_name = "load_%d" % i 

            cls._I_regions.append(pyo)

    @classmethod
    def Load(cls):
        cls.LoadMemoryRegions()

class ConvenienceVariables(object):

    @classmethod
    def Get(cls, name):
        pass

    @classmethod
    def Set(cls, name, value):
        str_name = "$%s" % name
        str_type = value.GetTypeName()
        str_addr = hex(value.GetValueAsUnsigned())
        print("(%s) %s = %s" % (str_type, str_name, str_addr))
        debugger.HandleCommand("expr %s %s = (%s) %s"%(
            str_type, str_name, str_type, str_addr))

""" Target 
"""
class Target(intf.Target):

    # holds the SBError for lldb apis
    _error = lldb.SBError()
    _error2 = lldb.SBError()

    @classmethod
    def LoadRaw(cls, value_name):
        value_name = value_name.replace("'", "")
        s = target.FindSymbols(value_name)
        if not s.IsValid():
            return None
        
        addr = s[0].symbol.addr.GetLoadAddress(target)
        size = s[0].symbol.end_addr.GetLoadAddress(target) - addr
        error = lldb.SBError()
        v = process.ReadUnsignedFromMemory(addr, size, error)
        return int(v)

    @classmethod
    def GetThreads(cls):
        rob = []
        #process = lldb.debugger.GetSelectedTarget().process
        num_threads = process.GetNumThreads()
        for i in range(num_threads):
            thread = process.GetThreadAtIndex(i)
            pyo = Thread()
            pyo._I_thread = thread
            rob.append(pyo)
        return rob

    @classmethod
    def GetMemoryRegions(cls):
        m = MemoryRegions()
        m.Load()
        return m

    @classmethod
    def AddDwfFile(cls, filename):
        debugger.HandleCommand("im add '%s'" % filename) 

    @classmethod
    def ReadInt(cls, addr, byte_size=8, is_sign=0):
        #if not isinstance(address, int):
        #    raise Exception
        address = int(addr)
        
        if not 1 <= byte_size <= 8:
            raise Exception

        # read unsgiend int from memory by byte_size
        v = process.ReadUnsignedFromMemory(address, byte_size, cls._error)
        if not cls._error.Success():
            print("andb.error: ", cls._error)
            return None

        if is_sign:
            if byte_size == 8:
                v = py23.SIC.toS64(v) 
            elif byte_size == 4:
                v = py23.SIC.toS32(v) 
            elif byte_size == 2:
                v = py23.SIC.toS16(v) 
            elif byte_size == 1:
                v = py23.SIC.toS8(v) 
            else:
                raise Exception
        return int(v)

    @classmethod
    def _ReadCStringFromTaget(cls, address, length=-1):
        sz = []

        max_size = 4096
        if length > 0:
            max_size = length

        while max_size > 0:
            m = min(128, max_size)
            s = target.ReadMemory(lldb.SBAddress(address, target), m, cls._error)
            max_size -= m 

            # compat with py2/3
            if not isinstance(s, str):
                s = s.decode('ascii')

            for c in s:
                if c == chr(0):
                    return "".join(sz)
                sz.append(c)

        return "".join(sz) 

    @classmethod
    def ReadCStr2(cls, address, length=-1):
        if not isinstance(address, int):
            raise Exception

        if length == 0:
            return ""
    
        max_size = 4096
        if length > 0:
            max_size = length

        # read C string of at most 4096 bytes from address
        s = process.ReadCStringFromMemory(address, max_size+1, cls._error)
        if not cls._error.Success():
            print("andb.error: ", cls._error)
            return None

        """ lldb can't read cstring from binary,
            fallback to target.ReadMemory()
        """
        if s == "":
            s = cls._ReadCStringFromTaget(address, length)

        # compact with py3
        if isinstance(s, str):
            return s
        return s.decode('ascii')

    @classmethod
    def ReadCStr(cls, address, length=-1):
        if length == 0:
            return ""
       
        elif length > 0:
            s = process.ReadMemory(address, length, cls._error)
            cls._error.Clear()
            return s.decode('utf8', 'ignore')

        s = process.ReadCStringFromMemory(address, 4096, cls._error)
        cls._error.Clear()
        return s

    @classmethod
    def ReadUStr(cls, address, length=-1):
        if length == 0:
            return ""
        elif length > 0:
            size = length * 2
            
            s = process.ReadMemory(address, size, cls._error)
            cls._error.Clear()
            return s.decode('utf-16', 'ignore')
        raise Exception('TBD')

    @classmethod
    def MemoryRead(cls, address, size):
        s = process.ReadMemory(address, size, cls._error)
        cls._error.Clear()
        return bytes(s)

    @classmethod
    def MemoryFind(cls, start, end, addr, byte_size=8):
        cmd = "mem find -c 100000 -e 0x%x -- 0x%x 0x%x" % (addr, start, end)
        out = ""
        try:
            interpreter = debugger.GetCommandInterpreter()
            res = lldb.SBCommandReturnObject()
            interpreter.HandleCommand(cmd, res)
            out = res.GetOutput()
        except Exception as e:
            print(start, end, e)
        lines = out.splitlines(False)
        find = []
        for i in lines:
            if i.startswith('data found at '):
                end = i.find('0x')
                if end > 0:
                    i = i[end:]
                find.append(int(i, 16))
        
        if len(find) > 0:
            return find
        return None

    @classmethod
    def MemoryDump(cls, file_to_save, start_address, end_address):
        size = end_address - start_address
        data = cls.MemoryRead(start_address, size)
        with open(file_to_save, 'wb') as f:
            f.write(data)

    @classmethod
    def ReadDouble(cls, address):
        data = cls.MemoryRead(address, 8)
        a = struct.unpack('d', data) 
        return a[0]

print('lldb debugger loaded')
