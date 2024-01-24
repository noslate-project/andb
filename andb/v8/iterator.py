# -*- coding: UTF-8 -*-
from __future__ import print_function, division

""" v8 engine support
"""

from abc import ABCMeta, abstractmethod
import re

from andb.stl import Vector
from .internal import ObjectSlot, ObjectSlots
from andb.config import Config

""" internal implimentations
"""
class SpaceIterator:
    """ iterator for heap spaces"""
    _next_space = 0

    def __init__(self, heap, non_ro=0):
        self._heap = heap
        self._next_space = 0
        if non_ro:
            self._all_spaces = AllocationSpace.NonROSpaces()
        else:
            self._all_spaces = AllocationSpace.AllSpaces()

    def HasNext(self):
        """ true if not EOF """
        return self._next_space < len(self._all_spaces) 

    def __iter__(self):
        return self

    def __next__(self):
        if self.HasNext():
            i = self._next_space
            self._next_space += 1

            sp_id = self._all_spaces[i]
            sp = self._heap.getSpace(sp_id)
            return sp
            
        raise StopIteration

    def next(self):
        """ compact with py2 """
        return self.__next__()

class ChunkIterator:
    """ iterator for memory chunks in space """
    _space = None
    _current = None

    def __init__(self, space):
        self._space = space 

    def __iter__(self):
        return self

    def __next__(self):
        if self._current is None:
            ptr = self._space['memory_chunk_list_']['front_']
        else:
            ptr = self._current['list_node_']['next_']
        self._current = ptr
        if self._current == 0:
            raise StopIteration
        return MemoryChunk(ptr)
    
    def next(self):
        """ compact with py2 """
        return self.__next__()

class ChunkObjectIterator:
    """ iterator for object inside a chunk """

    _space = None
    _chunk = None
    _next_ptr = None
    def __init__(self, chunk):
        self._chunk = chunk
        self._space = chunk.getSpace()
        self._next_ptr = chunk.area_start

    def __iter__(self):
        return self

    def nextObj(self):
        if self._next_ptr >= self._chunk.area_end:
            raise StopIteration

        ptr = self._next_ptr
        
        ho = HeapObject.FromAddress(ptr)
        if not ho.Access():
            # not accessable finish the chunk.
            return None

        #print(type(ptr), ptr, type(ho.Size()), ho.Size())
        try:
            ptr += ho.Size()
        except:
            print("failed: %x" % ptr)
            return None
     
        # readonly page don't have a space
        if self._space is not None:
            # current allocation top and limit 
            if ptr == self._space.top and ptr != self._space.limit:
                ptr = self._space.limit
        self._next_ptr = ptr

        return ho
    
    def __next__(self):
        return self.nextObj()
        try:
            return self.nextObj()
        except StopIteration:
            raise StopIteration
        except Exception as e:
            # we may meet ill HeapObject.
            if Config.cfgObjectDecodeFailedAction == 1: 
                print('Object(0x%x) decode failed, page dropped:' % (self._next_ptr), e)
                raise StopIteration
            else:
                print('Object(0x%x) decode failed, aborted:' % (self._next_ptr), e)
                raise e

    def next(self):
        """ compact with py2 """
        return self.__next__()

    def hasNext(self):
        return self._next_ptr < self._chunk.area_end

class SpaceObjectIterator:
    pass

class NewSpaceObjectIterator:
    """ iterator for objects in new space """
    _space = None
    _iter_space = None
    _next_space = None

    def __init__(self, space):
        self._space = space
        self._iter_space = PagedSpaceObjectIterator(space.from_space)
        self._next_space = PagedSpaceObjectIterator(space.to_space)

    def __iter__(self):
        return self

    def nextObj(self):
        if self._iter_space is None:
            return None
        try: 
            o = next(self._iter_space)
            return o
        except StopIteration:
            return None

    def nextSpace(self):
        if self._next_space is None:
            raise StopIteration
        p = self._next_space
        self._next_space = None
        return p

    def __next__(self):
        # has next
        o = self.nextObj()
        if o is not None:
            return o

        while o is None:
            self._iter_space = self.nextSpace() 
            
            # must have
            o = self.nextObj()

        return o

    def next(self):
        """ compact with py2 """
        return self.__next__()


