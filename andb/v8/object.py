# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import re
#import struct

from functools import wraps
from andb.utility import Logging as log, oneshot, CachedProperty
from andb.errors import AndbError as err

import andb.dbg as dbg
from .internal import (
    Internal,
    Struct,
    Value,
    Enum,
    AutoLayout,
    ObjectSlot,
    ObjectSlots,
    ALStruct,
    BitField,
    Version
)
from .enum import (
    ElementsKind,
    InstanceType,
)
import andb.py23 as py23
raw_print=print
print=log.print

""" v8 Objects

Inheritance,
- Value (abstract class for storage)
  - Object
    - Smi
    - HeapObject
      - Map
      - FixedArray
        - HashTable
      - JSReceiver
        - JSObject
        - JSFunction
      ...

"""

""" Begin of the Super Objects.
"""


class TaggedImpl(py23.int64):
    """ An TaggedImpl is a base class for Object (Smi or HeapObject)

    # the __new__ and __init__ instance functions are too slow,
    # what i found is when all the __new__ and __init__ had been removed,
    # the TaggedImpl instance is still be initialized with tag value.

    """
    @property
    def tag(self):
        # TaggedImpl only saved the tag value
        # HeapObject has the object dbg.Value.
        return super(TaggedImpl, self).__int__()

    @classmethod
    def cIsSmi(cls, val):
        return Internal.cHasSmiTag(val)

    @classmethod
    def cIsObject(cls, val):
        return (not cls.cIsWeakOrCleared(val))

    @classmethod
    def cIsHeapObject(cls, val):
        return cls.cIsStrong(val)

    @classmethod
    def cIsCleared(cls, val):
        return Internal.cHasClearedWeakHeapObjectTag(val)

    @classmethod
    def cIsStrong(cls, val):
        return Internal.cHasStrongHeapObjectTag(val)

    @classmethod
    def cIsWeak(cls, val):
        return cls.cIsWeakOrCleared(val) and (not cls.cIsCleared(val))

    @classmethod
    def cIsStrongOrWeak(cls, val):
        return (not cls.cIsSmi(val)) and (not cls.cIsCleared(val))

    @classmethod
    def cIsWeakOrCleared(cls, val):
        return Internal.cHasWeakHeapObjectTag(val)

    def IsSmi(self):
        return self.cIsSmi(self.tag)

    def IsObject(self):
        return self.cIsObject(self.tag)

    def IsHeapObject(self):
        return self.cIsHeapObject(self.tag)

    def IsCleared(self):
        return self.cIsCleared(self.tag)

    def IsStrong(self):
        return self.cIsStrong(self.tag)

    def IsWeak(self):
        return self.cIsWeak(self.tag)

    def IsStrongOrWeak(self):
        return self.cIsStrongOrWeak(self.tag)

    def IsWeakOrCleared(self):
        return self.cIsWeakOrCleared(self.tag)

    def ToSmi(self):
        return Smi(self.tag)

    def GetHeapObject(self):
        return self.Cast(HeapObject)

    def Cast(self, cls):
        """Cast operation on tagged values"""
        return cls(self.tag)


class Object(TaggedImpl):
    """
        Object represents an SMI or Tagged Object
    """

    _typeName = 'v8::internal::Object'

    """
    // Object is the abstract superclass for all classes in the
    // object hierarchy.
    // Object does not use any virtual functions to avoid the
    // allocation of the C++ vtable.
    // There must only be a single data member in Object: the Address ptr,
    // containing the tagged heap pointer that this Object instance refers to.
    // For a design overview, see https://goo.gl/Ph4CGz.
    """

    """ is type functions
    """
    @classmethod
    def IsFunctionFactory(cls, xxx):
        instance_type = xxx
        @property
        def IsFunctionWrap(self):
            if not self.IsHeapObject():
                return False
            o = self.GetHeapObject()
            return o.instance_type == instance_type
        return IsFunctionWrap

    def IsMapType(self):
        t = self.instance_type
        return t == InstanceType.MAP_TYPE

    def IsUndefined(self):
        o = Oddball(self)
        if o.instance_type != InstanceType.ODDBALL_TYPE:
            return False
        return o.IsUndefined()

    def IsNull(self):
        o = Oddball(self)
        if o.instance_type != InstanceType.ODDBALL_TYPE:
            return False
        return o.IsNull()

    def IsZero(self):
        pass

    def IsNullOrUndefined(self):
        pass

    def IsPublicSymbol(self):
        pass

    def IsPrivateSymbol(self):
        pass

    def IsPrimitive(self):
        pass

    def IsNumber(self):
        pass

    def IsNumeric(self):
        pass

    def IsNoSharedNameSentinel(self):
        pass

    @oneshot
    def Size(self):
        """return the size of the object"""
        o = self.GetHeapObject()
        return o.Size()

    def Brief(self):
        """ show brief normally one short line
        """
        if self.IsSmi():
            o = self.ToSmi()
            return "<Smi %d 0x%x>" % (o.ToInt(), self.tag)
        elif self.IsCleared():
            return "[Cleared]"
        elif self.IsWeak():
            o = self.GetHeapObject()
            return "[Weak] %s" % (o.Brief())
        else:
            o = self.GetHeapObject()
            return o.Brief()

    @classmethod
    def cBrief(cls, ptr):
        """ show brief from object ptr.
        """
        return Object(ptr).Brief()

    @classmethod
    def Bind(cls, obj):
        # bind class to object
        if obj is None:
            return None
        return cls(obj)

    def __str__(self):
        """brief the object"""
        return self.Brief()


class Smi(Object):
    """ V8 Smi """

    _typeName = 'v8::internal::Smi'

    """
    // Smi represents integer Numbers that can be stored in 31 bits.
    // Smi(s) are immediate which means they are NOT allocated in the heap.
    // The ptr_ value has the following format: [31 bit signed int] 0
    // For long smi(s) it has the following format:
    //     [32 bit signed int] [31 bits zero padding] 0
    // Smi stands for small integer.
    """

    @classmethod
    def IsValid(cls, val):
        """ return true is a Smi  """
        return (val & Internal.kSmiTagMask) == Internal.kSmiTag

    @classmethod
    def DebugCfg(cls):
        """ DebugPrint constants """
        print ("kSmiTag: %x" % (Internal.kSmiTag))
        print ("kSmiTagMask: %x" % (Internal.kSmiTagMask))
        print ("kSmiShiftSize: %x" % (Internal.kSmiShiftSize))

    @classmethod
    def cToInt(cls, val):
        """ return value of the Smi """
        shift = Internal.kSmiTagMask + Internal.kSmiShiftSize
        return val >> shift

    def ToInt(self):
        return self.cToInt(self.tag)

    def __int__(self):
        """return the integer value in Smi"""
        return self.ToInt()


def SmiTagged(cls):
    """wrapped Tagged Smi for other
    """
    @wraps(SmiTagged)
    def Wrap(val):
        return cls(Smi(val))
    return Wrap


