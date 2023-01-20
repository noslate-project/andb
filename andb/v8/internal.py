# -*- coding: UTF-8 -*-
from __future__ import print_function, division

""" v8 engine support
"""
import re
import types
import struct
import collections

import andb.dbg as dbg
import andb.py23 as py23
from andb.config import Config as cfg

from andb.utility import (
    Logging as log, 
    CachedProperty
)


log.verbose("PointerSize: %d " % dbg.PointerSize)
assert dbg.PointerSize == 8

class Version:
    major = dbg.Target.LoadRaw("'v8::internal::Version'::major_")
    minor = dbg.Target.LoadRaw("'v8::internal::Version'::minor_")
    patch = dbg.Target.LoadRaw("'v8::internal::Version'::patch_")
    build = dbg.Target.LoadRaw("'v8::internal::Version'::build_")
    log.info("V8Version: %d.%d.%d.%d" % (major, minor, build, patch))


def ObjectSlot(address):
    return dbg.Slot(address)


class ObjectSlots(dbg.Slots):
    """ similiar to range(start, end), iterate all object slots,
        and 'end' is not included.
    """
    pass


class BuildConfig:
    """ the consts in the class are all defined outside of 'v8'.
    """

    """ Page size """
    kPageSizeBits = 18
    assert kPageSizeBits == 18

    @classmethod
    def LoadDwf(cls):
        consts = []
        for v in cls.__dict__:
            if re.match(r'^k[A-Z]', v):
                consts.append(v)

        for v in consts:
            a = getattr(cls, v)

            b = dbg.Dwf.ReadConst(v)
            if b is None:
                log.warn("%s' (%d) not found." % (v, a))
                continue

            if a != b:
                setattr(cls, v, b)
                log.info("'%s' (%d) = %d" % (v, a, getattr(cls, v)))


