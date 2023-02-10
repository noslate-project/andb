# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import gdb
from gdb.unwinder import Unwinder
from gdb.FrameDecorator import FrameDecorator
 
import struct
import re
import itertools

from . import intf_dbg as intf
import andb.py23 as py23

inferior = gdb.selected_inferior()

class BasicTypes:

    ptr_t = gdb.lookup_type('void').pointer()
    
    u8_t = gdb.lookup_type('unsigned char')
    u16_t = gdb.lookup_type('unsigned short')
    u32_t = gdb.lookup_type('unsigned int')
    u64_t = gdb.lookup_type('unsigned long')
    
    s8_t = gdb.lookup_type('char')
    s16_t = gdb.lookup_type('short')
    s32_t = gdb.lookup_type('int')
    s64_t = gdb.lookup_type('long')

    u8p_t = u8_t.pointer()
    u16p_t = u16_t.pointer()
    u32p_t = u32_t.pointer()
    u64p_t = u64_t.pointer()
 
    s8p_t = s8_t.pointer()
    s16p_t = s16_t.pointer()
    s32p_t = s32_t.pointer()
    s64p_t = s64_t.pointer()

    p_double = gdb.lookup_type('double').pointer()

    """ 
    """
    #char16_t = gdb.lookup_type('char16_t')
    #char16p_t = char16_t.pointer()

    @classmethod
    def GetType(cls, typ):
        return Type(typ)


class Command(intf.Command, gdb.Command):
    _cxpr = None

    def __init__(self):
        gdb.Command.__init__(
            self, 
            self._cxpr, 
            gdb.COMMAND_USER,
            prefix=self._is_prefix)

    @classmethod
    def Register(cls):
        cls()

    def invoke(self, arg, tty):
        child_fn = getattr(self, 'Dispatch')
        return child_fn(arg)

    def complete(self, text, word):
        child_fn = getattr(self, 'Complete')
        return child_fn(text) 


class Block(intf.Block):

    _address = None

    @property
    def address(self):
        return self._address

    def LoadPtr(self, off):
        #b = inferior.read_memory(self._address + off, 8)
        #return struct.unpack('Q', b)[0]
        return int(gdb.Value(self._address + off).cast(BasicTypes.u64p_t).dereference())

    def LoadU64(self, off):
        #b = inferior.read_memory(self._address + off, 8)
        #return struct.unpack('Q', b)[0]
        return int(gdb.Value(self._address + off).cast(BasicTypes.u64p_t).dereference())

    def LoadU32(self, off):
        #b = inferior.read_memory(self._address + off, 4)
        #return struct.unpack('I', b)[0]
        return int(gdb.Value(self._address + off).cast(BasicTypes.u32p_t).dereference())

    def LoadU16(self, off):
        #b = inferior.read_memory(self._address + off, 2)
        #return struct.unpack('H', b)[0]
        return int(gdb.Value(self._address + off).cast(BasicTypes.u16p_t).dereference())

    def LoadU8(self, off):
        #b = inferior.read_memory(self._address + off, 1)
        #return struct.unpack('B', b)[0]
        return int(gdb.Value(self._address + off).cast(BasicTypes.u8p_t).dereference())

    def LoadDouble(self, off):
        address = self._address + off
        return Target.ReadDouble(address)

    """ String function. 
    """
    def GetCString(self, length=-1):
        return Target.ReadCStr(self.address, length=length)

    def LoadCString(self, off, length = -1):
        address = self.address + off
        return Target.ReadCStr(address, length=length)

    def LoadUString(self, off, length = -1):
        address = self.address + off
        return Target.ReadUStr(address, length=length)


