# -*- coding: UTF-8 -*-
from __future__ import print_function, division

""" v8 engine support
"""
from .internal import Version, Internal, Struct, ObjectSlot, Enum, ChunkBlock
from andb.utility import CachedProperty, Logging as log
from itertools import chain
import andb.stl as stl

""" v8 c++ class/structure
"""
class Bootstrapper(Struct):
    _typeName = 'v8::internal::Bootstrapper'

    @CachedProperty
    def extensions_cache(self):
        return SourceCodeCache(self['extensions_cache_'].AddressOf())

    def Iterate(self, v):
        ext_cache = self.extensions_cache
        ext_cache.Iterate(v)

class Builtins(Struct):
    _typeName = 'v8::internal::Builtins'

    _constList = [
        {"name": "builtin_count", "alias": ['kBuiltinCount']},
    ]

    @classmethod
    def Count(cls):
        return cls.builtin_count
   
    def GetName(self, index):
        v = BuiltinsName.CamelName(index)
        return v

    def Address(self, index):
        iso = self.parent
        tbl = iso['isolate_data_']['builtins_']
        return tbl[index].AddressOf()

    def Iterate(self, v):
        for i in range(self.Count()):
            v.VisitRootPointer(Root.kBuiltins, self.GetName(i), ObjectSlot(self.Address(i)))


class CompilationCache(Struct):
    _typeName = "v8::internal::CompilationCache"

    kSubCacheCount = 4

    def Iterate(self, v):
        for i in range(self.kSubCacheCount):
            s = CompilationSubCache(self['subcaches_'][i], self)
            s.Iterate(v)


class CompilationSubCache(Struct):
    _typeName = "v8::internal::CompilationSubCache"

    @property
    def generations(self):
        return int(self['generations_'])

    def Iterate(self, v):
        # t = gdb.lookup_type('v8::internal::Object').pointer()
        # tbl = self['tables_'].cast(t)
        tbl = self['tables_']
        a = tbl[0].address
        b = tbl[self.generations].address
        v.VisitRootPointers(Root.kCompilationCache, None, a, b)


class Internals(Struct):
    _typeName = 'v8::internal::Internals'

    kUndefinedValueRootIndex = 4
    kTheHoleValueRootIndex = 5
    kNullValueRootIndex = 6

class Isolate(Struct):
    """ represent Isolate structure in v8 """
    _typeName = "v8::internal::Isolate"

    # holds the global isolate (pyobject)
    _current_isolate = None

    def IsValid(self):
        try:
            p = self['heap_']['isolate_']
            return Struct.Equal(self.Value(), p)
        except:
            # print(err)
            return False

    @classmethod
    def SetCurrent(cls, pyo):
        cls._current_isolate = pyo

    @classmethod
    def GetCurrent(cls):
        return cls._current_isolate
   
    def MakeChunkCache(self):
        heap = self.Heap()
        spaces = AllocationSpace.AllSpaces() 
        print("Make ChunkCache ...")
        for name in spaces:
            space = heap.getSpace(name)
            chunks = space.getChunks()
            for i in chunks:
                try:
                    ChunkBlock.AddChunk(i)
                except Exception as e:
                    print('AddChunk %x failed, %s' % (i, e))
        print("Done ChunkCache, %d chunks cached." % ChunkBlock.CacheSize())

    def Heap(self):
        return Heap(self['heap_'].AddressOf(), self)

    def ReadOnlyHeap(self):
        return ReadOnlyHeap(self['read_only_heap_'], self)

    @CachedProperty
    def _roots_table(self):
        v = self['isolate_data_']['roots_'].AddressOf()
        return RootsTable(v, self)

    def Roots(self):
        return self._roots_table

    def GlobalHandles(self):
        return GlobalHandles(self['global_handles_'], self)

    def EternalHandles(self):
        return EternalHandles(self['eternal_handles_'], self)

    def CompilationCache(self):
        return CompilationCache(self['compilation_cache_'], self)

    def Builtins(self):
        return Builtins(self['builtins_'], self)

    def HandleScopeImplementer(self):
        return HandleScopeImplementer(self['handle_scope_implementer_'], self)
    
    def HandleScopeData(self):
        return HandleScopeData(self['handle_scope_data_'], self)

    @property
    def thread_local_top_(self):
        return self['isolate_data_']['thread_local_top_']

    @property
    def external_memory_(self):
        return int(self['isolate_data_']['external_memory_'])

    @property
    def id(self):
        return int(self['id_'])

    def IterateThreadTop(self, v, top):
        v.VisitRootPointer(Root.kTop, None, ObjectSlot(top['pending_exception_']))
        v.VisitRootPointer(Root.kTop, None, ObjectSlot(top['pending_message_obj_']))
        v.VisitRootPointer(Root.kTop, None, ObjectSlot(top['context_']))
        v.VisitRootPointer(Root.kTop, None, ObjectSlot(top['scheduled_exception_']))

        # TBD: top['try_catch_handler_']
        # TBD: StackFrameIterator

    def Iterate(self, v):
        self.IterateThreadTop(v, self.thread_local_top_) 

    def Bootstrapper(self):
        return Bootstrapper(self['bootstrapper_'])

    def IterateStartupObjectCache(self, v):
        # SerializerDeserializer::Iterate
        
        if not self.has('startup_object_cache_'):
            return
        
        cache = stl.Vector(self['startup_object_cache_'])
        for item in cache:
            #print('cache', item, item.address)
            v.VisitRootPointer(Root.kStartupObjectCache, None, ObjectSlot(item.address))