class HeapObject(Object, Value):
    """HeapObject is the superclass for all classes describing heap allocated objects."""

    _typeName = 'v8::internal::HeapObject'

    """
    // HeapObject is the superclass for all classes describing heap allocated
    // objects.
    """

    # default
    kMapOffset = 0

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "map_or_trans", "alias": ["map"], "type": Map},
         ]}

    def __init__(self, obj):
        tag = int(obj)
        #self._address = tag & (~Internal.kHeapObjectTagMask)
        address = tag & (~Internal.kHeapObjectTagMask)
        self.InitReader(address)

    def __int__(self):
        return self.tag

    def StrongTag(self):
        return self.tag | Internal.kHeapObjectTag

    @classmethod
    def FromAddress(cls, ptr):
        # let tagging happy
        return cls(Internal.TaggedT(ptr) | Internal.kHeapObjectTag)

    @classmethod
    def IsValid(cls, val):
        """ is a valid HeapObject """
        # try:
        #     gdb.parse_and_eval("*(int*)%d"%val)
        # except:
        #     return False

        # 1) memory is good

        # 2) has map word

        # 3) map is in MAP_SPACE
        if (val & Internal.kHeapObjectTag) != Internal.kHeapObjectTag:
            return False
        return not cls.cIsCleared(val)

    def Access(self):
        """ check the HeapObject accessable
        """
        # memory check
        try: 
            map = self.map
        except:
            return False

        # check map is valid.
        if map == 0:
            return False
        
        return True

    @classmethod
    def cPtr(cls, val):
        return int(val) & (~int(Internal.kHeapObjectTagMask))

    @property
    def ptr(self):
        return self.address

    @classmethod
    def cType(cls, val):
        o = HeapObject(val)
        return o.instance_type

    def GetMap2(self, allow_forward=1):
        """ return the Map instance """
        m = self.map

        # support forwarding
        if allow_forward and m.IsSmi():
            m = m.GetMap2(allow_forward=0)
        return m

    @property
    def map(self):
        m = self.map_or_trans
        if m.IsSmi():
            m = self.map_or_trans.map
        return m

    @CachedProperty
    def instance_type(self):
        """ return Instance Type (InstanceType) """
        return self.map.instance_type
        try:
            return self.map.instance_type
        except Exception as e:
            raise Exception("<0x%x> %s" % (self.tag, e))

    def IsString(self):
        return InstanceType.isString(self.instance_type) 

    def IsSymbol(self):
        return InstanceType.isSymbol(self.instance_type) 
    
    def IsJSProxy(self):
        return InstanceType.isJSProxy(self.instance_type)
    
    def IsJSFunction(self):
        return InstanceType.isJSFunction(self.instance_type)

    def IsJSGlobalObject(self):
        return InstanceType.isJSGlobalObject(self.instance_type)

    def IsJSGlobalProxy(self):
        return InstanceType.isJSGlobalProxy(self.instance_type)
    
    def IsJSBoundFunction(self):
        return InstanceType.isJSBoundFunction(self.instance_type)

    def IsSwissNameDictionary(self):
        return InstanceType.isSwissNameDictionary(self.instance_type)
    
    def IsPropertyCell(self):
        return InstanceType.isPropertyCell(self.instance_type)
 
    def IsScript(self):
        return InstanceType.isScript(self.instance_type)

    def IsJSObject(self):
        return InstanceType.isJSObject(self.instance_type)
    
    def IsByteArray(self):
        return InstanceType.isByteArray(self.instance_type)

    def IsContext(self):
        return InstanceType.isContext(self.instance_type)
    
    def IsNativeContext(self):
        return InstanceType.isNativeContext(self.instance_type)

    def IsFixedArray(self):
        return InstanceType.isFixedArray(self.instance_type)

    def IsFixedDoubleArray(self):
        return InstanceType.isFixedDoubleArray(self.instance_type)

    def IsOddball(self):
        return InstanceType.isOddball(self.instance_type)

    def IsTheHole(self):
        if not self.IsOddball():
            return False
        o = Oddball(self.address) 
        return o.IsTheHole()

    def IsMap(self):
        # Map Object has instance_type property, get from map's instance_type
        return InstanceType.isMap(self.map.instance_type)

    @CachedProperty
    def has_fast_properties(self):
        """ return true if may have fast properties """
        return not self.map.is_dictionary_map
 
    @oneshot
    def Size(self):
        """intf for all HeapObject should implemented"""
        #if self.__class__ == HeapObject:
        #    try:
        #        v = self._SizeByType()
        #    except Exception as e:
        #        err.ObjectError(self, e)
        #    return v
        #else:
            #err.NotImplemented(self, 'Size')
        try:
            v = self._SizeByType()
        except Exception as e:
            err.ObjectError(self, e)
        return v

    def Brief(self):
        try:
            return self._Brief()
        except:
            pass

        try:
            return "<%s 0x%x>" % (self.instance_type.camel_name, self.tag)
        except Exception as e:
            return "brief failed %s." % e

    def _Brief(self):
        """intf for all HeapObject should implemented"""
        #import traceback
        #traceback.print_stack()
        mid = None
        if self.IsString():
            o = String(self)
            mid = o.MidBrief()

        elif self.IsSymbol():
            o = Symbol(self)
            mid = o.ToString()
        
        elif self.IsJSFunction():
            o = JSFunction(self)
            mid = o.FunctionNameStr()
        
        elif InstanceType.isSharedFunctionInfo(self.instance_type):
            o = SharedFunctionInfo(self)
            mid = o.DebugName()
        
        elif self.IsScript():
            o = Script(self)
            mid = o.DebugName()
 
        elif InstanceType.isScopeInfo(self.instance_type):
            o = ScopeInfo(self)
            mid = o.FunctionName()
        
        elif InstanceType.isOddball(self.instance_type):
            o = Oddball(self)
            mid = o.CamelName()
    
        tag = self.StrongTag()

        if mid is None:
            return "<%s 0x%x>" % (self.instance_type.camel_name, tag)
        else:
            return "<%s %s 0x%x>" % (self.instance_type.camel_name, TextShort(mid), tag)

    def _SizeByType(self):
        m = self.map
        t = m.instance_type

        # with map instance
        instance_size = m.instance_size
        #print("instance_size: %d"%instance_size)
        if instance_size != Internal.kVariableSizeSentinel:
            return int(instance_size)

        # specific has Size method
        o = ObjectMap.BindObject(self)
        if o is not None:
            try:
                v = int(o.Size())
            except Exception as e:
                err.ObjectError(o, e)
            return v

        # not supported.
        print("Unknown 0x%x: %s (%d)" % (self.tag, t.name, int(t)))
        raise Exception("not support")

    def DebugPrint(self):
        if self.__class__ == HeapObject:
            # get the Binding Object 
            o = ObjectMap.BindObject(self)
            return o.DebugPrint()
        return super(HeapObject, self).DebugPrint()

    #def _DebugPrintByType(self):
    #    o = ObjectMap.BindObject(self)
    #    return o.DebugPrint()

    #def __not_use2(self):
    #    # Fixed Array
    #    if InstanceType.isFixedArray(typ):
    #        t = FixedArray(self.ptr())
    #        size = t.length
    #        return int(t.SizeFor(size))

    #    # Context
    #    if InstanceType.isContext(typ):
    #        if InstanceType.isType('NATIVE_CONTEXT_TYPE', typ):
    #            return NativeContext.kSize
    #        t = Context(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # TwoByteString
    #    if InstanceType.isType("STRING_TYPE", typ) or \
    #       InstanceType.isType("INTERNALIZED_STRING_TYPE", typ):
    #        t = SeqTwoByteString(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Fixed Double Array
    #    if InstanceType.isFixedDoubleArray(typ):
    #        t = FixedDoubleArray(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Feedback Metadata
    #    if InstanceType.isType("FEEDBACK_METADATA_TYPE", typ):
    #        t = FeedbackMetadata(self.ptr())
    #        return int(t.SizeFor(t.slot_count))

    #    # Descriptor Array
    #    if InstanceType.isDescriptorArray(typ):
    #        t = DescriptorArray(self.ptr())
    #        return int(t.SizeFor(t.number_of_all_descriptors))

    #    # Descriptor Array but all Strong, first added since node-v16
    #    if InstanceType.isType("STRONG_DESCRIPTOR_ARRAY_TYPE", typ):
    #        t = StrongDescriptorArray(self.ptr())
    #        return int(t.SizeFor(t.number_of_all_descriptors))

    #    # Weak Fixed Array
    #    if InstanceType.isWeakFixedArray(typ):
    #        t = WeakFixedArray(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Weak Array List
    #    if InstanceType.isWeakArrayList(typ):
    #        t = WeakArrayList(self.ptr())
    #        return int(t.SizeFor(t.capacity))

    #    # Small ordered hash set

    #    # Small ordered hash map

    #    # Ordered Name Dictionary

    #    # Property Array
    #    if InstanceType.isPropertyArray(typ):
    #        t = PropertyArray(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Feedback vector
    #    if InstanceType.isType("FEEDBACK_VECTOR_TYPE", typ):
    #        t = FeedbackVector(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Bigint
    #    if InstanceType.isBigInt(typ):
    #        t = BigInt(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    # Preparse data
    #    if InstanceType.isType("PREPARSE_DATA_TYPE", typ):
    #        t = PreparseData(self.ptr())
    #        return int(t.SizeFor(t.data_length, t.children_length))

    #    # Lots of types

    #    # Code
    #    if InstanceType.isCode(typ):
    #        t = Code(self.ptr())
    #        return int(t.CodeSize())

    #    # Wasm and others

    #    # EmbedderDataArray
    #    if InstanceType.isEmbedderDataArray(typ):
    #        t = EmbedderDataArray(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    if InstanceType.isScopeInfo(typ):
    #        t = ScopeInfo(self.ptr())
    #        return int(t.SizeFor(0))

    #    if InstanceType.isType("SLOPPY_ARGUMENTS_ELEMENTS_TYPE", typ):
    #        t = SloppyArgumentsElements(self.ptr())
    #        return int(t.SizeFor(t.length))

    #    if InstanceType.isType("PROMISE_REJECT_REACTION_JOB_TASK_TYPE", typ):
    #        t = PromiseRejectReactionJobTask(self.ptr())
    #        return int(t.Size())

    #    if InstanceType.isType("PROMISE_FULFILL_REACTION_JOB_TASK_TYPE", typ):
    #        t = PromiseFulfillReactionJobTask(self.ptr())
    #        return int(t.Size())

    #    if InstanceType.isType("SWISS_NAME_DICTIONARY_TYPE", typ):
    #        t = SwissNameDictionary(self.ptr())
    #        return int(t.SizeFor(t.capacity))

    #    # support forwarding pointer in GC

    #    # we need new object to support
    #    print("Unknown 0x%x: %s (%d)" % (self.ptr(), InstanceType.Name(typ), typ))
    #    raise Exception
    #    return None

    def ShortString(self):
        t = self.instance_type
        if InstanceType.isString(t):
            s = self.Cast(String)
            try:
                sz = s.to_string().replace('\n',' ').replace('\r', '')[:200]
            except:
                sz = "[ 0x%x to_string failed. ]" % self.tag
            return "<0x%x, len:%d> '%s'" % (self.tag, s.length(), sz)
        elif InstanceType.isOddball(t):
            o = self.Cast(Oddball)
            return "<%s '%s' 0x%x>" % (
                    InstanceType.CamelName(t), str(o.to_string), self.tag)
        elif InstanceType.isJSFunction(t):
            o = self.Cast(JSFunction)
            return "<%s '%s' 0x%x>" % (
                    InstanceType.CamelName(t), o.FunctionName(), self.tag)
        elif InstanceType.isJSObject(t):
            return "<%s 0x%x, Map:0x%x>" % (InstanceType.CamelName(t), self.tag, self.map)
        return "<%s 0x%x>" % (InstanceType.CamelName(t), self.tag)


    def PrintRaw(self):
        size = self.Size()
        for i in range(0, size//8):
            v = self.LoadFieldRaw(i)
            print(" - [%d] %016x %s" % (i, v, Object.SBrief(v)))

    def Slots(self):
        """iterator for HeapObject"""
        return ObjectSlots(self.address, self.address+self.Size())


class Map(HeapObject):
    """ the Map object """

    _typeName = 'v8::internal::Map'

    # cache all Map Object 
    _map_cache = {} 

    """
    // All heap objects have a Map that describes their structure.
    //  A Map contains information about:
    //  - Size information about the object
    //  - How to iterate over an object (for garbage collection)
    //
    // Map layout:
    // +---------------+------------------------------------------------+
    // |   _ Type _    | _ Description _                                |
    // +---------------+------------------------------------------------+
    // | TaggedPointer | map - Always a pointer to the MetaMap root     |
    // +---------------+------------------------------------------------+
    // | Int           | The first int field                            |
    //  `---+----------+------------------------------------------------+
    //      | Byte     | [instance_size]                                |
    //      +----------+------------------------------------------------+
    //      | Byte     | If Map for a primitive type:                   |
    //      |          |   native context index for constructor fn      |
    //      |          | If Map for an Object type:                     |
    //      |          |   inobject properties start offset in words    |
    //      +----------+------------------------------------------------+
    //      | Byte     | [used_or_unused_instance_size_in_words]        |
    //      |          | For JSObject in fast mode this byte encodes    |
    //      |          | the size of the object that includes only      |
    //      |          | the used property fields or the slack size     |
    //      |          | in properties backing store.                   |
    //      +----------+------------------------------------------------+
    //      | Byte     | [visitor_id]                                   |
    // +----+----------+------------------------------------------------+
    // | Int           | The second int field                           |
    //  `---+----------+------------------------------------------------+
    //      | Short    | [instance_type]                                |
    //      +----------+------------------------------------------------+
    //      | Byte     | [bit_field]                                    |
    //      |          |   - has_non_instance_prototype (bit 0)         |
    //      |          |   - is_callable (bit 1)                        |
    //      |          |   - has_named_interceptor (bit 2)              |
    //      |          |   - has_indexed_interceptor (bit 3)            |
    //      |          |   - is_undetectable (bit 4)                    |
    //      |          |   - is_access_check_needed (bit 5)             |
    //      |          |   - is_constructor (bit 6)                     |
    //      |          |   - has_prototype_slot (bit 7)                 |
    //      +----------+------------------------------------------------+
    //      | Byte     | [bit_field2]                                   |
    //      |          |   - new_target_is_base (bit 0)                 |
    //      |          |   - is_immutable_proto (bit 1)                 |
    //      |          |   - unused bit (bit 2)                         |
    //      |          |   - elements_kind (bits 3..7)                  |
    // +----+----------+------------------------------------------------+
    // | Int           | [bit_field3]                                   |
    // |               |   - enum_length (bit 0..9)                     |
    // |               |   - number_of_own_descriptors (bit 10..19)     |
    // |               |   - is_prototype_map (bit 20)                  |
    // |               |   - is_dictionary_map (bit 21)                 |
    // |               |   - owns_descriptors (bit 22)                  |
    // |               |   - is_in_retained_map_list (bit 23)           |
    // |               |   - is_deprecated (bit 24)                     |
    // |               |   - is_unstable (bit 25)                       |
    // |               |   - is_migration_target (bit 26)               |
    // |               |   - is_extensible (bit 28)                     |
    // |               |   - may_have_interesting_symbols (bit 28)      |
    // |               |   - construction_counter (bit 29..31)          |
    // |               |                                                |
    // +****************************************************************+
    // | Int           | On systems with 64bit pointer types, there     |
    // |               | is an unused 32bits after bit_field3           |
    // +****************************************************************+
    // | TaggedPointer | [prototype]                                    |
    // +---------------+------------------------------------------------+
    // | TaggedPointer | [constructor_or_backpointer_or_native_context] |
    // +---------------+------------------------------------------------+
    // | TaggedPointer | [instance_descriptors]                         |
    // +****************************************************************+
    // ! TaggedPointer ! [layout_descriptors]                           !
    // !               ! Field is only present if compile-time flag     !
    // !               ! FLAG_unbox_double_fields is enabled            !
    // !               ! (basically on 64 bit architectures)            !
    // +****************************************************************+
    // | TaggedPointer | [dependent_code]                               |
    // +---------------+------------------------------------------------+
    // | TaggedPointer | [prototype_validity_cell]                      |
    // +---------------+------------------------------------------------+
    // | TaggedPointer | If Map is a prototype map:                     |
    // |               |   [prototype_info]                             |
    // |               | Else:                                          |
    // |               |   [raw_transitions]                            |
    // +---------------+------------------------------------------------+
    """
    class MapBitFields1(BitField):

        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "has_non_instance_prototype", "bits": 1},
                {"name": "is_callable", "bits": 1},
                {"name": "has_named_interceptor", "bits": 1},
                {"name": "has_indexed_interceptor", "bits": 1},
                {"name": "is_undetectable", "bits": 1},
                {"name": "is_access_check_needed", "bits": 1},
                {"name": "is_constructor", "bits": 1},
                {"name": "has_prototype_slot", "bits": 1},
            ]}

    class MapBitFields2(BitField):

        @classmethod
        def __autoLayout(cls):
            cfg = AutoLayout.Builder()
            cfg.Add({"name": "new_target_is_base", "bits": 1})
            cfg.Add({"name": "is_immutable_prototype", "bits": 1})
            if Version.major <= 9:
                cfg.Add({"name": "unused", "bits": 1})
                cfg.Add({"name": "elements_kind", "bits": 5, "type": ElementsKind})
            else:
                cfg.Add({"name": "elements_kind", "bits": 6, "type": ElementsKind})
            return cfg.Generate()

    class MapBitFields3(BitField):

        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "enum_length", "bits": 10},
                {"name": "number_of_own_descriptors", "bits": 10},
                {"name": "is_prototype_map", "bits": 1},
                {"name": "is_dictionary_map", "bits": 1},
                {"name": "owns_descriptors", "bits": 1},
                {"name": "is_in_retained_map_list", "bits": 1},
                {"name": "is_deprecated", "bits": 1},
                {"name": "is_unstable", "bits": 1},
                {"name": "is_migration_target", "bits": 1},
                {"name": "is_extensible", "bits": 1},
                {"name": "may_have_intresting_symbols", "bits": 1},
                {"name": "construction_counter", "bits": 3},
            ]}

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {'name': 'instance_size_in_words', 'type': int},
            {'name': 'inobject_properties_start_or_constructor_function_index', 'type': int,
                'alias': ['in_object_properties_start_or_constructor_function_index']},
            {'name': 'used_or_unused_instance_size_in_words', 'type': int},
            {'name': 'visitor_id', 'type': int},
            {'name': 'instance_type', 'type': InstanceType},
            {'name': 'bit_field', 'type': Map.MapBitFields1},
            {'name': 'bit_field2', 'type': Map.MapBitFields2},
            {'name': 'bit_field3', 'type': Map.MapBitFields3},
            {'name': 'prototype', 'type': Object},  # [JSReceiver, Null]
            {'name': 'constructor_or_back_pointer_or_native_context', 'type': Object,
                'alias': ['constructor_or_back_pointer']},  # Object
            {'name': 'instance_descriptors', 'type': DescriptorArray},
            {'name': 'dependent_code', 'type': DependentCode},
            {'name': 'prototype_validity_cell', 'type': Object},  # [Smi, Cell]
            {'name': 'transitions_or_prototype_info', 'type': Object},  # [Map, TransitionArray, PrototypeInfo, Smi]},
        ]}

    #def __new__(cls, tag):
    #    ret = super(Map, cls).__new__(cls, tag)
    #    print(ret)
    #    return ret

    """ bitfield helper
    """
    @CachedProperty
    def is_dictionary_map(self):
        """ whether the object is a dictionary """
        return self.bit_field3.is_dictionary_map
    
    @CachedProperty
    def is_prototype_map(self):
        return self.bit_field3.is_prototype_map

    @CachedProperty
    def new_target_is_base(self):
        return self.bit_field2.new_target_is_base

    @CachedProperty
    def is_callable(self):
        return self.bit_field.is_callable

    @CachedProperty
    def elements_kind(self):
        return self.bit_field2.elements_kind
   
    @CachedProperty
    def is_access_check_needed(self):
        return self.bit_field.is_access_check_needed

    @CachedProperty
    def has_non_instance_prototype(self):
        return self.bit_field.has_non_instance_prototype

    @CachedProperty
    def inobject_properties_start(self):
        assert InstanceType.isJSObject(self.instance_type)
        return self.inobject_properties_start_or_constructor_function_index
    
    @CachedProperty
    def constructor_function_index(self):
        assert self.IsPrimitiveMap()
        return self.inobject_properties_start_or_constructor_function_index

    """ X in one field functions.
    """
    @CachedProperty
    def constructor(self):
        return self.constructor_or_back_pointer_or_native_context

    @CachedProperty
    def native_context(self):
        return self.constructor_or_back_pointer_or_native_context

    """ public functions.
    """
    @CachedProperty
    def instance_size(self):
        """ return the instance size in bytes """
        return self.instance_size_in_words * Internal.kTaggedSize
    
    @CachedProperty
    def number_of_inobjects(self):
        return self.instance_size_in_words - self.inobject_properties_start_or_constructor_function_index

    @CachedProperty
    def used_instance_size(self):
        words = self.used_or_unused_instance_size_in_words
        if words < JSObject.kFieldsAdded:
            return self.instance_size
        return words * Internal.kTaggedSize

    @CachedProperty
    def unused_inobject_properties(self):
        words = self.used_or_unused_instance_size_in_words 
        if words < JSObject.kFieldsAdded:
            return 0 
        return self.instance_size_in_words - words

    @CachedProperty
    def unused_property_fields(self):
        words = self.used_or_unused_instance_size_in_words 
        if words < JSObject.kFieldsAdded:
            return words
        return self.instance_size_in_words - words
   
    @CachedProperty
    def number_of_own_descriptors(self):
        return self.bit_field3.number_of_own_descriptors

    def IsSpecialReceiverMap(self):
        result = InstanceType.isSpecialReceiverInstanceType(self.instance_type)
        return result

    def IsPrimitiveMap(self):
        return self.instance_type <= InstanceType.ODDBALL_TYPE

    def DebugPrint(self):
        super(Map, self).ALDebugPrint()