class Internal:
    """ all consts and global functions are collected in 'Internal'
    """
    _typeName = "v8::internal"

    """ consts from globals.h """
    # consts for all c++ data size
    kUInt8Size = 1
    kByteSize = 1
    kCharSize = 1
    kShortSize = 2
    kUInt16Size = 2
    kIntSize = 4
    kInt32Size = 4
    kSizetSize = 8
    kFloatSize = 4
    kDoubleSize = 8
    kIntptrSize = 8
    kUIntptrSize = 8
    kSystemPointerSize = dbg.PointerSize
    kSystemPointerHexDigits = 12

    kExternalPointerSize = 8
    kEmbedderDataSlotSize = 8

    """ consts from v8-internal.h """
    # Tag information for HeapObject.
    kHeapObjectTag = 1
    kWeakHeapObjectTag = 3
    kHeapObjectTagSize = 2
    kHeapObjectTagMask = (1 << kHeapObjectTagSize) - 1
    assert kHeapObjectTag == 1

    # Tag information for Smi.
    kSmiTag = 0
    kSmiTagSize = 1
    kSmiTagMask = (1 << kSmiTagSize) - 1
    assert kSmiTag == 0

    # Smi constants for systems where tagged pointer is a 64b value.
    kSmiShiftSize = 31
    kSmiValueSize = 32
    assert kSmiShiftSize == 31
    assert kSmiValueSize == 32

    """ consts from global.h """
    # Mask for the sign bit in a Smi.
    kSmiSignMask = (1 << (kSmiValueSize + kSmiShiftSize + kSmiTagSize - 1))

    # Desired aligment for tagged pointers
    kObjectAlignment = 8
    kObjectAlignmentMask = 7

    # Desired alignment for system pointers
    kPointerAlignment = 8
    kPointerAlignmentMask = 7

    # Desired alignment for double values
    kDoubleAlignment = 8
    kDoubleAlignmentMask = 7

    # Desired alignment for code (32 bytes), improve cache line utilization.
    kCodeAlignment = 32
    kCodeAlignmentMask = (kCodeAlignment - 1)

    # Desired for Page
    kPageAlignmentMask = (1 << BuildConfig.kPageSizeBits) - 1

    # const value for cleared weak reference value.(only lower 32b)
    kClearedWeakHeapObjectLower32 = 3

    # Zap-value: the value used for zapping dead objects.
    kZapValue = 0xdeadbeedbeadbeef
    kHandleZapValue = 0x1baddead0baddeaf
    kGlobalHandleZapValue = 0x1baffed00baffedf
    kFromSpaceZapValue = 0x1beefdad0beefdaf
    kDebugZapValue = 0xbadbaddbbadbaddb
    kSlotsZapValue = 0xbeefdeadbeefdeef
    kFreeListZapValue = 0xfeed1eaffeed1eaf
    kCodeZapValue = 0xbadc0de
    kPhantomReferenceZap = 0xca11bac

    # Tagged pointer size
    kTaggedSize = kSystemPointerSize
    assert kTaggedSize == 8

    """ string definition from instance_type.h """
    # v8 uses 16 bits for instance_type field, and string uses 0-6 bits.
    kIsNotStringMask = ~((1 << 6) - 1) & 0xFFFFFFFF
    kStringTag = 0

    # 'v8::internal::StringRepresentationTag'
    kStringRepresentationMask = (1 << 3) - 1
    kSeqStringTag = 0
    kConsStringTag = 1
    kExternalStringTag = 2
    kSlicedStringTag = 3
    kThinStringTag = 5

    # bit 3 : one or two byte characters
    kStringEncodingMask = (1 << 3)
    kTwoByteStringTag = 0
    kOneByteStringTag = (1 << 3)

    # bit 4 : whether the data pointer of an external string is cached.
    kUncachedExternalStringMask = (1 << 4)
    kUncachedExternalStringTag = (1 << 4)

    # bit 5 : internalized (true if not)
    kIsNotInternalizedMask = 1 << 5
    kNotInternalizedTag = 1 << 5
    kInternalizedTag = 0

    # kShortcutType is for cons string.
    kShortcutTypeMask = (kIsNotStringMask | kIsNotInternalizedMask | kStringRepresentationMask) & 0xFFFFFFFF
    kShortcutTypeTag = kConsStringTag | kNotInternalizedTag

    """ global-handles.cc """
    kBlockSize = 256

    """ objects.h """
    # Instance size sentinel for objects of variable size.
    kVariableSizeSentinel = 0

    """ flag-definitions.h """
    FLAG_enable_embedded_constant_pool = 0

    """ property-details.h """
    kDescriptorIndexBitCount = 10
    kFirstInobjectPropertyOffsetBitCount = 7

    """ Has methods from globals.h
    """
    @classmethod
    def TaggedT(cls, val):
        """covert to Tagged_t"""
        return int(val) & 0xFFFFFFFFFFFFFFFF

    @classmethod
    def cHasSmiTag(cls, val):
        return (cls.TaggedT(val) & cls.kSmiTagMask) == cls.kSmiTag

    @classmethod
    def cHasStrongHeapObjectTag(cls, val):
        return (cls.TaggedT(val) & cls.kHeapObjectTagMask) == cls.kHeapObjectTag

    @classmethod
    def cHasWeakHeapObjectTag(cls, val):
        return (cls.TaggedT(val) & cls.kHeapObjectTagMask) == cls.kWeakHeapObjectTag

    @classmethod
    def cHasClearedWeakHeapObjectTag(cls, val):
        """ cleared weak reference value is special,
            difference based on architectures and pointer compression setting,
            on 64-bits machine with pointer compression off,
            the low 32 value is always equal to 'kClearWeakHeapObjectLower32'
        """
        return ((int(val) & 0xFFFFFFFF) == cls.kClearedWeakHeapObjectLower32)

    @classmethod
    def cObjectPointerAlign(cls, val):
        return (cls.TaggedT(val) + cls.kObjectAlignmentMask) & ~cls.kObjectAlignmentMask

    @classmethod
    def cPointerSizeAlign(cls, val):
        return (cls.TaggedT(val) + cls.kPointerAlignmentMask) & ~cls.kPointerAlignmentMask

    @classmethod
    def cCodeSizeAlign(cls, val):
        return (cls.TaggedT(val) + cls.kCodeAlignmentMask) & ~cls.kCodeAlignmentMask

    @classmethod
    def cDoublePointerAlign(cls, val):
        return (cls.TaggedT(val) + cls.kDoubleAlignmentMask) & ~cls.kDoubleAlignmentMask

    @classmethod
    def LoadDwf(cls):
        consts = []
        for v in cls.__dict__:
            if re.match(r'^k[A-Z]', v):
                consts.append(v)
            elif re.match(r'^FLAG_', v):
                consts.append(v)

        result = dbg.Dwf.ReadAllConstsNoInheritesByList(cls._typeName, consts)

        for v, b in result.items():
            a = getattr(cls, v)
            if b is None:
                log.warn("%s::%s' (%d) not found." % (cls._typeName, v, a))
                continue

            if a != b:
                setattr(cls, v, b)
                log.info("'%s::%s' (%d) = %d" % (cls._typeName, v, a, b))

    @classmethod
    def ObjectPointerAlign(cls, value):
        """ aligns value to ObjectPointer Alignment size.
        """
        return ((int(value) + cls.kObjectAlignmentMask) & ~(cls.kObjectAlignmentMask))

    @staticmethod
    def RoundUp(value, by):
        """ rounds value up to by boundary.
        """
        a = value + by - 1
        a = (a // by) * by
        return a


""" Base Classes
"""


class AutoLayout:
    """ AutoLayout is Torque-like Code generator.

        AutoLayout generates the layout configures to Property functions.

        Kind 1: BitField,
        { "name":"length", "bits":6 },
        for self.length to get the BitField property.
        "bits" tells the generator how many bits the property has.

        Kind 2: Const,
        { "name":"header_size" }
        Const is the basic property just geting the const value from Dwarf.
        for "header_size", the generator will search for
          "kHeaderSizeOffset" togather with "kHeaderSizeOffsetEnd",
          then "kHeaderSizeIndex" and "kHeaderSize",
          it returns the first found.
        if the const can't find a const, it just returns None.

        Const Alias,
        { "name":"header_size", "alias":["kHeaderBits", "kSize"] },
        Many v8 versions may have different Const names, so it's useful to collect those 'alias'
        in constant property, it would find in Dwarf for name and alias.

        Kind 3: Object,
        { "name":"to_string", "type":Object },
        v8 heap objects use a flat object layout, Object is a entry holds a single Object reference.
        the layout will generate a property return the Object by 'self.to_string',

        Kind 4: Array,
        { "name":"objects[length_name]", "type":Object },
        another common layout entry is array, each array must have a length name,
        the length_name could be either integer or a function to return the length.
        the generator will generate a property like 'self.objects(index)' to get the items.

        Kind 5: Variable,
        { "name":"info?[has_info]", "type":Info },
        torque uses variable length layout, each Variable layout has a function to indicate
        whether has the property.
        'self.info()' return the 'Info' type property, or None for not exists.

        Kind 6: ALStruct,
        { "name":"start", "type": Smi },
        ALStruct is structure generated by Torque but without a wrapped Cpp class.
        
        ALData(self),
        AutoLayout returns decoded layouts in python Array.
        [
            {"Name", "Data", "Offset", "OffsetEnd"},
        ]

        ALDebug(self),
        show object using auto layout information.

        ALBrief(self),
        one line brief string.
    """

    class Builder:

        def __init__(self, alcfg=None):
            if alcfg is not None:
                self._al_cfg = alcfg
                return

            self._al_cfg = {
                "layout": []
            }

        def Inherit(self):
            """ the class needs inherit the al config from parent.
            """
            self._al_cfg['inherit'] = True

        def HasInherit(self):
            if 'inherit' in self._al_cfg and self._al_cfg['inherit']:
                return True
            return False

        def Add(self, n):
            """ add layout entry
            """
            self._al_cfg['layout'].append(n)

        def Adds(self, a):
            """ add layout entries
            """
            for n in a:
                self._al_cfg['layout'].append(n)

        def Generate(self):
            """ generate autolayout configure
            """
            return self._al_cfg

        def Merge(self, alcfg):
            for n in alcfg['layout']:
                self._al_cfg.append(n)

    class RODict(dict):
        """ Generate a Readonly dictionary
        """
        def __readonly__(self, *args, **kwargs):
            raise RuntimeError("Cannot modify ReadOnlyDict")

        __setitem__ = __readonly__
        __delitem__ = __readonly__
        pop = __readonly__
        popitem = __readonly__
        clear = __readonly__
        update = __readonly__
        setdefault = __readonly__
        del __readonly__

    @classmethod
    def __cALGetLayout(cls):
        """ private method, get __autolayout """

        al_fun = getattr(cls, '_%s__autoLayout' % cls.__name__, None)
        if not callable(al_fun):
            return None

        al = al_fun()
        assert 'layout' in al

        return al

    @classmethod
    def __cALPutCfg(cls, cfg):
        setattr(cls, '_alcfg_%s' % cls.__name__, cfg)

    @classmethod
    def __cALGetCfg(cls, target_name, default=None):
        return getattr(cls, '_alcfg_%s' % target_name, default)

    @classmethod
    def ALGetCfg(cls):
        return cls.__cALGetCfg(cls.__name__)

    @classmethod
    def _cALResolveConst(cls, n, consts):
        """ Resolve property layout const and size
        """
        def _ConstName(name):
            """Get const name from input"""
            # const name
            arr = re.findall('^k[A-Z][a-z]*', name)
            if len(arr) > 0:
                # support kHeaderSize like const name
                arr = re.findall('[A-Z][a-z]*', name)
                return arr

            # property name to const name
            arr = name.split('_')
            arr = [x.capitalize() for x in arr]
            return arr

        def _ResolveConst(name):
            """ Resolve the Const info, return by (off, size)"""
            _s = "".join(_ConstName(name))
            k1 = 'k' + _s + 'Offset'
            k2 = 'k' + _s + 'OffsetEnd'
            k3 = 'k' + _s + 'Index'
            k4 = 'k' + _s
            k5 = 'k' + _s + 'End'

            resolved = {k1: None, k2: None, k3: None, k4: None, k5: None}

            for k in resolved:
                if k in consts:
                    resolved[k] = consts[k]

            # get size (OffsetEnd - Offset)
            size = None
            if resolved[k1] is not None and resolved[k2] is not None:
                size = resolved[k2] - resolved[k1] + 1
                #if size == 0:
                #    log.warn('dwf size of (%s) == 0' % (name))
                    #size = None
            elif resolved[k4] is not None and resolved[k5] is not None:
                size = resolved[k5] - resolved[k4] + 1
                #if size == 0:
                #    log.warn('dwf size of (%s) == 0' % (name))

            # get offset
            off = resolved[k1]
            if off is not None:
                return (off, size)
            off = resolved[k3]
            if off is not None:
                n['is_index'] = True
                return (off, size)
            off = resolved[k4]
            if off is not None:
                return (off, size)
            return (off, size)

        """ Resolve Layout const and size,
            search name then alias list.
        """
        alias = n['alias'] if 'alias' in n else []

        # using property name
        off, size = _ResolveConst(n['property_name'])

        # try alias
        if off is None:
            for i in alias:
                off, size = _ResolveConst(i)
                if off is not None:
                    break

        # we could not find
        if off is None:
            return True

        # save offset
        if 'offset' in n:
            if n['offset'] != off:
                log.warn('%s.%s (%d) = %d' % (cls.__name__, n['property_name'], n['offset'], off))
                n['offset'] = off
        else:
            n['offset'] = off

        # no size avariable
        if size is None:
            # only Const with End has size information, so Good if not has. 
            return False 

        # save size
        if 'size' in n:
            if n['size'] != size:
                log.warn('%s.%s (%d) = %d' % (cls.__name__, n['property_name'], n['size'], size))
                n['size'] = size
        else:
            n['size'] = size
        return False

    @classmethod
    def _cALInstallObject(cls, n):
        """ Install Property for getting Object
        """

        def AttrOffsetObject(xxx):
            """ get object by fixed offset
            """
            (offset, size, return_type) = xxx

            def GetOffsetObjectU8(self):
                return return_type(self.LoadU8(offset))

            def GetOffsetObjectU16(self):
                return return_type(self.LoadU16(offset))

            def GetOffsetObjectU32(self):
                return return_type(self.LoadU32(offset))

            def GetOffsetObjectU64(self):
                return return_type(self.LoadU64(offset))

            def GetOffsetALStruct(self):
                return return_type(self.address + offset)

            if cls._cALIsReturnTypeALStruct(return_type):
                r = GetOffsetALStruct
            elif size == 8:
                r = GetOffsetObjectU64
            elif size == 4:
                r = GetOffsetObjectU32
            elif size == 2:
                r = GetOffsetObjectU16
            elif size == 1:
                r = GetOffsetObjectU8
            elif size == 0:
                return None
            else:
                raise Exception(n, 'Size(%d) is not supported.' % (size))

            r.__name__ = n['property_name']
            return r

        def AttrPriorObject(xxx):
            """ get object by prior property 
            """
            (prior_offset_end, size, return_type,) = xxx

            def GetPriorObjectU8(self):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU8(offset))

            def GetPriorObjectU16(self):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU16(offset))

            def GetPriorObjectU32(self):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU32(offset))

            def GetPriorObjectU64(self):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU64(offset))

            def GetPriorALStruct(self):
                offset = getattr(self, prior_offset_end)
                return return_type(self.address + offset)

            if cls._cALIsReturnTypeALStruct(return_type):
                r = GetPriorALStruct
            if size == 8:
                r = GetPriorObjectU64
            elif size == 4:
                r = GetPriorObjectU32
            elif size == 2:
                r = GetPriorObjectU16
            elif size == 1:
                r = GetPriorObjectU8
            elif size == 0:
                return None
            else:
                raise Exception('Size(%d) is not supported.' % (size))

            r.__name__ = n['property_name']
            return r

        def AttrPriorObjectOffset(xxx):
            """ get offset by prior property
            """
            (prior_offset_end) = xxx

            def GetPriorObjectOffset(self):
                return getattr(self, prior_offset_end)

            r = GetPriorObjectOffset
            r.__name__ = "%s__offset" % n['property_name']
            return r

        def AttrPriorObjectOffsetEnd(xxx):
            """ get offset end by prior property
            """
            (prior_offset_end, size) = xxx

            def GetPriorObjectOffsetEnd(self):
                return getattr(self, prior_offset_end) + size

            r = GetPriorObjectOffsetEnd
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        def AttrOffsetFunctionObject(xxx):
            """ get object by offset function
            """
            (offset_func, index, size, return_type,) = xxx

            def GetOffsetFunctionObjectU64(self):
                offset = offset_func(self, index)
                return return_type(self.LoadU64(offset))

            if size == 8:
                r = GetOffsetFunctionObjectU64
            else:
                raise Exception('Size(%d) is not supported.' % size)

            r.__name__ = n['property_name']
            return r

        def AttrOffsetFunctionObjectOffset(xxx):
            (offset_func, index,) = xxx

            def GetOffsetFunctionObjectOffset(self):
                return offset_func(self, index)

            r = GetOffsetFunctionObjectOffset
            r.__name__ = "%s__offset" % n['property_name']
            return r

        def AttrOffsetFunctionObjectOffsetEnd(xxx):
            (offset_func, index, size, ) = xxx

            def GetOffsetFunctionObjectOffsetEnd(self):
                return offset_func(self, index) + size

            r = GetOffsetFunctionObjectOffsetEnd
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        assert 'size' in n
        assert 'type' in n

        if 'offset_func' in n:
            # object
            if n['size'] == 0:
                setattr(cls, n['property_name'], None)
            else:
                setattr(cls, n['property_name'],
                        CachedProperty(AttrOffsetFunctionObject((n['offset_func'], n['offset'], n['size'], n['type']))))

            # offset
            setattr(cls, "%s__offset" % n['property_name'],
                    CachedProperty(AttrOffsetFunctionObjectOffset((n['offset_func'], n['offset']))))

            # offset_end
            setattr(cls, "%s__offset_end" % n['property_name'],
                    CachedProperty(AttrOffsetFunctionObjectOffsetEnd((n['offset_func'], n['offset'], n['size']))))
        
        elif 'offset' in n:
            # object
            if n['size'] == 0:
                setattr(cls, n['property_name'], None)
            else:
                setattr(cls, n['property_name'],
                        CachedProperty(AttrOffsetObject((n['offset'], n['size'], n['type']))))

            # offset
            setattr(cls, "%s__offset" % n['property_name'], n['offset'])

            # offset_end
            setattr(cls, "%s__offset_end" % n['property_name'],
                    n['offset'] + n['size'])
        else:
            prior_offset_end = "%s__offset_end" % (n['prior'])

            # object
            if n['size'] == 0:
                setattr(cls, n['property_name'], None)
            else:
                setattr(cls, n['property_name'],
                        CachedProperty(AttrPriorObject((prior_offset_end, n['size'], n['type']))))

            # offset
            setattr(cls, "%s__offset" % n['property_name'],
                    CachedProperty(AttrPriorObjectOffset((prior_offset_end))))

            # offset_end
            setattr(cls, "%s__offset_end" % n['property_name'],
                    CachedProperty(AttrPriorObjectOffsetEnd((prior_offset_end, n['size']))))

    @classmethod
    def _cALInstallArray(cls, n):
        """ Install Property for getting array
        """

        def AttrOffsetArrayItem(xxx):
            """ Get Array item by offset
            """
            (offset, size, return_type,) = xxx

            def GetOffsetItemAtU64(self, index):
                return return_type(self.LoadU64(offset + index*size))

            def GetOffsetItemAtU32(self, index):
                return return_type(self.LoadU32(offset + index*size))

            def GetOffsetItemAtU16(self, index):
                return return_type(self.LoadU16(offset + index*size))

            def GetOffsetItemAtU8(self, index):
                return return_type(self.LoadU8(offset + index*size))

            def GetOffsetItemAtAddress(self, index):
                return return_type(self.address + offset + index*size)

            if cls._cALIsReturnTypeALStruct(return_type):
                r = GetOffsetItemAtAddress
            elif size == 8:
                r = GetOffsetItemAtU64
            elif size == 4:
                r = GetOffsetItemAtU32
            elif size == 2:
                r = GetOffsetItemAtU16
            elif size == 1:
                r = GetOffsetItemAtU8
            elif size == 0:
                return None
            else:
                raise Exception('Size(%d) is not supported.' % (size))

            r.__name__ = n['property_name']
            return r

        def AttrPriorArrayItem(xxx):
            """ Get Array item by prior property
            """
            (prior_offset_end, size, return_type,) = xxx

            def GetPriorItemAtU64(self, index):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU64(offset + index * size))

            def GetPriorItemAtU32(self, index):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU32(offset + index * size))

            def GetPriorItemAtU16(self, index):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU16(offset + index * size))

            def GetPriorItemAtU8(self, index):
                offset = getattr(self, prior_offset_end)
                return return_type(self.LoadU8(offset + index * size))

            def GetPriorItemAtAddress(self, index):
                offset = getattr(self, prior_offset_end)
                return return_type(self.address + offset + index * size)

            if cls._cALIsReturnTypeALStruct(return_type):
                r = GetPriorItemAtAddress
            elif size == 8:
                r = GetPriorItemAtU64
            elif size == 4:
                r = GetPriorItemAtU32
            elif size == 2:
                r = GetPriorItemAtU16
            elif size == 1:
                r = GetPriorItemAtU8
            elif size == 0:
                return None
            else:
                raise Exception('Size(%d) is not supported.' % (size))

            r.__name__ = n['property_name']
            return r

        def AttrOffsetArrayOffsetEndFunc(xxx):
            """ Get Array offset by fixed offset
            """
            (offset, size, length_name, ) = xxx

            def GetOffsetArrayOffsetEndFunc(self):
                length = int(getattr(self, length_name) or 0)
                return length * size + offset

            r = GetOffsetArrayOffsetEndFunc
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        def AttrPriorArrayOffset(xxx):
            """ Get Array offset by prior property
            """
            (prior_offset_end, size, ) = xxx

            def GetPriorArrayItemOffset(self):
                return getattr(self, prior_offset_end)
        
            r = GetPriorArrayItemOffset
            r.__name__ = "%s__offset" % n['property_name']
            return r

        def AttrPriorArrayOffsetEndFix(xxx):
            """ Get Array offset end by prior property and fixed length
            """
            (prior_offset_end, size, length,) = xxx

            def GetPriorArrayOffsetEndFix(self):
                offset = getattr(self, prior_offset_end)
                return length * size + offset

            r = GetPriorArrayOffsetEndFix
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        def AttrPriorArrayOffsetEndFunc(xxx):
            """ Get Array offset end by prior property and length function
            """
            (prior_offset_end, size, length_name,) = xxx

            def GetPriorArrayOffsetEndFunc(self):
                length = int(getattr(self, length_name) or 0)
                offset = getattr(self, prior_offset_end)
                return length * size + offset

            r = GetPriorArrayOffsetEndFunc
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        if 'offset' in n:
            # array item getter function
            setattr(cls, n['property_name'],
                    AttrOffsetArrayItem((n['offset'], n['size'], n['type'])))

            # offset
            setattr(cls, "%s__offset" % n['property_name'], n['offset'])

            # offset_end
            if n['length_name'].isdigit():
                # fixed length
                setattr(cls, "%s__offset_end" % n['property_name'],
                        int(n['length_name']) * n['size'] + n['offset'])
            else:
                # dynamic length function
                setattr(cls, "%s__offset_end" % n['property_name'], CachedProperty(
                        AttrOffsetArrayOffsetEndFunc((n['offset'], n['size'], n['length_name']))))
        else:
            prior_offset_end = "%s__offset_end" % (n['prior'])
            
            # object
            setattr(cls, n['property_name'],
                    AttrPriorArrayItem((prior_offset_end, n['size'], n['type'])))
            
            # offset
            setattr(cls, "%s__offset" % n['property_name'], CachedProperty(
                    AttrPriorArrayOffset((prior_offset_end, n['size']))))

            # offset_end
            if n['length_name'].isdigit():
                # fixed length
                setattr(cls, "%s__offset_end" % n['property_name'], CachedProperty(
                    AttrPriorArrayOffsetEndFix((prior_offset_end, n['size'], int(n['length_name'])))))
            else:
                # dynamic length function
                setattr(cls, "%s__offset_end" % n['property_name'], CachedProperty(
                    AttrPriorArrayOffsetEndFunc((prior_offset_end, n['size'], n['length_name']))))

    @classmethod
    def _cALInstallVariable(cls, n):
        """ Install Property for getting Variable
        """
        def AttrVariableObject(xxx):
            """ get object from variable
            """
            (prior_offset_end, has_name, size, return_type,) = xxx

            def GetPriorVariableU64(self):
                offset = getattr(self, prior_offset_end)
                has = getattr(self, has_name)
                if has:
                    return return_type(self.LoadU64(offset))
                return None

            def GetPriorVariableAddress(self):
                offset = getattr(self, prior_offset_end)
                has = getattr(self, has_name)
                if has:
                    return return_type(self.address + offset)
                return None

            if cls._cALIsReturnTypeALStruct(return_type):
                r = GetPriorVariableAddress
            elif size == 8:
                r = GetPriorVariableU64
            else:
                raise Exception(cls, "size not support(%d)" % size)

            r.__name__ = n['property_name']
            return r

        def AttrVariableOffset(xxx):
            """ get offset from variable
            """
            (prior_offset_end) = xxx
            
            def GetPriorVariableOffset(self):
                offset = getattr(self, prior_offset_end)
                return offset
            
            r = GetPriorVariableOffset
            r.__name__ = "%s__offset" % n['property_name']
            return r

        def AttrVariableOffsetEnd(xxx):
            """ get offset end from variable
            """
            (prior_offset_end, has_name, size,) = xxx
            
            def GetPriorVariableOffsetEnd(self):
                offset = getattr(self, prior_offset_end)
                has = getattr(self, has_name)
                if has:
                    return offset + size
                return offset

            r = GetPriorVariableOffsetEnd
            r.__name__ = "%s__offset_end" % n['property_name']
            return r

        # object
        prior_offset_end = "%s__offset_end" % n['prior']
        setattr(cls, n['property_name'], CachedProperty(
                AttrVariableObject((prior_offset_end, n['has_name'], n['size'], n['type']))))

        # offset
        setattr(cls, "%s__offset" % n['property_name'], CachedProperty(
                AttrVariableOffset((prior_offset_end))))

        # offset_end
        setattr(cls, "%s__offset_end" % n['property_name'], CachedProperty(
                AttrVariableOffsetEnd((prior_offset_end, n['has_name'], n['size']))))

    @classmethod
    def _cALInstallBitField(cls, n):
        """ Install Property for getting BitField
        """

        def AttrOffsetBitField(xxx):
            """ get bitfiled by offset
            """
            (pos, bits, return_type,) = xxx

            def GetOffsetBitField(self):
                return return_type(self.BitSize(pos, bits))

            r = GetOffsetBitField
            r.__name__ = n['property_name']
            return r
       
        # value
        setattr(cls, n['property_name'], CachedProperty(
                AttrOffsetBitField((n['pos'], n['bits'], n['type']))))
        
        # offset
        setattr(cls, "%s__offset" % n['property_name'], n['pos'])

        # offset_end
        setattr(cls, "%s__offset_end" % n['property_name'], n['pos'] + n['bits'])
        
    @classmethod
    def _cALInstallConst(cls, n):
        """ Install Property for getting Const
        """
        assert 'type' not in n

        setattr(cls, n['property_name'], n['offset'])

        # if has size
        if 'size' in n:
            setattr(cls, "%s__size" % n['property_name'], n['size'])

    @classmethod
    def _cALInstallALStruct(cls, n):
        """ Install Property for getting Const
        """

        def AttrOffsetALStructObject(xxx):
            (offset, size, return_type,) = xxx

            def GetOffsetALStructObjectU64(self):
                return return_type(self.LoadU64(offset))

            if size == 8:
                r = GetOffsetALStructObjectU64
            else:
                raise Exception(cls, "not support the size(%d)" % (size))

            r.__name__ = n['property_name']
            return r

        # object
        setattr(cls, n['property_name'], CachedProperty(
                AttrOffsetALStructObject((n['offset'], n['size'], n['type']))))

    @classmethod
    def _cALIsReturnTypeALStruct(cls, return_type):
        """ Return True if return_type is ALStruct
        """
        if not isinstance(return_type, types.FunctionType) and \
                issubclass(return_type, ALStruct):
            return True
        return False

    @classmethod
    def _cALGetReturnTypeSize(cls, n):
        return_type = n['type']
        if not isinstance(return_type, types.FunctionType) and \
                issubclass(return_type, ALStruct):
            size = return_type.SizeOf()
        elif 'size' in n:
            size = int(n['size'])
        else:
            size = Internal.kTaggedSize
        return size

    @classmethod
    def _cALInstallProperty(cls, cfg, p, n):
        """ Install property
        """
        # save the prior property name
        if p is not None:
            n['prior'] = p['property_name']

        # bitfield
        if n['kind'] == 'bitfield':
            assert 'bits' in n

            # caculate the position
            pos = 0
            if 'after' in n:
                pos = getattr(cls, "%s__offset_end" % n['after'], 0)
            elif 'offset' in n:
                pos = n['offset']
            elif p:
                pos = p['pos'] + p['bits']
            n['pos'] = pos

            # default return_type if not specified.
            if 'type' not in n:
                n['type'] = int

            # install the attributes
            cls._cALInstallBitField(n)

        # alstruct
        elif n['kind'] == 'alstruct':
            assert 'type' in n
            
            offset = 0
            if p:
                offset = p['offset'] + p['size']
            n['offset'] = offset

            if 'size' not in n:
                n['size'] = Internal.kTaggedSize

            cls._cALInstallALStruct(n)

        # const
        elif n['kind'] == 'const':
            assert 'offset' in n, "const %s" % (n)

            cls._cALInstallConst(n)

        # variable
        elif n['kind'] == 'variable':
            assert 'has_name' in n
            assert 'type' in n

            n['size'] = cls._cALGetReturnTypeSize(n)

            cls._cALInstallVariable(n)

        # array
        elif n['kind'] == 'array':
            assert 'length_name' in n
            assert 'type' in n

            n['size'] = cls._cALGetReturnTypeSize(n)

            cls._cALInstallArray(n)

        # object
        elif n['kind'] == 'object':
            assert 'type' in n

            # we get size in decode phase
            if 'size' not in n:
                size = 0
                if 'offset' in n:
                    # hit in dwarf
                    size = cls._cALGetReturnTypeSize(n)
                n['size'] = size

            # install the attributes
            cls._cALInstallObject(n)

    @classmethod
    def _cALDecodeLayout(cls, cfg, n):
        # bit field
        if 'bits' in n:
            n['property_name'] = n['name']
            n['kind'] = 'bitfield'

            # defult return type
            if 'type' not in n:
                n['type'] = int

        # alstruct
        elif 'IsALStruct' in cfg and cfg['IsALStruct']:
            n['property_name'] = n['name']
            n['kind'] = 'alstruct'

        # variable
        elif n['name'].find('?[') > 0:
            m = re.findall("(.*)\?\[(.*)\]", n['name'])
            n['property_name'] = m[0][0]
            n['has_name'] = m[0][1]
            n['kind'] = 'variable'

        # array
        elif n['name'].find('[') > 0:
            m = re.findall("(.*)\[(.*)\]", n['name'])
            n['property_name'] = m[0][0]
            n['length_name'] = m[0][1]
            n['kind'] = 'array'

        # object
        elif 'type' in n:
            n['property_name'] = n['name']
            n['kind'] = 'object'

        # const
        else:
            n['property_name'] = n['name']
            n['kind'] = 'const'

        # offset function
        if 'offsetFunction' in cfg:
            n['offset_func'] = cfg['offsetFunction']

    @classmethod
    def _cALGenerate(cls, consts, cfg=None):
        """ The very entry of the AutoLayout.
            It parses all  in __autoLayout()
        """
        # get layout
        al = cls.__cALGetLayout()

        # check layout
        if al is None or 'layout' not in al:
            return

        # save or overwrite cfg in al
        if cfg is not None:
            for k, v in cfg.items():
                al[k] = v
         
        # install properties
        prior = None
        for n in al['layout']:
            cls._cALDecodeLayout(al, n)
            cls._cALResolveConst(n, consts)
            cls._cALInstallProperty(al, prior, n)
            prior = n

        # saves the decoded layouts
        if 'inherit' in al and al['inherit']:
            # 'inherit' option includes the parent al_cfg.
            array = []
            for n in cls._alcfg['layout']:
                array.append(n)
            array.extend(al['layout'])
            alcfg = {"layout": array}
        else:
            # replace the auto layout cfg
            alcfg = al
        #cls.__cALPutCfg(al)
        cls._alcfg = alcfg

    def ALGetData(self, alcfg):
        """ return a ordered dictionary holds all the values decoded.
        """

        out = collections.OrderedDict()
        for n in alcfg['layout']:
            name = n['property_name']
            if n['kind'] == 'array':
                arr = []
                item_func = getattr(self, name)
                length = int(getattr(self, n['length_name']) or 0)
                limit = min(length, cfg.cfgArrayElements)
                for i in range(limit):
                    arr.append(item_func(i))
                out[name] = arr
            else:
                out[name] = getattr(self, name)

        return out

    @CachedProperty
    def aldata(self):
        return self.ALGetData(self._alcfg)

    def _ALDebugPrint(self, data=None, pos=0, **kwargs):
        """ Auto generated DebugPrint.
            
        Arguments:
            data: aldata generated by ALGetData(),
            pos: indent blocks output
            kwargs: options passthrough when recursion.

        Return:
            None

        Options:
            al_show_only_set: omits all ZERO values.

        """

        def CamelName(name):
            # show in Camel liked-name
            arr = name.split('_')
            arr = [x.capitalize() for x in arr]
            return "".join(arr)

        # get cached aldata if None
        if data is None:
            data = self.aldata
        if data is None:
            raise Exception(self, 'aldata is None')

        # show title
        pos = kwargs['pos'] if 'pos' in kwargs else 0
        if pos == 0:
            log.print("[%s 0x%x]" % (self.__class__.__name__, int(self)))

        # show the aldata
        for k, v in data.items():
            attr_name = CamelName(k)

            if isinstance(v, BitField):
                log.print('- %s: 0x%x' % (CamelName(k), int(v)), pos)
                v._ALDebugPrint(pos=pos+2, **kwargs)
            
            elif isinstance(v, ALStruct):
                log.print('- %s: ' % (CamelName(k)), pos)
                v._ALDebugPrint(pos=pos+2, **kwargs)

            elif isinstance(v, list):
                length = len(v)
                if length == 0:
                    log.print('- %s[%d]: {}' % (attr_name, length), pos)
                    continue

                limit = min(length, cfg.cfgArrayElements)

                log.print('- %s[%d]: {' % (attr_name, length), pos)
                for i in range(limit):
                    vv = v[i]
                    if isinstance(vv, BitField):
                        log.print("  %d: {" % i, pos+2)
                        vv._ALDebugPrint(pos=pos+4, **kwargs)
                        log.print("  }", pos+2)

                    elif isinstance(v[i], ALStruct):
                        log.print("  %d: {" % i, pos+2)
                        vv._ALDebugPrint(pos=pos+4, **kwargs)
                        log.print("  }", pos=pos+2)

                    else:
                        log.print("  %d: %s" % (i, vv), pos+2)
                if limit < length:
                    log.print("   ...")
                log.print('  }', pos)

            elif isinstance(v, dict):
                log.print('- dict', pos)
                raise Exception("we don't support dict yet.")

            else:
                log.print("- %s: %s" % (CamelName(k), v), pos)

    def ALDebugPrint(self, **kwargs):
        """ the function is the bottom of ALDebugPrint Chain.
        """
        self._ALDebugPrint(**kwargs)

    def DebugPrint2(self, **kwargs):
        if hasattr(self, '_DebugPrint'):
            self._DebugPrint(**kwargs)
        else:
            self._ALDebugPrint(**kwargs)

        # show parent aldata
        for c in self.__class__.mro():
            if c == AutoLayout or c == Value or c == ALStruct or c == BitField:
                break

            #print(c.__name__)
            alcfg = self.__cALGetCfg(c.__name__)
            #print(c.__name__, alcfg)
            if hasattr(c, '_DebugPrint'):
                o = c(self)
                o._DebugPrint(**kwargs)
            elif alcfg is not None:
                aldata = self.ALGetData(alcfg)
                self._ALDebugPrint(aldata, **kwargs)

            #parent = super(c, self)
            #if hasattr(parent, '_alcfg'):
            #    print(parent, parent._alcfg)
            #alcfg = self.__cALGetCfg(parent.__class__.__name__)
            #print('aaa', alcfg)
            #if hasattr(parent, '_DebugPrint'):
            #    pass
            #elif alcfg is not None:
            #    aldata = self.ALGetData(alcfg)
            #    parent._ALDebugPrint(aldata, **kwargs)

    def DebugPrint(self, **kwargs):

        class Options:
            AL_SHOW_ONLY_SET = 0
            AL_SHOW_DETAIL_LEVEL = 0


        self._ALDebugPrint(**kwargs) 

    @classmethod
    def DebugLayout(cls, **kwargs):
        for i in cls._alcfg['layout']:
            print(i)