class PagedSpaceObjectIterator:
    """ iterator for objects in a paged space """
   
    _space = None
    _iter_chunk = None
    _iter_obj = None

    def __init__(self, space):
        self._space = space
        self._iter_chunk = ChunkIterator(space)

    def __iter__(self):
        return self

    def nextObj(self):
        if self._iter_obj is None:
            return None
        try:
            o = next(self._iter_obj)
            return o
        except StopIteration:
            #print("finish page")
            return None

    def nextChunk(self):
        try:
            p = next(self._iter_chunk)
            #print(p)
            return p
        except StopIteration:
            #print("finish space")
            raise StopIteration

    def __next__(self):
        # has next
        o = self.nextObj()
        if o is not None:
            return o

        while o is None:
            # next chunk
            p = self.nextChunk()

            # reset iterator object
            self._iter_obj = ChunkObjectIterator(p)
            
            # must have
            o = self.nextObj()

        return o

    def next(self):
        """ compact with py2 """
        return self.__next__()

class HeapObjectIterator:
    """ Iterator for all objects in heap """
   
    _heap = None
    _iter_space = None
    _iter_obj = None

    def __init__(self, heap):
        self._heap = heap
        self._iter_space = SpaceIterator(heap, non_ro=1)

    def __iter__(self):
        return self

    def nextObj(self):
        if self._iter_obj is None:
            return None
        
        try:
            o = next(self._iter_obj)
            return o
        except StopIteration:
            #print("finish space")
            return None

    def nextSpace(self):
        try:
            p = next(self._iter_space)
            print(p['id_'])
            return p
        except StopIteration:
            #print("finish heap")
            raise StopIteration

    def __next__(self):
        o = self.nextObj()
        if o is not None:
            return o

        while o is None:
            # next space
            p = self.nextSpace()

            # reset iterator object
            self._iter_obj = PagedSpaceObjectIterator(p)

            # must have
            o = self.nextObj()
        
        return o

    def next(self):
        """ compact with py2 """
        return self.__next__()

class ReadOnlyPagesObjectIterator:
    _space = None
    _iter_vector = None
    _iter_obj = None

    def __init__(self, space):
        self._space = space
        self._iter_vector = Vector(space['pages_']).__iter__()

    def __iter__(self):
        return self

    def nextObj(self):
        if self._iter_obj is None:
            return None
        try:
            o = next(self._iter_obj)
            return o
        except StopIteration:
            #print("finish page")
            return None

    def nextPage(self):
        try:
            p = next(self._iter_vector)
            print(p)
            return MemoryChunk(p)
        except StopIteration:
            #print("finish space")
            raise StopIteration

    def __next__(self):
        # has next
        o = self.nextObj()
        if o is not None:
            return o

        while o is None:
            # next chunk
            p = self.nextPage()

            # reset iterator object
            self._iter_obj = ChunkObjectIterator(p)
            
            # must have
            o = self.nextObj()

        return o

    def next(self):
        """ compact with py2 """
        return self.__next__()


class ReadOnlyHeapObjectIterator:
    """ Iterator for all objects in Readonly Heap """
    
    _ro_heap = None
    _iter_obj = None
    
    def __init__(self, ro_heap):
        self._ro_heap = ro_heap
        space = ro_heap.read_only_space
        if space.has("memory_chunk_list_"):
            self._iter_obj = PagedSpaceObjectIterator(space)
        else:
            self._iter_obj = ReadOnlyPagesObjectIterator(space)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter_obj)

    def next(self):
        """ compact with py2 """
        return self.__next__()

class NodeIterator:
    """ Iterate Nodes in NodeSpace
        NodeSpace is used in GlobalHandles
    """

    def __init__(self, node_space):
        self._space = node_space

    def __iter__(self):
        return self
    
    def __next__(self):
        raise StopIteration

    def next(self):
        """ compact with py2 """
        return self.__next__()

class RootVisitor:
    """ abstractor vistor for itrator all roots """

    def VisitRootPointers(self, root, desc, start, end):
        for p in ObjectSlots(start, end):
            self.VisitRootPointer(root, desc, p)

    def VisitRootPointer(self, root, desc, p):
        raise NotImplementedError

    @classmethod
    def RootName(cls, root):
        return Root.RootName(root)

class viewRootVisitor(RootVisitor):
 
    def VisitRootPointers(self, root, desc, start, end):
        for p in ObjectSlots(start, end):
            self.VisitRootPointer(root, desc, p)

    def VisitRootPointer(self, root, desc, p):
        i = ObjectSlot(p)
        print("field: %d %s 0x%x"%(root, desc, i))