class Oddball(HeapObject):

    _typeName = 'v8::internal::Oddball'

    kFalse = 0
    kTrue = 1
    kTheHole = 2
    kNull = 3
    kArgumentsMarker = 4
    kUndefined = 5
    kUninitialized = 6
    kOther = 7
    kException = 9
    kOptimizedOut = 10
    kStaleRegister = 10
    kSelfReferenceMarker = 10
    kBasicBlockCounterMarker = 11

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {'name': 'to_number_raw', 'type': float},
            {'name': 'to_string', 'type': String},
            {'name': 'to_number', 'type': int},
            {'name': 'type_of', 'type': String},
            {'name': 'kind', 'type': Smi},
        ]}

    def __str__(self):
        return str(self.to_string)

    def CamelName(self):
        s = str(self.to_string).lower().capitalize() 
        if s.find('_') > 0:
            y = []
            for x in s.split('_'):
                y.append(x.lower().capitalize())
            return ''.join(y)
        return s

    def IsFalse(self):
        return int(self.kind) == self.kFalse

    def IsTrue(self):
        return int(self.kind) == self.kTrue

    def IsTheHole(self):
        return int(self.kind) == self.kTheHole

    def IsNull(self):
        return int(self.kind) == self.kNull

    def IsUndefined(self):
        return int(self.kind) == self.kUndefined

    def IsUninitialized(self):
        return int(self.kind) == self.kUninitialized

    def IsException(self):
        return int(self.kind) == self.kException


"""
//     - FixedArrayBase
//       - ByteArray
//       - BytecodeArray
//       - FixedArray
//         - FrameArray
//         - HashTable
//           - Dictionary
//           - StringTable
//           - StringSet
//           - CompilationCacheTable
//           - MapCache
//         - OrderedHashTable
//           - OrderedHashSet
//           - OrderedHashMap
//         - FeedbackMetadata
//         - TemplateList
//         - TransitionArray
//         - ScopeInfo
//         - SourceTextModuleInfo
//         - ScriptContextTable
//         - ClosureFeedbackCellArray
//       - FixedDoubleArray
"""

class FixedArrayBase(HeapObject):
    """ V8 FixedArrayBase """

    _typeName = 'v8::internal::FixedArrayBase'

    """
    // Common superclass for FixedArrays that allow implementations to share
    // common accessors and some code paths.
    """

    kHeaderSize = 16

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": SmiTagged(int)},
        ]}

    # TBD: should support non-8-bytes type, eg. ByteArray.
    def Get(self, index):
        """ getter for elements
        """
        return Object(self.LoadPtr(self.kHeaderSize + (index * Internal.kTaggedSize)))

    def GetDouble(self, index):
        return (self.LoadPtr(self.kHeaderSize + (index * Internal.kTaggedSize)))

    def OffsetElementAt(self, index):
        """ get offset of a element
        """
        return self.SizeFor(index)

    def SizeFor(self, length):
        """ virtual function """
        raise NotImplementedError("<0x%x>"%self)

    def Size(self):
        """ Object Size """
        return self.SizeFor(self.length)


class FixedArray(FixedArrayBase):
    """ An V8 Fixed Array Object """

    _typeName = 'v8::internal::FixedArray'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": SmiTagged(int)},
            {"name": "objects[length]", "type": Object},
        ]}

    def SizeFor(self, length):
        return self.kHeaderSize + (length * Internal.kTaggedSize)

    def PrintElements(self):
        for i in range(self.length):
            v = self.Get(i)
            print("   [%d] %s" % (i, Object.SBrief(v)))

    def WalkElements(self):
        for i in range(self.length):
            v = self.Get(i)
            yield (i, v)


class ByteArray(FixedArrayBase):

    _typeName = 'v8::internal::ByteArray'

    kHeaderSize = 16

    def SizeFor(self, length):
        return Internal.ObjectPointerAlign(self.kHeaderSize + length)

    def DataBegin(self):
        return self.address + self.kHeaderSize


class BytecodeArray(FixedArrayBase):

    _typeName = 'v8::internal::BytecodeArray'

    kHeaderSize = 54

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "constant_pool", "type": Object},
            {"name": "handler_table", "type": Object},
            {"name": "source_position_table", "type": Object},
            {"name": "frame_size", "type": int},
            {"name": "parameter_size", "type": int},
            {"name": "incoming_new_target_or_generator_register", "type": int},
            {"name": "osr_loop_nesting_level", "type": int},
            {"name": "bytecode_age", "type": int},
        ]}

    def BytecodeBegin(self):
        return self.address + self.kHeaderSize

    def SizeFor(self, length):
        return Internal.ObjectPointerAlign(self.kHeaderSize + length)

    def DebugPrint2(self):
        print("[BytecodeArray]")
        print(" - constant_pool :", Object.SBrief(self.constant_pool))
        print(" - handler_table :", Object.SBrief(self.handler_table))
        print(" - source_position_table :", Object.SBrief(self.source_position_table))
        print(" - frame_size : %u" % self.frame_size)
        print(" - parameter_size : %u" % self.parameter_size)
        print(" - incoming_new_target_or_generator_register : %u" % self.incoming_new_target_or_generator_register)
        print(" - osr_loop_nesting_level : %u" % self.osr_loop_nesting_level)
        print(" - bytecode_age : %u" % self.bytecode_age)
        print(" - bytecode begin at : 0x%x" % self.BytecodeBegin())


class FixedDoubleArray(FixedArrayBase):

    _typeName = 'v8::internal::FixedDoubleArray'

    def SizeFor(self, length):
        return self.kHeaderSize + (length * Internal.kDoubleSize)

    def GetDouble(self, index):
        off = self.kHeaderSize + (index * Internal.kTaggedSize)
        return self.LoadDouble(off) 

    def WalkElements(self):
        for i in range(self.length):
            v = self.GetDouble(i)
            yield (i, v)

class WeakFixedArray(FixedArrayBase):

    _typeName = 'v8::internal::WeakFixedArray'

    def SizeFor(self, length):
        return self.kHeaderSize + (int(length) * Internal.kTaggedSize)


class HashTableBase(FixedArray):
    """ represents a HashTableBase object """

    _typeName = 'v8::internal::HashTableBase'

    """
    // HashTable is a subclass of FixedArray that implements a hash table
    // that uses open addressing and quadratic probing.
    //
    // In order for the quadratic probing to work, elements that have not
    // yet been used and elements that have been deleted are
    // distinguished.  Probing continues when deleted elements are
    // encountered and stops when unused elements are encountered.
    //
    // - Elements with key == undefined have not been used yet.
    // - Elements with key == the_hole have been deleted.
    //
    // The hash table class is parameterized with a Shape.
    // Shape must be a class with the following interface:
    //   class ExampleShape {
    //    public:
    //     // Tells whether key matches other.
    //     static bool IsMatch(Key key, Object other);
    //     // Returns the hash value for key.
    //     static uint32_t Hash(ReadOnlyRoots roots, Key key);
    //     // Returns the hash value for object.
    //     static uint32_t HashForObject(ReadOnlyRoots roots, Object object);
    //     // Convert key to an object.
    //     static inline Handle<Object> AsHandle(Isolate* isolate, Key key);
    //     // The prefix size indicates number of elements in the beginning
    //     // of the backing storage.
    //     static const int kPrefixSize = ..;
    //     // The Element size indicates number of elements per entry.
    //     static const int kEntrySize = ..;
    //     // Indicates whether IsMatch can deal with other being the_hole (a
    //     // deleted entry).
    //     static const bool kNeedsHoleCheck = ..;
    //   };
    // The prefix size indicates an amount of memory in the
    // beginning of the backing storage that can be used for non-element
    // information by subclasses.
    """

    @classmethod
    def __autoLayout(cls):
        return {
            "offsetFunction": cls.OffsetElementAt,
            "layout": [
                {"name": "number_of_elements", "type": SmiTagged(int)},
                {"name": "number_of_deleted_elements", "type": SmiTagged(int)},
                {"name": "capacity", "type": SmiTagged(int)},
            ]}


class BaseShape(Value):
    """ abstract class for all v8 HashTable Shapes """

    # not a v8 object
    _typeName = None

    """ Must have const values """
    kEntrySize = None
    kPrefixSize = None
    kEntryValueIndex = None


class HashTable(HashTableBase):
    """ abstract class for all v8 HashTables """

    # not a v8 object
    _typeName = None

    """
        the python class is a HashTable abstract class for all v8 HashTables,
        likes NameDictionary, StringTable etc ...

        [ v8 HashTables ]
          ObjectHashTable,
          EphemeronHashTable,
          ObjectHashSet,
          StringTable,
          StringSet,
          NameDictionary,
          GlobalDictionary,
          SimpleNumberDictionary,
          NumberDictionary,
          CompilationCacheTable.

        Each kind of HashTables has its own Shape,

        for example,

        NameDictionary,
          : BaseNameDictionary<NameDictionary, NameDictionaryShape>
            : Dictionary<NameDictionary, NameDictionaryShape>
              : HashTable<NameDictionary, NameDictionaryShape>

        NameDictionaryShape,
          : BaseDictionaryShape<Name>
            : BaseShape<Name> {
            kPrefixSize = 2         // each entry has 2 elements
            kEntrySize = 3          // include key
            kEntryValueIndex = 1
        }

    """

    """ MUST have const values """
    #kEntryKeyIndex = 0
    #kElementsStartIndex = 0

    def EntryToIndex(self, entry_index):
        """ Entry to Index, returns the index for an entry (for the key)
            Entry is int value in Range(self.Capacity),
            Entry has kEntrySize,
            for reference the slot in FixedArray,
            needs to convert to Index.
        """
        return (entry_index * self.entry_size) + self.kElementsStartIndex

    def IndexToEntry(self, slot_index):
        return (slot_index - self.kElementStartIndex) // self.entry_size

    def FindEntry(self, key):
        raise NotImplementedError()

    def KeyAt(self, entry_index):
        array_index = self.EntryToIndex(entry_index) + self.kEntryKeyIndex
        return self.Get(array_index)

    def ValueAt(self, entry_index):
        array_index = self.EntryToIndex(entry_index) + self.entry_value_index
        return self.Get(array_index)

    """ BaseShape functions,
        we don't implement a BaseShape

        any Hashtable must have
          [ kPrefixSize, kEntryKeyIndex, kEntrySize ] values.
    """
    
    @CachedProperty
    def prefix_size(self):
        return getattr(self, "kPrefixSize")

    @CachedProperty
    def entry_value_index(self):
        return getattr(self, "kEntryValueIndex")

    @CachedProperty
    def entry_size(self):
        return getattr(self, "kEntrySize")

    def isKey(self, key):
        iso = Isolate.GetCurrent()
        roots = iso.Roots()
        if key == roots.undefined_value or \
                key == roots.the_hole_value:
            return False
        return True

    def PrintElements2(self):
        for i in range(self.capacity):
            key = self.KeyAt(i)
            if not self.isKey(key):
                continue
            val = self.ValueAt(i)
            print("   [%d] %s: %s" % (i, Object.SBrief(key), Object.SBrief(val)))

    def DebugPrint2(self, header="HashTable"):
        print("[%s]" % header)
        print(" - elements: %d" % self.number_of_elements())
        print(" - deleted: %d" % self.number_of_deleted_elements())
        print(" - capacity: %d" % self.capacity())
        print(" - elements: {")
        self.PrintElements()
        print(" }")


class Dictionary(HashTable):
    """ abstract class for all v8 dictionaries """

    kEntryDetailsIndex = None

    def DetailsAt(self, entry_index):
        array_index = self.EntryToIndex(entry_index) + self.kEntryDetailsIndex
        return PropertyDetailsSlowTo(self.Get(array_index))


class NameDictionaryShape(BaseShape):
    _typeName = 'v8::internal::NameDictionaryShape'

    kEntrySize = 3
    kEntryValueIndex = 1
    kPrefixSize = 2


class NameDictionary(Dictionary, NameDictionaryShape):
    """ represents a Name Dictionary """

    _typeName = 'v8::internal::NameDictionary'

    kEntryKeyIndex = 0
    kEntryValueIndex = 1
    kEntryDetailsIndex = 2
    kElementsStartIndex = 5

    def WalkProperties(self):
        for i in range(self.capacity):
            key = Name(self.KeyAt(i))
            if not self.isKey(key):
                continue
            name = key.ToString()
            val = self.ValueAt(i)
            details = PropertyDetailsSlowTo(self.DetailsAt(i))
            yield (name, details, val)
            

    @CachedProperty
    def properties(self):
        pass

    def Search(self, name):
        for i in range(self.capacity):
            maybe_key = self.KeyAt(i)
            if not self.isKey(maybe_key):
                continue
            key = Name(maybe_key)
            assert key.IsString() or key.IsSymbol(), "i=%d <0x%x>"% (i, self)
            #print(key.ToString(), name)
            if key.ToString() == name:
                return i
        # not found
        return None

    def _DebugPrint(self, **kwargs):
        pos = kwargs['pos'] if 'pos' in kwargs else 0
        if pos == 0:
            print('[%s 0x%x]' % (self.__class__.__name__, self.address))
        i = 0
        for (key, details, val) in self.WalkProperties():
            log.print("%d: {" % i, pos=pos)
            log.print("- name: %s" % str(key), pos=pos+2)
            log.print("- details: 0x%x" % int(details), pos=pos+2)
            details.DebugPrint(pos=pos+4)
            log.print("- value: %s" % str(val), pos=pos+2)
            log.print("}", pos=pos)
            i += 1


class GlobalDictionaryShape(NameDictionaryShape):
    _typeName = 'v8::internal::GlobalDictionaryShape'

    # overrides
    kEntrySize = 1


class GlobalDictionary(Dictionary, GlobalDictionaryShape):
    """ represents a Global Dictionary """

    _typeName = 'v8::internal::GlobalDictionary'

    kEntryKeyIndex = 0
    kEntryValueIndex = 1
    kElementsStartIndex = 5

    def PrintElements(self):
        # override
        print(self.SPrint())
   
    def CellAt(self, index):
        cell = PropertyCell(self.KeyAt(index))
        #assert cell.IsPropertyCell()
        return cell 

    def ValueAt(self, index):
        cell = self.CellAt(index)
        assert cell.IsPropertyCell()
        return cell.value
    
    def WalkProperties(self):
        for i in range(self.capacity):
            cell = self.CellAt(i)
            if not cell.IsHeapObject() or not cell.IsPropertyCell():
                continue

            name = cell.name.ToString()
            details = cell.property_details
            value = cell.value
            #print(name, details, value)
            yield (name, details, value)

    def FindEntry(self, key_to_find):
        for i in range(self.capacity):
            cell = self.CellAt(i)
            if not cell.IsPropertyCell():
                continue

            if str(cell.name) == key_to_find:
                return i

        return None

    def DebugPrint2(self):
        super(GlobalDictionary, self).DebugPrint("GlobalDictionary")


