# -*- coding: UTF-8 -*-
from __future__ import print_function, division

""" defined a common debugger interface.
"""

class Command(object):
    """ Register User-defined Command
    """

    # command line express
    _cxpr = None

    # is a prefix 
    _is_prefix = False

    # __doc__ as help string

    def __init__(self):
        raise NotImplementedError()

    def Title(self):
        if self.__doc__:
            # get first line of docstring as title
            return self.__doc__.splitlines()[0].lstrip()
        return ""

    def Help(self):
        if self.__doc__:
            return self.__doc__.lstrip()
        return "This command is not documented."

class Block(object):
    """ holds a block memory, but not a struct or class.
    """
    pass

class Value(object):
    """ represents a Value in debugger.
        
    A dbg.Value holds the memory value it obtains from the corefile. 

    There two major kinds Value in debugger,
        1) holds a memory structure directly in memory. 
           simply like a DOT operator in c/c++, eg. a_value.member to reference.
           in this case, a_value is the dbg.Value, member is the name for reference.

        2) holds a pointer value
           we still want to reference it by 'a_value.member', instead of a_value->member. 
           python don't have the 'arrow' operater.

    Create Entry,
        1) create from type and address. 
            create a Value to access a Named Class/Structure from corefile.

            eg. 
            obj = JSObject(0x12345)
            the python calss 'JSObject' has the C++ type to v8, in this case 'v8::internal::JSObject',
            and create a JSObject for address 0x12345.

            map = obj.map       # now we can get hidden class by obj.map 
            instance_type = map.instance_type

            the pointer address only saved in Debugger, corefile doesn't know it.

        2) create by structure/array member reference.
            2.1) inner structure 
            class Isolate {
                Heap heap_;     // the Isolate holds the whole Heap contents. 
            };

            isolate['heap_']['old_space_']  # isolate->heap_.old_space_;

            the heap_ doesn't have a pointer, but it can be calculated by offset of isolate address.

            2.2) pointer 
            class Isolate {
                GlobalHandles* global_handles_;  // the Isolate holds the pointer to GlobalHandles. 
            };
            isolate['global_handles_']['blocks_'] # isolate->global_handles_->blocks_;
            the isolate class stored the global_handles_ address in memory, 
            and the pointer has the memory address either.

    API,

    Value.address
        return the address of the memory the value is, it's the absolutly memory address.
        that means the address always indicats the block/structure where stored in memory.

    Value.is_pointer
        return true if the Value.type is a pointer type.

    Value.size
        return the byte size from type.

    Value.__getitem__(member_name_or_index)
        in c/c++ we uses "DOT" or "ARROW" for a member reference, but in andb we uses '[]' to
        reference all the members. 

        eg. 
        isolate['heap_'] // isolate->heap_
        array[0] // array[0]

    Value.AddressOf
        return a new Value holds the   

    Value.LoadXXX()
        if the value don't have a structure/class, we use LoadXXX functions to read memory directly.
        it's commonly used in v8.HeapObjects.

    Value.__eq__(other)
        check the other object is same to this Value.

    Value.__int__
        int() call to get the integer number.
        for pointer type, return the  pointer (address),
        for non pointer type, if basic integer types, return the integer number,
        for non integer type, exception should be performed.

    Value.__add__
        if the value is integer, return the new number added.
        in c/c++ pointer can also be added, thus return a new Value holds the address added.

    """

    # inner value (gdb.Value or lldb.SBValue)
    _I_value = None

    def __init__(self, pyo_value):
        raise NotImplementedError()

    @classmethod
    def CreateTypedAddress(cls, pyo_type, address):
        """ Create a Value from type and address

            The API imples a Pointer type.

            e.g.
               t = Type.LookupType('v8::internal::Isolate')
               v = Value.CreateTypedAddress(t, 0x416ec60)
               print(v)
               # (v8::internal::Isolate *) z_2 = 0x000000000416ec60

            return: Value()
        """
        raise NotImplementedError()

    @classmethod
    def CreateFromString(cls, type_name, address):
        """ Create from type_name and address 

            keep same as LoadTypedAddress().
            only the type_name should be a python string.

            return: Value()
        """
        raise NotImplementedError()

    def Cast(self, pyo_type):
        """ Cast as 'pyo_type' in new dbg.Value()

            return: Value()
        """
        raise NotImplementedError()

    def __getiterm__(self, key):
        """ support quick member reference

            iso = Value()
            heap = iso['heap_']

            return: Value()
        """
        raise NotImplementedError()

    """ Ponter, Reference supports

        // b = &a;
        Value.AddressOf()

        // b = *a;
        Value.Dereference()

        // b = (long)&a;  // a is data
        // or  b = (long)a;  // a is pointer
        Value.address always returns data's memory load address.;
    """

    def AddressOf(self):
        """ return the pointer to the value. 
            
            // a = isolate.heap_
            Heap a = isolate.heap_;
            // b = a.AddressOf()
            Heap *b = &a;

            AddressOf() for return the pointer to the member.
           
            return: Value() or None

            example, 
               # (v8::internal::Heap)(heap)
               heap = $isolate->heap_   # heap_ is struct member of Isolate
               # (v8::internal::Heap *)(heap.AddressOf())
               print(heap.AddressOf())     # show heap_'s address
        """
        raise NotImplementedError()

    def Dereference(self):
        """ for pinter data types, the method returns a new Value() object whose
            contents is the object pointed to by the pointer.
           
            // a = Value()
            char *a = value;
            // b = a.Dereference()
            char b = *a;

            return: Value() or None
        """
        raise NotImplementedError()

    @property
    def address(self):
        """ always return the address of the value. 
            return: int
        """
        raise NotImplementedError()

    @property
    def GetType(self):
        return NotImplementedError()

    """ load operaters,
        get data from member 
    """

    @property
    def is_pointer(self):
        """ return the value whether a pointer type.
        """
        raise NotImplementedError()

    def GetCString(self):
        """ return python string of the value
            
            return: 'utf-8' coded str
        """
        raise NotImplementedError()

    """ Load Functions, load offset value 
    """
    def LoadType(self, off, typ):
        """ Load 'type' value from offset 
            offset is the start address of a inner struct.

            return: Value()

            e.g. iso.LoadType(38176, 'v8::internal::Heap')
        """
        raise NotImplementedError()

    def LoadCString(self, off, length = -1):
        raise NotImplementedError()
 
    def LoadUString(self, off, length = -1):
        raise NotImplementedError()

    def LoadPtr(self, off):
        raise NotImplementedError()
        #return int(self.LoadType(off, self.ptr_t).Dereference())

    def LoadU8(self, off):
        raise NotImplementedError()
        #return int(self.LoadType(off, self.u8_t).Dereference())

    def LoadU16(self, off):
        raise NotImplementedError()
        #return int(self.LoadType(off, self.u16_t).Dereference())
    
    def LoadU32(self, off):
        raise NotImplementedError()
        #return int(self.LoadType(off, self.u32_t).Dereference())
   
    def LoadU64(self, off):
        raise NotImplementedError()
        #return int(self.LoadType(off, self.u64_t).Dereference())

    def LoadS8(self, off):
        raise NotImplementedError()

    def LoadS16(self, off):
        raise NotImplementedError()
 
    def LoadS32(self, off):
        raise NotImplementedError()
   
    def LoadS64(self, off):
        raise NotImplementedError()

    @property
    def _unsigned(self):
        s = self.size
        if s == 8:
            return self.LoadU64(0)
        elif s == 4:
            return self.LoadU32(0)
        raise NotImplementedError("not supported size = %d" % s)

    @property
    def _signed(self):
        s = self.size
        if s == 8:
            return self.LoadS64(0)
        elif s == 4:
            return self.LoadS32(0)
        raise NotImplementedError

    def LoadBit(self, off, pos):
        if pos < 8:
            x = self.LoadU8(off)
        elif pos < 16:
            x = self.LoadU16(off)
        elif pos < 32:
            x = self.LoadU32(off)
        else:
            raise("out of range")
        return x & ( 1 << pos ) 

    def LoadBits(self, off, start, end):
        if end < 8:
            x = self.LoadU8(off)
        elif end < 16:
            x = self.LoadU16(off)
        elif end < 32:
            x = self.LoadU32(off)
        else:
            raise("out of range")
        v = 0
        x = x >> start
        for i in range(end - start + 1):
            if x & 0x1:
                v |= ( 1 << i )
            x = x >> 1
        return v

    def LoadBitSize(self, off, pos, size):
        start = pos
        end = pos + size - 1
        return self.LoadBits(off, start, end)

    """ useful bit clac
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
                v |= ( 1 << i )
            x = x >> 1
        return v

    """ string 
    """
    def __str__(self):
        """ str() return short description
        """
        raise NotImplementedError()

    """ arithmetic operaters 
    """
    def __int__(self):
        """ int(). return int of the value

            for pointer value:
                iso = Value()
                int(iso) = 0x416ec60  # return the pointer. 

            for struct value:
                heap = iso['heap_']
                int(heap) = 0x4286990 # return the struct start address.
        """
        raise NotImplementedError()

    def __add__(self, other):
        """ value + offset. return new value of the new address.
            return Value()
        """
        return int(self) + int(other)

    def __radd__(self, other):
        """ offset + value. return new value of the new address.
            return Value()
        """
        return int(self) + int(other)

    def __iadd__(self, other):
        """ value += offset. return new value of the new address.
            return Value()
        """
        return int(self) + int(other)

    """ logical operaters
    """
    def __and__(self, other):
        """ v & other """
        return int(self) & int(other)
    
    def __or__(self, other):
        """ v | other """
        return int(self) | int(other)

    def __xor__(self, other):
        """ v ^ other """
        return int(self) ^ int(other)
 
    def __rand__(self, other):
        """ other & v """
        return int(self) & int(other)

    def __ror__(self, other):
        """ other | v """
        return int(self) | int(other)
   
    def __rxor__(self, other):
        """ other ^ v """
        return int(self) ^ int(other)

    def __iand__(self, other):
        """ v &= other """
        return int(self) & int(other)

    def __ior__(self, other):
        """ v |= other """
        return int(self) | int(other)
   
    def __ixor__(self, other):
        """ v &^ other """
        return int(self) ^ int(other)

    """ shift
    """
    def __lshift__(self, other):
        return int(self) << other

    def __rshift__(self, other):
        return int(self) >> other

    """ compare operaters
    """
    def __eq__(self, other):
        """ == """
        return int(self) == int(other)

    def __ne__(self, other):
        """ != """
        return int(self) != int(other)

    def __lt__(self, other):
        """ < """
        return int(self) < int(other)

    def __gt__(self, other):
        """ > """
        return int(self) > int(other)
    
    def __le__(self, other):
        """ <= """
        return int(self) <= int(other)
    
    def __ge__(self, other):
        """ >= """
        return int(self) >= int(other)

class Type(object):
    """ represents a Type in debugger.

    Type is the structure the block of memory provided by Debugger.

    Type.__str__(self)
    return the type name 
    
    Type.__eq__(self, other):
    check the Type is same

    Type.SizeOf(self)
    return the Type size in bytes.

    Type.GetPointerType(self)
    return a new Type is the this type's pointer type.

    Type.GetArrayType(self, size)
    return a new Type is the this type's array type with size.

    Type.GetTemplateArgument(self, index)
    if the type is a template, the function return the template argument type (indexed start at 0).

    Type.IsPointerType(self)
    return true if is pointer type.

    Type.LookupType(cls, type_name)
    Lookup the type name in global and return the Type found.

    """

    # inner type save (gdb.type or lldb.SBType)
    _I_type = None

    def __init__(self, pyo_type):
        raise NotImplementedError()
    
    @classmethod
    def LookupType(cls, type_name):
        """ lookup 'type_name' in debugger.

            e.g.
               t = Type.LookupType('v8::internal::Isolate')
               print(t)
               # v8::internal::Isolate

            Return dbg.Type object if found, nor None
        """
        raise NotImplementedError()

    def GetEnumMembers(self):
        """ return enum members in list

        Returns:
            [ {"name": TYPE_1, "value": 1 },
              {"name": TYPE_2, "value": 2 },
            ]
           
            or []
        """
        raise NotImplementedError()

    def GetPointerType(self):
        """ return a new dbg.Type object represents a reference to this type

            return Type()
        """
        raise NotImplementedError()

    def GetArrayType(self, size):
        """ return a new dbg.Type object represents a array of this type
        """
        raise NotImplementedError()

    def IsIntegralType(self):
        """ return true if a integra type (can convert to integer)
        """
        raise NotImplementedError()

    def IsFloatType(self):
        """ return true if is a float type (float or double)
        """
        raise NotImplementedError()

    def IsPointerType(self):
        """ return true if is a pointer type ( or typedefs of these types)
        """

    def GetTemplateArgument(self, index):
        """ get the argument of a template by given index.
        """
        raise NotImplementedError()

    def __str__(self):
        """ return a short string of the type
            return: string.
        """
        raise NotImplementedError()

    def SizeOf(self):
        """ return the byte size of the type.
            return: int
        """
        raise NotImplementedError()


class Thread:
    """ represent a thread in core
    """
    _I_thread = None

    @property
    def tid(self):
        """ get thread id
        """
        raise NotImplementedError()

    @property
    def name(self):
        """ get thread name if has
        """
        raise NotImplementedError()

    def GetFrameTop(self):
        """ return the newest frame on thread 
        """
        raise NotImplementedError()

    def GetEnviron(self):
        raise NotImplementedError()
        
class Symval:

    def __init__(self, sym, val):
        self.sym = sym
        self.val = val

    def Flatten(self):
        return [str(self.sym), str(self.val)]

    def __repr__(self):
        return "%s=%s" % (str(self.sym), str(self.val))

    def __str__(self):
        return "%s=%s" % (str(self.sym), str(self.val))

class Frame(object):
    """ represent a stack frame in thread
    """
    _I_frame = None

    def __init__(self, frame):
        if isinstance(frame, Frame):
            self._I_frame = frame._I_frame
        else:
            self._I_frame = frame
  
    def IsValue(self):
        """Is Value
        """
        raise NotImplementedError()

    def GetFunctionName(self):
        """Get Function name
        """
        raise NotImplementedError()

    #def ReadAddress(self, address, size):
    #    """Read memory address by size
    #    """
    #    raise NotImplementedError()

    def GetSP(self):
        """ get stack pointer from the Frame
            return: int 
        """
        raise NotImplementedError()
   
    def GetPC(self):
        """ get program counter from th frame
            return: int 
        """
        raise NotImplementedError()
 
    def GetFP(self):
        """ get program counter from th frame
            return: int 
        """
        raise NotImplementedError()
    
    def GetRegister(self, name):
        """ return register value by name
            return: int 
        """
        raise NotImplementedError()

    def GetArgs(self):
        """ return Symval[]
        """
        return None

    def GetLocals(self):
        """ return Symval[]
        """
        return None

    def Description(self, full=0):
        function_name = self.GetFunctionName()
        if function_name is None or len(function_name) == 0:
            function_name = "(anonymous)"

        args = [] 
        for i in self.GetArgs():
            args.append(str(i))

        position = ""
        filename, fileline = self.GetPosition()
        if filename and fileline:
            position = "at %s:%d" % (filename, fileline)

        if not full:
            return "0x%016x %s(%s) %s" % (
                    self.GetPC(), 
                    function_name,
                    ', '.join(args), 
                    position)

        return "0x%016x %s(%s)" % (self.GetPC(), function_name, args.join(','))

    def Flatten(self):
        out = {}
        def trycall(fn, dv=None):
            v = None
            try:
                v = fn()
            except Exception as e:
                print(e)
            if v is None and dv is not None:
                return dv
            return v

        out['pc'] = trycall(self.GetPC)
        out['sp'] = trycall(self.GetSP)
        out['function_name'] = trycall(self.GetFunctionName)
        out['position'] = trycall(self.GetPosition)
        out['args'] = [ x.Flatten() for x in trycall(self.GetArgs, dv=[]) ] 
        out['locals'] = [ x.Flatten() for x in trycall(self.GetLocals, dv=[]) ]

        return out