class GlobalHandles(Struct):
    _typeName = 'v8::internal::GlobalHandles'

    #kBlockSize = 256

    class Node(Struct):
        _typeName = 'v8::internal::GlobalHandles::Node'

        FREE = 0
        NORMAL = 1
        WEAK = 2
        PENDING = 3
        NEAR_DEATH = 4

        FINALIZER_WEAK = 0
        PHANTOM_WEAK = 1
        PHANTOM_WEAK_2_EMBEDDER_FIELDS = 2
        PHANTOM_WEAK_RESET_HANDLE = 3

        @property
        def NodeState(self):
            x = self['flags_']
            return self.BitSize(x, 0, 3)

        @property
        def IsInYoungList(self):
            x = self['flags_']
            return self.Bit(x, 3)
 
        @property
        def NodeWeaknessType(self):
            x = self['flags_']
            return self.BitSize(x, 4, 2)

        def isRetainer(self):
            state = self.NodeState
            return (state != self.FREE) and \
                not (state == self.NEAR_DEATH and
                     self.NodeWeaknessType != self.FINALIZER_WEAK)

        @property
        def label(self):
            if self.NodeState != self.NORMAL:
                return None
            x = self['data_']['parameter']
            if x == 0:
                return None
            return x

        @property
        def location(self):
            return self['object_'].AddressOf()

    class NodeSpace(Struct):
        """ Global Handles uses NodeSpace for node management. """
        _typeName = 'v8::internal::GlobalHandles::NodeSpace<v8::internal::GlobalHandles::Node>'

        def Iterate(self, v):
            ptr = self['first_used_block_']
            cnt = 0
            while ptr != 0:
                for i in range(Internal.kBlockSize):
                    x = ptr['nodes_'][i].AddressOf()
                    node = GlobalHandles.Node(x)
                    if node.isRetainer():
                        v.VisitRootPointer(Root.kGlobalHandles, node.label, ObjectSlot(node.location))
                        cnt += 1
                        if cnt % 10000 == 0:
                            print("handles: %d" % cnt)
                ptr = ptr['next_used_']
            print("handles: %d" % cnt)

    class OnStackTracedNodeSpace(Struct):
        """ introduced by v8.8, holds the on stack global handles.
        """
        _typeName = 'v8::internal::GlobalHandles::OnStackTracedNodeSpace'

        def Iterate(self, v) :
            #raise Exception('TBD')
            log.warn('OnStackTracedNodeSpace.Iterate NotImplemented.')

    """ begin of the GlobalHandles functions.
    """
    @CachedProperty
    def _on_stack_nodes(self):
        if GlobalHandles.OnStackTracedNodeSpace.IsDisabled():
            return None
        return GlobalHandles.OnStackTracedNodeSpace(self['on_stack_nodes_'], self)

    def IterateAllRoots(self, v):
        """ 1) iterate all Retainer regular_nodes
            2) iterate all retainer traced_nodes
            3) iterate all nodes on stack
        """
        ns = GlobalHandles.NodeSpace(self['regular_nodes_'], self)
        ns.Iterate(v)

        ns = GlobalHandles.NodeSpace(self['traced_nodes_'], self)
        ns.Iterate(v)

        on_stack_nodes = self._on_stack_nodes
        if on_stack_nodes:
            # TBD: Iterate 
            on_stack_nodes.Iterate(v)