class Value(intf.Value):

    # holds the gdb.Value()
    _I_value = None

    # save the address 
    _I_address = None

    # cache is pointer
    _I_is_pointer = None

    def __init__(self, pyo_value=None):
        # holds the internal Value
        if isinstance(pyo_value, Value):
            self._I_value = pyo_value._I_value 
            self._I_address = pyo_value._I_address
            self._I_is_pointer = pyo_value._I_is_pointer
        elif isinstance(pyo_value, gdb.Value):
            self._I_value = pyo_value
        elif pyo_value is None:
            self._I_value = None
        else:
            raise Exception

    def __getitem__(self, member_name_or_index):
        #print(type(member_name_or_index), member_name_or_index)
        return Value(self._I_value[member_name_or_index])

    @classmethod
    def CreateTypedAddress(cls, pyo_type, address):
        o = Value(gdb.Value(int(address)).cast(pyo_type._I_type))
        o._I_address = int(address)
        o._I_is_pointer = True
        return o

    @classmethod
    def CreateFromString(cls, type_name, address):
        t = Type.LookupType(type_name)
        if t is None:
            return None
        return cls.CreateTypedAddress(t, address)

    def Cast(self, pyo_type):
        return Value(self._I_value.cast(pyo_type._I_type))

    """ pointer and reference
    """

    @property
    def address(self):
        if self._I_address is not None:
            return self._I_address
        if self.is_pointer:
            self._I_address = int(self.__GetNonTypedefValue())
        else:
            o = self._I_value.address
            self._I_address = int(o)
        return self._I_address 

    def IsPointerType(self):
        """ return True if is a pointer type (or typedefs) 
        """
        # strip all the typedefs, check whether is pointer code.
        code = self._I_value.type.strip_typedefs().code
        #print('%s.type = %s' % (str(self), code))
        return code == gdb.TYPE_CODE_PTR
    
    is_pointer = property(IsPointerType)

    @property
    def size(self):
        return self._I_value.type.sizeof

    def GetType(self):
        return Type(self._I_value.type)

    def has(self, name):
        try:
            x = self[name]
            return x is not None
        except:
            return False

    def AddressOf(self):
        o = self._I_value.address
        if o is None:
            return None
        return Value(o)

    def Dereference(self):
        o = self._I_value.dereference()
        if o is None:
            return None
        return Value(o)

    def __GetNonTypedefValue(self):
        t = self._I_value.type.strip_typedefs()
        return Value(self._I_value.cast(t))

    """ String function. 
    """
    def GetCString(self, length=-1):
        return Target.ReadCStr(self.address, length=length)

    def LoadCString(self, off, length = -1):
        address = self.address + off
        return Target.ReadCStr(address, length=length)

    def LoadUString(self, off, length = -1):
        address = self.address + off
        return Target.ReadUStr(address, length=length)

    """ Load functions.
    """
    def LoadType(self, off, typ):
        """ Load 'type' value from offset """
        v = Value.CreateFromString(typ, self.address + off)
        return v 

    def LoadIntValue(self, off, typ):
        v = gdb.Value(self.address + off).cast(typ).dereference()
        return int(v)

    def LoadPtr(self, off):
        return self.LoadIntValue(off, BasicTypes.u64p_t)

    def LoadU8(self, off):
        return self.LoadIntValue(off, BasicTypes.u8p_t)

    def LoadU16(self, off):
        return self.LoadIntValue(off, BasicTypes.u16p_t)
    
    def LoadU32(self, off):
        return self.LoadIntValue(off, BasicTypes.u32p_t)
   
    def LoadU64(self, off):
        return self.LoadIntValue(off, BasicTypes.u64p_t)

    def LoadS8(self, off):
        return self.LoadIntValue(off, BasicTypes.s8p_t)

    def LoadS16(self, off):
        return self.LoadIntValue(off, BasicTypes.s16p_t)
 
    def LoadS32(self, off):
        return self.LoadIntValue(off, BasicTypes.s32p_t)
   
    def LoadS64(self, off):
        return self.LoadIntValue(off, BasicTypes.s64p_t)

    def LoadDouble(self, off):
        address = self.address + off
        return TarGet.ReadDouble(address)
    
    """ magic methods
    """
    def __eq__(self, other):
        
        # both Values, compare address
        if isinstance(other, Value):
            if self.address == other.address:
                return True
        
        # other is an integer
        elif isinstance(other, py23.integer_types):
            # self is pointer, compare address
            if self.is_pointer:
                if self.address == int(other):
                    return True

            # self is data, compare number
            else:
                if int(self) == int(other):
                    return True
        
        return False

    def __int__(self):
        """ GDB valpy_int implement return integer number if,
            1) is_floating_type(value)
            2) is_integral_type(value) 
            3) type->code() == TYPE_CODE_PTR
            otherwise, a Exception('Connot convert value to int') will raise.
        """
        v = self.__GetNonTypedefValue()
        return int(v._I_value) 

    def __add__(self, other):
        """ 
            C-style pointer arithmetic
            1) ptr + int, return 
            2）
        """
        if self.is_pointer and isinstance(other, py23.integer_types):
            return Value(self._I_value + other)

        # number arithmetic 
        return int(self) + int(other)

    def __sub__(self, other):
        if self.is_pointer and  isinstance(other, py23.integer_types):
            # C-Style Pointer sub
            return Value(self._I_value - other)

        # number arithmetic
        return int(self) - int(other)

    def __str__(self):
        return "(%s) %s" % (self._I_value.type, str(self._I_value))


