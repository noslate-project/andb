
from __future__ import print_function, division

import os
import time
import json
try:
    import cPickle as pickle
except:
    import pickle

import andb.dbg as dbg 
import andb.v8 as v8
from andb.config import Config as cfg
from andb.utility import (
    profiler, 
    Logging as log , 
    TextShort, 
    TextLimit
)
import andb.py23 as py23

testNames=None

class Picklable(object):

    def __getstate__(self):
        a = dict([(k, getattr(self,k,None)) for k in self.__slots__])
        #print(a)
        return a

    def __setstate__(self, data):
        for k,v in data.items():
            setattr(self,k,v)

class HeapGraphEdge(Picklable):
    """ HeapGraphEdge representa a edge between two HeapEntries.
        
    """

    kContextVariable = 0
    kElement = 1
    kProperty = 2
    kInternal = 3
    kHidden = 4
    kShortcut = 5
    kWeak = 6

    __slots__ = ["to_entry_", "from_entry_", "type_", "index_or_name_"]
    
    """
    edges consums lots of memory.
    """
    def __init__(self, snapshot):
        # the snapshot it belongs to
        #self._snapshot = snapshot
        # edge to object
        self.to_entry_ = None
        # edge from index (object index)
        self.from_entry_ = None 
        # type above
        self.type_ = -1
        # index of the edge, (either index or name) 
        #self.index_ = 0
        # index or name of the edge, None for uninialized
        self.index_or_name_ = None

    @property
    def to_entry(self):
        return self.to_entry_

    @property
    def from_entry(self):
        return self.from_entry_ 

    def type(self):
        return self.type_

    def index(self):
        t = self.type
        if t == self.kElement or t == self.kHidden:
            return int(self.index_or_name_)
        return None

    def name(self):
        t = self.type
        if t == self.kContextVariable or \
           t == self.kProperty or \
           t == self.kInternal or \
           t == self.kShortcut or \
           t == self.kWeak:
            return self.index_or_name_
        return None

    def __str__(self):
        return "edge: type(%d), index_or_name(%s), to(%s), from(%s)" % (self.type_, self.index_or_name_, self.to_entry_, self.from_entry_)

    def DebugPrint(self):
        log.print(str(self))


class HeapEntry(Picklable):

    # Type from 'HeapGraphNode'
    kHidden = 0
    kArray = 1
    kString = 2
    kObject = 3
    kCode = 4
    kClosure = 5
    kRegExp = 6
    kHeapNumber = 7
    kNative = 8
    kSynthetic = 9
    kConsString = 10
    kSlicedString = 11
    kSymbol = 12
    kBigInt = 13
    
    type_strings = { 
        kHidden: '/hidden/',
        kObject: '/object/',
        kClosure: '/closure/',
        kString: '/string/',
        kCode: '/code/',
        kArray: '/arry/',
        kRegExp: '/regexp/',
        kHeapNumber: '/number/',
        kNative: '/native/',
        kSynthetic: '/synthetic/',
        kConsString: '/concatenated string/',
        kSlicedString: '/sliced string/',
        kSymbol: '/symbol/',
        kBigInt: '/bigint/',
    }

    __slots__ = ["type_", "index_", "self_size_", "id_", "name_", "mem_addr_", "children_count_", "children_end_count_" ]
    
    def __init__(self, snapshot):
        #self._snapshot = snapshot

        # keep as same as C++ code, with "_" tail
        # HeapGraphNode type
        self.type_ = -1

        # array index
        self.index_ = 0

        # self but without children size
        self.self_size_ = 0

        # Snapshot Object Id ( by self.id )
        self.id_ = 0

        # name of the HeapEntry
        self.name_ = None

        # not used for now
        #self.trace_node_id_ = 0

        # memory address 
        self.mem_addr_ = 0

        # edges count
        self.children_count_ = 0

        # edges end index
        self.children_end_count_ = 0

    def SetIndexedReference(self, snap, typ, index, child):
        assert typ == HeapGraphEdge.kElement or typ == HeapGraphEdge.kHidden
        self.children_count_ += 1
        snap._AddEdge(typ, int(index), self, child)
        #log.debug("SetIndexedReference: type(%d), index(%d), entry(%d)" % (typ, index, child.id_))

    def SetNamedReference(self, snap, typ, name, child):
        assert typ != HeapGraphEdge.kElement and typ != HeapGraphEdge.kHidden
        self.children_count_ += 1
        snap._AddEdge(typ, str(name), self, child)
        #log.debug("SetNamedReference: type(%d), name(%s), entry(%d)" % (typ, name, child.id_))

    def SetIndexedAutoIndexReference(self, snap, typ, child_entry):
        # heap snapshot count array from 1.
        index = self.children_count_ + 1
        self.SetIndexedReference(snap, typ, index, child_entry)
    
    def SetNamedAutoIndexReference(self, snap, typ, desc, child_entry):
        index = self.children_count_ + 1
        if isinstance(desc, str) and len(desc) > 0:
            name = "%d / %s" % (index, desc)
        else:
            name = "%d" % index
        #print("SetNamedAutoIndexReference", name, typ)
        self.SetNamedReference(snap, typ, name, child_entry)

    def set_children_index(self, index):
        next_index = index + self.children_count_
        self.children_end_count_ = index
        return next_index

    def GetRealEntry(self):
        return self

    def GetLastEntry(self):
        return self

    def DebugPrint(self):
        log.print("node: type(%s), id(%s), child(%d), size(%s), name(%s)" % (self.type_, self.id_, self.children_count_, self.self_size_, self.name_.encode('unicode_escape')))

    def TypeAsString(self):
        """ return type's string
        """
        root_type = self.type_
        if root_type in type_strings:
            return type_strings[root_type]
        return "???"

    def __str__(self):
        return "<Entry %s>" % (self.name_.encode('unicode_escape'))

class LazyEntry(Picklable):
    __slots__ = ['real_entry_']

    def __init__(self):
        # Unresolved HeapEntry should be None
        self.real_entry_ = None 

    def GetRealEntry(self):
        """ Get Last HeapEntry,
            return None if not exists.
        """
        next_entry = self.real_entry_
        while next_entry is not None:
            if isinstance(next_entry, HeapEntry):
                return next_entry
            next_entry = next_entry.real_entry_
        return None

    def GetLastEntry(self):
        """ Return Last Entry in list,
            return self if only One entry in list.
        """
        if self.real_entry_ is None:
            return self

        last_entry = self.real_entry_
        
        while True:
            if isinstance(last_entry, HeapEntry):
                return last_entry
            
            if last_entry.real_entry_ is None:
                return last_entry
            
            last_entry = next_entry.real_entry_

    def SetRealEntry(self, entry):
        """ Set entry to last of list.
        """
        last_entry = self.GetLastEntry()
        assert isinstance(last_entry, LazyEntry)
        last_entry.real_entry_ = entry

    #def __str__(self):
    #    if self.real_entry_ is None:
    #        return "<LazyEntry None>"
    #    return "<LazyEntry %s>" % (self.real_entry_)


class SourceLocation(Picklable):
    __slots__ = ["_entry", "_id", "_line", "_col"]

    def __init__(self, entry, script_id, line, col):
        self._entry = entry 
        self._id = script_id
        self._line = line
        self._col = col

class v8HeapExplorer:
    """ iterator all objects in v8 heap """
    pass

class NativeObjectsExplorer:
    """ iterator all native objects """
    pass