class EternalHandles(Struct):
    _typeName = 'v8::internal::EternalHandles'

    kSize = 1 << 8

    @CachedProperty
    def size_(self):
        return int(self['size_'])

    @property
    def blocks_(self):
        return stl.Vector(self['blocks_'])

    def IterateAllRoots(self, v):
        limit = self.size_
        for block in self.blocks_:
            used = min(limit, self.kSize)
            #print("0x%x"%int(block), "0x%x"%int(block + used))
            v.VisitRootPointers(Root.kEternalHandles, None, \
                int(block), int(block + used))
            limit = limit - self.kSize

class HandleScopeData(Struct):
    _typeName = "v8::internal::HandleScopeData"

    def next(self):
        return self['next']

class DetachableVectorBase(Struct):
    _typeName = 'v8::internal::DetachableVectorBase'

    @property
    def size(self):
        return int(self['size_'])

    @property
    def capacity(self):
        return int(self['capacity_'])

    @property
    def data(self):
        return self['data_']

    def empty(self):
        return self.size == 0

    def at(self, index):
        return self.data.LoadPtr(index * 8)

    def back(self):
        return self.at(self.size - 1)

    def front(self):
        return self.at(0) 

    def begin(self):
        return int(self.data)

    def end(self):
        return self.begin() + (self.size * 8)


class HandleScopeImplementer(Struct):
    _typeName = "v8::internal::HandleScopeImplementer"

    @property
    def blocks_(self):
        return DetachableVectorBase(self['blocks_'].AddressOf())

    @property
    def saved_contexts_(self):
        return DetachableVectorBase(self['saved_contexts_'].AddressOf())
    
    @property
    def entered_contexts_(self):
        return DetachableVectorBase(self['entered_contexts_'].AddressOf())

    def Iterate(self, v):
        """
        """
        if not self.blocks_.empty():
            v.VisitRootPointers(Root.kHandleScope, None, 
                                self.blocks_.back(), 
                                self['handle_scope_data_']['next'])

        # saved_contexts_ and entered_contexts_
        for ctx in (self.saved_contexts_, self.entered_contexts_):
            if not ctx.empty():
                v.VisitRootPointers(Root.kHandleScope, None,
                                    ctx.begin(),
                                    ctx.end())