class Type(intf.Type):

    def __init__(self, pyo_type = None):
        # holds the internal Type
        if pyo_type is None:
            self._I_type = None
        elif isinstance(pyo_type, Type):
            self._I_type = pyo_type._I_type 
        elif isinstance(pyo_type, gdb.Type):
            self._I_type = pyo_type
        else:
            raise Exception

    @classmethod 
    def LookupType(cls, type_name):
        try:
            t = gdb.lookup_type(type_name)
        except:
            return None
        return Type(t) 

    def GetPointerType(self):
        return Type(self._I_type.pointer()) 

    def GetArrayType(self, size):
        return Type(self._I_type.array(size)) 

    def GetEnumMembers(self):
        out_list = []
        for i in self._I_type.fields():
            if i.enumval is None:
                continue
            nam = i.name.split('::')[-1]
            val = i.enumval 
            out_list.append({"name": nam, "value": val}) 
        return out_list

    def SizeOf(self):
        return int(self._I_type.sizeof)

    def IsIntergralType(self):
        if self._I_type == gdb.TYPE_CODE_INT or \
            self._I_type == gdb.TYPE_CODE_ENUM or \
            self._I_type == gdb.TYPE_CODE_FLAGS or \
            self._I_type == gdb.TYPE_CODE_CHAR or \
            self._I_type == gdb.TYPE_CODE_RANGE or \
            self._I_type == gdb.TYPE_CODE_BOOL:
            return True
        return False

    def IsPointerType(self):
        code = self._I_type.strip_typedefs().code
        return code == TYPE_CODE_PTR 

    def GetTemplateArgument(self, index):
        return Type(self._I_type.template_argument(index))

    def __str__(self):
        return str(self._I_type)

    def __eq__(self):
        pass

class Thread(intf.Thread):

    @property 
    def tid(self):
        """
            InferiorThread.ptid
            [0] : Process ID 
            [1] : LWPID
            [2] : Thread ID
        """
        return self._I_thread.ptid[1] 

    @property
    def name(self):
        return self._I_thread.name

    def GetFrameTop(self):
        # by gdb.selected_frame()
        self._I_thread.switch()
        _frame = gdb.newest_frame()
        rob = Frame(_frame)
        return rob

    @classmethod
    def BacktraceCurrent(self, parser):
        v8_unwinder.Enable()
        f = gdb.newest_frame()
        for i in range(100):
            if f is None:
                break
            
            frame = Frame(f)
            v8f = parser(frame)
            if v8f:
                print("#%-2d %s" % (i, v8f.Description()))
            else:
                print("#%-2d %s" % (i, frame.Description()))
            f = f.older()
        v8_unwinder.Disable()

class Symval(intf.Symval):
    pass 