class ProgressCounter:
    """ show heap snapshot info during progress 
    """
    # tick the counter by every Object count. 
    PROGRESS_OBJ_TICK = 10*1000

    # show progress after seconds
    PROGRESS_SECONDS = 10

    def __init__(self, snap):
        self._snapshot = snap
        # the counter after last output
        self._count = 0
        # the size in Byte after last output
        self._size = 0
        # the total object count
        self._object_count = 0
        # the total object size
        self._object_size = 0
        # last saved entry count 
        self._saved_size_entry = 0
        # last saved edge count
        self._saved_size_edge = 0
        # time now
        self._saved_timestamp = time.time()
        # heap totol size 
        self._heap_size = snap.heap().CommitSize()

    def Tick(self, size):
        if self._count < self.PROGRESS_OBJ_TICK:
            self._count += 1
            self._size += size
            return
        
        timestamp = time.time()
        d_ts = timestamp - self._saved_timestamp
        if d_ts < self.PROGRESS_SECONDS:
            return

        size_entry = len(self._snapshot.entries_)
        size_edge = len(self._snapshot.edges_)
        obj_count = self._object_count + self._count

        log.info('%.1f%%: %.1f/sec, Object(%d), Entry(%d), Edge(%d)' % (
            (self._object_size + self._size) / self._heap_size * 100,
            self._count / d_ts,
            obj_count,
            size_entry,
            size_edge
            ))
       
        self._saved_timestamp = timestamp
        self._object_count += self._count
        self._object_size += self._size
        self._count = 0
        self._size = 0;


class GraphHolder(object):
   
    # id 
    kObjectIdStep = 2

    def __init__(self):

        # current isolate
        self._isolate = v8.Isolate.GetCurrent()
        if self._isolate is None:
            print("isolate is not set.")
            raise Exception
        
        # uniq next ObjectId
        self._next_id = 0
        
        # holds all objects resolved
        self.entries_ = []

        # holds all edges
        self.edges_ = []

        # holds the location info
        self.locations_ = []

        # address to HeapEntry or LazyEntry map 
        self.entries_map_ = {}

    @property
    def id(self):
        """ return current object id """
        i = self._next_id
        # from HeapObjectsMap::kObjectIdStep
        self._next_id += self.kObjectIdStep 
        return i

    def _AddEntry(self, typ, name, size, addr, object_id = -1):
        """ add HeapEntry to self.entries_ 

        arguments,
            typ: is one of HeapEntry.kXXX
            name: tagged name of the object 
            id : uniq object id 
            self_size : only self node size
            mem_addr : HeapObject memory address
        """
        # print(typ, name, size, addr, object_id)
        if isinstance(name, py23.string_types) or \
                isinstance(name, py23.text_type):
            pass
        elif isinstance(name, py23.binary_type):
            name = name.decode('utf8')
        else:
            print(type(name), name)
            raise Exception

        if object_id <= 0:
            object_id = self.id
        e = HeapEntry(self)
        e.index_ = len(self.entries_)
        e.type_ = typ
        e.name_ = name
        e.self_size_ = size
        e.mem_addr_ = addr 
        e.id_ = object_id
        #e.DebugPrint()
        #if typ == 3 and len(name) == 0:
        #    raise Exception('name is blank')
        #log.debug("_AddEntry: type(%d), id(%d), size(%d)" % (typ, object_id, size))
        self.entries_.append(e)
        return e
    
    def _AddEdge(self, edge_type, name_or_index, entry, child):
        """ new HeapGraphEdge for self.edges_

        arg:
          edge_type: the type of the Edge defined in HeapGraphEdge
          name_or_index : edge name or index
          entry : parent HeapEntry (from)
          child : child HeapEntry (to)
        """
        e = HeapGraphEdge(self)
        e.type_ = edge_type
        #if isinstance(name_or_index, str):
            # is string
        #    e.name_ = name_or_index
        #else:
        #    e.index_ = name_or_index


        e.index_or_name_ = name_or_index
        e.from_entry_ = entry
        e.to_entry_ = child

        self.edges_.append(e)
        #e.DebugPrint()
        return e

    def AddLazyEntry(self, obj):
        assert isinstance(obj, v8.HeapObject)
        ptr = obj.address

        assert ptr not in self.entries_map_
        entry = LazyEntry()
        self.entries_map_[ptr] = entry
        return entry

    def AddDummyEntry(self, obj):
        addr = obj.address 
        # allocate a new object id
        entry = self._AddEntry(HeapEntry.kHidden, "dummy", 0, addr)
        self.AddMapHeapEntry(addr, entry)
        return entry

    def GetHeapEntry(self, tag):
        """ get (or create) an HeapEntry

        """
        if isinstance(tag, v8.HeapObject):
            obj = tag
        else:
            # assume not a HeapObject, check it
            obj = v8.HeapObject(int(tag))
            if not obj.IsHeapObject():
                log.warn("not a heapObject 0x%x" % obj)
                return None

        # get address(pointer)
        ptr = obj.address

        # return cached entry
        entry = self.FindMapHeapEntry(ptr)
        if entry is not None:
            return entry

        # Add New HeapEntry from HeapObject (maybe None)
        return self.AddEntryObject(obj)

    def GetEntryOrLazy(self, tag):
        """ Get tag HeapEntry or a LazyEntry should be created.

        """
        if isinstance(tag, v8.HeapObject):
            obj = tag
        else:
            # assume not a HeapObject, check it
            obj = v8.HeapObject(int(tag))
            if not obj.IsHeapObject():
                log.warn("not a heapObject 0x%x" % obj)
                return None

        # get address(pointer)
        ptr = obj.address

        # return cached entry
        if ptr in self.entries_map_:
            log.debug("Found <0x%x> Entry." % ptr)
            return self.entries_map_[ptr]

        # Add New LazyEntry
        return self.AddLazyEntry(obj)

    def AddEntryObject(self, obj):
        """ new HeapEntry by HeapObject address

        base on object.type:
        """
        heap_obj = obj
        #heap_obj = v8.HeapObject(obj)
        obj_type = heap_obj.map.instance_type
        #print("AddEntryObject(0x%x), Map(0x%x), %s" % (heap_obj.address, heap_obj.map, v8.InstanceType.Name(obj_type)))
        #import traceback
        #traceback.print_stack()

        if v8.InstanceType.isJSFunction(obj_type):
            o = v8.JSFunction(obj)
            shared = o.shared_function_info
            script = shared.script
            if script is not None:
                name = "%s %s" % (shared.NameStr(), script.name)
            else:
                name = shared.NameStr()
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kClosure, name)

        elif v8.InstanceType.isJSBoundFunction(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kClosure, "native_bind")
        
        elif v8.InstanceType.isJSObject(obj_type):
            o = v8.JSObject(obj)
            name = self.GetConstructorName(o)
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kObject, name)

        elif v8.InstanceType.isString(obj_type):
            o = v8.String(obj)
            if o.IsConsString():
                return self.AddEntryObjectSize(heap_obj, HeapEntry.kConsString, "(concatenated string)")
            elif o.IsSlicedString():
                return self.AddEntryObjectSize(heap_obj, HeapEntry.kSlicedString, "(sliced string)")
            else:
                #print("%x: %s" % (o.address, o.to_string()))
                name = o.to_string()
                return self.AddEntryObjectSize(heap_obj, HeapEntry.kString, name)

        elif v8.InstanceType.isSymbol(obj_type):
            o = v8.Symbol(obj)
            if o.is_private:
                return self.AddEntryObjectSize(heap_obj, HeapEntry.kHidden, "private symbol") 
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kSymbol, "symbol")

        elif v8.InstanceType.isBigInt(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kBigInt, "bigint")

        elif v8.InstanceType.isCode(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kCode, "")

        elif v8.InstanceType.isSharedFunctionInfo(obj_type):
            o = v8.SharedFunctionInfo(obj)
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kCode, o.DebugName())

        elif v8.InstanceType.isScript(obj_type):
            o = v8.Script(obj)
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kCode, o.DebugName())

        elif v8.InstanceType.isNativeContext(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kHidden, "system / NativeContext")

        elif v8.InstanceType.isContext(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kObject, "system / Context")

        elif v8.InstanceType.isFixedArray(obj_type) or \
             v8.InstanceType.isFixedDoubleArray(obj_type) or \
             v8.InstanceType.isByteArray(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kArray, "")

        elif v8.InstanceType.isHeapNumber(obj_type):
            return self.AddEntryObjectSize(heap_obj, HeapEntry.kHeapNumber, "heap number")

        # STUB: remove after implemented.
        return self.AddEntryObjectSize(
                heap_obj, 
                HeapEntry.kHidden, 
                self.GetSystemEntryName(heap_obj))

    def AddEntryObjectSize(self, obj, typ, name, size = -1):
        """ Add Object(with name and size) to snapshot.
            
            if size is not specified, gets from object.Size().
            
            1) make the (address to HeapEntry) map
            2) add to entries_ list
        """
        if size < 0:
            size = int(obj.Size())
            assert size < 2*1024*1024*1024, "Object<0x%x> has a too large size '%d'" % (obj, size)
            if not isinstance(size, int):
                print(type(size))
                raise Exception
        addr = obj.address

        #assert addr not in self.entries_map_, print(self.entries_map_[addr])

        #entry = self.FindMapEntry(addr)
        #if not entry is None:
        #    if v8.InstanceType.isScript(obj.instance_type):
        #        print(entry, entry.name)
        #    return entry
        
        def good_name(name):
            if name is None:
                return 'None'
            return TextShort(name, limit=128)

        log.debug("AddEntry: <0x%x> type(%d), name(%s), size(%d)"% 
                (addr, typ, good_name(name), size))
            
        # allocate a new object id
        entry = self._AddEntry(typ, name, size, addr)
        self.AddMapHeapEntry(addr, entry)
        return entry

    def GetConstructorName(self, jsobj):
        """ Get Constructor Name for JSObject
        """
        t = jsobj.map.instance_type
        if v8.InstanceType.isJSFunction(t):
            # TBD: refere from readonly roots.
            return "(closure)"
        return jsobj.GetConstructorName()

    def GetSystemEntryName(self, obj):
        typ = obj.instance_type
        if v8.InstanceType.isMap(typ):
            obj2 = v8.Map(obj.tag)
            typ2 = v8.InstanceType.CamelName(obj2.instance_type)
            return "system / Map (%s)" % typ2
        elif v8.InstanceType.isCell(typ):
            return "system / Cell"
        elif v8.InstanceType.isPropertyCell(typ):
            return "system / PropertyCell"
        elif v8.InstanceType.isForeign(typ):
            return "system / Foreign"
        elif v8.InstanceType.isOddball(typ):
            return "system / Oddball"
        elif v8.InstanceType.isAllocationSite(typ):
            return "system / AllocationSite"
        else:
            return "system / %s" % v8.InstanceType.CamelName(typ)

    """ Map Entries List API
        
        the map list holds the all address to HeapObject mappings.

        FindMapEntry: get the first entry for address.
        FindMapHeapEntry: get the HeapEntry for address.
        AddMapEntry: put HeapEntry or LazyEntry to list. 
        AddMapHeapEntry: put HeapEntry to map list(last in list).
        AddMapLazyEntry: put LazyEntry to map list(first in list).
    """

    def FindMapEntry(self, addr):
        """ find by address
            
            Return,
              None: not found,
              entry: HeapEntry or LazyEntry found
        """
        if addr in self.entries_map_:
            return self.entries_map_[addr]
        return None

    def FindMapHeapEntry(self, addr):
        """ get Real HeapEntry from LazyEntry list.
            
            Return:
              None: no HeapEntry at end of list.
              HeapEntry: first HeapEntry in list.
        """
        next_entry = self.FindMapEntry(addr)
        while next_entry is not None:
            if isinstance(next_entry, HeapEntry):
                return next_entry
            next_entry = next_entry.real_entry_
        return None

    def AddMapEntry(self, addr, entry):
        """ Add Entry to entries map 
        """
        if isinstance(entry, HeapEntry):
            return self.AddMapHeapEntry(addr, entry)
        return self.AddMapLazyEntry(addr, entry) 

    def AddMapHeapEntry(self, addr, entry):
        """ Add HeapEntry to MapEntry List
        """
        assert isinstance(entry, HeapEntry)
        if addr not in self.entries_map_:
            self.entries_map_[addr] = entry
            return entry

        cur = self.entries_map_[addr]
        assert isinstance(cur, LazyEntry)
        while cur is not None:
            if cur.real_entry_ is None:
                cur.real_entry_ = entry
                return entry
            cur = cur.real_entry_
        return entry

    def AddMapLazyEntry(self, addr, entry):
        """ Add LazyEntry to MapEntry List
        """
        assert isinstance(entry, LazyEntry)
        if addr not in self.entries_map_:
            self.entries_map_[addr] = entry
            return entry
        
        cur = self.entries_map_[addr]
        entry.real_entry_ = cur
        self.entries_map_[addr] = entry
        return entry


    """ utility
    """

    def TagObject(self, obj, name):
        entry = self.GetHeapEntry(obj)
        if entry is None:
            return None

        if entry.name_ is None or len(entry.name_) == 0:
            entry.name_ = name
            log.debug("TagObject: 0x%x as '%s'" % (obj, name))

    def CleanAll(self):
        self.entries_map_.clear()
        del self.entries_[:]
        del self.edges_[:]
        del self.locations_[:]

    def Validity(self):
        id_map = {}
        for p,e in self.entries_map_.items():
            id_map[id(e)] = p

        for i in self.edges_:
            print(i)
            from_entry = id(i.from_entry_)
            to_entry = id(i.to_entry_)
            print("from: %x, to: %x" % (id_map[from_entry], id_map[to_entry]))

    @profiler
    def SaveFile(self, filename):
        """ write data to file.
        """
        a = {"entries_map": self.entries_map_,
             "entries": self.entries_,
             "edges": self.edges_,
             "locations": self.locations_}

        with open(filename, 'wb') as f:
            pickle.dump(a, f, pickle.HIGHEST_PROTOCOL)

    @profiler
    def LoadFile(self, filename):
        """ read data from file.
        """
        with open(filename, 'rb') as f:
            a = pickle.load(f)

        self.entries_map_ = a['entries_map']
        self.entries_ = a['entries']
        self.edges_ = a['edges']
        self.locations_ = a['locations']