class MemoryRegionInfo:
    """ represent a memory region entry
    """
    
    _I_start_address = 0
    _I_end_address = 0
    _I_mode = 0
    _I_name = None

    # enum
    READ = 1 
    WRITE = 2
    EXECUTE = 4 

    @property 
    def start_address(self):
        return self._I_start_address

    @property 
    def end_address(self):
        return self._I_end_address

    @property 
    def size(self):
        return self._I_end_address - self._I_start_address

    @property
    def name(self):
        return self._I_name

    @property
    def mode(self):
        return self._I_mode

    def IsReadable(self):
        return bool(self._I_mode & 1)

    def IsWritable(self):
        return bool(self._I_mode & 2)

    def IsExecutable(self):
        return bool(self._I_mode & 4)

    def __str__(self):
        mode_str = "r" if self._I_mode & self.READ else '-'
        mode_str += "w" if self._I_mode & self.WRITE else '-'
        mode_str += "x" if self._I_mode & self.EXECUTE else '-'
        return " 0x%x-0x%x %s %s %d" % (
                self.start_address,
                self.end_address,
                self.name,
                mode_str,
                self.size)

class MemoryRegions:
    """ represent Memory maps in process.
    """
    
    # holds the regions list
    _I_regions = [] 
 
    @classmethod
    def GetRegions(cls):
        """ return Regions list
        """
        return cls._I_regions
        
    @classmethod
    def Access(cls, address, mode = 'r'):
        """ return 'address' whether could be accessed.
            
            mode :
              r: read
              w: write 
              x: execute
            valid modes:
              'r', 'rw', 'rwx', 'rx'

            return :
               None : not found in regions.
               True : can be accessed.
               False : can't be accessed.
        """
        mode_v = 0
        for i in mode:
            if i == 'r': mode_v |= MemoryRegionInfo.READ 
            elif i == 'w': mode_v |= MemoryRegionInfo.WRITE
            elif i == 'x': mode_v |= MemoryRegionInfo.EXECUTE
            else: raise Exception

        m = cls.Search(address)
        if m is None:
            return None
        return bool(mode_v & m.mode == mode_v)

    @classmethod
    def Search(cls, address):
        """ return MemoryRegionInfo if found, 
            otherwise None.
        """
        ptr = int(address)
        for i in cls._I_regions:
            if ptr >= i.start_address and ptr < i.end_address:
                return i
        return None

    @classmethod
    def Load(cls):
        """ load memory regions info from debugger.
        """
        raise NotImplementedError()