class Frame(intf.Frame):
    _decorate = None

    def GetSP(self):
        return int(self._I_frame.read_register('rsp').cast(BasicTypes.u64p_t))

    def GetPC(self):
        return int(self._I_frame.read_register('rip').cast(BasicTypes.u64p_t))

    def GetFP(self):
        return int(self._I_frame.read_register('rbp').cast(BasicTypes.u64p_t))

    def GetFunctionName(self):
        return self._I_frame.name() 

    def Decorate(self):
        if self._decorate is None:
            self._decorate = FrameDecorator(self._I_frame) 
        return self._decorate

    def GetArgs(self):
        dec = self.Decorate()
        if dec is None: return []
        out = []
        frame_args = dec.frame_args()
        if frame_args is None: return []
        for i in frame_args:
            out.append(Symval(i.symbol(), self._I_frame.read_var(i.symbol())))
        return out

    def GetLocals(self):
        dec = self.Decorate()
        if dec is None: return []
        out = []
        frame_locals = dec.frame_locals()
        if frame_locals is None: return []
        for i in frame_locals:
            print(i)
            out.append(Symval(i.symbol(), i.value()))
        return out
 
    def GetPosition(self):
        dec = self.Decorate()
        return (dec.filename(), dec.line())

class MemoryRegionInfo(intf.MemoryRegionInfo):
    pass


class MemoryRegions(intf.MemoryRegions):
    _I_regions = None

    """
        Sections Flags,
        ALLOC: Section will have space allocated in the process when loaded. Set for all sections except those containing debug information.
        LOAD: Section will be loaded from the file into the child process memory. Set for pre-initialized code and data, clear for .bss sections.
        RELOC: Section needs to be relocated before loading.
        READONLY: Section cannot be modified by the child process.
        CODE: Section contains executable code only.
        DATA: Section contains data only (no executable code).
        ROM: Section will reside in ROM.
        CONSTRUCTOR: Section contains data for constructor/destructor lists.
        HAS_CONTENTS: Section is not empty.
        NEVER_LOAD: An instruction to the linker to not output the section.
        COFF_SHARED_LIBRARY: A notification to the linker that the section contains COFF shared library information.
        IS_COMMON: Section contains common symbols.    
    """

    @classmethod
    def LoadFromSection(cls):
        v = gdb.execute('maintenance info sections', to_string = True)
        for l in v.splitlines():
            s = '\[(\d+)\]\s+([a-zA-Z0-9]+)->([a-zA-Z0-9]+) at [a-zA-Z0-9]+: (\S+) (.*)'
            m = re.search(s, l)
            if m is None:
                continue

            start_address = int(m.group(2), 16) 
            if start_address == 0:
                continue

            has_contents = 0
            v = MemoryRegionInfo.READ | MemoryRegionInfo.WRITE
            for i in m.group(5).split(' '):
                if i == 'CODE':
                    v |= MemoryRegionInfo.EXECUTE
                    v &= (~MemoryRegionInfo.WRITE)
                elif i == 'READONLY':
                    v &= (~MemoryRegionInfo.WRITE)
                elif i == 'HAS_CONTENTS':
                    has_contents = 1
            if not has_contents:
                v = 0

            pyo = MemoryRegionInfo()
            pyo._I_mode = v 
            #pyo._I_id = int(m.group(1))
            pyo._I_start_address = start_address
            pyo._I_end_address = int(m.group(3), 16)
            pyo._I_name = m.group(4)
            
            # add to _I_regions
            cls._I_regions.append(pyo)

    @classmethod
    def LoadFromProc(cls):
        """ for live process, we couldn't get memory maps from sections, 
            we need read from proc filesystem. 

            TBD: support attached process. 
        """
        pass

    @classmethod
    def Load(cls):
        if cls._I_regions is None:
            cls._I_regions = []
            cls.LoadFromSection()
        return cls._I_regions