class ObjectParser(GraphHolder):

    _non_essential_addrs = [] 

    def __init__(self):
        super(ObjectParser, self).__init__()
        self.MakeNonEssentialAddrs()

    def MakeNonEssentialAddrs(self):
        if len(self._non_essential_addrs) > 0:
            return 
        
        ro_heap = self._isolate.ReadOnlyHeap()
        for obj in v8.ReadOnlyHeapObjectIterator(ro_heap):
            if obj.IsOddball():
                self._non_essential_addrs.append(obj.address) 

        roots = self._isolate.Roots()
        #print(obj, roots.empty_fixed_array, obj == roots.empty_fixed_array)
        ar = [roots.empty_byte_array,
            roots.empty_fixed_array,
            roots.empty_weak_fixed_array,
            roots.empty_descriptor_array,
            roots.fixed_array_map,
            roots.cell_map,
            roots.global_property_cell_map,
            roots.shared_function_info_map,
            roots.free_space_map,
            roots.one_pointer_filler_map,
            roots.two_pointer_filler_map]
        
        for o in ar:
            ho = v8.HeapObject(o)
            self._non_essential_addrs.append(ho.address)

        print("Cache NonEssetialAddress,")
        for p in self._non_essential_addrs:
            print(" 0x%x" % p)

    def ExtractObject(self, obj):
        # obj: HeapObject
        assert isinstance(obj, v8.HeapObject)

        # skip FreeSpace object
        if v8.InstanceType.isFreeSpace(obj.instance_type) and \
            cfg.cfgHeapSnapshotShowFreeSapce == 0:
            return

        # get the HeapEntry
        entry = self.GetHeapEntry(obj)
        
        # extract reference
        self.ExtractReferences(entry, obj)

        # reference to map
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "map", obj.map)

        # show Tagged Pointer in heapsnapshot 
        #entry.SetNamedReference(HeapGraphEdge.kInternal, "0x%x" % obj, self.mem_entry_)

        # Extrace Location
        #self.ExtractLocation(entry, obj)

    def AddLocation(self, entry, script, line, col):
        l = SourceLocation(entry, script, line, col)
        self.locations_.append(l)

    def IsSessentialObject(self, obj):
        """ heapobject, not oddball, not roots.
        """
        #if not obj.IsHeapObject(): return False
        ptr = obj.address
        for p in self._non_essential_addrs:
            if ptr == p:
                return False
        return True

    def SetReferenceValue(self, typ, parent_entry, name_or_index, child_tag):
        child_obj = v8.HeapObject(child_tag)
        if child_obj.IsSmi():
            return
        elif child_obj.IsWeak():
            return 
        return self.SetReferenceObject(typ, parent_entry, name_or_index, child_obj)

    def SetReferenceObject(self, typ, parent_entry, name_or_index, child_obj):
        assert parent_entry is not None

        #if not isinstance(child_obj, v8.HeapObject):
        #    print(child_obj, type(child_obj))
        #    raise Exception
        #    return 

        # check if child_obj is a HeapObject
        assert isinstance(child_obj, v8.HeapObject)
        if not child_obj.IsHeapObject():
            return

        child_entry = self.GetEntryOrLazy(child_obj)
        assert child_entry is not None, child_obj

        if not self.IsSessentialObject(child_obj):
            return

        # based on typeof(name_or_index)
        if isinstance(name_or_index, int):
            raise Exception(name_or_index)
            parent_entry.SetIndexedReference(self, typ, name_or_index, child_entry)
        elif isinstance(name_or_index, str):
            parent_entry.SetNamedReference(self, typ, name_or_index, child_entry)
        elif isinstance(name_or_index, unicode):
            name = name_or_index.encode('utf-8')
            parent_entry.SetNamedReference(self, typ, name, child_entry)
        else:
            print(name_or_index, type(name_or_index))
            raise Exception

    def SetReferenceElement(self, typ, parent_entry, name_or_index, child_obj):
        assert isinstance(name_or_index, int)
       
        if not child_obj.IsHeapObject():
            return

        child_entry = self.GetEntryOrLazy(child_obj)
        assert child_entry is not None
       
        parent_entry.SetIndexedReference(self, typ, name_or_index, child_entry)

    def ExtractReferencesAccessorInfo(self, parent_entry, obj):
        o = v8.AccessorInfo(obj)
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "name", v8.HeapObject(o.name))
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "expected_receiver_type", v8.HeapObject(o.expected_receiver_type))
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "setter", v8.HeapObject(o.setter))
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "getter", v8.HeapObject(o.getter))
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "data", v8.HeapObject(o.data))

    def ExtractReferencesAccessorPair(self, parent_entry, obj):
        o = v8.AccessorPair(obj)
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "setter", v8.HeapObject(o.setter))
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "getter", v8.HeapObject(o.getter))

    def ExtractReferencesMap(self, parent_entry, obj):
        # transitions
        # isWeak
        m = v8.Map(obj)
        assert m.IsMap()
        typ = m.instance_type
        field = v8.HeapObject(m.transitions_or_prototype_info)
        if field.IsHeapObject() and field.IsWeak():
            # is a weak HeapObject
            self.SetReferenceObject(HeapGraphEdge.kWeak, parent_entry, "transition", field)
        else:
            # a Strong HeapObject
            if v8.InstanceType.isTransitionArray(typ):
                # TransitionArray
                # TBD: Tag (prototype transitions)
                #self.TagObject(field, "(transition array)")
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "transitions", field)

            elif v8.InstanceType.isFixedArray(typ):
                # FixedArray
                #self.TagObject(field, "(transition)")
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "transition", field)

            elif m.is_prototype_map:
                # prototype_info
                #self.TagObject(field, "prototype_info")
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "prototype_info", field)

        # descriptors 
        #self.TagObject(descriptors, "(map descriptors)")
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "descriptors", v8.HeapObject(m.instance_descriptors))

        # prototype
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "prototype", v8.HeapObject(m.prototype))

        # context, back pointer, constructor
        field = v8.HeapObject(m.native_context)
        if v8.InstanceType.isNativeContext(typ):
            #self.TagObject(field, "(native context)")
            self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "native_context", field)
        else:
            typ = v8.HeapObject(field).instance_type
            if v8.InstanceType.isMap(typ):
                #self.TagObject(field, "(back pointer)")
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "back_pointer", field)

            elif v8.InstanceType.isFunctionTemplateInfo(typ):
                #self.TagObject(field, "(constructor function data)")
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "constructor_function_data", field)

            else:
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "constructor", field)

        # dependent_code
        field = v8.HeapObject(m.dependent_code)
        #self.TagObject(field, "(dependent_code")
        self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "dependent_code", field)

    def ExtractReferencesDescriptorArray(self, parent_entry, obj):
        o = v8.DescriptorArray(obj.address)
        self.SetReferenceValue(HeapGraphEdge.kInternal, parent_entry, "enum_cache", v8.HeapObject(o.enum_cache))
        cnt = o.number_of_descriptors
        for i in range(cnt):
            p = v8.HeapObject(o.GetKey(i))
            #print("DescriptorArray[%d]: %s"%(i, p))
            if p.IsWeak():
                self.SetReferenceObject(HeapGraphEdge.kWeak, parent_entry, "%d" % i, p)
            else:
                self.SetReferenceObject(HeapGraphEdge.kInternal, parent_entry, "%d" % i, p)

    def ExtractReferencesWeakArray(self, entry, obj):
        o = v8.WeakFixedArray(obj.address)
        length = o.length
        for i in range(length):
            p = v8.HeapObject(o.Get(i))
            #print("WeakArray[%d]: %s"%(i, p))
            if p.IsWeak():
                self.SetReferenceObject(HeapGraphEdge.kWeak, entry, i, p)
            else:
                self.SetReferenceObject(HeapGraphEdge.kInternal, entry, i, p)

    def ExtractReferencesString(self, entry, obj):
        o = v8.String(obj)
        if o.IsConsString():
            p = v8.ConsString(obj.address)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "first", p.first)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "second", p.second)
        elif o.IsSlicedString():
            p = v8.SlicedString(obj.address)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "parent", p.parent)
        elif o.IsThinString():
            p = v8.ThinString(obj.address)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "actual", p.actual)

    def ExtractReferencesFixedArray(self, entry, obj):
        o = v8.FixedArray(obj.address)
        length = o.length
        for i in range(length):
            tag = o.Get(i)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "%d" % i, v8.HeapObject(tag))

    def ExtractReferencesPropertyCell(self, entry, obj):
        o = v8.PropertyCell(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "value", v8.HeapObject(o.raw_value))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "dependent_code", v8.HeapObject(o.dependent_code))

    def ExtractReferencesSymbol(self, entry, obj):
        o = v8.Symbol(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "name", v8.HeapObject(o.description))

    def ExtractReferencesCode(self, entry, obj):
        o = v8.Code(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "relocation_info", v8.HeapObject(o.relocation_info))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "deoptimization_data", v8.HeapObject(o.deoptimization_data))
        if o.source_position_table is not None:
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "source_position_table", v8.HeapObject(o.source_position_table))

    def ExtractReferencesCell(self, entry, obj):
        o = v8.Cell(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "value", v8.HeapObject(o.value))

    def ExtractReferencesFeedbackCell(self, entry, obj):
        o = v8.FeedbackCell(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "value", v8.HeapObject(o.value))

    def ExtractReferencesFeedbackVector(self, entry, obj):
        o = v8.FeedbackVector(obj.address)
        if o.IsWeak():
            code = v8.HeapObject(o.maybe_optimized_code)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "optimized code", code)

    def ExtractReferencesPropertyCell(self, entry, obj):
        o = v8.PropertyCell(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "value", v8.HeapObject(o.value))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "dependent_code", v8.HeapObject(o.dependent_code))

    def ExtractReferencesScript(self, entry, obj):
        o = v8.Script(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "source", v8.HeapObject(o.source))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "name", v8.HeapObject(o.name))

        context_data = v8.HeapObject(o.context_data)
        if context_data.IsHeapObject():
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "context_data", context_data)

        line_ends = v8.HeapObject(o.line_ends)
        if line_ends.IsHeapObject():
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "line_ends", line_ends)

    def ExtractReferncesContext(self, entry, obj):
        context = v8.Context(obj.address)
        instance_type = context.map.instance_type

        scope_info = v8.ScopeInfo(context.scope_info)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "scope_info", scope_info)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "previous", v8.HeapObject(context.previous))

        if context.IsNativeContext():
            native_context = v8.NativeContext(obj.address)
            for name, value in native_context.WalkAllSlots():
                self.SetReferenceObject(HeapGraphEdge.kInternal, entry, name, v8.HeapObject(value))
        else:
            for local_name, value in context.WalkAllSlots():
                local = v8.HeapObject(value)
                if local.IsHeapObject():
                    self.SetReferenceObject(HeapGraphEdge.kContextVariable, entry, local_name, local)

            #func_name = scope_info.FunctionName()
            #if func_name is not None:
            #    self.SetReferenceObject(HeapGraphEdge.kContextVariable, entry, local_name, value)

    def ExtractAccessorPairProperty(self, parent_entry, name, obj):
        o = v8.AccessorPair(obj)
        setter = v8.HeapObject(o.setter)
        if not setter.IsOddball():
            self.SetReferenceObject(HeapGraphEdge.kProperty, parent_entry, "set %s" % name, setter)

        getter = v8.HeapObject(o.getter)
        if not getter.IsOddball():
            self.SetReferenceObject(HeapGraphEdge.kProperty, parent_entry, "get %s" % name, getter)

    def ExtractReferencesJSObject(self, entry, obj):
        o = v8.JSObject(obj.address)

        # extract properties
        for (k,d,v) in o.WalkAllProperties():
            # v10 don't has the location in slow properties.
            #if d.location == v8.PropertyLocation.kField:
                if d.IsDouble():
                    continue

                child = v8.HeapObject(v)
                if child.IsHeapObject():
                    if child.IsAccessorPair():
                        self.ExtractAccessorPairProperty(entry, k, child);
                    self.SetReferenceObject(HeapGraphEdge.kProperty, entry, k, child)

        # extract elements
        if not o.elements_array.IsByteArray() and not o.elements_array.IsFixedDoubleArray():
            for (i,v) in o.WalkAllElements():
                child = v8.HeapObject(v)
                if child.IsHeapObject():
                    self.SetReferenceElement(HeapGraphEdge.kElement, entry, i, child)

        # __proto__ 
        proto = v8.HeapObject(o.GetPrototype())
        self.SetReferenceObject(HeapGraphEdge.kProperty, entry, "__proto__", proto)

        if o.IsJSBoundFunction():
            bound_fun = v8.JSBoundFunction(obj.address) 
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "bindings", v8.HeapObject(bound_fun.bound_arguments))
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "bound_this", v8.HeapObject(bound_fun.bound_this))
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "bound_function", v8.HeapObject(bound_fun.bound_target_function))
            
            args = bound_fun.bound_arguments
            if args.IsFixedArray():
                for i in range(args.length):
                    v = v8.HeapObject(args.Get(i))
                    self.SetReferenceObject(HeapGraphEdge.kShortcut, entry, "bound_argument_%d" % i, v)

        elif o.IsJSFunction():
            js_fun = v8.JSFunction(obj.address)
            shared_info = js_fun.shared_function_info
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "feedback_cell", v8.HeapObject(js_fun.feedback_cell))
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "shared", shared_info)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "context", js_fun.context)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "code", js_fun.code)

            if js_fun.prototype_or_initial_map is not None:
                proto_or_map = v8.HeapObject(js_fun.prototype_or_initial_map)
                if not proto_or_map.IsTheHole():
                    if proto_or_map.IsMap():
                        self.SetReferenceObject(HeapGraphEdge.kProperty, entry, "prototype", v8.HeapObject(js_fun.prototype))
                        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "initial_map", proto_or_map)
                    else:
                        self.SetReferenceObject(HeapGraphEdge.kProperty, entry, "prototype", proto_or_map)

        elif o.IsJSGlobalObject():
            glob = v8.JSGlobalObject(obj.address)
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "native_context", v8.HeapObject(glob.native_context))
            self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "global_proxy", v8.HeapObject(glob.global_proxy))

        # maybe hash
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, 'properties', v8.HeapObject(o.raw_properties))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, 'elements', v8.HeapObject(o.raw_elements))

    def ExtractReferencesSharedFunctionInfo(self, entry, obj):
        o = v8.SharedFunctionInfo(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "name_or_scope_info", v8.HeapObject(o.name_or_scope_info))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "script_or_debug_info", v8.HeapObject(o.script_or_debug_info))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "function_data", v8.HeapObject(o.function_data))
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "raw_outer_scope_info_or_feedback_metadata", v8.HeapObject(o.outer_scope_info_or_feedback_metadata))

    def ExtractReferencesJSGlobalProxy(self, entry, obj):
        o = v8.JSGlobalProxy(obj.address)
        self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "native_context", v8.HeapObject(o.native_context))

    def ExtractReferences(self, entry, obj):
        #log.debug("ExtractReferences : 0x%x"% (obj.address))

        typ = obj.instance_type
        #print("<0x%x> %s" % (obj, v8.InstanceType(typ).name))

        """ only for debugging
        """
        if v8.InstanceType.isJSGlobalProxy(typ):
            self.ExtractReferencesJSGlobalProxy(entry, obj)

        # TBD: JSArrayBuffer

        elif v8.InstanceType.isJSObject(typ):
            # TBD: JSWeakSet, JSSet, JSMap, JSPromise, JSGeneratorObject
            self.ExtractReferencesJSObject(entry, obj)
        
        elif v8.InstanceType.isString(typ):
            self.ExtractReferencesString(entry, obj)

        elif v8.InstanceType.isSymbol(typ):
            self.ExtractReferencesSymbol(entry, obj)
        
        elif v8.InstanceType.isMap(typ):
            self.ExtractReferencesMap(entry, obj)

        elif v8.InstanceType.isSharedFunctionInfo(typ):
            self.ExtractReferencesSharedFunctionInfo(entry, obj)

        elif v8.InstanceType.isScript(typ):
            self.ExtractReferencesScript(entry, obj)

        elif v8.InstanceType.isAccessorInfo(typ):
            self.ExtractReferencesAccessorInfo(entry, obj)

        elif v8.InstanceType.isAccessorPair(typ):
            self.ExtractReferencesAccessorPair(entry, obj)

        elif v8.InstanceType.isCode(typ):
            self.ExtractReferencesCode(entry, obj)

        elif v8.InstanceType.isCell(typ):
            self.ExtractReferencesCell(entry, obj)

        # TBD: FeedbackCell

        elif v8.InstanceType.isPropertyCell(typ):
            self.ExtractReferencesPropertyCell(entry, obj)

        # TBD: AllocationSite

        elif v8.InstanceType.isFeedbackVector(typ):
            self.ExtractReferencesFeedbackVector(entry, obj)

        elif v8.InstanceType.isDescriptorArray(typ):
            self.ExtractReferencesDescriptorArray(entry, obj)

        # TBD: WeakFixedArray

        # TBD: WeakArrayList

        elif v8.InstanceType.isContext(typ):
            self.ExtractReferncesContext(entry, obj)

        # TBD: EphemronHashTable

        # TBD: FixedArray
        elif v8.InstanceType.isFixedArray(typ):
            self.ExtractReferencesFixedArray(entry, obj)

    def ExtractLocation(self, entry, obj):
        if obj.IsJSFunction():
            js_fun = v8.JSFunction(obj.address) 
            script = js_fun.shared_function_info.script
            if script is None:
                return

            script_id = int(script.id)
            self.AddLocation(entry, script_id, 0, 0)

        # TBD: JSObject Constructor


