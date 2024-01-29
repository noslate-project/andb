# -*- coding: UTF-8 -*-
from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix, Target, Value, Type, MemoryRegions
from andb.ptmalloc import ArenaVisitor
from andb.shadow import ObjectVisitor, TestVisitor, HeapSnapshot

""" test commands
"""
class cli_test(CommandPrefix):
    _cxpr = "test"


class cli_test_help(Command):
    _cxpr = "test help"

    def invoke(self, argv):
        pass

class cli_test_autolayout(Command):
    _cxpr = "test autolayout"

    def invoke(self, argv):
        ObjectVisitor().TestAutoLayout(argv)

class cli_test_find_double_in_range(Command):
    _cxpr = "test double"

    def invoke(self, argv):
        import struct
        t1 = int(argv[0])
        t2 = t1 + int(argv[1]) 
        a = Target.GetMemoryRegions()
        for m in a._I_regions:
            for m in range(m._I_start_address, m._I_end_address, 4096):
                b = Target.MemoryRead(m, 4096);
                for offset in range(0, 4096, 8):
                    p = m + offset
                    c, = struct.unpack_from('d', b, offset)
                    if c > t1 and c < t2:
                        print("0x%x:" % p, c)

class cli_test_find_function_context_scripts(Command):
    _cxpr = "test function_context_script"

    def invoke(self, argv):
        TestVisitor.FunctionContextScripts(argv)


class cli_test_find_function(Command):
    _cxpr = "test function"

    def invoke(self, argv):
        TestVisitor.FindFunction(argv)

class cli_test_value(Command):
    _cxpr = "test value"

    def invoke(self, argv):
        TestVisitor.ValueTest(argv)

class cli_test_single(Command):
    _cxpr = "test single"

    def invoke(self, argv):
        TestVisitor().SingleValue(argv)


""" stack command
"""
class cli_stack(CommandPrefix):
    _cxpr = "ss"

class cli_stack_stack(Command):
    _cxpr = "ss guess"

    def invoke(self, argv):
        far = 4*1024 
        if len(argv) == 1:
            far = int(argv[0]) // 8 * 8

        t = Target.GetCurrentThread()
        sp = t.GetFrameTop().GetSP()
        segs = Target.GetMemoryRegions().Load()
        seg = MemoryRegions.Lookup(segs, sp) 
        sp_low = sp - far 
        print("sp: %x, far: %d, seq: %s" % (sp, far, seg))

        for x in range(sp_low, seg._I_end_address, 8):
            if x == sp:
                print("0x%x : <===== RSP ======>" % x)
                continue

            p = Target.ReadInt(x, 8)
            if p == 0: continue
            seg = MemoryRegions.Lookup(segs, p) 
            if seg is None or not seg.IsExecutable(): continue
            v = Target.TryDecodeIr(p) 
            print("0x%x :" % x, v)
            if v.find('in clone (') > 0 or \
               v.find('in main (') > 0: 
                break;

""" mm command
"""
class cli_mm(CommandPrefix):
    _cxpr = "mm"


class cli_mm_maps(Command):
    _cxpr = "mm maps"

    def invoke(self, argv):
        a = Target.GetMemoryRegions()
        for m in a._I_regions:
            print(m)


class cli_mm_list(Command):
    _cxpr = "mm list"

    def invoke(self, argv):
        a = Target.GetMemoryRegions()
        for m in sorted(a._I_regions, key=lambda s: s._I_end_address - s._I_start_address):
            print(m)


class cli_mm_find(Command):
    _cxpr = "mm find"
    
    def invoke(self, argv):
        addr = int(argv[0], 16)
        a = Target.GetMemoryRegions()
        cnt = 0
        for m in a._I_regions:
            r = Target.MemoryFind(m._I_start_address, m._I_end_address, addr)
            if r is not None:
                cnt += len(r)
                for i in r:
                    print("0x%x in %s" % (i, m))
        print("Found %d" % cnt)


class cli_mm_arena(Command):
    _cxpr = "mm arena"

    def invoke(self, argv):
        ArenaVisitor.ParseArena(argv) 


class cli_mm_walk(Command):
    _cxpr = "mm walk"

    def invoke(self, argv):
        start = int(argv[0], 16)
        end = int(argv[1], 16)
        only_inuse = 0 
        if len(argv) > 2:
            only_inuse = bool(argv[2])
        ArenaVisitor.WalkChunks(start, end, only_inuse)

class cli_mm_locate(Command):
    _cxpr = "mm locate"

    def invoke(self, argv):

        if len(argv) == 3:
            start = int(argv[0], 16)
            end = int(argv[1], 16)
            addr = int(argv[2], 16)
        elif len(argv) == 1:
            addr = int(argv[0], 16)
            a = Target.GetMemoryRegions()
            mro = None
            for m in a._I_regions:
                if addr >= m._I_start_address and addr <= m._I_end_address:
                    mro = m
                    break
            if mro is None:
                print('seg not found.')
                return

            d = Target.ReadInt(m._I_start_address)
            if d == m._I_start_address + 0x20:
                # thread arena
                start = m._I_start_address + 0x8b0
            else:
                print("for main_arena <start> and <end> address should be specified.")
                return 
                start = m._I_start_address
            end = m._I_end_address
        else:
            print("mm locate <addr>")
            print("mm locate <start> <end> <addr>")
            return

        ArenaVisitor.LocateChunk(start, end, addr)

class cli_mm_addr(Command):
    _cxpr = "mm address"

    def invoke(self, argv):
        addr = int(argv[0], 16)
        a = Target.GetMemoryRegions()
        cnt = 0
        for m in a._I_regions:
            if addr >= m._I_start_address and addr <= m._I_end_address:
                print(m) 

class cli_objgraph(CommandPrefix):
    _cxpr = "og"
    

class cli_objgraph_state(Command):
    _cxpr = "og state"

    def invoke(self, argv):
        import objgraph
        al = sorted(objgraph.typestats().items(), key=lambda x:x[1])
        for k,v in al:
            print('%10d %s' % (v, k))


class cli_objgraph_type(Command):
    _cxpr = "og type"

    def invoke(self, argv):
        import objgraph
        al = objgraph.by_type(argv[0])
        for i in al:
            print(i)

class cli_objgraph_refs(Command):
    _cxpr = "og refs"

    def invoke(self, argv):
        import objgraph
        obj = objgraph.at(argv[0])
        objgraph.show_refs(obj, max_depth=5, filename="og.png")


class cli_objgraph_backrefs(Command):
    _cxpr = "og backrefs"

    def invoke(self, argv):
        import objgraph
        obj = objgraph.at(argv[0])
        objgraph.show_backrefs(obj, max_depth=5, filename="og_b.png")


class cli_mapreduce(CommandPrefix):
    _cxpr = "mapreduce"


class cli_mapreduce_index(Command):
    _cxpr = "mapreduce index"

    def invoke(self, argv):
        snap = HeapSnapshot()
        snap.MapWriteIndex(int(argv[0]))

class cli_mapreduce_snapshot(Command):
    _cxpr = "mapreduce snapshot"

    def invoke(self, argv):
        snap = HeapSnapshot()
        index = int(argv[0])
        snap.MapSnapshot(index)

class cli_mapreduce_reduce(Command):
    _cxpr = "mapreduce reduce"

    def invoke(self, argv):
        snap = HeapSnapshot()
        snap.ReduceGenerate()