class ConvenienceVariables(object):

    @classmethod
    def Get(cls, name):
        return gdb.convenience_variable(name)

    @classmethod
    def Set(cls, name, value):
        print("(%s) $%s = %s" % (value.type, name, value))
        gdb.set_convenience_variable(name, value)


""" Target
"""
class Target(intf.Target):

    @classmethod
    def GetThreads(cls):
        rob = []
        inferior = gdb.selected_inferior()
        for i in inferior.threads():
            pyo = Thread()
            pyo._I_thread = i
            rob.insert(0, pyo)
        return rob

    @classmethod
    def GetCurrentThread(cls):
        _thread = gdb.selected_thread()
        if _thread is None:
            return None
        robj = Thread()
        robj._I_thread = _thread
        return robj

    @classmethod
    def GetMemoryRegions(cls):
        m = MemoryRegions()
        m.Load()
        return m

    @classmethod
    def AddDwfFile(cls, filename):
        gdb.execute("add-symbol-file '%s'" % filename)

    @classmethod
    def LoadRaw(cls, name):
        """ read raw value from GDB """
        try:
            v = gdb.parse_and_eval(name)
            return int(v) 
        except:
            return None

    @classmethod
    def ReadCStr(cls, address, length=-1):
        """ decode value(char string pointer) to python string
        """
        if length == 0:
            return ''
        elif length > 0:
            # read bytes then decode
            s = Target.MemoryRead(address, length)
            return s.decode('utf8', 'ignore')
        else:
            # use gdb.Value.string()
            v = gdb.Value(address).cast(BasicTypes.s8p_t)
            return v.string('utf8', 'ignore')

    @classmethod
    def ReadUStr(cls, address, length=-1):
        """ decode value(char16_t string pointer) to python string
        """
        if length == 0:
            return ''
        elif length > 0:
            # read bytes then decode
            length *= 2 
            s = Target.MemoryRead(address, length)
            return s.decode("utf-16", 'ignore')
        else:
            # use gdb.Value.string()
            v = gdb.Value(address).cast(BasicTypes.char16p_t)
            return v.string("utf-16", 'ignore')

    @classmethod
    def ReadInt(cls, addr, byte_size=8, is_sign=0):
        #if not isinstance(address, int):
        #    print("type error: ", type(address), address)
        #    raise Exception
        address = int(addr)
       
        if not 1 <= byte_size <= 8:
            raise Exception

        if is_sign:
            if byte_size == 1:
                t = BasicTypes.s8p_t
            elif byte_size == 2:
                t = BasicTypes.s16p_t
            elif byte_size == 4:
                t = BasicTypes.s32p_t
            elif byte_size == 8:
                t = BasicTypes.s64p_t
        else:
            if byte_size == 1:
                t = BasicTypes.u8p_t
            elif byte_size == 2:
                t = BasicTypes.u16p_t
            elif byte_size == 4:
                t = BasicTypes.u32p_t
            elif byte_size == 8:
                t = BasicTypes.u64p_t
 
        v = gdb.Value(address).cast(t).dereference()
        return int(v) 

    @classmethod
    def MemoryRead(cls, address, size):
        inferior = gdb.selected_inferior()
        s = inferior.read_memory(address, size)
        return bytes(s)

    @classmethod
    def MemoryFind(cls, start, end, addr, byte_size=8):
        cmd = "find /g 0x%x, 0x%x, 0x%x" % (start, end, addr)
        out = ""
        try:
            out = gdb.execute(cmd, False, True)
        except Exception as e:
            print(start, end, e)
        lines = out.splitlines(False)
        find = []
        for i in lines:
            if i.startswith('0x'):
                end = i.find(' ')
                if end > 0:
                    i = i[:end]
                find.append(int(i, 16))
        
        if len(find) > 0:
            return find
        return None

    @classmethod
    def ReadDouble(cls, address):
        t = BasicTypes.p_double 
        v = gdb.Value(address).cast(t).dereference()
        return v

    @classmethod
    def LookupSymbol(cls, symbol_name):
        t, s = gdb.lookup_symbol(symbol_name)
        if t is None:
            return None
        v = t.value()
        return Value(v) 

    @classmethod
    def MemoryDump(cls, file_to_save, start_address, end_address):
        v = gdb.execute('dump memory %s 0x%x 0x%x' % (file_to_save, start_address, end_address), to_string = True)
        return v

