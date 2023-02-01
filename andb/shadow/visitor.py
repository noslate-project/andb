from __future__ import print_function, division

import sys

import andb.dbg as dbg
import andb.v8 as v8
import andb.node as node

from andb.utility import (
    profiler, 
    Logging as log,
)

#print=log.print

class IsolateGuesser:
    """ guess an isolate address from core.
    """
    _isolate_addr_map = {} 

    def SetIsolate(self, iso):
        v8.Isolate.SetCurrent(iso)
        # set convenience_variable
        dbg.ConvenienceVariables.Set('isolate', iso._I_value)

    def CheckIsolate(self, address):
        try:
            _iso = v8.Isolate(address)
            _heap_iso = _iso['heap_']['isolate_']
            if _iso == _heap_iso:
                return _iso
        except:
            pass
        return None

    def CheckMemoryChunk(self, address):
        m = v8.MemoryChunk(address)
        _heap = m['heap_']
        _iso = _heap['isolate_']
        _iso_heap = _iso['heap_'].AddressOf()
        if _heap == _iso_heap:
            return v8.Isolate(_iso)
        return None

    def GuessFromStacks(self):
        """ walk all thread, guess from sp """
        for t in dbg.Target.GetThreads():

            # get low addres from 'sp'
            low = t.GetFrameTop().GetSP()
            
            # search for memory region of 'sp'
            mri = dbg.Target.GetMemoryRegions().Search(low)
            
            # stack range
            high = mri.end_address

            for ptr in dbg.Slots(low, high):

                if ptr & 0b11 != 0:
                    continue

                if ptr < 0x40000:
                    continue

                iso = self.CheckIsolate(ptr)
                if iso is None:
                    continue

                # found
                #print(iso)
                self.SetIsolate(iso)
                return iso
        return None

    def GuessFromPages(self):
        """ guess from all 256K pages """
        regions = dbg.Target.GetMemoryRegions().GetRegions()
        for m in regions:
            if m.size == 256*1024:
                try:
                    iso = self.CheckMemoryChunk(m.start_address)
                except Exception as e:
                    #print("0x%x %s" % (m.start_address, e))
                    iso = None
                if iso is None:
                    continue
                else:
                    # found
                    #print(iso)
                    self.SetIsolate(iso)
                    return iso 
        return None

    def ListFromPages(self):
        regions = dbg.Target.GetMemoryRegions().GetRegions()
        for m in regions:
            if m.size == 256*1024:
                try:
                    iso = self.CheckMemoryChunk(m.start_address)
                except Exception as e:
                    #print("0x%x %s" % (m.start_address, e))
                    iso = None
                if iso is None:
                    continue
                else:
                    # Add Isolate 
                    self.GetIsolate(iso)
        self.ShowIsolates()
        return None

    def ListFromStack(self):
        """ walk all thread, guess from sp """
        for t in dbg.Target.GetThreads():

            # get low addres from 'sp'
            low = t.GetFrameTop().GetSP()
            
            # search for memory region of 'sp'
            mri = dbg.Target.GetMemoryRegions().Search(low)
            
            # stack range
            high = mri.end_address

            for ptr in dbg.Slots(low, high):

                if ptr & 0b11 != 0:
                    continue

                if ptr < 0x40000:
                    continue

                iso = self.CheckIsolate(ptr)
                if iso is None:
                    continue

                # found
                if self.GetIsolate(iso):
                    break
        self.ShowIsolates()
        return None
    
    def guess_from_tls(self):
        """ guess from thread local storage """
        #key = gdb.parse_and_eval('(int)v8::internal::Isolate::isolate_key_')
        raise NotImplementedError()

    def SetAddress(self, argv):
        addr = int(argv[0], 16)
        iso = self.CheckIsolate(addr)
        if iso:
            self.SetIsolate(iso)

    def SelectIndex(self, argv):
        if len(argv) == 0:
            iso = v8.Isolate.GetCurrent()
            print(iso)
            return
        idx = int(argv[0])
        iso = self.GetIsolateById(idx)
        if iso:
            self.SetIsolate(iso)
            return
        print("Can't find Isolate with Id == %d" % idx)

    def GetIsolateById(self, idx):
        for k,v in self._isolate_addr_map.items():
            if v.id == idx:
                return v 
        return None

    def FindIsolate(self, iso):
        addr = iso.address
        if addr in self._isolate_addr_map:
            return self._isolate_addr_map[addr]
        return None

    def GetIsolate(self, iso):
        # true if find
        found = self.FindIsolate(iso)
        if found:
            return found
        addr = iso.address
        self._isolate_addr_map[addr] = iso

    def ClearAll(self):
        self._isolate_addr_map.clear()

    def ShowIsolates(self):
        print("%3s %-14s %10s %10s" % ("ID", "ISOLATE-ADDR", "HEAP-SIZE", "GLOB-SIZE"))
        for k,v in sorted(self._isolate_addr_map.items(), key=lambda x: x[1].id):
            try:
                heap = v.Heap()
                print("%3d 0x%-12x %10d %10d" % (v.id, k, heap.CommitSize() ,heap.GlobalMemoryLimitSize()))
            except Exception as e:
                print("%3d 0x%-12x (%s)" % (v.id, k, e))
        print("Found %d Isolate(s)." % len(self._isolate_addr_map))

    def ListIsolates(self):
        if len(self._isolate_addr_map) < 1:
            self.ListFromPages()
            return 
        self.ShowIsolates()

    def BatchHeapSnapshot(self):
        from .heap_snapshot import HeapSnapshot
        for addr,iso in sorted(self._isolate_addr_map.items(), key=lambda x: x[1].id):
            print("Switch to Isolate:%d (0x%x)" % (iso.id, addr))
            self.SetIsolate(iso)

            outf = "isolate_%d.heapsnapshot" % iso.id
            snap = HeapSnapshot()
            snap.Generate(outf)