class LookupIterator:
    """ Implement LookupIterator according to v8.
    """

    class Configuration:
        # Configuration bits.
        kInterceptor = 1<<0
        kPrototypeChain = 1<<1
   
        # Conveience combinations of bits.
        OWN_SKIP_INTERCEPTOR = 0
        OWN = kInterceptor
        PROTOTYPE_CHAIN_SKIP_INTERCEPTOR = kPrototypeChain
        PROTOTYPE_CHAIN = kPrototypeChain | kInterceptor
        DEFAULT = PROTOTYPE_CHAIN

    class State:
        ACCESS_CHECK = 0
        INTEGER_INDEXED_EXOTIC = 1
        INTERCEPTOR = 2
        JSPROXY = 3
        NOT_FOUND = 4
        ACCESSOR = 5
        DATA = 6
        TRANSITION = 7
        BEFORE_PROPERTY = INTERCEPTOR

    def __init__(self, receiver, **kwargs):
        # receiver to be lookup
        self._receiver = receiver

        # state of the lookup
        self._state = self.State.NOT_FOUND

        # indicate whether property has been found. 
        self._has_property = False
        
        # set first holder, default is same as receiver
        self._holder = kwargs.get('lookup_start_object', receiver)

        # lookup configuration
        self._configuration = kwargs.get('configuration', self.Configuration.DEFAULT) 

        # indicate the property name to be found.
        self._name = kwargs.get('name', None)

        # indicate the index of elements
        self._index = kwargs.get('index', None)

        # indicate the property index.
        self._number = None

    def IsElement(self):
        raise Exception('now we dont support Elements yet.')

    def Start(self):
        """ Begin of the lookup
        """
        holder = ObjectMap.BindObject(self._holder)
        map = holder.map
        self._state = self.LookupInHolder(map, holder)
        #print(self._state)
        if self.IsFound():
            return
        self.NextInternal(map, holder)

    def Next(self):
        """ Next the lookup 
        """
        holder = self._holder
        map = holder.map
        if map.IsSpecialReceiverMap():
            self._state = LookupInSpecialHolder(map, holder)
            if self.IsFound():
                return
        self.NextInternal(map, holder)

    def NextInternal(self, map, holder):
        while True:
            maybe_holder = self.NextHolder(map)
            #print("next:", maybe_holder)
            if maybe_holder is None:
                self._state = self.State.NOT_FOUND
                self._holder = holder
                return

            holder = ObjectMap.BindObject(maybe_holder)
            map = holder.map
            self._state = self.LookupInHolder(map, holder)
            if self.IsFound():
                break;

        self._holder = holder

    def NextHolder(self, map):
        """ follow prototype until Null
        """
        prototype = map.prototype
        if prototype.IsNull(): 
            return None
        if not self.check_prototype_chain:
            return None
        #print(prototype)
        return HeapObject(prototype)
    
    def IsFound(self):
        return self._state != self.State.NOT_FOUND

    def SetNotFound(self):
        self._has_property = false
        self._state = self.State.NOT_FOUND

    @property
    def check_prototype_chain(self):
        return (self._configuration & self.Configuration.kPrototypeChain) != 0

    @property
    def check_interceptor(self):
        return (self._configuration & self.Configuration.kInterceptor) != 0

    def LookupInHolder(self, map, holder):
        if map.IsSpecialReceiverMap():
            return self.LookupInSpecialHolder(map, holder)
        else:
            return self.LookupInRegularHolder(map, holder)

    def LookupInRegularHolder(self, map, holder):
        if not map.is_dictionary_map:
            descriptors = map.instance_descriptors
            index = descriptors.Search(self._name) 
            #print("find", self._name, "=", index)
            if index is None:
                return LookupIterator.State.NOT_FOUND
            self._property_detail = descriptors.GetDetails(index)
            self._number = index
        else:
            maybe_dict = holder.property_dictionary
            if InstanceType.isSwissNameDictionary(maybe_dict.instance_type):
                raise Exception('TBD')
            else:
                name_dict = holder.property_dictionary
                index = name_dict.Search(self._name) 
                #print("dict", self._name, "at", index)
                if index is None:
                    return LookupIterator.State.NOT_FOUND
                self._property_detail = name_dict.DetailsAt(index)
                self._number = index

        self.has_property = True
        if self._property_detail.kind == PropertyKind.kData:
            return LookupIterator.State.DATA
        elif self._property_detail.kind == PropertyKind.kAccessor:
            return LookupIterator.State.ACCESSOR
        
        raise Exception('Unreachable')

    def LookupInSpecialHolder(self, map, holder):
        fall_through = False
        if self._state == self.State.NOT_FOUND:
            map_type = map.instance_type
            if InstanceType.isJSProxy(map_type):
                return self.State.JSPROXY
            elif map.is_access_check_needed:
                return self.State.ACCESS_CHECK
            fall_through = True

        if fall_through or self._state == self.State.ACCESS_CHECK:
            if self.check_interceptor:
                return self.State.INTERCEPTOR
            fall_through = True

        if fall_through or self._state == self.State.INTERCEPTOR:
            map_type = map.instance_type
            if InstanceType.isJSGlobalObject(map_type):
                global_object = JSGlobalObject(holder)
                global_dictionary = global_object.global_dictionary 
                index = global_dictionary.FindEntry(self._name)
                if index is None:
                    return self.State.NOT_FOUND

                cell = global_dictionary.CellAt(index)
                if not cell.IsPropertyCell():
                    return self.State.NOT_FOUND
               
                # we get the property cell
                self._property_detail = cell.property_details
                self._number = index
                
                if self._property_detail.kind == PropertyKind.kData:
                    return self.State.DATA
                elif self._property_detail.kind == PropertyKind.kAccessor:
                    return self.State.ACCESSOR
            
            # other cases lookup in regular
            return self.LookupInRegularHolder(map, holder)

        if self._state == self.State.ACCESSOR or \
            self._state == self.State.DATA:
                return self.State.NOT_FOUND

        raise Exception('Unreachable')

    def GetAccessor(self):
        raise NotImplementedError() 

    def FetchValue(self):
        """ get selected property value
        """
        holder = self._holder
        result = None
        if holder.IsJSGlobalObject():
            jsobj = JSGlobalObject(holder)
            result = jsobj.global_dictionary.ValueAt(self._number)
        elif not holder.has_fast_properties:
            jsobj = JSObject(holder)
            result = jsobj.DictPropertyAt(self._number) 
        elif self._property_detail.location == PropertyLocation.kField:
            assert holder.IsObject()
            jsobj = JSObject(holder)
            result = jsobj.FastPropertyAt(self._number)
        else:
            # get strong value
            raise Exception('TBD')
        return result

    def GetDataValue(self):
        return self.FetchValue()

    def GetDataProperty(self):
        self.Start()
        value = None
        while self.IsFound():
            state = self._state
            #print("state:", state)
            
            if state == self.State.DATA:
                value = self.GetDataValue()
                #print(value)
                break
            else:
                # other cases return None
                break

            self.Next()
        return value