class ObjectHashTable(HashTable):
    """ Object HashTable """

    _typeName = 'v8::internal::ObjectHashTable'


class OrderedHashTable(FixedArray):
    """ Ordered HashTable """

    _typeName = None


class NameHash(BitField):

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "hash_field_type", "bits": 2},
            {"name": "array_index_value", "bits": 24},
            {"name": "array_index_length", "bits": 6},
        ]}


class Name(HeapObject):
    """ 'Name' is the super class for all Strings """

    _typeName = 'v8::internal::Name'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "hash_field", "type": NameHash,
                "alias": ["raw_hash_field"]},  # NameHash
        ]}

    def BindObject(self):
        if self.IsSymbol():
            return Symbol(self)
        elif self.IsString():
            return String(self)
        raise Exception('New Type? %s' % self.instance_type)

    def ToString(self):
        obj = self.BindObject()
        return obj.ToString()
    
    def __str__(self):
        return self.ToString()

class SymbolFlags(BitField):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "is_private", "bits": 1},
            {"name": "is_well_know_symbol", "bits": 1},
            {"name": "is_in_public_symbol_table", "bits": 1},
            {"name": "is_interesting_symbol", "bits": 1},
            {"name": "is_private_name", "bits": 1},
            {"name": "is_private_brand", "bits": 1},
        ]}


class Symbol(HeapObject):
    """ V8 Symbol """

    _typeName = 'v8::internal::Symbol'

    kFlagsOffset = 12
    kDescriptionOffset = 16

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "flags", "type": SymbolFlags},
            {"name": "description", "type": Object, "alias": ["kNameOffset"]},
        ]}

    def ToString(self):
        o = String(self.description)
        if o.IsString():
            return o.ToString()
        return ''

    @CachedProperty
    def is_private(self):
        return self.flags.is_private

class String(Name):
    """ V8 String Object """

    _typeName = 'v8::internal::String'

    kHeaderSize = 16

    """ ConsString cache.
    """
    _ConsString_Cache = {}

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": int},
        ]}

    def IsOneByte(self):
        t = self.instance_type
        return (t & Internal.kStringEncodingMask) == Internal.kOneByteStringTag

    def IsTwoByte(self):
        return not Internal.isOneByte()

    @property
    def type(self):
        t = self.instance_type
        return (t & Internal.kStringRepresentationMask)

    def IsSeqString(self):
        return self.type == Internal.kSeqStringTag
    
    def IsConsString(self):
        return self.type == Internal.kConsStringTag

    def IsSlicedString(self):
        return self.type == Internal.kSlicedStringTag

    def IsThinString(self):
        return self.type == Internal.kThinStringTag

    def IsInternalized(self):
        t = self.instance_type
        return (t & Internal.kIsNotInternalizedMask) == 0

    def Representation(self):
        t = self.instance_type
        return t & Internal.kStringRepresentationMask

    def Size(self):
        t = self.Representation()
        if t == Internal.kSeqStringTag:
            v = self.Cast(SeqString)
        else:
            instance_size = self.map.instance_size
            if instance_size > 0:
                return instance_size
            raise IndexError(t)
        return v.Size()

    def BindObject(self):
        t = self.Representation()
        if t == Internal.kSeqStringTag:
            v = self.Cast(SeqString)
        elif t == Internal.kConsStringTag:
            v = self.Cast(ConsString)
        elif t == Internal.kExternalStringTag:
            v = self.Cast(ExternalString)
        elif t == Internal.kSlicedStringTag:
            v = self.Cast(SlicedString)
        elif t == Internal.kThinStringTag:
            v = self.Cast(ThinString)
        else:
            raise IndexError(t, "0x%x" % self)
        return v

    @staticmethod
    def sBind(obj):
        return String(obj).BindObject()

    def to_string(self, **kwargs):
        assert self.__class__ == String

        v = self.BindObject()
        return v.to_string(**kwargs)

    def MidBrief(self):
        t = self.Representation()
        length = self.length
        if length > 128*1024:
            return "'too long to show...'"
        else:
            return self.to_string(recurse_limit=100)

    def ToString(self, length=-1):
        return TextLimit(self.to_string(), limit=length)

    def __str__(self):
        return self.to_string()

    def SaveFile(self, file_to_save = None):
        start_address = self.address + self.kHeaderSize 
        end_address = start_address + self.Size()

        if file_to_save is None:
            file_to_save = "string_0x%x.raw" % self.tag 
        dbg.Target.MemoryDump(file_to_save, start_address, end_address)
        return file_to_save

    def DebugPrint(self):
        # first show string
        log.print(self.ToString())

        # show subtype details, except SeqString
        if not self.IsSeqString():
            v = self.BindObject()
            v.ALDebugPrint()

        # string type details
        self.ALDebugPrint()

class SeqString(String):

    _typeName = 'v8::internal::SeqString'

    def Size(self):
        if self.IsOneByte():
            v = self.Cast(SeqOneByteString)
        else:
            v = self.Cast(SeqTwoByteString)
        return v.SizeFor(v.length)

    def to_string(self, **kwargs):
        if self.IsOneByte():
            v = self.Cast(SeqOneByteString)
            return v.to_string()
        else:
            v = self.Cast(SeqTwoByteString)
            return v.to_string()

    def DebugPrint2(self):
        len = self.length
        if self.IsOneByte():
            c = "#"
            v = self.Cast(SeqOneByteString)
        else:
            c = "u"
            v = self.Cast(SeqTwoByteString)
        print('[%d] %s"%s"' % (len, c, v.to_string()))


class SeqOneByteString(SeqString):

    _typeName = 'v8::internal::SeqOneByteString'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": int},
            {"name": "chars[length]", "type": int, "size": 1},
        ]}

    def SizeFor(self, length):
        size = Internal.ObjectPointerAlign(self.kHeaderSize)
        size += length
        size = Internal.ObjectPointerAlign(size)
        return size

    def to_string(self):
        len = self.length
        s = self.LoadCString(self.kHeaderSize, len)
        return s


class SeqTwoByteString(SeqString):

    _typeName = 'v8::internal::SeqTwoByteString'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": int},
            {"name": "chars[length]", "type": int, "size": 2},
        ]}

    def SizeFor(self, length):
        size = Internal.ObjectPointerAlign(self.kHeaderSize)
        size += length * 2
        size = Internal.ObjectPointerAlign(size)
        return size

    def to_string(self):
        len = self.length
        try:
            s = self.LoadUString(self.kHeaderSize, len)
        except Exception as e:
            s = "[ 0x%x decode failed (%s) ]" % (self.tag, e)
        return s


class ConsString(String):

    _typeName = 'v8::internal::ConsString'

    #kSize = 32

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "first", "type": String.sBind},
            {"name": "second", "type": String.sBind},
            #{ "name":"size" },
        ]}

    #def Size(self):
    #    return self.size

    def to_string(self, **kwargs):
        """ cons string may be too long to reach end.
        """
        a = self.first
        b = self.second
        return a.to_string(**kwargs) + b.to_string(**kwargs)


class ExternalString(String):

    _typeName = 'v8::internal::ExternalString'

    #kResourceOffset = 16
    #kResourceDataOffset = 24

    @classmethod
    def __autoLayout(cls):
        return {
        "layout": [
            { "name":"resource", "type": int },
            { "name":"resource_data", "type": int },
        ]}

    def to_string(self, **kwargs):
        v = dbg.Target.ReadCStr(self.resource_data)
        return v


class SlicedString(String):

    _typeName = 'v8::internal::SlicedString'

    #kSize = 32

    @classmethod
    def __autoLayout(cls):
        return {
        "layout": [
            { "name":"parent", "type":String.sBind },
            { "name":"offset", "type":SmiTagged(int)},
        ]}

    def to_string(self, **kwargs):
        a = self.parent
        b = self.offset
        return a.to_string(**kwargs)[b:]


class ThinString(String):

    _typeName = 'v8::internal::ThinString'

    #kSize = 24

    @classmethod
    def __autoLayout(cls):
        return {
        "layout": [
            { "name":"actual", "type":String.sBind },
        ]}

    def to_string(self, **kwargs):
        a = self.actual
        return a.to_string(**kwargs)


class JSReceiver(HeapObject):
    """ JSreceiver is the super class for all JS Objects """

    _typeName = 'v8::internal::JSReceiver'

    kPropertiesOrHashOffset = 8
    kHeaderSize = 16

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name":"properties_or_hash", "type":Object},  #SwissNameDictionary|FixedArrayBase|PropertyArray|Smi
            ]}

    #@property
    #def raw_properties_or_hash(self):
    #    return self.LoadPtr(self.kPropertiesOrHashOffset)

    # def GetProperty(self):
    #     return self.LoadPtr(self.kPropertiesOrHashOffset)

    @CachedProperty
    def property_dictionary(self):
        return NameDictionary(self.properties_or_hash)
   
    @CachedProperty
    def property_dictionary_swiss(self):
        return SwissNameDictionary(self.properties_or_hash)

    @CachedProperty
    def property_array(self):
        return PropertyArray(self.properties_or_hash)
    
    def DebugPrint2(self):
        print("[JSReceiver]")
        print(" - properties:", Object.SBrief(self.raw_properties_or_hash))

    def ClassName(self):
        """ return the class name of the object
        """
        t = self.map.instance_type
        if InstanceType.isJSFunction(t):
            return "Function" 
        elif InstanceType.isJSArgumentsObject(t):
            return "Arguments" 
        elif InstanceType.isJSArray(t):
            return "Array"
        elif InstanceType.isJSArrayBuffer(t):
            o = JSArrayBuffer(self)
            if o.is_shared:
                return "SharedArrayBuffer"
            return "ArrayBuffer"
        elif InstanceType.isJSArrayIterator(t):
            return "Array Iterator"
        elif InstanceType.isJSDate(t):
            return "Date"
        elif InstanceType.isJSError(t):
            return "Error"
        elif InstanceType.isJSGeneratorObject(t):
            return ".generator_object"
        elif InstanceType.isJSMap(t):
            return "Map"
        elif InstanceType.isJSMapIterator(t):
            return "Map Iterator"
        elif InstanceType.isJSProxy(t):
            m = self.map
            if m.is_callable:
                return "Function"
            else:
                return "Object"
        elif InstanceType.isJSRegExp(t):
            return "RegExp"
        elif InstanceType.isJSSet(t):
            return "Set"
        elif InstanceType.isJSSetIterator(t):
            return "Set Iterator"

        elif InstanceType.isJSTypedArray(t):
            m = self.map
            if m.elements_kind == ElementsKind.INT8_ELEMENTS:
                return "Int8Array"
            elif m.elements_kind == ElementsKind.INT16_ELEMENTS:
                return "Int16Array"
            elif m.elements_kind == ElementsKind.INT32_ELEMENTS:
                return "Int32Array"
            elif m.elements_kind == ElementsKind.UINT8_ELEMENTS:
                return "Uint8Array"
            elif m.elements_kind == ElementsKind.UINT16_ELEMENTS:
                return "Uint16Array"
            elif m.elements_kind == ElementsKind.UINT32_ELEMENTS:
                return "Uint32Array"
            elif m.elements_kind == ElementsKind.FLOAT32_ELEMENTS:
                return "Float32Array"
            elif m.elements_kind == ElementsKind.FLOAT64_ELEMENTS:
                return "Float64Array"
            elif m.elements_kind == ElementsKind.BIGINT64_ELEMENTS:
                return "BigInt64Array"
            elif m.elements_kind == ElementsKind.BIGUINT64_ELEMENTS:
                return "BigUint64Array"
            else:
                raise Exception('elements_kind(%d) is unknown.' % (m.elements_kind))
      
        elif InstanceType.isJSPrimitiveWrapper(t):
            raise Exception('TBD: not support JSPrimitive Wrapper')

        elif InstanceType.isJSWeakMap(t):
            return "WeakMap"
        elif InstanceType.isJSWeakSet(t):
            return "WeakSet"
        elif InstanceType.isJSGlobalProxy(t):
            return "global"

        else:
            return "Object"

    @CachedProperty
    def class_name(self):
        return self.ClassName()

     


""" Begin of all other Sub-Objects
"""


class BigIntBitFields(BitField):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "sign", "bits": 1},
            {"name": "length", "bits": 30},
        ]}


class BigIntBase(HeapObject):
    _typeName = 'v8::internal::BigIntBase'

    kHeaderSize = 16
    kDigitsOffset = 16
    kDigitSize = 8
    assert kDigitSize == dbg.PointerSize

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "bitfield", "type": BigIntBitFields},
            #{ "name":"digits", "type": None },
        ]}

    @property
    def length(self):
        return int(self.bitfield.length)

    @property
    def sign(self):
        return self.bitfield.sign

    def Digit(self, n):
        return self.LoadU8(self.kDigitsOffset + n * self.kDigitSize)

    def SizeFor(self, length):
        return self.kHeaderSize + (int(length) * self.kDigitSize)

    def Size(self):
        return self.SizeFor(self.length)


class BigInt(BigIntBase):
    """v8 BitInt"""
    pass


class Cell(HeapObject):

    _typeName = 'v8::internal::Cell'

    kValueOffset = 8

    @property
    def value(self):
        return self.LoadPtr(self.kValueOffset)


class Code(HeapObject):
    """ V8 Code Object """

    _typeName = 'v8::internal::Code'

    class CodeFlagsBitFields(BitField):

        @classmethod
        def __autoLayout(cls):
            cfg = AutoLayout.Builder()
            if Version.major >= 9: 
                cfg.Add({"name": "kind_field", "bits": 4, "type":  CodeKind})
            else:
                cfg.Add({"name": "has_unwind_info_field", "bits": 1})
                cfg.Add({"name": "kind_field", "bits": 5, "type":  CodeKind})

            cfg.Adds([
                {"name": "is_turbo_fanned_field", "bits": 1},
                {"name": "stack_slots_field", "bits": 24},
                {"name": "is_off_heap_trampoline", "bits": 1},
            ])
            return cfg.Generate()
                
    class CodeKindSpecificFlagsBitFields(BitField):
        @classmethod
        def __autoLayout(cls):
            cfg = AutoLayout.Builder() 
            cfg.Adds([
                {"name": "marked_for_deoptimization", "bits": 1},
                {"name": "embedded_objects_cleared", "bits": 1},
                {"name": "deopt_already_counted", "bits": 1},
                {"name": "can_have_weak_objects", "bits": 1},
                {"name": "is_promise_rejection", "bits": 1},
                {"name": "is_exception_caught", "bits": 1}
            ])

            if Version.major >= 8:
                cfg.Add({"name": "deopt_count", "bits": 4})
            return cfg.Generate()

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "relocation_info", "type":  Object},
            {"name": "deoptimization_data", "type":  Object},
            {"name": "source_position_table", "type":  Object},
            {"name": "code_data_container", "type":  Object},
            {"name": "data_start"},
            {"name": "instruction_size", "type":  int},
            {"name": "metadata_size", "type": int},
            {"name": "flags", "type": Code.CodeFlagsBitFields},
            {"name": "safepoint_table_offset", "type": int},
            {"name": "handler_table_offset", "type": int},
            {"name": "constant_pool_offset", "type": int},
            {"name": "code_comments_offset", "type": int},
            {"name": "builtin_index", "type": int},
            {"name": "unaligned_header_size", "type": int},
            #{"name": "optional_padding", "type": int},
            {"name": "header_size"},
        ]}

    @property
    def kind(self):
        return self.flags.kind

    @property
    def raw_body_size(self):
        metadata_size = int(self.metadata_size or 0)
        return self.instruction_size + metadata_size

    def SizeFor(self, instr_size):
        size = self.header_size + instr_size
        return Internal.RoundUp(size, Internal.kCodeAlignment)

    def Size(self):
        return self.SizeFor(self.raw_body_size)