class HeapVisitor:
    _size = 0
    _cnt = 0
    _map_tbl = {}
    _typ_tbl = {}

    # dict for map tag lookup
    _maps = None

    def __init__(self):
        iso = v8.Isolate.GetCurrent()
        if iso is None:
            log.error('isolate is not set.')
            raise Exception('isolate is not set.') 
        self._heap = v8.Heap(iso['heap_'].AddressOf())

    """ Private
    """
    def PrintChunk(self, chunk, *args):
        print ("{:>#15x} : size({:d}), sweep({:d}), start({:#x})".format(
            int(chunk),
            chunk.size,
            int(chunk.sweeping_state),
            chunk.area_start))

    def PrintObject(self, obj, *args):
        #if obj is None:
        #    return

        mp = obj.map
        tpe = obj.instance_type
        size = obj.Size()
        #o = v8.HeapObject.FromAddress(obj)
        # print ("0x%x : size(%d), mapsize(%d), %s" % (obj.ptr(), size, mp.GetInstanceSize(), v8.InstanceType.Name(tpe)))
        print ("0x%x: %s" % (obj.ptr, obj.Brief()))
        #try:
        #    print ("0x%x: %s" % (obj.tag, obj.Brief()))
        #except:
        #    print ("0x%x: %s" % (obj.tag, "[ string decode failed.]"))


    def ShowSpaceSummay(self):
        hp =self._heap
        size = 0
        print("%-14s  %10s %10s" % ("SPACE NAME", "COMMIT", "MAX"))
        for i in v8.SpaceIterator(hp):
            if i is None:
                continue
            i.show_sl()
            size += i.committed
        print ("Total Committed %10u" % size)

    def SpaceWalkChunk(self, space_name):
        hp = self._heap
        cnt = 0
        space = hp.getSpace(space_name)
        if space is None:
            return
        for chunk in space.walkPages():
            self.PrintChunk(chunk)
            cnt += 1
        print("Total %d pages." % cnt)
    
    def SpaceWalkObject(self, space_name):
        hp = self._heap
        space = hp.getSpace(space_name)
        if space is None:
            return
        cnt = 0
        size = 0
        chunks = v8.ChunkIterator(space)
        for chunk in chunks:
            objs = v8.ChunkObjectIterator(chunk)
            for obj in objs:
                #self.parseObject(obj)
                cnt += 1
                size += obj.Size()
        print("Total Cnt(%d), Size(%d)" % (cnt, size))

    def ShowInstanceSummary(self, argv):
        self._map_tbl = {}
        hp = self._heap
        space = hp.getSpace("map")
        if space is None:
            return

        print_type = None
        if len(argv) == 2:
            print_type = v8.InstanceType.Find(argv[1])

        tbl = self._map_tbl
        tbl.clear()
        if space.isNewSpace():
            iterator = v8.NewSpaceObjectIterator(space)
        else:
            iterator = v8.PagedSpaceObjectIterator(space)
        for obj in iterator:
            if not obj.IsMapType():
                continue
            m = v8.Map(obj)
            typ = m.instance_type
            if typ == print_type:
                print("0x%012x: %s %s" % (obj.tag(), v8.InstanceType.Name(typ), v8.Object.SBrief(obj)));
            size = obj.Size()
            if typ in tbl:
                a = tbl[typ]
                a[0] += 1
                a[1] += size
            else:
                tbl[typ] = [1, size]

        for i in (sorted(tbl.items(), key = lambda v:(v[1], v[0]), reverse = True)):
            print("0x%012x: %8d %12d %s" % (i[0], i[1][0], i[1][1], v8.InstanceType.Name(i[0])))

    @profiler
    def ShowMapSummary(self, argv):
        if argv[0] == "type":
            return self.ShowInstanceSummary(argv)
        
        self._map_tbl = {}
        hp = self._heap
        space = hp.getSpace(argv[0])
        if space is None:
            return

        tbl = self._map_tbl
        if space.isNewSpace():
            iterator = v8.NewSpaceObjectIterator(space)
        else:
            iterator = v8.PagedSpaceObjectIterator(space)
        for obj in iterator:
            tag = obj.map.tag
            size = obj.Size()
            if tag in tbl:
                a = tbl[tag]
                a[0] += 1
                a[1] += size
            else:
                tbl[tag] = [1, size]

        for i in (sorted(tbl.items(), key = lambda v:(v[1], v[0]), reverse = False)):
            mp = v8.Map(i[0])
            print("0x%012x: %8d %12d %s" % (i[0], i[1][0], i[1][1], v8.InstanceType.Name(mp.instance_type)))

    def roheapwalk(self):
        hp = self._heap
        iso = hp.getIsolate()
        ro_heap = iso.ReadOnlyHeap()
        cnt = 0
        size = 0
        for obj in v8.ReadOnlyHeapObjectIterator(ro_heap):
            self.parseObject(obj)
            cnt += 1
            size += obj.Size()
        print("Total Cnt(%d), Size(%d)" % (cnt, size))

    def DumpAllHeapObjects(self):
        """ dump all heap objects
        """
        hp = self._heap
        cnt = 0
        size = 0
        for obj in v8.HeapObjectIterator(hp):
            self.PrintObject(obj)
            cnt += 1
            size += obj.Size()
        print("Total Cnt(%d), Size(%d)" % (cnt, size))

    def DumpSpaceHeapObjects(self, argv):
        # get space
        hp = self._heap
        space = hp.getSpace(argv[0])
        if space is None:
            return
        
        # get type filter
        for_type = None
        if len(argv) > 2 and argv[1] == 'type':
            for_type = v8.InstanceType.Find(argv[2])
            print(for_type)

        cnt = 0
        size = 0
        if space.isNewSpace():
            iterator = v8.NewSpaceObjectIterator(space)
        else:
            iterator = v8.PagedSpaceObjectIterator(space)
        for obj in iterator:
            cnt += 1
            if for_type is None or \
                    for_type == obj.instance_type:
                self.PrintObject(obj)
            #elif cnt % 10000 == 0:
            #    print("%d" % cnt)
            size += obj.Size()
        print("Total Cnt(%d), Size(%d)" % (cnt, size))

    def ShowGlobalObject(self):
        native_context = self._heap.GetNativeContextList()
        while native_context.IsNativeContext():

            print("JSGlobalObject: %s" % (native_context.GetJSGlobalObject()))
            native_context = native_context.GetNextContextLink()

    """ Public
    """
    def HeapSpace(self, argv):
        """ heap space [ro|new|old|lo]
        """
        if len(argv) == 0:
            self.ShowSpaceSummay()
        else:
            self.SpaceWalkChunk(argv[0])

    @profiler
    def DumpChunk(self, argv):
        """ heap page <address>
        """
        ptr = int(argv[0], 16)
        chunk = v8.MemoryChunk(ptr)
        cnt = 0
        for obj in chunk.walk():
            self.PrintObject(obj)
            cnt += 1
        print("Total Cnt(%d)" % (cnt))

    @profiler
    def HeapDump(self, args):
        """ heap dump
        """
        if args is None:
            self.DumpAllHeapObjects()
        self.DumpSpaceHeapObjects(args)

    #@profiler
    def HeapFind(self, argv):
        """ heap find 
        """
        hp = self._heap
        space = hp.getSpace(argv[0])
        if space is None:
            return

        cnt = 0
        tag_to_find = int(argv[1], 16)
        for page in v8.ChunkIterator(space):
            s = dbg.Target.MemoryFind(page.area_start, page.area_end, tag_to_find)
            if s is not None:
                cnt += len(s)
                for obj in v8.ChunkObjectIterator(page):
                    address = obj.address
                    for p in v8.ObjectSlots(address, address+obj.Size()):
                        if p == tag_to_find:
                            print(obj.Brief())
        print("find %d" % cnt);

    def ShowGlobal(self, args):
        """ show JSGlobalObject 
        """
        self.ShowGlobalObject()

    def SearchMapSummary(self, argv):
        if argv is None:
            print("heap map <space> <tag>")
            return None
        
        hp = self._heap
        space = hp.getSpace(argv[0])
        if space is None:
            return
      
        tag_to_find = int(argv[1], 16)
        tbl = self._map_tbl
        if space.isNewSpace():
            iterator = v8.NewSpaceObjectIterator(space)
        else:
            iterator = v8.PagedSpaceObjectIterator(space)
        for obj in iterator:
            tag = obj.map.tag
            size = obj.Size()
            if tag == tag_to_find:
                try:
                    print ("0x%x : size(%d) %s" % (obj.tag, size, obj.Brief()))
                except Exception as e:
                    print ("0x%x : size(%d) [ %s %s ]" % (obj.tag, size, "brief failed", e))

    def FollowTag(self, argv):
        all = {} 
        save = {} 
        done = {}
        if argv is None:
            print("heap follow <tag>")

        tag_to_follow = int(argv[0], 16)
        ho = v8.HeapObject(tag_to_follow)
        if not ho.IsHeapObject():
            print("not a heapobject")
            return None

        max_deep = 0 
        if len(argv) > 1:
            max_deep = int(argv[1])

        total_size = 0
        deep = 0
        save[ho.address] = 1 

        while len(save) > 0:
            all = save
            save = {} 
            for tag in all:
                ho = v8.HeapObject(tag)
                done[ho.address] = 1
                
                for tag in ho.Slots():
                    o = v8.HeapObject(tag)
                    if o.address in done:
                        continue
                    if not o.IsHeapObject():
                        continue

                    try:
                        t = o.instance_type
                        total_size += o.Size()
                    except:
                        t = None
   
                    if t is None or v8.InstanceType.Name(t) is None:
                        continue
                    
                    if v8.InstanceType.isFixedArray(t) or \
                       v8.InstanceType.inRange("FIRST_JS_OBJECT_TYPE", "LAST_JS_OBJECT_TYPE", t) or \
                       v8.InstanceType.inRange("FIRST_HASH_TABLE_TYPE", "LAST_HASH_TABLE_TYPE", t) or \
                       v8.InstanceType.isSymbol(t):
                        save[o.address] = 1
                        done[ho.address] = 1
                        print("[%d]0x%x : %u" % (deep, o.tag(), total_size), v8.Object.SBrief(o.tag()))
            deep += 1
            if max_deep and deep > max_deep:
                break
      
        tbl = {} 
        tbl.clear()
        for tag in done:
            obj = v8.HeapObject(tag)
            size = obj.Size()
            typ = obj.instance_type
            if typ in tbl:
                a = tbl[typ]
                a[0] += 1
                a[1] += size
            else:
                tbl[typ] = [1, size]

        for i in (sorted(tbl.items(), key = lambda v:(v[1], v[0]), reverse = False)):
            print(" %4d: %8d %12d %s" % (i[0], i[1][0], i[1][1], v8.InstanceType.Name(i[0])))
  
        print("objects:", len(done))
        print("follow_size:", total_size)