""" Stack Frames
"""
class AndbFrameFilter():

    def __init__(self):
        self.name = "AndbFrameFilter"
        self.priority = 100
        self.enabled = False 
        gdb.frame_filters[self.name] = self

    def Enable(self):
        self.enabled = True

    def Disable(self):
        self.enabled = False

    def filter(self, frame_iter):
        #return itertools.imap(InlinedFrameDecorator, frame_iter)
        return AndbFrameIterator(frame_iter)

class AndbFrameIterator:
    """ filter out JS Frames 
    """
    def __init__(self, it, paser):
        self.frame_iterator = it
        self.parser = paser

    def __iter__(self):
        return self

    def next(self):
        decorator = next(self.frame_iterator)
        frm = Frame(decorator.inferior_frame())
   
        v8f = self.parser(frm)
        if v8f:
            return V8FrameDecorator(decorator)
        return decorator 


class SymValueWrapper():

    def __init__(self, symbol, value):
        self._sym = symbol
        self._val = value

    def value(self):
        return self._val

    def symbol(self):
        return self._sym

class V8FrameDecorator(FrameDecorator):

    def __init__(self, fobj):
        super(AndbFrameDecorator, self).__init__(fobj)

    def function(self):
        frame = self.inferior_frame()
        #print (frame)
        name = str(frame.name())

        #if frame.type() == gdb.INLINE_FRAME:
        name = name + " [inlined]"

        return name

    def frame_args(self):
        return [SymValueWrapper('Context', 0x3)] 

    def frame_locals(self):
        return None
   
    def filename(self):
        return 'test.js'

    def line(self):
        return 0

class FrameId(object):
    """ caller frame id
    """

    def __init__(self, sp, pc):
        self._sp = sp
        self._pc = pc

    @property
    def sp(self):
        return self._sp

    @property
    def pc(self):
        return self._pc

class V8Unwinder(Unwinder):
    """ v8 unwinder based on Frame Pointer.
    """

    def __init__(self):
        super(V8Unwinder, self).__init__("V8Unwinder")
        self.enabled = False
        gdb.unwinder.register_unwinder(None, self, True)
        print("v8 unwinder registed.")

    def Enable(self):
        self.enabled = True
        gdb.invalidate_cached_frames()

    def Disable(self):
        self.enabled = False 
        gdb.invalidate_cached_frames()
    
    def __call__(self, pending_frame):
        bp = pending_frame.read_register('rbp')
        pc = pending_frame.read_register('rip')
        sp = pending_frame.read_register('rsp')
        #gdb.write("bp(%x), sp(%x), pc(%x)\n"%(bp, sp, pc)) 

        # rbp used as frame pointer
        base = 8*1024*1024-1
        if int(bp) & ~base != int(sp) & ~base or int(bp) <= int(sp):
            return None

        if (bp == 0):
            return None

        caller_bp = bp.cast(gdb.lookup_type('long').pointer()).dereference()
        caller_pc = (bp+8).cast(gdb.lookup_type('long').pointer()).dereference()
        caller_sp = bp + 16 

        # valid rbp
        if int(caller_bp) & ~base != int(sp) & ~base:
            return None

        frameid = FrameId(sp, pc)
        unwind_info = pending_frame.create_unwind_info(frameid)
        unwind_info.add_saved_register('rip', caller_pc)
        unwind_info.add_saved_register('rsp', caller_sp)
        unwind_info.add_saved_register('rbp', caller_bp)
        #unwind_info.level = 0 
        return unwind_info

v8_unwinder = V8Unwinder()
#AndbFrameFilter

print("gdb debugger loaded")