class Script(HeapObject):
    """ V8 Script Object """

    _typeName = 'v8::internal::Script'
    class ScriptFlags(BitField):

        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "compilation_type", "bits": 1},
                {"name": "compilation_state", "bits": 1},
                {"name": "is_repl_mode", "bits": 1},
                {"name": "origin_options", "bits": 4},
                {"name": "break_on_entry", "bits": 1},
            ]}
    
    @classmethod
    def __autoLayout(cls):
        return {"layout":  [
            {"name": "source", "type": Object},
            {"name": "name", "type": String},
            {"name": "line_offset", "type": Smi},
            {"name": "column_offset", "type": Smi},
            {"name": "context_data", "type": Object,
                "alias": ["context"]},
            {"name": "script_type", "type": Smi},
            {"name": "line_ends", "type": Object},
            {"name": "id", "type": Smi},
            {"name": "eval_from_shared_or_wrapped_arguments_or_sfi_table", "type": Object,
                "alias": ["eval_from_shared_or_wrapped_arguments"]},
            {"name": "eval_from_position", "type": Object},
            {"name": "flags", "type": SmiTagged(Script.ScriptFlags)},
            {"name": "source_url", "type": Object},
            {"name": "source_mapping_url", "type": Object},
            {"name": "host_defined_options", "type": Object},
        ]}

    def DebugName(self):
        name = self.name
        if name.IsString():
            return name.ToString() 
        return ""

class ContextSlot(Enum):
    _typeName = 'v8::internal::Context::Field'

    SCOPE_INFO_INDEX = 0
    PREVIOUS_INDEX = 1
    EXTENSION_INDEX = 2
    MIN_CONTEXT_SLOTS = 2
    EMBEDDER_DATA_INDEX = 4

    # native context link
    NEXT_CONTEXT_LINK = 0

    # last 
    NATIVE_CONTEXT_SLOTS = 0

    @classmethod
    def Slots(cls):
        assert cls.NATIVE_CONTEXT_SLOTS > 0
        return cls.NATIVE_CONTEXT_SLOTS 

    @classmethod
    def WalkSlots(cls):
        assert cls.NATIVE_CONTEXT_SLOTS > 0
        for i in range(cls.NATIVE_CONTEXT_SLOTS):
            yield cls(i)

class Context(HeapObject):
    _typeName = 'v8::internal::Context'

    kFixedArrayLikeHeaderSize = 16
    kLengthOffset = 8
    kScopeInfoOffset = 16
    kPreviousOffset = 24

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length", "type": SmiTagged(int)},
            {"name": "scope_info", "type": Object},
            {"name": "previous", "type": Object},
        ]}

    @property
    def native_context(self):
        m = self.map
        x = m.GetNativeContext()
        return HeapObject(x)

    def Get(self, index):
        off = self.kFixedArrayLikeHeaderSize + (index * Internal.kTaggedSize)
        return self.LoadPtr(off)

    def GetLocal(self, index):
        index = ContextSlot.MIN_CONTEXT_SLOTS + index
        off = self.kFixedArrayLikeHeaderSize + ( index * Internal.kTaggedSize)
        return self.LoadPtr(off)

    def SizeFor(self, length):
        return self.kFixedArrayLikeHeaderSize + (int(length) * Internal.kTaggedSize)

    def Size(self):
        return self.SizeFor(self.length)

    def WalkAllSlots(self):
        scope_info = ScopeInfo(self.scope_info)

        if scope_info.is_empty:
            return

        local_count = scope_info.context_local_count
        for i in range(local_count):
            name = String(scope_info.context_local_names(i)).ToString()
            o = Object(self.GetLocal(i))
            yield (name, o)

    def DebugPrint(self):
        super(Context, self).DebugPrint()
        print("- Locals: ")
        for i,v in self.WalkAllSlots():
            print("  - %s : %s" % (i, v))

class NativeContext(Context):

    _typeName = 'v8::internal::NativeContext'
    kSize = 0
     
    @classmethod
    def __autoLayout(cls):
        return {
        "layout":[
            { "name":"microtask_queue", "type":Object },
            { "name":"size_of", "alias":["kSize"] },
        ]}

    def Size(self):
        return self.kSize

    def GetJSGlobalObject(self):
        o = self.Get(ContextSlot.EXTENSION_INDEX)
        return JSGlobalObject(o)

    def GetEmbedderData(self):
        o = self.Get(ContextSlot.EMBEDDER_DATA_INDEX)
        return EmbedderDataArray(o)

    def GetJSGlobalProxy(self):
        o = self.Get(ContextSlot.GLOBAL_PROXY_INDEX)
        return JSGlobalProxy(o)

    def GetNextContextLink(self):
        o = self.Get(ContextSlot.NEXT_CONTEXT_LINK)
        return NativeContext(o)

    def WalkAllSlots(self):
        for i in ContextSlot.WalkSlots():
            v = Object(self.Get(i))
            yield (i.name, v)

    def DebugPrint(self):
        print('[NativeContext 0x%x]' % self.tag)
        for n,v in self.WalkAllSlots():
            print(" - %s : %s" % (n, v))

class DescriptorArray(HeapObject):

    _typeName = 'v8::internal::DescriptorArray'

    """
    // A DescriptorArray is a custom array that holds instance descriptors.
    // It has the following layout:
    //   Header:
    //     [16:0  bits]: number_of_all_descriptors (including slack)
    //     [32:16 bits]: number_of_descriptors
    //     [48:32 bits]: raw_number_of_marked_descriptors (used by GC)
    //     [64:48 bits]: alignment filler
    //     [kEnumCacheOffset]: enum cache
    //   Elements:
    //     [kHeaderSize + 0]: first key (and internalized String)
    //     [kHeaderSize + 1]: first descriptor details (see PropertyDetails)
    //     [kHeaderSize + 2]: first value for constants / Smi(1) when not used
    //   Slack:
    //     [kHeaderSize + number of descriptors * 3]: start of slack
    // The "value" fields store either values or field types. A field type is either
    // FieldType::None(), FieldType::Any() or a weak reference to a Map. All other
    // references are strong.
    """

    # sharp definitions
    kEntryKeyIndex = 0
    kEntryDetailsIndex = 1
    kEntryValueIndex = 2
    kEntrySize = 3
    kHeaderSize = 24

    class DescriptorEntry(ALStruct):
        """ Torque definition from descriptor-array.tq
        """
        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "key", "type": Object},  # Name|Undefined
                {"name": "details", "type": SmiTagged(PropertyDetailsFastTo)},
                {"name": "value", "type": Object},  # JSAny|AccessorInfo|AccessorPair|ClassPositions
                ]}

        @classmethod
        def SizeOf(cls):
            return 24

    class EnumCache(ALStruct):
        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "keys", "type": FixedArray},
                {"name": "indices", "type": FixedArray},
                ]}

        @classmethod
        def SizeOf(cls):
            return 16

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "number_of_all_descriptors", "type": int},
            {"name": "number_of_descriptors", "type": int},
            {"name": "raw_number_of_marked_descriptors", "type": int},
            {"name": "filler16_bits", "type": int},
            {"name": "enum_cache", "type": Object},
            {"name": "descriptors[number_of_all_descriptors]", "type": DescriptorArray.DescriptorEntry,
                "offset": cls.kHeaderSize},
        ]}

    @property
    def number_of_slack_descriptors(self):
        return self.number_of_all_descriptors - self.number_of_descriptors

    def GetKey(self, index):
        #entry_offset = self.OffsetOfDescriptorAt(index) + (self.kEntryKeyIndex * Internal.kTaggedSize)
        return self.descriptors(index).key

    def GetDetails(self, index):
        #entry_offset = self.OffsetOfDescriptorAt(index) + (self.kEntryDetailsIndex * Internal.kTaggedSize)
        #return PropertyDetails(self.LoadPtr(entry_offset))
        #v = self.descriptors(index + self.kEntryDetailsIndex)
        #return PropertyDetails(v)
        return self.descriptors(index).details

    def GetValue(self, index):
        #entry_offset = self.OffsetOfDescriptorAt(index) + (self.kEntryValueIndex * Internal.kTaggedSize)
        #return self.LoadPtr(entry_offset)
        #v = self.descriptors(index + self.kEntryValueIndex)
        #return Object(v)
        return self.descriptors(index).value

    #def OffsetOfDescriptorAt(self, index):
        #return self.kDescriptorsOffset + index * self.kEntrySize * Internal.kTaggedSize
        #offset = self.ALGetOffset(self.descriptors)
        #offset = self.descriptors__offset
        #item = index * self.kEntrySize
        #return offset + (item * Internal.kTaggedSize)

    #def SizeFor(self, num_of_all_desc):
    #    return self.OffsetOfDescriptorAt(num_of_all_desc)

    def Size(self):
        return int(self.descriptors__offset_end)
        #return int(self.SizeFor(self.number_of_all_descriptors))

    def WalkProperties(self):
        for i in range(self.number_of_descriptors):
            item = self.descriptors(i)
            yield (item.key, item.details, item.value)

    def Search(self, name):
        for i in range(self.number_of_descriptors):
            item = self.descriptors(i)
            key = Name(item.key)
            if key.ToString() == name:
                return i
        # not found
        return None

    def SPrintDescriptorDetails(self, index):
        details = self.GetDetails(index)
        out = details.PrintAsFastTo()
        out += " @ "
        value = self.GetValue(index)
        if details.location == PropertyLocation.kField:
            out += "Field: %s" % FieldType(value).SPrintTo()
        elif details.location == PropertyLocation.kDescriptor:
            out += "Descriptor: 0x%x" % value
        else:
            print(details.location)
            raise Exception
        return out

    def PrintDescriptors(self):
        for i in range(self.number_of_descriptors):
            k = self.GetKey(i)
            print ("   [%d] '%s' %s" % (i, k.to_string(), self.SPrintDescriptorDetails(i)))

    def DebugPrint2(self):
        print("DescriptorArray")
        print(" - enum_cache:")
        print("   0x%x" % self.enum_cache)
        print(" - nof slack descriptors: %d" % self.number_of_slack_descriptors)
        print(" - nof descriptors: %d" % self.number_of_descriptors)
        self.PrintDescriptors()

class EmbedderDataArray(HeapObject):

    _typeName = 'v8::internal::EmbedderDataArray'
    kHeaderSize = 16

    @classmethod
    def __autoLayout(cls):
        return {
        "layout":[
            { "name":"length", "type":Smi },
        ]}

    def SizeFor(self, length):
        return self.kHeaderSize + (int(length) * Internal.kEmbedderDataSlotSize)

    def Size(self):
        return self.SizeFor(int(self.length))

    def Get(self, index):
        return self.LoadPtr(self.kHeaderSize + (index * Internal.kEmbedderDataSlotSize))

    def DebugPrint2(self):
        print("EmbedderDataArray")
        a = FixedArray(self.tag())
        a.PrintElements()


class FreeSpace(HeapObject):

    _typeName = 'v8::internal::FreeSpace'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "size", "type": Smi},
            {"name": "next", "type": Object},
        ]}

    def Size(self):
        return int(self.size)


class FeedbackMetadata(HeapObject):

    _typeName = 'v8::internal::FeedbackMetadata'

    kHeaderSize = 16
    kSlotCountOffset = 8
    kFeedbackCellCountOffset = 12
    kFeedbackSlotKindBits = 5
    @classmethod
    def word_count(cls, slot_count):
        if slot_count == 0: return 0
        v = ((slot_count - 1) // ( 32 // cls.kFeedbackSlotKindBits)) + 1
        return v

    @property
    def slot_count(self):
        return self.LoadU32(self.kSlotCountOffset)

    def SizeFor(self, slot_count):
        # kInt32Size
        return Internal.ObjectPointerAlign(self.kHeaderSize + (self.word_count(slot_count) * 4))

    def Size(self):
        return self.SizeFor(self.slot_count)

class FeedbackVectorFlags(BitField):

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "optimization_marker", "bits": 3},
            {"name": "optimization_tier", "bits": 2},
            {"name": "global_ticks_at_last_runtime_profiler_interrupt", "bits": 24},
        ]}

class FeedbackSlotKind(Enum):
    _typeName = 'v8::internal::FeedbackSlotKind'


class FeedbackVector(HeapObject):

    _typeName = 'v8::internal::FeedbackVector'

    kHeaderSize = 48
    kLengthOffset = 32
    kFeedbackSlotsOffset = 48

    @classmethod
    def __autoLayout(cls):
        return {
        "layout": [
            { "name":"length", "type":int },
            { "name":"invocation_count", "type":int },
            { "name":"profiler_ticks", "type":int },
            { "name":"flags", "type":FeedbackVectorFlags },
            { "name":"shared_function_info", "type":Object },
            { "name":"maybe_optimized_code", "type":Object },
            { "name":"closure_feedback_cell_array", "type":Object },
            { "name":"feedback_slots[length]", "type":Object },
        ]}

    def OffsetElementAt(self, index):
        return self.kFeedbackSlotsOffset + (index * Internal.kTaggedSize)

    def SizeFor(self, length):
        return self.OffsetElementAt(length)

    def Size(self):
        return self.SizeFor(self.length)

class FieldType(Object):
    _typeName = 'v8::internal::FieldType'

    def isNone(self):
        if self.isSmi():
            v = self.as_Smi().ToInt()
            return v == 2
        return False

    def isAny(self):
        if self.isSmi():
            v = self.as_Smi().ToInt()
            return v == 1
        return False

    def isClass(self):
        if self.IsHeapObject():
            return True
        return False

    def SPrintTo(self):
        if self.isAny():
            out = 'Any'
        elif self.isNone():
            out = 'None'
        else:
            out = "Class(0x%x)" % self.stor()
        return out