class ObjectVisitor:
    """
        v8 object  convenient visitor
    """
    @classmethod
    def showHeapObj(cls, o):
        """ show HeapObject """
        o.DebugPrint()

        """ Show Map """
        if not o.IsMapType():
            m = o.map
            m.DebugPrint()

        """ Baisc info """
        print("[HeapObject]")
        print(" - MapWord: 0x%x" % o.map)
        print(" - Size: %d " % o.Size())
        print(" - Page: 0x%x " % (v8.MemoryChunk.BaseAddress(o.ptr)))
        print("   - NextObject: 0x%x" % (o.tag + o.Size()))

    @classmethod
    def inspect(cls, argv):
        v = int(argv[0], 16)

        # smi
        if v8.Smi.IsValid(v):
            print("SMI: %d" % int(v8.Smi(v)))
            return v
        
        # HeapObject
        if not v8.HeapObject.IsValid(v):
            return v
       
        o = v8.HeapObject(v) 
        cls.showHeapObj(o)

    @classmethod
    def inspectObject(cls, argv):
        v = int(argv[0], 16)

        # smi
        if (v & 0x3):
            print("v8 object <address>")
            return

        o = v8.HeapObject.FromAddress(v)
        cls.showHeapObj(o)

    @classmethod
    def printObject(cls, argv):
        obj_type = argv[0]
        obj_tag = argv[1]

        obj = v8.ObjectMap.CreateObject(obj_type, obj_tag)
        obj.DebugPrint()

    @profiler
    def TestAutoLayout(self, argv):
        v = int(argv[0], 16)

        o = v8.HeapObject.FromAddress(v)
        for i in range(10000*100):
            #x = o.map
            x = o.map
        #m = o['map']
        #print(m, m.offset, m.size, m.value)
        #print("%s" % o.map)
        # print(m.offset, m.size, m.value)