class PrototypeIterator:
    """ 
    A class to uniformly access the prototype of any Object and walk its
    prototype chain.
    """

    # WhereToStart
    START_AT_RECEIVER = 0
    START_AT_PROTOTYPE = 1
    
    # WhereToEnd
    END_AT_NULL = 0
    END_AT_NON_HIDDEN = 1

    def __init__(self, receiver, **kwargs):

        # TBD: support map prototyp chain.
        assert isinstance(receiver, JSReceiver)

        # current object
        self._object = receiver
        
        # user config
        self._where_to_start = kwargs.get('where_to_start', self.START_AT_PROTOTYPE) 
        self._where_to_end = kwargs.get('where_to_end', self.END_AT_NULL) 

        # init
        self._is_at_end = False

        # if start at prototype, do the first advance.
        if self._where_to_start == self.START_AT_PROTOTYPE:
            self.Advance()

    def GetCurrent(self):
        return self._object

    def IsAtEnd(self):
        return self._is_at_end

    def Advance(self):
        obj = self._object
        if obj and obj.IsJSProxy():
            self._is_at_end = True
            self._object = RootsTable.null_value
            return
        self.AdvanceIgnoringProxies() 

    def AdvanceIgnoringProxies(self):
        obj = self._object
        
        prototype = HeapObject(obj.map.prototype)
        self._is_at_end = prototype.IsNull() or \
            (self._where_to_end == self.END_AT_NON_HIDDEN and \
            not obj.IsJSGlobalProxy())

        self._object = prototype

""" tail imports
"""

from .object import (
    Object,
    HeapObject,
    Map,
    JSReceiver,
    JSObject,
    ObjectMap,
    JSGlobalObject,
)
from .enum import (
    AllocationSpace, 
    Root,
    InstanceType,
    PropertyKind,
    PropertyLocation,
)
from .structure import (
    PagedSpace, 
    MemoryChunk,
    RootsTable,
)