class WeakArrayList(HeapObject):

    _typeName = 'v8::internal::WeakArrayList'

    kHeaderSize = 24
    #kCapacityOffset = 8
    #kLengthOffset = 16

    @classmethod
    def __autoLayout(cls):
        return {
        "layout":[
            { "name":"capacity", "type":Smi },
            { "name":"length", "type":Smi },
            { "name":"objects[capacity]", "type":Object},  #"offset":cls.kHeaderSize },
        ]}

    def SizeFor(self, capacity):
        #return self.kHeaderSize + (capacity * Internal.kTaggedSize)
        #offset = self.ALGetOffset(self.objects)
        offset = self.objects__offset
        index = capacity * Internal.kTaggedSize
        return offset + index

    def Size(self):
        return self.SizeFor(int(self.capacity))


"""
//     - JSReceiver  (suitable for property access)
//       - JSObject
//         - JSArray
//         - JSArrayBuffer
//         - JSArrayBufferView
//           - JSTypedArray
//           - JSDataView
//         - JSCollection
//           - JSSet
//           - JSMap
//         - JSCustomElementsObject (may have elements despite empty FixedArray)
//           - JSSpecialObject (requires custom property lookup handling)
//             - JSGlobalObject
//             - JSGlobalProxy
//             - JSModuleNamespace
//           - JSPrimitiveWrapper
//         - JSDate
//         - JSFunctionOrBoundFunction
//           - JSBoundFunction
//           - JSFunction
//         - JSGeneratorObject
//         - JSMapIterator
//         - JSMessageObject
//         - JSRegExp
//         - JSSetIterator
//         - JSStringIterator
//         - JSWeakCollection
//           - JSWeakMap
//           - JSWeakSet
"""


class JSObject(JSReceiver):
    """ V8 JSObject """

    _typeName = 'v8::internal::JSObject'

    #kElementsOffset = 16
    kHeaderSize = 24
    kFieldsAdded = 3 

    """
        Properties storage,
        1) JSObject.Map.Descriptor (DescriptorArray) holds properties name and details
        2) JSObject.Properties (PropertyArray) holds named properties, aka JSReceiver.PropertiesOrHash
        3) JSObject.Elements (FixedArray) holds array properties
        4) In Object properties (JSObject tail slots)

        Three types of named properities,
           e.g. object['named'] = obj

        1) in object (very fast properties)
           slots after JSObject Header, predefined,
           holds the properties values (key and details in DescriptorArray)

        2) normal PropertyArray, (fast properties)
           the JSObject.Properties pointer to a PropertyArray,
           holds the properties value (key and details in DescriptorArray)

        3) Property Dictionary, (slow properties)
           JSObject.Map.Descriptor pointer to a EMPTY Descriptor. (no DescriptorArray)
           the JSObject.Properties pointer to a NAME_DICTIONARY_TYPE,
           holds the {key, value, details} array for whole named properties.

        Array properties,
           e.g. object[0] = 0

        1) JSObject.Elements holds the properties could be referenced by index.

    """

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "elements", "type": FixedArrayBase},
            ]}

    """ raw properties, return only Object type.
    """
    @CachedProperty
    def raw_properties(self):
        return self.properties_or_hash

    @CachedProperty
    def raw_elements(self):
        return self.elements

    @CachedProperty
    def raw_descriptors(self):
        return self.map.instance_descriptors

    """ get properties storages
    """
    @CachedProperty
    def properties_array(self):
        return PropertyArray(self.raw_properties)

    @CachedProperty
    def properties_dictionary(self):
        return NameDictionary(self.raw_properties)

    @CachedProperty
    def properties_swiss_dictionary(self):
        return SwissNameDictionary(self.raw_properties)

    @CachedProperty
    def global_dictionary(self):
        return GlobalDictionary(self.raw_properties)

    @CachedProperty
    def elements_array(self):
        elm = self.raw_elements
        if elm.IsFixedDoubleArray():
            return FixedDoubleArray(elm)
        return FixedArray(elm)

    @CachedProperty
    def descriptors_array(self):
        return DescriptorArray(self.raw_descriptors)

    """ inner functions 
    """
    @CachedProperty
    def number_of_inobjects(self):
        return self.map.number_of_inobjects 

    @CachedProperty
    def number_of_own_descriptors(self):
        return self.map.number_of_own_descriptors

    def IsInobject(self, field_index):
        """ indicate index whether is inobject property """
        return field_index < self.number_of_inobjects 

    """ Raw At() functions (without type)
    """
    def RawInObjectPropertyAt(self, field_index, is_double=False):
        """ get inobject value
        """
        assert field_index < self.number_of_inobjects
        array_index = self.kHeaderSize + (field_index * Internal.kTaggedSize)
        if is_double:
            return self.LoadDouble(array_index)
        return self.LoadPtr(array_index)

    def RawFastPropertyAt(self, field_index, is_double=False):
        """ get property value by property_index.
        """
        # get field_index from descriptors
        #field_index = self.descriptors_array.GetDetails(property_index).field_index
        array_index = field_index - self.number_of_inobjects
        assert array_index >= 0, (field_index, self.number_of_inobjects)

        # get value
        array = self.properties_array
        if is_double:
            return array.GetDouble(array_index)
        return array.Get(array_index)

    """ Property At Functions
    """
    def FastPropertyAt(self, property_index, details=None):
        """ get property at index
        """
        if details is None:
            details = self.descriptors_array.GetDetails(property_index)
        is_double = details.IsDouble()
        field_index = details.field_index
        if self.IsInobject(field_index):
            value = self.RawInObjectPropertyAt(field_index, is_double)
        else:
            value = self.RawFastPropertyAt(field_index, is_double)
        assert value is not None, 'index=%d, <0x%x>' % (field_index, self)
        if is_double:
            return value
        return Object(value)

    def DictPropertyAt(self, index):
        if self.IsSwissNameDictionary():
            raise Exception('TBD')
        else:
            dict = self.property_dictionary
            return Object(dict.ValueAt(index))

    """ public methods
    """
    def WalkAllProperties(self):
        if self.has_fast_properties:
            # not a dictionary map
            descs = self.descriptors_array
            nof_inobject_prop = self.map.number_of_inobjects
            for i in range(self.number_of_own_descriptors):
                key = Name(descs.GetKey(i)).ToString()
                details = descs.GetDetails(i)
                if details.location == PropertyLocation.kField:
                    value = self.FastPropertyAt(i, details)
                elif details.location == PropertyLocation.kDescriptor:
                    value = descs.GetValue(i)
                yield (key, details, value)

        elif InstanceType.isJSGlobalObject(self.instance_type):
            # JSGlobalObject
            dicts = self.global_dictionary
            for (key, details, value) in dicts.WalkProperties():
                # TBD: filter out roots
                yield (key, details, value)
            
        else:
            # dictionary map
            dicts = self.properties_dictionary
            for (key, details, value) in dicts.WalkProperties():
                yield (key, details, value)

    def WalkAllElements(self):
        elements = self.elements_array
        return elements.WalkElements()

    #def Lookup(self, name):
    #    """ Lookup name in properties, return index of the property.
    #    """
    #    pass

    def GetConstructorTuple(self):
        m = self.map
        t = m.instance_type
        
        # new target is base, the constructor has the accurate name.
        if not InstanceType.isJSProxy(t) and \
            m.new_target_is_base and \
            not m.is_prototype_map:
            func = HeapObject(m.constructor)
            func_type = func.map.instance_type
            # JSFunction
            if InstanceType.isJSFunction(func_type):
                constructor = JSFunction(m.constructor)
                name = constructor.FunctionName()
                if name and len(name) > 0:
                    return (constructor, name)

            # FunctionTemplateInfo 
            elif InstanceType.isFunctionTemplateInfo(func_type):
                raise Exception('TBD') 
           
        receiver = self
        # Lookup Symbol.toStringTag
        #it_symbol_to_string_tag = LookupIterator(receiver, 
        #        name="Symbol.toStringTag",
        #        configuration=LookupIterator.Configuration.PROTOTYPE_CHAIN_SKIP_INTERCEPTOR,
        #    )
        #maybe_tag = it_symbol_to_string_tag.GetDataProperty()
        #if maybe_tag:
        #    tag = String(maybe_tag)
        #    if tag.IsString():
        #        #print("2 GetConstructorTuple.tag_name")
        #        return (None, tag.ToString())

        # Protoperty Iterator
        it = PrototypeIterator(receiver) 
        if it.IsAtEnd():
            #print("2 GetConstructorTuple.IsAtEnd")
            return (None, self.ClassName())

        start = it.GetCurrent()
        it_constructor = LookupIterator(receiver, 
                name="constructor",
                configuration=LookupIterator.Configuration.PROTOTYPE_CHAIN_SKIP_INTERCEPTOR,
                lookup_start_object=start,
            )
        maybe_constructor = it_constructor.GetDataProperty()
        if maybe_constructor:
            constructor = JSFunction(maybe_constructor)
            if constructor.IsJSFunction():
                name = constructor.FunctionName()
                if name and len(name) > 0:
                    #print("2 GetConstructorTuple.construtor")
                    return (constructor, name)

        # default class name
        return (None, self.ClassName())

    def GetPrototype(self):
        it = PrototypeIterator(self)
        return it.GetCurrent()

    def GetConstructorName(self):
        constructor, name = self.GetConstructorTuple()
        return name

    @CachedProperty
    def named_properties(self):
        """ get all JSObject's named properties.
        """
        data = {}
        for (k,d,v) in self.WalkAllProperties():
            data[k] = v
        return data

    @CachedProperty
    def indexed_properties(self):
        data = []
        for (i,v) in self.WalkAllElements():
            data.append(v) 
        return data

    def PrintElements(self):
        elements = self.elements_array
        if elements.length == 0:
            print('- Elements: []')
            return

        print('- Elements: [')
        for (i,v) in self.WalkAllElements():
            # TBD: by ElementsKind
            print(" %d: %s" % (i, str(v)))
        print(']')

    def DebugPrint(self):
        if self.__class__ != JSObject:
            super(JSObject, self).DebugPrint()

        print('[JSObject 0x%x]' % self.tag)
        properties = self.named_properties
        if len(properties) > 0:
            print('- Properties:')
            for k,v in properties.items():
                if isinstance(v, Object):
                    print(" - %s: %s" % (k, v.Brief()))
                else:
                    print(" - %s: %s" % (k, v))
        else:
            print('- Properties: {}')

        self.PrintElements()

        constructor, name = self.GetConstructorTuple()
        print(" - constructor: %s" % constructor)
        print(" - name: %s" % name)

class JSProxy(JSReceiver):
    _typeName = 'v8::internal::JSProxy'


class JSMap(JSObject):
    _typeName = 'v8::internal::JSMap'


class JSSet(JSObject):
    _typeName = 'v8::internal::JSSet'


class JSFunction(JSObject):
    """ V8 JSFunction """

    _typeName = 'v8::internal::JSFunction'

    kSharedFunctionInfoOffset = 24
    kContextOffset = 32
    kFeedbackCellOffset = 40
    kCodeOffset = 48
    kPrototypeOrInitialMapOffset = 56

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "shared_function_info", "type": SharedFunctionInfo},
            {"name": "context", "type": Context},
            {"name": "feedback_cell", "type": Object},
            {"name": "code", "type": Code},
            {"name": "prototype_or_initial_map?[has_prototype_or_initial_map]", "type": Object},
        ]}

    @property
    def has_prototype_or_initial_map(self):
        return self.Size() > self.kPrototypeOrInitialMapOffset 

    def FunctionName(self):
        return self.shared_function_info.GetFunctionName()

    def FunctionNameStr(self):
        """ return empty string if doesn't have a name """
        name = self.FunctionName()
        if name is None:
            return ''
        return name

    @property
    def prototype(self):
        m = self.map
        # non-JSReceiver prototype stores in map's constructor
        if m.has_non_instance_prototype:
            return Object(m.constructor)
        return self.prototype_or_initial_map

    def DebugPrint(self):
        super(JSFunction, self).DebugPrint()

class JSBoundFunction(HeapObject):
    _typeName = 'v8::internal::JSBoundFunction'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "bound_target_function", "type": Object},
            {"name": "bound_this", "type": Object},
            {"name": "bound_arguments", "type": FixedArray},
        ]}
 
class PreparseData(HeapObject):
    """ store the pre-parser information about scopes and inner functions.
    """
    _typeName = 'v8::internal::PreparseData'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "data_length", "type": int},
            {"name": "children_length", "type": int, "alias": ["inner_length"]},
            {"name": "data_start", "alias": ["kSize"]},
        ]}

    def InnerOffset(self, data_length):
        return Internal.RoundUp(self.data_start + (data_length * 1), Internal.kTaggedSize) 

    def SizeFor(self, data_length, children_length):
        return self.InnerOffset(data_length) + children_length * Internal.kTaggedSize

    def Size(self):
        return self.SizeFor(self.data_length, self.children_length) 


class UncompiledData(HeapObject):
    _typeName = 'v8::internal::UncompiledData'


class UncompiledDataWithoutPreparseData(UncompiledData):
    _typeName = 'v8::internal::UncompiledDataWithoutPreparseData'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "inferred_name", "type": String},
            {"name": "start_position", "type": int},
            {"name": "end_position", "type": int},
            {"name": "size"},
        ]}


class UncompiledDataWithPreparseData(UncompiledData):
    _typeName = 'v8::internal::UncompiledDataWithPreparseData'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "inferred_name", "type": String},
            {"name": "start_position", "type": int},
            {"name": "end_position", "type": int},
            {"name": "preparse_data", "type": PreparseData},
            {"name": "size"},
        ]}