class Heap(Struct):
    _typeName = "v8::internal::Heap"
    
    class ExternalStringTable(Struct):
        _typeName = 'v8::internal::Heap::ExternalStringTable'

        @property
        def young_strings(self):
            return stl.Vector(self['young_strings_'])
        
        @property
        def old_strings(self):
            return stl.Vector(self['old_strings_'])

        def IterateYoung(self, v):
            old_strings = self.old_strings
            for item in old_strings:
                v.VisitRootPointer(Root.kExternalStringsTable, None, ObjectSlot(item.address))

        def IterateOld(self, v):
            young_strings = self.young_strings
            for item in young_strings:
                v.VisitRootPointer(Root.kExternalStringsTable, None, ObjectSlot(item.address))

        def IterateAll(self, v):
            self.IterateYoung(v)
            self.IterateOld(v)

    def getIsolate(self):
        if self.parent is not None:
            return self.parent

    def getSpace(self, name_or_index):
        space_id = name_or_index
        if isinstance(name_or_index, str):
            space_id = AllocationSpace.SpaceId(name_or_index)

        space_name = AllocationSpace.SpaceName(space_id) 
        if space_name is None:
            raise ValueError('not a valid space name')

        s = int(self[ "%s_" % space_name ])
        if space_id == AllocationSpace.NEW_SPACE:
            return NewSpace(s)
        elif space_id == AllocationSpace.RO_SPACE:
            return ReadOnlySpace(s)
        return PagedSpace(s)

    def GetNativeContextList(self):
        o = self['native_contexts_list_']
        if o.has('ptr_'):
            p = int(o['ptr_'])
        else:
            p = int(o._unsigned)
        return NativeContext(p)

    def GetGlobalObject(self):
        nc = self.GetNativeContextList()
        return nc.GetJSGlobalObject()

    def CommitSize(self):
        """ return the size of all heapobject committed
        """
        size = 0
        for space in SpaceIterator(self):
            if space is None:
                continue
            size += space.committed
        return size

    def GlobalMemoryLimitSize(self):
        o = self['global_allocation_limit_']
        p = int(o)
        return p 

    @property
    def gc_state(self):
        return self['gc_state_']

    def isInGC(self):
        return self.gc_state != 0

    def IterateReadOnlyRoots(self, v, options):
        iso = self.getIsolate()
        # readonly roots
        v.VisitRootPointers(
            Root.kReadOnlyRootList, None, 
            iso.Roots().read_only_roots_begin(),
            iso.Roots().read_only_roots_end())

    def IterateRoots(self, v, options):
        iso = self.getIsolate()

        # strong root list
        v.VisitRootPointers(
                Root.kStrongRootList, None, 
                iso.Roots().strong_roots_begin(),
                iso.Roots().strong_roots_end())
        log.debug("Synchronize: (Strong roots)", level=9)

        # Bootstrapper (kExtensions)
        iso.Bootstrapper().Iterate(v)
        log.debug("Synchronize: (Bootstrapper)", level=9)

        # Relocatable
        Relocatable.Iterate(iso, v)
        log.debug("Synchronize: (Relocatable)", level=9)

        # Debug
        # isolate.debug_
        log.debug("Synchronize: (Debugger)", level=9)
        
        # Compilation cache
        iso.CompilationCache().Iterate(v)
        log.debug("Synchronize: (Compilation cache)", level=9)

        # Builtins
        iso.Builtins().Iterate(v) 
        log.debug("Synchronize: (Builtins)", level=9)

        # Thread Manager
        # isolate.thread_manager_ 
        log.debug("Synchronize: (Thread manager)", level=9)

        # Global Handles
        iso.GlobalHandles().IterateAllRoots(v)
        log.debug("Synchronize: (Global handles)", level=9)
        
        # TBD: stack roots
        # p1. Isolate (kTop)
        #iso.iterate(v)
        log.debug("Synchronize: (Stack roots)", level=9)

        # Stack
        #  1. isolate.thread_local_top_
        #  2. globalhandes.on_stack_nodes_
    
        # Handle Scope 
        iso.HandleScopeImplementer().Iterate(v)
        log.debug("Synchronize: (Handle scope)", level=9)

        # Persistent Handles
        # isolate.persistent_handles_list

        # Deferred Handles
        # isolate.deferred_handles_head_

        # p1.ethernal Handles
        iso.EternalHandles().IterateAllRoots(v)
        log.debug("Synchronize: (Eternal handles)", level=9)
        
        # Micro task queue
        # isolate.default_microtask_queue

        # p1.Strong Roots list
        # heap.strong_roots_list_ or strong_roots_head_

        # Startup object cache
        iso.IterateStartupObjectCache(v)
        log.debug("Synchronize: (Startup object cache)", level=9)

        # Weak Roots
        self.IterateWeakRoots(iso, v)
   
    def IterateWeakRoots(self, iso, v):
        # StringTable (ExternalStringTable, Unserializable)
        # isolate.string_table
        if Version.major >= 9:
            string_table = StringTable(iso['string_table_']._unsigned)
            string_table.Iterate(v)
        else:
            address = iso.Roots().GetRootByName('kStringTable').address
            v.VisitRootPointer(Root.kStringTable, None, ObjectSlot(address))
        log.debug("Synchronize: (Internalized strings)", level=9)

        # heap.external_string_table
        external_string_table = Heap.ExternalStringTable(self['external_string_table_'].AddressOf())
        external_string_table.IterateAll(v)
        log.debug("Synchronize: (External strings)", level=9)
 
    def Flatten(self):
        out = {}
        spaces = []
        for i in range(AllocationSpace.LAST_SPACE):
            space = self.getSpace(i)
            spaces.append(space.Flatten())
        out['spaces'] = spaces 
        return out