class NodeEnvGuesser:
    """ guess a node::Environment address from v8 """
   
    def __init__(self):
        iso = v8.Isolate.GetCurrent()
        if iso is None:
            print('isolate is not set.')
            raise Exception
        self._heap = v8.Heap(iso['heap_'].AddressOf())

    def SetNodeEnv(self, pyo_node_env):
        node.Environment.SetCurrent(node.Environment(pyo_node_env))
        dbg.ConvenienceVariables.Set('node_env', pyo_node_env._I_value)

    def GuessFromV8Context(self):
        """ guess from v8 native context """
        native_context = self._heap.GetNativeContextList()
        embedder_data = native_context.GetEmbedderData()
        ptr = embedder_data.Get(node.ContextEmbedderIndex.kEnvironment)
        env = node.Environment(ptr)
        self.SetNodeEnv(env)

    def GuessFromStacks(self):
        pass


class StackVisitor:
    """ Visit Stack """

    def __init__(self):
        pass

    def frame(self, pc, sp, bp):
        print("0x%x, 0x%x, 0x%x" % (pc, sp, bp))

    def parse(self, frame):
        try:
            v8frame = v8.StackFrame(frame)
            return v8frame.Parse()
        except Exception as e:
            return None

    def Backtrace(self):
        #dbg.Target.WalkStackFrames(self.frame)
        dbg.Thread.BacktraceCurrent(self.parse)