class Struct(dbg.Struct):
    """ represents an abstract structure/class in v8
    """

    _parent = None

    def __init__(self, address, parent=None):
        self._parent = parent
        super(Struct, self).__init__(address)

    @classmethod
    def LoadDwf(cls):
        super(Struct, cls).LoadDwf()

        # readout all dwf consts
        dwf_consts = dbg.Dwf.ReadAllConsts(cls._typeName)

        # class 'k' consts
        consts = []
        for v in cls.__dict__:
            if re.match(r'^k[A-Z]', v):
                consts.append(v)

        typ = getattr(cls, '_typeName')
        for v in consts:
            a = getattr(cls, v)

            if v not in dwf_consts:
                log.warn("'%s.%s' (%d) not found." % (typ, v, a))
                continue

            b = dwf_consts[v]
            if a != b:
                setattr(cls, v, b)
                log.info("'%s.%s' (%d) = %d" % (typ, v, a, getattr(cls, v)))

        # parse _constList
        consts = getattr(cls, '_constList', None)
        if consts is None:
            return

        for c in consts:
            v = c['name']
            
            alias = [v]
            if alias is not None:
                alias.extend(c['alias'])
           
            a = 0 
            if 'default' in c:
                a = c['default']

            b = None
            for x in alias:
                if x in dwf_consts:
                    b = dwf_consts[x]
                    break
            
            if b is None:
                log.warn("'%s.%s' (%d) not found." % (typ, v, a))
                continue

            setattr(cls, v, b)
            if a != b:
                log.info("'%s.%s' (%d) = %d" % (typ, v, a, getattr(cls, v)))

    # @classmethod
    # def LoadDwfConst(cls, name, alias=None):
    #     typ = getattr(cls, '_typeName')
    #     a = getattr(cls, name)

    #     b = dbg.Dwf.ReadClassConst(typ, name)
    #     if b is None:
    #         log.warn("'%s.%s' (%d) not found." % (typ, name, a))
    #         return

    #     if a != b:
    #         setattr(cls, name, b)
    #         log.info("'%s.%s' (%d) = %d" % (typ, name, a, getattr(cls, name)))
    
    @property
    def parent(self):
        return self._parent