class ReadOnlyHeap(Struct):
    _typeName = 'v8::internal::ReadOnlyHeap'

    @property
    def read_only_space(self):
        p = self['read_only_space_']
        return p

class ReadOnlyRoots(Struct):
    _typeName = 'v8::internal::ReadOnlyRoots'

    kEntriesCount = 0

    @classmethod
    def EntriesCount(cls):
        return cls.kEntriesCount

    def Name(self, root):
        if root >= self.kEntriesCount:
            raise IndexError

class MemoryChunk(Struct):
    _typeName = 'v8::internal::MemoryChunk'

    kAlignment = 256*1024
    kAlignmentMask = 0x3ffff

    _CacheAreaEnd = None

    @classmethod
    def FromHeapObject(cls, obj):
        """ get MemoryChunk from given Object """
        pass

    def getSpace(self):
        v = self['owner_']['_M_b']['_M_p']
        return PagedSpace(v)

    @property
    def size(self):
        """ get chunk size
            return: int
        """
        return int(self['size_'])

    @property
    def area_start(self):
        """ get area start ptr
            return: int
        """
        return int(self['area_start_'])

    @property
    def area_end(self):
        """ get area end ptr
            return: int
        """
        if self._CacheAreaEnd is not None:
            return self._CacheAreaEnd
        self._CacheAreaEnd = int(self['area_end_'])
        return self._CacheAreaEnd

    @property
    def sweeping_state(self):
        return self['concurrent_sweeping_']['_M_i']

    @classmethod
    def BaseAddress(cls, ptr):
        return ptr & (~cls.kAlignmentMask)

    def GetOffset(self, address):
        pass

    def walk(self):
        """ walk for objects """
        spc = self.getSpace()
        ptr = self.area_start
        while ptr < self.area_end:
            if ptr == spc.top and ptr != spc.limit:
                ptr = spc.limit
                continue

            ho = HeapObject.FromAddress(ptr)
            if not ho.Access():
                return

            # mp = ho.GetMap()
            try:
                size = ho.Size()
            except:
                print("failed: %x"  % ptr)
                return

            # print("Object(0x%x) size(%d) %s" % (ptr, size, InstanceType.Name(mp.GetType())))
            yield ho
            ptr += size