class StringVisitor(object):

    @classmethod
    def SaveFile(cls, tag, file_to_save = None):
        o = v8.String(tag)
        if not v8.InstanceType.isString(o.instance_type):
            print("only support String object") 
            return 

        return o.SaveFile(file_to_save)

    @classmethod
    def StartsWithSave(self, argv):
        iso = v8.Isolate.GetCurrent()
        hp = iso.Heap()
        space = hp.getSpace(argv[0])
        if space is None:
            return

        cnt = 0 
        size = 0
        sz = argv[1]
        print("find %s" % sz)
        l = len(sz)
        for obj in v8.PagedSpaceObjectIterator(space):
            if not v8.InstanceType.isString(obj.instance_type):
                continue

            o = v8.String(obj)
            v = o.to_string()[:l]
            if not v.startswith(sz):
                continue
            
            cnt += 1
            size += obj.Size()
            
            f = o.SaveFile()
            print("%d: %10u %s" % (cnt, size, f))

        print("Total Cnt(%d), Size(%d)" % (cnt, size))

class TestVisitor(object):

    @classmethod
    def FunctionContextScripts(cls, argv):
        iso = v8.Isolate.GetCurrent()
        hp = iso.Heap()
        space = hp.getSpace(argv[0])
        if space is None:
            return
       
        tbl = {}
        iterator = v8.PagedSpaceObjectIterator(space)
        for obj in iterator:
            if not v8.InstanceType.isSharedFunctionInfo(obj.instance_type):
                continue

            fun = v8.SharedFunctionInfo(obj.address)
            script = fun.script
            if script is None:
                continue

            if script.name in tbl:
                tbl[script.name] += 1
            else:
                tbl[script.name] = 1

        for i in (sorted(tbl.items(), key = lambda v:(v[1], v[0]), reverse = False)):
            print("%s : %d" % (i[0], i[1]))

    @classmethod
    def FindFunction(cls, argv):
        iso = v8.Isolate.GetCurrent()
        heap = iso.Heap()
        space = heap.getSpace('old')
        
    @classmethod
    def ValueTest(cls, argv):
        from time import time
        import struct
        #iso = v8.Isolate.GetCurrent()
        #heap = iso.Heap()
        tag = int(argv[0], 16)
        ptr = tag & ~v8.Internal.kHeapObjectTagMask 

        buf = dbg.Target.MemoryRead(ptr, 80)

        t = time()
        for i in range(1000000):
            o = ptr 
        print("for %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            o = object() 
        print("object() %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            o = v8.HeapObject(tag)
        print("HeapObject() %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            r = v8.ChunkBlock() 
            r.InitReader(ptr)
        print("ChunkBlock() %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            r = v8.ChunkBlock() 
            r.InitReader(ptr)
            o = r.LoadU64(0)
        print("ChunkBlock().LoadU64 %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            o = v8.HeapObject(tag)
            m = o.instance_type
        print("HeapObject.instance_type %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            o = dbg.Block()
            o._address = ptr
        print("dbg.Block %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            o = dbg.Block()
            o._address = ptr
            m = o.LoadU64(0)
        print("dbg.Block.LoadU64 %.3f" % (time()-t))

        t = time()
        for i in range(1000000):
            m = struct.unpack_from("Q", buf, 0)
        print("struct.unpack %.3f" % (time()-t))

    @profiler
    def SingleValue(self, argv):
        from time import time
        #iso = v8.Isolate.GetCurrent()
        #heap = iso.Heap()
        tag = int(argv[0], 16)
        ptr = tag & ~v8.Internal.kHeapObjectTagMask 

        count = 1000000
        t = time()
        for i in range(count):
            o = v8.HeapObject(tag)
        print("HeapObject() %.3f" % (time()-t))