class Enum(int, dbg.Enum):
    """ represents an abstract Enumeration in v8
    """

    @property
    def name(self):
        return self.Name(int(self))

    def to_string(self):
        v = int(self)
        return "%s (%d)" % (self.Name(v), v)

    def __str__(self):
        return self.to_string()

class ChunkBlock(object):

    #_address = None 
    #_reader = None
    
    kAlignmentMask = 0x3ffff
    
    _cls_chunks = {}

    class ChunkInfo(object):
        
        def __init__(self, chunk):
            self._address = chunk.address
            self._size = chunk.size
            self._bytes = dbg.Target.MemoryRead(self._address, self._size)

    class ChunkBlockReader(dbg.Block):
        
        _chunk = None
        
        def GetInChunkOffset(self, off):
            return self._address + off - self._chunk._address

        def LoadPtr(self, off):
            return struct.unpack_from('Q', self._chunk._bytes, self.GetInChunkOffset(off))[0]

        def LoadU64(self, off):
            return struct.unpack_from('Q', self._chunk._bytes, self.GetInChunkOffset(off))[0]

        def LoadU32(self, off):
            return struct.unpack_from('I', self._chunk._bytes, self.GetInChunkOffset(off))[0]

        def LoadU16(self, off):
            return struct.unpack_from('H', self._chunk._bytes, self.GetInChunkOffset(off))[0]
        
        def LoadU8(self, off):
            return struct.unpack_from('B', self._chunk._bytes, self.GetInChunkOffset(off))[0]

        def LoadDouble(self, off):
            return struct.unpack_from('Q', self._chunk._bytes, self.GetInChunkOffset(off))[0]

    def InitReader(self, addr):
        #self._address = addr
        reader = self.GetChunkBlock(addr)
        if reader is None:
            reader = dbg.Block()
            reader._address = addr 
        self._reader = reader
        assert self._reader

    @classmethod
    def AddChunk(cls, chunk):
        if chunk.address in cls._cls_chunks:
            return
        c = ChunkBlock.ChunkInfo(chunk)
        ChunkBlock._cls_chunks[chunk.address] = c 

    @classmethod
    def CacheSize(cls):
        return len(cls._cls_chunks)

    @classmethod
    def GetChunkBaseAddress(cls, ptr):
        return ptr & (~cls.kAlignmentMask)

    def GetChunkBlock(self, ptr):
        chunk_addr = self.GetChunkBaseAddress(ptr)
        if chunk_addr in self._cls_chunks:
            reader = ChunkBlock.ChunkBlockReader()
            reader._address = ptr 
            reader._chunk = self._cls_chunks[chunk_addr]
            return reader
        return None 

    @property
    def address(self):
        return self._reader._address

    def LoadPtr(self, off):
        return self._reader.LoadPtr(off)
    
    def LoadU64(self, off):
        return self._reader.LoadU64(off)
    
    def LoadU32(self, off):
        return self._reader.LoadU32(off)
    
    def LoadU16(self, off):
        return self._reader.LoadU16(off)
    
    def LoadU8(self, off):
        return self._reader.LoadU8(off)
    
    def LoadDouble(self, off):
        return self._reader.LoadDouble(off)

    def GetCString(self, length=-1):
        return self._reader.GetCString(length)
    
    def LoadCString(self, off, length=-1):
        return self._reader.LoadCString(off, length)
    
    def LoadUString(self, off, length=-1):
        return self._reader.LoadUString(off, length)