class RootsTable(Struct):
    _typeName = 'v8::internal::RootsTable'

    kEntriesCount = 0

    #_undefined_value = None
    #_the_hole_value = None
    
    def strong_roots_begin(self):
        v = self['roots_'][RootIndex.kFirstStrongRoot].AddressOf()
        return v

    def strong_roots_end(self):
        v = self['roots_'][RootIndex.kLastStrongRoot + 1].AddressOf()
        return v

    def read_only_roots_begin(self):
        v = self['roots_'][RootIndex.kFirstReadOnlyRoot].AddressOf()
        return v

    def read_only_roots_end(self):
        v = self['roots_'][RootIndex.kLastReadOnlyRoot + 1].AddressOf()
        return v

    @classmethod
    def EntriesCount(cls):
        return cls.kEntriesCount 

    def Name(self, root):
        """ get name of the root """
        if root >= self.kEntriesCount:
            raise IndexError
        v = self['root_names_'][root]
        return v.GetCString()

    def root(self, root):
        """ get tagged pointer of the root """
        v = self['roots_'][root]
        return v

    def GetRootByName(self, root_name):
        index = RootIndex.Find(root_name)
        return self['roots_'][index]

    @CachedProperty
    def undefined_value(self):
        ptr = self['roots_'][Internals.kUndefinedValueRootIndex]
        return Oddball(int(ptr))

    @CachedProperty
    def the_hole_value(self):
        ptr = self['roots_'][Internals.kTheHoleValueRootIndex]
        return Oddball(int(ptr))

    @CachedProperty
    def null_value(self):
        ptr = self['roots_'][Internals.kNullValueRootIndex]
        return Oddball(int(ptr))

    @CachedProperty
    def empty_byte_array(self):
        ptr = self['roots_'][RootIndex.kEmptyByteArray]
        return Object(int(ptr))

    @CachedProperty
    def empty_fixed_array(self):
        ptr = self['roots_'][RootIndex.kEmptyFixedArray]
        return Object(int(ptr))

    @CachedProperty
    def empty_weak_fixed_array(self):
        ptr = self['roots_'][RootIndex.kEmptyWeakFixedArray]
        return Object(int(ptr))

    @CachedProperty
    def empty_descriptor_array(self):
        ptr = self['roots_'][RootIndex.kEmptyDescriptorArray]
        return Object(int(ptr))

    @CachedProperty
    def fixed_array_map(self):
        ptr = self['roots_'][RootIndex.kFixedArrayMap]
        return Object(int(ptr))

    @CachedProperty
    def cell_map(self):
        ptr = self['roots_'][RootIndex.kCellMap]
        return Object(int(ptr))

    @CachedProperty
    def global_property_cell_map(self):
        ptr = self['roots_'][RootIndex.kGlobalPropertyCellMap]
        return Object(int(ptr))
    
    @CachedProperty
    def shared_function_info_map(self):
        ptr = self['roots_'][RootIndex.kSharedFunctionInfoMap]
        return Object(int(ptr))

    @CachedProperty
    def free_space_map(self):
        ptr = self['roots_'][RootIndex.kFreeSpaceMap]
        return Object(int(ptr))

    @CachedProperty
    def one_pointer_filler_map(self):
        ptr = self['roots_'][RootIndex.kOnePointerFillerMap]
        return Object(int(ptr))

    @CachedProperty
    def two_pointer_filler_map(self):
        ptr = self['roots_'][RootIndex.kTwoPointerFillerMap]
        return Object(int(ptr))

class Space(Struct):
    _typeName = 'v8::internal::Space'

    @property
    def id(self):
        return self['id_']

    @property
    def name(self):
        return AllocationSpace.Name(self.id)

    @property
    def committed(self):
        return self['committed_']._unsigned
    
    @property
    def max_committed(self):
        return self['max_committed_']._unsigned

    @property
    def external_backing_store_bytes(self):
        return self['external_backing_store_bytes_']._unsigned

    def isNewSpace(self):
        return self.id == AllocationSpace.NEW_SPACE
        
    def walkPages(self):
        """ walk for chunks """
        ptr = self['memory_chunk_list_']['front_']
        while ptr != 0:
            chunk = MemoryChunk(ptr)
            yield chunk
            ptr = ptr['list_node_']['next_']

    def getChunks(self):
        chunks = []
        for i in self.walkPages():
            chunks.append(i)
        return chunks

    def Flatten(self):
        out = {}
        out['name'] = str(self.name)
        out['committed'] = str(self.committed)
        out['max_committed'] = str(self.max_committed)
        arr = []
        for page in self.walkPages():
            arr.append({"address": page.BaseAddress(page.area_start), "size": page.size})
        out['pages'] = arr
        return out


class SpaceWithLinearArea(Space):
    _typeName = 'v8::internal::SpaceWithLinearArea'

    _CacheTop = None
    _CacheLimit = None
    
    @property
    def top(self):
        if self._CacheTop is not None:
            return self._CacheTop
        self._CacheTop = int(self['allocation_info_']['top_'])
        return self._CacheTop

    @property
    def limit(self):
        if self._CacheLimit is not None:
            return self._CacheLimit
        self._CacheLimit = int(self['allocation_info_']['limit_'])
        return self._CacheLimit


class PagedSpace(SpaceWithLinearArea):
    _typeName = 'v8::internal::PagedSpace'

    def show_sl(self):
        print("%-14s: %10u %10u" % (self.name, self.committed, self.max_committed))