class ConvenienceVariables:
    """ convenience variable is a '$xxx' like symbol only in debugger.
    """
    @classmethod
    def Get(cls, name):
        """ get a convenience variable from debugger
        """
        raise NotImplementedError()

    @classmethod
    def Set(cls, name, value):
        """ set a convenience variable to debugger
        """
        raise NotImplementedError()

""" Target 
"""
class Target:

    @classmethod
    def GetCurrentThread(cls):
        """ get current thread 
        """
        raise NotImplementedError()

    @classmethod
    def GetThreads(cls):
        """ all threads in list
        """
        raise NotImplementedError()

    @classmethod
    def GetMemoryRegions(cls):
        """ return memory regions, in singleton
        """
        raise NotImplementedError()

    @classmethod
    def AddDwfFile(cls, filename):
        """ add 'typ' file to debugger.
        """
        raise NotImplementedError()

    @classmethod
    def LoadRaw(cls, value_name):
        """ Load global variable by linkage name
        """
        raise NotImplementedError()

    @classmethod
    def ReadSymbolAddress(cls, symbol_name):
        """ Get address of symbol.
        """
        raise NotImplementedError()

    @classmethod
    def ReadSymbolValue(cls, symbol_name):
        """ Get value of symbol.
        """
        raise NotImplementedError()

    """ String in andb
        andb.dbg can read one-byte or two-byte char string from memory.
        ReadCStr supports read (utf-8/ascii) strings,
        and ReadUStr suports (utf-16) strings.

        return: inner python unicode string
    """
    @classmethod
    def ReadCStr(cls, address, length=-1):
        """ covert cstring (in memory) to python string
        """
        raise NotImplementedError()

    @classmethod
    def ReadUStr(cls, address, length=-1):
        """ covert unicode16 string (in memory) to python string
        """
        raise NotImplementedError()

    @classmethod
    def ReadInt(cls, address, size=8, is_sign=0):
        """ read int from memory.
        """
        raise NotImplementedError()

    @classmethod
    def ReadDouble(cls, address):
        """ Read double (float) from memory.
        """
        raise NotImplementedError()