class Value(AutoLayout, ChunkBlock):
    """
        represents an abstract object for any v8 Object
    """

    # mapped C++ class name
    _typeName = None

    # gdb.type for _typeName
    _S_type = None

    #def __init__(self, v):
    #    #AutoLayout.__init__(self)
    #    dbg.Value.__init__(self, v)

    @classmethod
    def LoadDwf(cls):
        """ Load Object's constants from Dwarf.

        Retrieves object constants from Dwarf,

        HeapObject may have several fields, and field using offset value to reference,
        LoadDwf could load the offset value from Dwarf.

        """
        if cls._typeName is None:
            # Object doesn't have typeName
            cls._cALGenerate({})
            return

        # read all consts
        dwf_consts = dbg.Dwf.ReadAllConsts(cls._typeName)

        # resolve c++ type
        log.verbose("loaded object '%s'." % cls.__name__)
        t = dbg.Type.LookupType(cls._typeName)
        if t is None:
            log.error("'%s' not found, use default layout." % (cls._typeName))
            # Object doesn't have dwarf debug info. 
            cls._cALGenerate({})
            return

        cls._S_type = t.GetPointerType()

        # collect interesting consts
        consts = []
        for v in cls.__dict__:
            if re.match(r'^k[A-Z]', v):
                consts.append(v)

        # resolve all interesting consts
        typ = getattr(cls, '_typeName')
        for v in consts:
            a = getattr(cls, v)

            if v in dwf_consts:
                b = dwf_consts[v]
            else:
                b = None

            if b is None:
                log.warn("'%s.%s' (%d) not found." % (typ, v, a))
                continue

            # update new value
            if a != b:
                setattr(cls, v, b)
                log.info("'%s.%s' (%d) = %d" % (typ, v, a, getattr(cls, v)))

        # generate auto layout
        cls._cALGenerate(dwf_consts)

    @staticmethod
    def LoadAllDwf():
        for c in dbg.AllSubClasses(Value):
            c.LoadDwf()

    def __init__(self, address):
        #self._address = address
        self.InitReader(address)

    def __int__(self):
        return self._address