class SemiSpace(SpaceWithLinearArea):
    _typeName = 'v8::internal::SemiSpace'

    @property
    def pages_used(self):
        return self['pages_used_']

    @property
    def current_capacity(self):
        return self['current_capacity_']

    @property
    def maximum_capacity(self):
        return self['maximum_capacity_']
    
    @property
    def minimum_capacity(self):
        return self['minimum_capacity_']
   
    @property
    def committed(self):
        """ override """
        v = Space(self)
        return v.committed


class NewSpace(SpaceWithLinearArea):
    _typeName = 'v8::internal::NewSpace'

    @property
    def to_space(self):
        v = self['to_space_'].address
        return SemiSpace(v) 

    @property
    def from_space(self):
        v = self['from_space_'].address
        return SemiSpace(v) 

    def walkPages(self):
        """ walk for chunks """
        return chain(self.from_space.walkPages(), self.to_space.walkPages())

    @property
    def committed(self):
        to_committed = self.to_space.committed
        from_committed = self.from_space.committed
        return to_committed + from_committed 

    #def walkPages(self):
    #    for i in self.from_space.walkPages():
    #        yield i
    #    for i in self.to_space.walkPages():
    #        yield i

    def getChunks(self):
        chunks = []
        for i in self.walkPages():
            chunks.append(i)
        return chunks

    def show_sl(self):
        to_committed = self.to_space.committed
        from_committed = self.from_space.committed
        print("%-14s: %10u" % (self.name, to_committed + from_committed))
        print(" - from_space : %10u" % from_committed)
        print(" - to_space   : %10u" % to_committed)


if Version.major >= 9:
    class ReadOnlySpace(Struct):
        _typeName = 'v8::internal::ReadOnlySpace'
     
        @property
        def id(self):
            return self['id_']

        @property
        def name(self):
            return AllocationSpace.Name(self.id)

        @property
        def committed(self):
            return self['committed_']._unsigned
        
        @property
        def max_committed(self):
            return self['max_committed_']._unsigned

        def show_sl(self):
            print("%-14s: %10u %10u" % (self.name, self.committed, self.max_committed))

        def walkPages(self):
            for i in stl.Vector(self['pages_']).__iter__():
                yield MemoryChunk(i)

        def getChunks(self):
            chunks = []
            for i in self.walkPages():
                chunks.append(i)
            return chunks

else:
    class ReadOnlySpace(PagedSpace):
        _typeName = 'v8::internal::ReadOnlySpace'


class Relocatable(Struct):
    _typeName = 'v8::internal::Relocatable'

    @classmethod
    def Iterate(self, isolate, v):
        # TBD: visit isolate relocateble list.
        pass

class SourceCodeCache(Struct):
    _typeName = 'v8::internal::SourceCodeCache'

    @CachedProperty
    def cache(self):
        v = self['cache_'].AddressOf()
        print(v)
        return FixedArray(v)

    def Iterate(self, v):
        cache = self['cache_'].AddressOf() 
        v.VisitRootPointer(Root.kExtensions, None, ObjectSlot(cache))

class SourcePosition(Struct):
    _typeName = 'v8::internal::SourcePosition'

    @property
    def is_external_field(self):
        pass

    @property
    def external_line_field(self):
        pass

    @property
    def external_file_id_field(self):
        pass

    def Decode(self, raw):
        pass


class InterpreterData(Struct):
    _typeName = 'v8::internal::InterpreterData'


class Representation(Struct):
    _typeName = 'v8::internal::Representation'

    def __init__(self, kind):
        self._kind = kind

    def Kind(self):
        return self._kind

    def IsSmi(self):
        return self._kind == self.kSmi 

    def IsDouble(self):
        return self._kind == self.kDouble 

    def IsHeapObject(self):
        return self._kind == self.kHeapObject 

    def IsTagged(self):
        return self._kind == self.kTagged


""" tail imports
"""
from .enum import (
    AllocationSpace,
    AllocationType,
    BuiltinsName,
    ElementsKind, 
    InstanceType,
    LanguageMode,
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
)

from .object import (
    Object,
    HeapObject, 
    Oddball,
    NativeContext,
    JSGlobalObject,
    FixedArray,
    StringTable,
)

from .iterator import (
    SpaceIterator,
)