class HeapSnapshot(GraphHolder):

    def __init__(self):
       
        super(HeapSnapshot, self).__init__()

        #self._size = 0
        #self._cnt = 0

        # uniq next ObjectId
        #self._next_id = 0

        # root_entry is the root entry for any object
        self.root_entry_ = None

        # gc_roots_entry is the root entry for all GC Subroots
        self.gc_roots_entry_ = None

        # each GC_Root has a entry for children (root to entry) 
        self.gc_subroot_entries_ = [] 

        """ core data storage
        """
        # holds all objects
        #self.entries_ = []

        # holds all edges
        #self.edges_ = []

        # holds the location info
        #self.locations_ = []

        # holds all names the snapshot has 
        self.names_ = {}

        """ caches 
        """
        # all edges belongs to HeapEntry, flat list
        self.children_ = []

        # map for HeapObject adddress to HeapEntry (ptr to entry)
        #self.entries_map_ = {}

        # map for Root address to Root Name (ptr to string)
        self.strong_gc_subroot_names_ = {} 

        # user roots
        self.user_roots_ = {}

        """ counter
        """
        self._progress_counter = ProgressCounter(self)

        #self._lock = threading.Lock()

    def root(self):
        return self.root_entry_

    def gc_roots(self):
        return self.gc_roots_entry_

    def gc_subroot(self, index):
        """ return the GC_ROOT by index """
        return self.gc_subroot_entries_[index]

    def heap(self):
        """ return the Heap object(py) """
        return self._isolate.Heap()
    
    def initRootNames(self):
        """ init the root name table """
        root_index = self._isolate.Roots()
        for i in range(v8.RootIndex.kFirstStrongOrReadOnlyRoot, v8.RootIndex.kLastStrongOrReadOnlyRoot):
            ptr = int(root_index.root(i))
            name = root_index.Name(i)
            log.debug("[%d] <0x%x> %s" % (i, ptr, name))
            self.strong_gc_subroot_names_[ptr] = name

    def RootName(self, addr):
        """ return root name of the addr if it was """
        if addr in self.strong_gc_subroot_names_:
            return self.strong_gc_subroot_names_[addr]
        return None
    
    def AddSyntheticRootEntries(self):
        """ Add all Synthetic Root Entries 
            
            Synthetic roots don't have a entry for (address, entry) map, 
            uses the '_addEntry' instead.
        """
        self._next_id = 1
        # root entry, root entry id(1) and has a blank name.
        self.root_entry_ = self._AddEntry(HeapEntry.kSynthetic, "", 0, 0)
        assert len(self.entries_) == 1

        # put (GC roots), id(2)
        self.gc_roots_entry_ = self._AddEntry(HeapEntry.kSynthetic, "(GC roots)", 0, 0)

        # all gc roots
        self.gc_subroot_entries_ = list(range(v8.Root.kNumberOfRoots))
        for i in range(v8.Root.kNumberOfRoots):
            name = v8.RootVisitor.RootName(i)
            x = self._AddEntry(HeapEntry.kSynthetic, name, 0, 0)
            self.gc_subroot_entries_[i] = x
            #print("[%d] %s"%(i, name), self.gc_subroot_entries_[i])
        #raise Exception

        # root_entry -- Element --> gc_root_entry
        self.root().SetIndexedAutoIndexReference(self, HeapGraphEdge.kElement, self.gc_roots())
       
        # gc_root -- Element --> gc_subroot(i)
        for i in range(v8.Root.kNumberOfRoots):
            self.gc_roots().SetIndexedAutoIndexReference(self, HeapGraphEdge.kElement, self.gc_subroot(i)) 

        # a memory entry for object address
        self.mem_entry_ = self._AddEntry(HeapEntry.kSynthetic, "(Tagged Pointer)", 0, 0)

    def SetGcSubrootReference(self, root, desc, is_weak, child_obj):
        """ puts child_obj to subroot(root)'s reference """
        child_entry = self.GetEntryOrLazy(child_obj)
        if child_entry is None:
            return
        # TBD: is_weak
        name = self.RootName(child_obj.tag)
        if name is None:
            self.gc_subroot(root).SetNamedAutoIndexReference(self, HeapGraphEdge.kInternal, desc, child_entry)
        else:
            self.gc_subroot(root).SetNamedReference(self, HeapGraphEdge.kInternal, name, child_entry)

        # treat global objects as user roots
        if is_weak or not child_obj.IsNativeContext():
            return

        native_context = v8.NativeContext(child_obj)
        js_global = native_context.GetJSGlobalObject()
        if not js_global.IsJSGlobalObject():
            return
        
        ptr = child_obj.address
        if ptr not in self.user_roots_:
            self.user_roots_[ptr] = 1
            child_entry = self.GetEntryOrLazy(js_global)
            self.root().SetNamedAutoIndexReference(self, HeapGraphEdge.kShortcut, "", child_entry)

    def IterateRoots(self):

        class RootReferencesExtractor(v8.RootVisitor):
            """ Visitor for walk all roots """
        
            # 
            _saved_root = 0
            _visiting_weak_roots = 0

            def __init__(self, snap):
                self._snapshot = snap

            def SetVisitingWeakRoots(self):
                self._visiting_weak_roots = 1

            def VisitRootPointer(self, root, desc, p):
                self.VisitRootPointerImpl(root, desc, p)
                #try:
                #    self.VisitRootPointerImpl(root, desc, p)
                #except Exception as e:
                #    raise Exception("Exception '%s' ocured during Visit <0x%x>" % (str(e), p))

            def VisitRootPointerImpl(self, root, desc, p):
                # debugging purpose
                if self._saved_root != root:
                    log.debug("  Begin.%s: (%u, %u)" % (v8.Root.CamelName(root), len(self._snapshot.entries_), len(self._snapshot.edges_)))
                    self._saved_root = root
                
                # not a heapobject 
                obj = v8.HeapObject(p)
                if not obj.IsHeapObject():
                    return

                # tag Object
                #if root == v8.Root.kBuiltins:
                #    assert v8.InstanceType.isCode(obj.instance_type)
                #    self._snapshot.TagObject(p, "(%s builtin)" % str(desc))

                # set to GC subroot reference
                self._snapshot.SetGcSubrootReference(root, desc, self._visiting_weak_roots, v8.HeapObject(p))


        heap = self.heap()
        # private visitor
        v = RootReferencesExtractor(self)
        #v = v8.viewRootVisitor()

        # 1. ReadOnly Roots
        heap.IterateReadOnlyRoots(v, None)
        log.debug("After.IterateReadOnlyRoots = (%u, %u)" % (len(self.entries_), len(self.edges_)))

        # 2. Roots
        heap.IterateRoots(v, None)
        log.debug("After.IterateRoots = (%u, %u)" % (len(self.entries_), len(self.edges_)))

        # 3. WeakRoots
        #TBD

        # 4. WeakGlobalHandle
        #TBD

    def ParseObject(self, obj, parser):
        # obj: HeapObject

        # tick the progress counter
        #self._progress_counter.Tick(obj.Size()) 

        # skip FreeSpace object
        if v8.InstanceType.isFreeSpace(obj.instance_type) and \
            cfg.cfgHeapSnapshotShowFreeSapce == 0:
            return

        # get the HeapEntry
        #entry = self.GetEntry(obj)
        
        # extract reference
        #self.ExtractReferences(entry, obj)

        # reference to map
        #self.SetReferenceObject(HeapGraphEdge.kInternal, entry, "map", obj.map)

        # show Tagged Pointer in heapsnapshot 
        #entry.SetNamedReference(HeapGraphEdge.kInternal, "0x%x" % obj, self.mem_entry_)

        # Extrace Location
        #self.ExtractLocation(entry, obj)

        # Parser holds the node and edges. 
        #parser = ObjectParser()

        # Extract info from object
        parser.ExtractObject(obj)
        
        # write back to snapshot
        #self.Merge(parser)

    def ParsePage(self, page):
        parser = ObjectParser()
        cnt = 0
        failed = []
        
        for obj in page.walk():
            cnt = cnt + 1

            # skip free space
            if v8.InstanceType.isFreeSpace(obj.instance_type) and \
                cfg.cfgHeapSnapshotShowFreeSapce == 0:
                continue

            # debug only, don't check in.
            #parser.ExtractObject(obj)
            #continue

            try:
                parser.ExtractObject(obj)
            except Exception as e:
                log.error("Parse <0x%x> failed: %s" % (obj, e))
                failed.append(obj)

        self.Merge(parser)
        return (cnt, failed,)

    def Merge(self, parser):

        #print("entries: %d, keys(%d), edges: %d, location: %d" % (len(parser.entries_), len(parser.entries_map_.keys()), len(parser.edges_), len(parser.locations_))) 

        """
        Linkup, Link all entries of parser and snapshot by memory address,
        cases,
        | in parser | in snapshot | action |
        | HeapEntry |        None | move HeapEntry link to snapshot |
        | HeapEntry |   LazyEntry | link snapshot's LazyEntry link to parser's |
        | LazyEntry |        None | move LazyEntry link to snapshot |
        | LazyEntry |   LazyEntry | link snapshot's lazyEntry to parser's |
        """
        for p,n in parser.entries_map_.items():

            # parser has HeapEntry
            parser_last_entry = n.GetLastEntry()

            # address in snapshot
            snap_entry = self.FindMapEntry(p)
            
            # 1. not found, add HeapEntry
            if snap_entry is None:
                self.entries_map_[p] = parser_last_entry
                continue 

            snap_last_entry = snap_entry.GetLastEntry()

            # 2. parser has HeapEntry 
            if isinstance(parser_last_entry, HeapEntry):
                assert snap_last_entry.real_entry_ is None, print("0x%x"%p, snap_last_entry)
                snap_last_entry.real_entry_ = parser_last_entry
            
            # 3. Snapshot has HeapEntry
            elif isinstance(snap_last_entry, HeapEntry):
                assert parser_last_entry.real_entry_ is None, print("0x%x"%p, parser_last_entry)
                parser_last_entry.real_entry_ = snap_last_entry
            
            # 4. link parser LazyEntry to snapshot's
            else:
                assert parser_last_entry.real_entry_ is None
                assert isinstance(snap_entry, LazyEntry)
                parser_last_entry.real_entry_ = snap_entry

        # Move entries,
        # entries_ holds all the HeapEntry 
        for n in parser.entries_:
            # update id
            n.index_ = len(self.entries_) 
            n.id_ = self.id
            self.entries_.append(n)

        # Move edges,
        # entries_map[addr]
        #   \ LazyEntry -> None
        #   \ LazyEntry -> HeapEntry 
        for n in parser.edges_:
            #print(n.to_entry_, n.from_entry_)
            
            assert isinstance(n.from_entry_, HeapEntry)
            if isinstance(n.to_entry_, LazyEntry):
                last_entry = n.to_entry_.GetLastEntry()
                n.to_entry_ = last_entry
            self.edges_.append(n)

    def IterateROHeapObjects(self):
        cnt = 0
        ro_heap = self._isolate.ReadOnlyHeap()
        failed = []
        parser = ObjectParser()
        for obj in v8.ReadOnlyHeapObjectIterator(ro_heap):
            self.ParseObject(obj, parser)
            cnt += 1
        self.Merge(parser)

        print("Iterated %d RO Heap Objects" % (cnt))
        print("failed RO Heap Object: %d" % (len(failed)))
        for i in failed:
            m = i.map
            print("0x%x : Map(0x%x), Type(%s)" % (i.tag, m.address, v8.InstanceType.Name(m.instance_type)))

    def IterateHeapObjects(self):
        from time import time
        heap = self.heap()
        spaces = v8.AllocationSpace.OnlyOldSpaces()
        total = 0
        failed = []
        
        t1 = time()
        for name in spaces:
            space = heap.getSpace(name)
            chunks = space.getChunks()
            len_chunks = len(chunks)
            print("%s : %d pages" % (space.name, len(chunks)))
            for i in range(len_chunks):
                c = chunks[i]
                cnt, fail = self.ParsePage(c)

                total = total + cnt
                if len(fail) > 0:
                    failed.extend(fail)

                t2 = time()
                print("%d/%d 0x%012x: Entry(%d), Edge(%d), Time(%.3fs), Obj(%d)" % 
                        (i, len_chunks, c.address, len(self.entries_), len(self.edges_), t2-t1, cnt))
                t1 = t2 

        print("Iterated %d Objects" % (total))
        print("failed HeapObject: %d" % (len(failed)))
        for i in failed:
            m = i.map
            print("0x%x : Map(0x%x), Type(%s)" % (i.tag, m.address, v8.InstanceType.Name(m.instance_type)))

    def IterateHeapObjects2(self):
        cnt = 0
        failed = []
        heap = self.heap()
        for obj in v8.HeapObjectIterator(heap):
            if cfg.cfgObjectDecodeFailedAction == 0:
                self.ParseObject(obj)
            else:
                try:
                    self.ParseObject(obj)
                except Exception as e:
                    log.error("Parse <0x%x> failed: %s" % (obj, e))
                    failed.append(obj)
            cnt += 1

        print("Iterated %d Objects" % (cnt))
        print("failed HeapObject: %d" % (len(failed)))
        for i in failed:
            m = i.map
            print("0x%x : Map(0x%x), Type(%s)" % (i.tag, m.address, v8.InstanceType.Name(m.instance_type)))

    def ResolveEdges(self):

        cnt=0
        failed=0
        print("Resolve all edges ...")
        for p,v in self.entries_map_.items():
            last = v.GetLastEntry()
            if isinstance(last, LazyEntry):
                #print("0x%x" % p)
                ho = v8.HeapObject.FromAddress(p)
                try:
                    entry = self.GetHeapEntry(ho)
                    cnt = cnt + 1
                except Exception as e:
                    print("Parsing failed %x" % p, e)
                    entry = self.AddDummyEntry(ho)
                    failed = failed + 1
        print("Done, resolved %d, failed %d." % (cnt, failed))

        def ResolveEntry(entry):
            if isinstance(entry, HeapEntry):
                return entry

            last = entry.GetLastEntry()
            assert last is not None
            assert isinstance(last, HeapEntry), print(last)
            return last

        for e in self.edges_:
            e.from_entry_ = ResolveEntry(e.from_entry_)
            #assert isinstance(e.from_entry_, HeapEntry), print(e) 
            e.to_entry_ = ResolveEntry(e.to_entry_)
            #assert isinstance(e.to_entry_, HeapEntry), print(e)

        print("Total Entry(%d), Edge(%d)" % (len(self.entries_), len(self.edges_)))

    def FillChild(self):

        acuminate_index = 0
        for node in self.entries_:
            acuminate_index = node.set_children_index(acuminate_index) 

        # enlarge the children size to edges 
        self.children_ = []
        for i in range(len(self.edges_)):
            self.children_.append(None)

        # add_child
        for edge in self.edges_:
            entry = edge.from_entry
            self.children_[entry.children_end_count_] = edge 
            entry.children_end_count_ += 1

        log.debug("child_cnt: %d, edges_cnt: %d" % (len(self.children_), len(self.edges_)))
        if len(self.children_) != len(self.edges_):
            raise Exception

        # check all the chilren was filled.
        bad_list = []
        for i in range(len(self.children_)):
            if self.children_[i] is None:
                bad_list.append(i)
        assert len(bad_list) == 0, bad_list

    def NameIndex(self, name_string):
        name = name_string
        
        # cut string
        if cfg.cfgHeapSnapshotMaxStringLength > 0 and \
            len(name) > cfg.cfgHeapSnapshotMaxStringLength:
            name = name[:cfg.cfgHeapSnapshotMaxStringLength] + '...'

        # heap snapshot string uses arrays start from 1.
        next_index = len(self.names_) + 1
        if name in self.names_:
            # if exists
            return self.names_[name] 
        self.names_[name] = next_index
        return next_index 

    def CleanAll(self):
        self.root_entry_ = None
        self.gc_roots_entry_ = None
        del self.gc_subroot_entries_[:]
        self.names_.clear()
        del self.children_[:]
        self.strong_gc_subroot_names_.clear()

        #del self.entries_[:]
        #del self.edges_[:]
        #del self.locations_[:]
        #self.entries_map_.clear()
 
        # super clean
        super(HeapSnapshot, self).CleanAll()

    def SerializeNodes(self):
        ay = []
        for n in self.entries_:
            #n.DebugPrint()
            ay += [ n.type_, 
                    self.NameIndex(n.name_),
                    n.id_,
                    n.self_size_,
                    n.children_count_,
                    n.mem_addr_,
                    ]
        return ay 

    def SerializeEdges(self):
        ay = []
        for n in self.children_:
            #n.DebugPrint() 
            if isinstance(n.index_or_name_, int):
                index = int(n.index_or_name_)
                assert n.type_ == HeapGraphEdge.kElement or n.type_ == HeapGraphEdge.kHidden
            else:
                index = self.NameIndex(n.index_or_name_)

            # edge needs multiple to sizeof(node_fields)
            ay += [ n.type_,
                    int(index),
                    int(n.to_entry.index_) * 7
                  ]
        return ay

    def SerializeLocations(self):
        ay = []
        for n in self.locations_:
            ay += [ n._entry.index_,
                    int(n._id),
                    int(n._line),
                    int(n._col)]
        return ay

    def SerializeNames(self):
        def noNewLine(s):
            return s.replace('\r', '').replace('\n', '')
        ay = ["<dummy>"]
        for s in sorted(self.names_.items(), key = lambda k: k[1]):
            ay.append(noNewLine(s[0]))
        return ay

    def serializer(self, filename):
        an = self.SerializeNodes()
        ae = self.SerializeEdges()
        ay = self.SerializeNames()
        al = self.SerializeLocations()

        #nodes = json.dumps(an)
        nodes = '['
        for i in range(0, len(an), 6):
            if i == 0:
                nodes += "%d,%d,%d,%d,%d,0,%d\n" % (an[i], an[i+1], an[i+2], an[i+3], an[i+4], an[i+5])
            else:
                nodes += ",%d,%d,%d,%d,%d,0,%d\n" % (an[i], an[i+1], an[i+2], an[i+3], an[i+4], an[i+5])
        nodes += ']'

        #edges = json.dumps(ae)
        edges = '['
        for i in range(0, len(ae), 3):
            if i == 0:
                edges += "%d,%d,%d\n" % (ae[i], ae[i+1], ae[i+2])
            else:
                edges += ",%d,%d,%d\n" % (ae[i], ae[i+1], ae[i+2])
        edges += ']'

        # locations
        locations = '['
        for i in range(0, len(al), 4):
            if i == 0:
                locations += "%d,%d,%d,%d\n" % (al[i], al[i+1], al[i+2], al[i+3])
            else:
                locations += ",%d,%d,%d,%d\n" % (al[i], al[i+1], al[i+2], al[i+3])
        locations += ']'

        # one string one line
        names = json.dumps(ay, indent=0, separators=(',', ':'))

        meta = '''{"node_fields":["type","name","id","self_size","edge_count","trace_node_id","mem_addr"],
"node_types":[["hidden","array","string","object","code","closure","regexp","number","native","synthetic","concatenated string","sliced string","symbol","bigint"],"string","number","number","number","number","number"],
"edge_fields":["type","name_or_index","to_node"],
"edge_types":[["context","element","property","internal","hidden","shortcut","weak"],"string_or_number","node"],
"trace_function_info_fields":["function_id","name","script_name","script_id","line","column"],
"trace_node_fields":["id","function_info_index","count","size","children"],
"sample_fields":["timestamp_us","last_assigned_id"],
"location_fields":["object_index","script_id","line","column"]}'''

        j = '''{"snapshot":{
"title":"andb",
"uid":1,
"meta":%s,
"node_count":%d,
"edge_count":%d,
"trace_function_count":0
},
"nodes":%s,
"edges":%s,
"trace_function_infos":[],
"trace_tree":[],
"samples":[],
"locations":%s,
"strings":%s
}''' % (
            meta,
            len(self.entries_),
            len(self.children_),
            nodes,
            edges,
            locations,
            names
        )
 
        # write 
        with open(filename, 'w') as f:
            f.write(j)
        print("heap snapshot written to '%s'"%filename)

    @profiler
    def Generate(self, filename="core.heapsnapshot"):
        # init helpers
        self.initRootNames()

        # add all Synthetic entries
        self.AddSyntheticRootEntries()
       
        # iterate roots 
        self.IterateRoots()

        # iterate Readonly Heap Objects
        self.IterateROHeapObjects()

        # iterate all Heap Objets
        self.IterateHeapObjects()

        # resolve all edges
        self.ResolveEdges()

        # Fill the child
        self.FillChild()

        # output json
        self.serializer(filename)

        # clean 
        self.CleanAll()

    def MapWriteIndex(self, eachsize=100):
        heap = self.heap()
        spaces = v8.AllocationSpace.OnlyOldSpaces()
        assert eachsize > 10

        if not os.path.exists("snapshot.d"):
            os.mkdir("snapshot.d") 

        pages = []
        cnt = 0
        page_cnt = 0

        def WriteIndexFile(idx):
            with open("snapshot.d/snapshot_%d.map" % (idx), 'wb') as f:
                pickle.dump(pages, f, pickle.HIGHEST_PROTOCOL)

        for name in spaces:
            space = heap.getSpace(name)
            print(space.name)
            chunks = space.getChunks()
            for i in chunks:
                pages.append(i.address)

                if len(pages) >= eachsize:
                    # write to index 
                    WriteIndexFile(page_cnt)
                    page_cnt = page_cnt + 1
                    pages = []

                cnt = cnt + 1
        
        WriteIndexFile(page_cnt)
        page_cnt = page_cnt + 1
        pages = []

        print("Total %d pages in %d maps." % (cnt, page_cnt))

    @profiler
    def MapSnapshot(self, index):
      
        with open("snapshot.d/snapshot_%d.map" % index, 'rb') as f:            
            pages = pickle.load(f)

        parser = ObjectParser()
        cnt = 0
        for p in pages:
            page = v8.MemoryChunk(p)
            cnt = cnt + 1
            print("map_%d (%d/%d) page(0x%x)" % (index, cnt, len(pages), int(page)))
            for obj in page.walk():
                # skip free space
                if v8.InstanceType.isFreeSpace(obj.instance_type) and \
                    cfg.cfgHeapSnapshotShowFreeSapce == 0:
                    continue

                try:
                    parser.ExtractObject(obj)
                except Exception as e:
                    log.error("Parse <0x%x> failed: %s" % (obj, e))

        print("entries: %d, keys(%d), edges: %d, location: %d" % (len(parser.entries_), len(parser.entries_map_.keys()), len(parser.edges_), len(parser.locations_))) 

        parser.SaveFile("snapshot.d/snapshot_%d.rec.tmp" % index)
        os.rename("snapshot.d/snapshot_%d.rec.tmp" % index, "snapshot.d/snapshot_%d.rec" % index) 

    @profiler
    def ReduceGenerate(self, filename="core.heapsnapshot"):
        # init helpers
        self.initRootNames()

        # add all Synthetic entries
        self.AddSyntheticRootEntries()
       
        # iterate roots 
        self.IterateRoots()

        # iterate Readonly Heap Objects
        self.IterateROHeapObjects()

        # reduce
        rec_files = [] 
        for f in os.listdir("snapshot.d"):
            if f.endswith(".map"):
                rec = f[:-4] + ".rec"
                rec_files.append("snapshot.d/%s" % rec)
        print("Polling %d files ..." % (len(rec_files)))

        len_files = len(rec_files)
        while len(rec_files) > 0:
            print("reduce (%d/%d)" % (len_files - len(rec_files), len_files))

            is_idle = 1
            for f in rec_files:
                if os.path.exists(f):
                    print("Merging %s" % f)

                    # merge
                    parser = ObjectParser()
                    parser.LoadFile(f)
                    self.Merge(parser)
                    parser.CleanAll()
                    
                    rec_files.remove(f)
                    is_idle = 0

            # delay
            if is_idle:
                time.sleep(5)

        print("Polling done.")

        # resolve all edges
        self.ResolveEdges()

        # Fill the child
        self.FillChild()

        # output json
        self.serializer(filename)

        # clean 
        self.CleanAll()
        