class SharedFunctionInfo(HeapObject):
    """ SharedFunctionInfo """

    _typeName = 'v8::internal::SharedFunctionInfo'

    kNoSharedNameSentinel = 0

    class SharedFunctionInfoFlags(BitField):

        @classmethod
        def __autoLayout(cls):
            layout = [
                {"name": "function_kind", "bits": 5, "type": FunctionKind},
                {"name": "is_native", "bits": 1},
                {"name": "is_strict", "bits": 1},
                {"name": "function_syntax_kind", "bits": 3, "type": FunctionSyntaxKind},
                {"name": "is_class_constructor", "bits": 1},
                {"name": "has_duplicate_parameters", "bits": 1},
                {"name": "allow_lazy_compilation", "bits": 1},
                {"name": "is_asm_wasm_broken", "bits": 1},
                {"name": "function_map_index", "bits": 5},
                {"name": "disabled_optimization_reason", "bits": 4, "type": int},  # BailoutReason
                {"name": "requires_instance_members_initializer", "bits": 1},
                {"name": "construct_as_builtin", "bits": 1},
                {"name": "name_should_print_as_anonymous", "bits": 1},
                {"name": "has_reported_binary_coverage", "bits": 1},
                {"name": "is_top_level", "bits": 1},
            ]
            if Version.major <= 8:
                layout.extend([
                    {"name": "is_oneshot_iife_or_properties_are_final", "bits": 1},
                    {"name": "is_safe_to_skip_arguments_adaptor", "bits": 1},
                    {"name": "private_name_lookup_skips_outer_class", "bits": 1},
                ])
            elif Version.major > 8:
                layout.extend([
                    {"name": "properties_are_final", "bits": 1},
                    {"name": "private_name_lookup_skips_outer_class", "bits": 1},
                    {"name": "osr_code_cache_state", "bits": 2, "type": int},  # OSRCodeCacheStateOfSFI
                ])

            return {"layout": layout}

    class SharedFunctionInfoFlags2(BitField):

        @classmethod
        def __autoLayout(cls):
            return {"layout": [
                {"name": "class_scope_has_private_brand", "bits": 1},
                {"name": "has_static_private_methods_or_accessors", "bits": 1},
            ]}

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
                {"name": "function_data", "type": Object}, # UncompiledData|Smi|InterpreterData
                {"name": "name_or_scope_info", "type": Object},  # String|NoSharedNameSentine|ScopeInfo
                {"name": "outer_scope_info_or_feedback_metadata", "type": Object},  # HeapObject
                {"name": "script_or_debug_info", "type": Object},  # Script|DebugInfo|Undefined
                {"name": "length", "type": int, "size": 2},
                {"name": "formal_parameter_count", "type": int, "size": 2},
                {"name": "function_token_offset", "type": int, "size": 2},
                {"name": "expected_nof_properties", "type": int, "size": 1},
                {"name": "flags2", "type": SharedFunctionInfo.SharedFunctionInfoFlags2},
                {"name": "flags", "type": SharedFunctionInfo.SharedFunctionInfoFlags},
                {"name": "function_literal_id", "type": int, "size": 4},
            ]}

    @property
    def script(self):
        o = Script(self.script_or_debug_info)
        if o.IsScript():
            return o
        return None 

    @CachedProperty
    def uncompiled_data(self):
        return UncompiledData(self.function_data)

    def GetInferrredName(self):
        """ get inferrer name, None if not found
        """
        v = HeapObject(self.name_or_scope_info)
        if not v.IsHeapObject():
            return None 
        t = v.map.instance_type
        if InstanceType.isScopeInfo(t):
            scope_info = ScopeInfo(v) 

    def GetFunctionName(self):
        """ get funtion name, None if not found.
        """
        v = HeapObject(self.name_or_scope_info)
        if not v.IsHeapObject():
            return None 
        t = v.map.instance_type
        if InstanceType.isString(t):
            return String(v).to_string()
        elif InstanceType.isScopeInfo(t):
            o = ScopeInfo(v)
            return o.FunctionNameStr()
        else:
            raise Exception('unknown function type.')
        return None 

    def Name(self):
        v = HeapObject(self.name_or_scope_info)
        if not v.IsHeapObject():
            return None 
        t = v.map.instance_type
        if InstanceType.isString(t):
            return String(v).to_string()
        elif InstanceType.isScopeInfo(t):
            o = ScopeInfo(v)
            return o.Name()
        else:
            raise Exception('unknown function type.')
        return None 

    def NameStr(self):
        v = self.Name()
        if v is None:
            return ""
        return v

    def DebugName(self):
        """ return blank string if not decoded. """
        name = self.GetFunctionName()
        if name is None or len(name) == 0:
            return ""
        return name

    @CachedProperty
    def parameter_count(self):
        return self.formal_parameter_count

    def DebugPrint2(self):
        print(" - function_data :", Object.SBrief(self.function_data))
        print(" - name:", Object.SBrief(self.name_or_scope_info))
        print(" - outer_scope_info: ", Object.SBrief(self.outer_scope_info_or_feedback_metadata))
        print(" - script_or_debuginfo: ", Object.SBrief(self.script_or_debug_info))
        print(" - length: %d" % (self.length))
        print(" - formal_parameter_count: %d" % (self.formal_parameter_count))
        print(" - function_token: %d" % (self.function_token))
        print(" - expected_nof_properties: %d" % (self.expected_nof_properties))
        print(" - flags: 0x%x 0x%x" % (self.flags, self.flags2))
        print(" - funtion_liternal_id: %d" % (self.function_liternal_id))

        flags = SharedFunctionInfo.Flags(self.flags)
        flags2 = SharedFunctionInfo.Flags2(self.flags2)

        if flags2.class_scope_has_private_brand:
            print(" - class_scope_has_private_brand")
        if flags2.has_static_private_methods_or_accessors:
            print(" - has_static_private_methods_or_accessors")
        if flags.needs_home_object:
            print(" - needs_home_object")
        if flags.is_safe_to_skip_arguments_adaptor:
            print(" - safe_to_skip_arguments_adaptor")

        print(" - kind: ", flags.function_kind, FunctionKind.CamelName(flags.function_kind))
        print(" - syntax kind: ", flags.function_syntax_kind, FunctionSyntaxKind.CamelName(flags.function_syntax_kind))


class JSArray(JSObject):
    _typeName = 'v8::internal::JSArray'


class JSGeneratorObject(JSObject):
    _typeName = 'v8::internal::JSGeneratorObject'

    kFunctionOffset = 24
    kContextOffset = 32
    kReceiverOffset = 40
    kInputOrDebugPosOffset = 48
    kResumeModeOffset = 56
    kContinuationOffset = 64
    kParametersAndRegistersOffset = 72

    @property
    def function(self):
        return self.LoadPtr(self.kFunctionOffset)

    @property
    def context(self):
        return self.LoadPtr(self.kContextOffset)

    @property
    def receiver(self):
        return self.LoadPtr(self.kReceiverOffset)

    @property
    def input_or_debug_pos(self):
        return self.LoadPtr(self.kInputOrDebugPosOffset)

    @property
    def resume_mode(self):
        return self.LoadSmi(self.kResumeModeOffset)

    @property
    def continuation(self):
        return self.LoadSmi(self.kContinuationOffset)

    @property
    def parameters_and_register(self):
        return self.LoadPtr(self.kParametersAndRegistersOffset)

    def DebugPrint2(self):
        print("[JSGeneratorObject]")
        print(" - function :", Object.SBrief(self.function))
        print(" - context :", Object.SBrief(self.context))
        print(" - receiver :", Object.SBrief(self.receiver))
        print(" - input_or_debug_pos :", Object.SBrief(self.input_or_debug_pos))
        print(" - resume_mode : %d" % self.resume_mode)
        print(" - continuation : %d" % self.continuation)
        print(" - parameters_and_register :", Object.SBrief(self.parameters_and_register))
        super(JSObject, self).DebugPrint()

class JSAsyncFunctionObject(JSGeneratorObject):
    _typeName = 'v8::internal::JSAsyncFunctionObject'

    kPromiseOffset = 80

    @property
    def promise(self):
        return self.LoadPtr(self.kPromiseOffset)

    def DebugPrint2(self):
        print("[JSAsyncFunctionObject]")
        print(" - promise :", Object.SBrief(self.promise))
        super(JSAsyncFunctionObject, self).DebugPrint()

class JSAsyncGeneratorObject(JSGeneratorObject):
    _typeName = 'v8::internal::JSAsyncGeneratorObject'

    kQueueOffset = 80
    kIsAwaiting = 88

    @property
    def queue(self):
        return self.LoadPtr(self.kQueueOffset)

    @property
    def is_awaiting(self):
        return self.LoadSmi(self.kIsAwaitingOffset)

    def DebugPrint2(self):
        print("[JSAsyncGeneratorObject]")
        print(" - queue :", Object.SBrief(self.queue))
        print(" - is_awaiting : %d", self.is_awaiting)
        super(JSAsyncGeneratorObject, self).DebugPrint()

class JSGlobalObject(JSObject):
    """ JS Global Object """

    _typeName = 'v8::internal::JSGlobalObject'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "native_context", "type": NativeContext},
            {"name": "global_proxy", "type": JSGlobalProxy},
        ]}



class JSGlobalProxy(JSObject):
    """ JS Global Proxy """

    _typeName = 'v8::internal::JSGlobalProxy'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "native_context", "type": Object},
        ]}


class JSPrimitiveWrapper(JSObject):
    """ JS Primitive Wrapper """

    _typeName = 'v8::internal::JSPrimitiveWrapper'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "value", "type": JSObject},
        ]}


class JSArrayBuffer(JSObject):
    """ JS Array Buffer """
    
    _typeName = 'v8::internal::JSArrayBuffer'


    class JSArrayBufferFlags(BitField):

        @classmethod
        def __autoLayout(cls):
            return {"layout":[
                {"name": "is_external", "bits": 1},
                {"name": "is_detachable", "bits": 1},
                {"name": "was_detached", "bits": 1},
                {"name": "is_asm_js_memory", "bits": 1},
                {"name": "is_shared", "bits": 1},
                {"name": "is_resizable", "bits": 1},
            ]}

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "byte_length", "type": int},
            {"name": "max_byte_length", "type": int},
            {"name": "backing_store", "type": int},
            {"name": "extension", "type": int},
            {"name": "bit_field", "type": JSArrayBuffer.JSArrayBufferFlags},
        ]}

    @CachedProperty
    def is_shared(self):
        return self.bit_field.is_shared

class JSPromise(JSObject):
    """ JS Promise """

    _typeName = 'v8::internal::JSPromise'

    kReactionsOrResultOffset = 24
    kFlagsOffset = 32

    @property
    def reactions_or_result(self):
        return self.LoadPtr(self.kReactionsOrResultOffset)

    @property
    def flags(self):
        return self.LoadPtr(self.kFlagsOffset)

    @property
    def flags_status(self):
        return self.LoadBitSize(self.kFlagsOffset, 0, 2)

    @property
    def flags_has_handler(self):
        return self.LoadBit(self.kFlagsOffset, 2)

    @property
    def flags_handled_hint(self):
        return self.LoadBit(self.kFlagsOffset, 3)

    @property
    def flags_async_task_id(self):
        return self.LoadBitSize(self.kFlagsOffset, 4, 22)

    def DebugPrint2(self):
        print("[JSPromise]")
        print(" - reactions_or_result : ", Object.SBrief(self.reactions_or_result))
        print(" - flags : 0x%x" % self.flags)
        print("   - status: %s (%d)" % (PromiseState.Name(self.flags_status), self.flags_status))
        print("   - has_handler: %d" % self.flags_has_handler)
        print("   - handled_hint: %d" % self.flags_handled_hint)
        print("   - async_task_id: %d" % self.flags_async_task_id)
        super(JSObject, self).DebugPrint()



"""
//     - Struct
//       - AccessorInfo
//       - AsmWasmData
//       - PromiseReaction
//       - PromiseCapability
//       - AccessorPair
//       - AccessCheckInfo
//       - InterceptorInfo
//       - CallHandlerInfo
//       - EnumCache
//       - TemplateInfo
//         - FunctionTemplateInfo
//         - ObjectTemplateInfo
//       - Script
//       - DebugInfo
//       - BreakPoint
//       - BreakPointInfo
//       - CachedTemplateObject
//       - StackFrameInfo
//       - StackTraceFrame
//       - CodeCache
//       - PropertyDescriptorObject
//       - PrototypeInfo
//       - Microtask
//         - CallbackTask
//         - CallableTask
//         - PromiseReactionJobTask
//           - PromiseFulfillReactionJobTask
//           - PromiseRejectReactionJobTask
//         - PromiseResolveThenableJobTask
//       - Module
//         - SourceTextModule
//         - SyntheticModule
//       - SourceTextModuleInfoEntry
//       - WasmValue
"""


class PromiseCapability(HeapObject):
    _typeName = 'v8::internal::PromiseCapability'

    kPromiseOffset = 8
    kResolveOffset = 16
    kRejectOffset = 24

    @property
    def promise(self):
        return self.LoadPtr(self.kPromiseOffset)

    @property
    def resolve(self):
        return self.LoadPtr(self.kResolveOffset)

    @property
    def reject(self):
        return self.LoadPtr(self.kRejectOffset)

    def DebugPrint2(self):
        print('[PromiseCapability]')
        print(' - Promise: ', Object.SBrief(self.promise))
        print(' - Resolve: ', Object.SBrief(self.resolve))
        print(' - Reject : ', Object.SBrief(self.reject))


class PromiseReaction(HeapObject):
    _typeName = 'v8::internal::PromiseReaction'

    kNextOffset = 8
    kRejectHandlerOffset = 16
    kFulfillHandlerOffset = 24
    kPromiseOrCapabilityOffset = 32
    kContinuationPreservedEmbedderDataOffset = 40

    @property
    def next(self):
        return self.LoadPtr(self.kNextOffset)

    @property
    def reject_handler(self):
        return self.LoadPtr(self.kRejectHandlerOffset)

    @property
    def ful_fill_handler(self):
        return self.LoadPtr(self.kFulfillHandlerOffset)

    @property
    def promise_or_capability(self):
        return self.LoadPtr(self.kPromiseOrCapabilityOffset)

    @property
    def continuation_reserved_embeder_data(self):
        return self.LoadPtr(self.kContinuationPreservedEmbedderDataOffset)

    def DebugPrint2(self):
        print('[PromiseReaction]')
        print(' - next :', Object.SBrief(self.next))
        print(' - reject_handler :', Object.SBrief(self.reject_handler))
        print(' - full_fill_handler :', Object.SBrief(self.ful_fill_handler))
        print(' - promise_or_capability :', Object.SBrief(self.promise_or_capability))
        print(' - continuation_reserved_embeder_data :', Object.SBrief(self.continuation_reserved_embeder_data))

class PromiseReactionJobTask(HeapObject):
    _typeName = 'v8::internal::PromiseReactionJobTask'

    @classmethod
    def __autoLayout(cls):
        return {
        "layout":[
            { "name":"argument", "type":Object },
            { "name":"context", "type":Object },
            { "name":"handler", "type":Object },
            { "name":"promise_or_capability", "type":Object },
            { "name":"continuation_reserved_embeder_data", "type":Object },
            { "name":"size_of",
                "alias":["kSizeOfAllPromiseReactionJobTasks", "kSize"] },
        ]}

    def Size(self):
        return self.size_of

class PromiseFulfillReactionJobTask(PromiseReactionJobTask):
    _typeName = 'v8::internal::PromiseFulfillReactionJobTask'