class ALStruct(AutoLayout, dbg.Block):
    """ base class for AutoLayout Structures.
        AutoLayout structures doesn't have a typeName,
        So it's different from Struct class.
    """
    def __init__(self, addr):
        self._address = addr

    @classmethod
    def LoadDwf(cls):
        # resolve c++ type
        log.verbose("loaded ALStruct '%s'." % cls.__name__)
        #cls._S_type = dbg.Type.LookupType(cls._typeName).GetPointerType()
        
        # Object doesn't have typeName
        cls._cALGenerate({}, {'IsALStruct': True})

    @staticmethod
    def LoadAllDwf():
        for c in dbg.AllSubClasses(ALStruct):
            c.LoadDwf()

    def __int__(self):
        return self._address

class BitField(AutoLayout, py23.int64):
    """ represents a v8 BitField """
    
    def __init__(self, val):
        #if not isinstance(val, py23.integer_types):
        #    raise Exception('BitField only accpts integer value.')
        self._value = int(val)

    @property
    def value(self):
        return self._value

    def BitSize(self, pos, size):
        x = self._value
        v = 0
        x = x >> pos
        for i in range(size):
            if x & 0x1:
                v |= (1 << i)
            x = x >> 1
        return v

    @classmethod
    def LoadDwf(cls):
        log.verbose("loaded bitfield '%s'" % cls.__name__)
        cls._cALGenerate({})

    @staticmethod
    def LoadAllDwf():
        for c in dbg.AllSubClasses(BitField):
            c.LoadDwf()


def LoadDwf():
    """Load v8 from dwarf"""
    # Build Config consts
    BuildConfig.LoadDwf()

    # v8::internal consts
    Internal.LoadDwf()

    # load all Class
    Struct.LoadAllDwf()

    # load all Enum
    Enum.LoadAllDwf()

    # load all BitField
    BitField.LoadAllDwf()

    # load all Object
    Value.LoadAllDwf()

    # load all ALStruct
    ALStruct.LoadAllDwf()

    # build Maps
    from .object import ObjectMap
    ObjectMap.LoadDwf()