class PromiseRejectReactionJobTask(PromiseReactionJobTask):
    _typeName = 'v8::internal::PromiseRejectReactionJobTask'


class PropertyDetails(BitField):
    _typeName = 'v8::internal::PropertyDetails'

    #kDescriptorIndexBitCount = 10

    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        cfg.Add({"name": "kind", "bits": 1, "type": PropertyKind})
        if Version.major <= 9:
            cfg.Add({"name": "location", "bits": 1, "type": PropertyLocation})
        cfg.Add({"name": "constness", "bits": 1, "type": PropertyConstness})
        cfg.Add({"name": "attributes", "bits": 3, "type": PropertyAttributes})
        return cfg.Generate()

    def RepresentationKind(self):
        return None

    def IsDouble(self):
        rep = self.RepresentationKind()
        if rep is None:
            return False
        return rep == RepresentationKind.kDouble


class PropertyDetailsFastTo(PropertyDetails):
    """ BitFields for Fast Property details.
    """

    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        # we need's Bits defines in PropertyDetails
        cfg.Inherit()
        # for node-v18
        if Version.major >= 10:
            cfg.Add({"name": "location", "bits": 1, "type": PropertyLocation, "after": "attributes"})
            cfg.Add({"name": "representation", "bits": 3, "type": RepresentationKind}),
        else:
            cfg.Add({"name": "representation", "bits": 3, "type": RepresentationKind, "after": "attributes"}),
        cfg.Add({"name": "descriptor_pointer", "bits": Internal.kDescriptorIndexBitCount, "type": int})
        cfg.Add({"name": "field_index", "bits": Internal.kDescriptorIndexBitCount, "type": int})
        return cfg.Generate()

    def RepresentationKind(self):
        return self.representation

class PropertyDetailsSlowTo(PropertyDetails):
    """ BitFields for Slow Property details.
    """
    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        # we need's Bits defines in PropertyDetails
        cfg.Inherit()
        # for node-v18
        if Version.major >= 10:
            cfg.Add({"name": "property_cell_type", "bits": 3, "type": PropertyCellType, "after": "attributes"})
        else:
            cfg.Add({"name": "property_cell_type", "bits": 2, "type": PropertyCellType, "after": "attributes"})
        cfg.Add({"name": "dictionary_storage", "bits": 23, "type": int})
        return cfg.Generate()


class FieldIndex(BitField):
    """ FieldIndex for FastTo
    """

    _typeName = 'v8::internal::FieldIndex'
    
    kOffsetBitsSize = 14
    kTagged = 0
    kDouble = 1
    kWord32 = 2

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "offset", "bits": cls.kOffsetBitsSize},
            {"name": "is_in_object", "bits":1},
            {"name": "encoding", "bits":2},
            {"name": "in_object_property", "bits": Internal.kDescriptorIndexBitCount},
            {"name": "first_inobject_property", "bits": Internal.kFirstInobjectPropertyOffsetBitCount},
        ]}


class PropertyArray(HeapObject):

    _typeName = 'v8::internal::PropertyArray'

    kLengthAndHashOffset = 8
    kLengthFieldSize = 10
    kHeaderSize = 16

    class PropertyArrayLengthHashFields(BitField):
        @classmethod
        def __autoLayout(cls):
            return {"layout":  [
                {"name": "length", "bits": 10, "type": int},
                {"name": "hash", "bits": 21, "type": int},
            ]}

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "length_and_hash", "type": SmiTagged(PropertyArray.PropertyArrayLengthHashFields)},
        ]}

    @CachedProperty
    def length(self):
        return self.length_and_hash.length

    def _offset(self, index):
        """ return value at index """
        assert index < self.length, "%d < %d, <0x%x>" % (index, self.length, self)
        offset = self.kHeaderSize + (index * Internal.kTaggedSize)
        return offset

    def Get(self, index):
        return self.LoadPtr(self._offset(index))

    def GetDouble(self, index):
        return self.LoadDouble(self._offset(index))

    def WalkProperties(self):
        for i in range(self.length):
            tag = self.Get(i)
            yield Object(tag)

    @property
    def properties(self):
        out = []
        for o in self.WalkProperties():
            out.append(o)
        return out

    def SizeFor(self, length):
        return self.kHeaderSize + (length * Internal.kTaggedSize)

    def Size(self):
        return self.SizeFor(self.length)


class PropertyCell(HeapObject):

    _typeName = 'v8::internal::PropertyCell'

    @classmethod
    def __autoLayout(cls):
        return {"layout":[
            {"name": "name", "type": Name},
            {"name": "property_details", "type": SmiTagged(PropertyDetails),
                "alias": ["property_details_raw"]},
            {"name": "value", "type": Object},
            {"name": "dependent_code", "type": DependentCode},
        ]}

class DependentCode(WeakFixedArray):
    _typeName = 'v8::internal::DependentCode'


class TransitionArray(WeakFixedArray):
    _typeName = 'v8::internal::TransitionArray'


class PrototypeInfo(HeapObject):
    _typeName = 'v8::internal::PrototypeInfo'


class AccessorPair(HeapObject):
    _typeName = 'v8::internal::AccessorPair'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "getter", "type": Object}, 
            {"name": "setter", "type": Object}, 
        ]}


class AccessInfoFlags(BitField):
    
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "all_can_read", "bits": 1}, 
            {"name": "all_can_write", "bits": 1}, 
            {"name": "is_special_data_property", "bits": 1}, 
            {"name": "is_sloppy", "bits": 1}, 
            {"name": "replace_on_access", "bits": 1}, 
            {"name": "getter_side_effect_type", "bits": 2}, 
            {"name": "setter_side_effect_type", "bits": 2}, 
            {"name": "initial_attributes", "bits": 3}, 
        ]}


class AccessorInfo(HeapObject):
    _typeName = 'v8::internal::AccessorInfo'

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "name", "type": Name}, 
            {"name": "flags", "type": SmiTagged(AccessInfoFlags)}, 
            {"name": "expected_receiver_type", "type": Object}, 
            {"name": "setter", "type": Object}, 
            {"name": "getter", "type": Object}, 
            {"name": "js_getter", "type": Object}, 
            {"name": "data", "type": Object}, 
        ]}


""" New Objects
"""

# for v9 v8 engine
if Version.major >= 9:
    from .object_v9 import SloppyArgumentsElements
    from .object_v9 import StrongDescriptorArray
    from .object_v9 import SwissNameDictionary
    from .object_v9 import ScopeInfo
    from .object_v9 import StringTable
else:
    from .object_v8 import ScopeInfo
    from .object_v8 import StringTable

class ObjectMap:
    """singleton"""

    @classmethod
    def InstanceTypeTable(cls, table):
        def InstallType(index, rtype):
            if index is None:
                return
            table[index] = rtype

        types = [
                # String types
                # STRING_TYPE_LIST
                {'name': 'INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'ONE_BYTE_INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'EXTERNAL_INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'EXTERNAL_ONE_BYTE_INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'UNCACHED_EXTERNAL_INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'UNCACHED_EXTERNAL_ONE_BYTE_INTERNALIZED_STRING_TYPE', 'type': String},
                {'name': 'STRING_TYPE', 'type': String},
                {'name': 'ONE_BYTE_STRING_TYPE', 'type': String},
                {'name': 'CONS_STRING_TYPE', 'type': String},
                {'name': 'CONS_ONE_BYTE_STRING_TYPE', 'type': String},
                {'name': 'SLICED_STRING_TYPE', 'type': String},
                {'name': 'SLICED_ONE_BYTE_STRING_TYPE', 'type': String},
                {'name': 'EXTERNAL_STRING_TYPE', 'type': String},
                {'name': 'EXTERNAL_ONE_BYTE_STRING_TYPE', 'type': String},
                {'name': 'UNCACHED_EXTERNAL_STRING_TYPE', 'type': String},
                {'name': 'UNCACHED_EXTERNAL_ONE_BYTE_STRING_TYPE', 'type': String},
                {'name': 'THIN_STRING_TYPE', 'type': String},
                {'name': 'THIN_ONE_BYTE_STRING_TYPE', 'type': String},

                # base types
                {'name': 'SYMBOL_TYPE', 'type': Symbol},
                {'name': 'ODDBALL_TYPE', 'type': Oddball},
                #{'name': 'HEAP_NUMBER_TYPE', 'type': HeapNumber},
                {'name': 'BIGINT_TYPE', 'type': BigInt},
                {'name': 'MAP_TYPE', 'type': Map},
                {'name': 'CODE_TYPE', 'type': Code},
                {'name': 'SCRIPT_TYPE', 'type': Script},
                {'name': 'FREE_SPACE_TYPE', 'type': FreeSpace},

                # FixedArray
                {'name': 'FIXED_ARRAY_TYPE', 'type': FixedArray},
                {'name': 'BYTE_ARRAY_TYPE', 'type': ByteArray},
                {'name': 'BYTECODE_ARRAY_TYPE', 'type': BytecodeArray},
                {'name': 'FIXED_DOUBLE_ARRAY_TYPE', 'type': FixedDoubleArray},
                {'name': 'WEAK_FIXED_ARRAY_TYPE', 'type': WeakFixedArray},
                {'name': 'WEAK_ARRAY_LIST_TYPE', 'type': WeakArrayList},

                # HashTables

                # Contexts
                {'name': 'NATIVE_CONTEXT_TYPE', 'type': NativeContext},
                {'name': 'UNCOMPILED_DATA_WITHOUT_PREPARSE_DATA_TYPE', 'type': UncompiledDataWithoutPreparseData},
                {'name': 'UNCOMPILED_DATA_WITH_PREPARSE_DATA_TYPE', 'type': UncompiledDataWithPreparseData},

                # Misc

                # STRUCT_LIST_GENERATOR
                {'name': 'DESCRIPTOR_ARRAY_TYPE', 'type': DescriptorArray},
                {'name': 'FEEDBACK_METADATA_TYPE', 'type': FeedbackMetadata},
                {'name': 'PROPERTY_ARRAY_TYPE', 'type': PropertyArray},
                {'name': 'FEEDBACK_VECTOR_TYPE', 'type': FeedbackVector},
                {'name': 'PREPARSE_DATA_TYPE', 'type': PreparseData},
                {'name': 'EMBEDDER_DATA_ARRAY_TYPE', 'type': EmbedderDataArray},
                {'name': 'SCOPE_INFO_TYPE', 'type': ScopeInfo},
                {'name': 'PROMISE_REJECT_REACTION_JOB_TASK_TYPE', 'type': PromiseRejectReactionJobTask},
                {'name': 'PROMISE_FULFILL_REACTION_JOB_TASK_TYPE', 'type': PromiseFulfillReactionJobTask},
                {'name': 'ACCESSOR_INFO_TYPE', 'type': AccessorInfo},
                {'name': 'ACCESSOR_PAIR_TYPE', 'type': AccessorPair},

                # Inner  
                {'name': 'SHARED_FUNCTION_INFO_TYPE', 'type': SharedFunctionInfo},
                {'name': 'PROPERTY_CELL_TYPE', 'type': PropertyCell},

                # JSObject
                {'name': 'JS_FUNCTION_TYPE', 'type': JSFunction},
                {'name': 'JS_PROXY_TYPE', 'type': JSProxy},
        ]

        if Version.major >= 9:
            types.extend([
                {'name': 'SLOPPY_ARGUMENTS_ELEMENTS_TYPE', 'type': SloppyArgumentsElements},
                {'name': 'STRONG_DESCRIPTOR_ARRAY_TYPE', 'type': StrongDescriptorArray},
                {'name': 'SWISS_NAME_DICTIONARY_TYPE', 'type': SwissNameDictionary},
            ])

        # install defaults
        for i in range(InstanceType.FIRST_FIXED_ARRAY_TYPE, InstanceType.LAST_FIXED_ARRAY_TYPE+1):
            InstallType(i, FixedArray)

        for i in range(InstanceType.FIRST_WEAK_FIXED_ARRAY_TYPE, InstanceType.LAST_WEAK_FIXED_ARRAY_TYPE+1):
            InstallType(i, WeakFixedArray)

        for i in range(InstanceType.FIRST_CONTEXT_TYPE, InstanceType.LAST_CONTEXT_TYPE+1):
            InstallType(i, Context)

        for i in range(InstanceType.FIRST_JS_OBJECT_TYPE, InstanceType.LAST_JS_OBJECT_TYPE+1):
            InstallType(i, JSObject)

        for n in types:
            InstallType(InstanceType.Find(n['name']), n['type'])

        if Version.major >= 9:
            for i in range(InstanceType.FIRST_JS_FUNCTION_TYPE, InstanceType.LAST_JS_FUNCTION_TYPE+1):
                InstallType(i, JSFunction)
        
        
    @classmethod
    def LoadDwf(cls):
        # get last InstanceType
        last_type = InstanceType.LAST_TYPE
        if last_type is None:
            log.critical("Can't get InstaceType.LAST_TYPE.")
        elif last_type > 2000:
            log.warn("InstanceType range (%d) is too large." % last_type)

        # create the InstanceType to Class array.
        cls._cached_table = [None for x in range(last_type+1)]
        cls.InstanceTypeTable(cls._cached_table)

    @classmethod
    def BindObject(cls, obj):
        """binding dbg.Value to corresponding Object"""
        tag = Internal.TaggedT(obj)
        instance_type = obj.instance_type
        instance_type_num = int(instance_type)
        assert instance_type_num < len(cls._cached_table), print("instance_type(%d), len(%d) %x" % (instance_type_num, len(cls._cached_table), tag))
        obj_class = cls._cached_table[instance_type_num]
        if obj_class is None:
            log.error('not binding for %s (%d)' % (str(instance_type), int(instance_type)))
            return None
        return obj_class(tag)

    def SBrief(cls, obj):
        """return one line brief of the Object"""
        pass

    def ShortString(cls, obj):
        """return short string of the Object"""
        pass


""" tail imports
"""
from .enum import (
    AllocationSpace,
    AllocationType,
    BuiltinsName,
    ElementsKind,
    InstanceType,
    LanguageMode,
    PromiseState,
    PropertyAttributes,
    PropertyFilter,
    PropertyKind,
    PropertyLocation,
    PropertyConstness,
    PropertyCellType,
    PropertyCellConstantType,
    Root,
    RootIndex,
    ScopeType,
    VariableAllocationInfo,
    FunctionKind,
    FunctionSyntaxKind,
    CodeKind,
    RepresentationKind,
)

from .structure import (
    Isolate,
)

from .iterator import (
    LookupIterator,
    PrototypeIterator,
)

from andb.utility import (
    TextLimit,
    TextShort,
)
