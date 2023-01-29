# -*- coding: UTF-8 -*-

from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix, Target 

""" V8 commands
"""
class cli_v8(CommandPrefix):
    _cxpr = "v8"

class cli_v8_version(Command):
    _cxpr = "v8 version"

    @staticmethod
    def PrintV8Version():
        # TBD: find symbol variables        
        major = Target.LoadRaw("'v8::internal::Version'::major_") 
        minor = Target.LoadRaw("'v8::internal::Version'::minor_") 
        patch = Target.LoadRaw("'v8::internal::Version'::patch_") 
        build = Target.LoadRaw("'v8::internal::Version'::build_") 
        log.print ("%d.%d.%d.%d" % (major, minor, build, patch));
        ptr = Target.LoadRaw("'v8::internal::Version'::version_string_") 
        version = Target.ReadCStr(ptr)
        log.print (version)

    def invoke(self, argv):
        self.PrintV8Version()

# v8 inspect cli
class cli_v8_inspect(Command):
    _cxpr = "v8 inspect"

    def invoke(self, argv):
        ObjectVisitor.inspect(argv)

# v8 object cli
class cli_v8_object(Command):
    _cxpr = "v8 object"

    def invoke(self, argv):
        ObjectVisitor.inspectObject(argv)

# v8 print <type> <address/tag>
class cli_v8_print(Command):
    _cxpr = "v8 print"

    def invoke(self, argv):
        ObjectVisitor.printObject(argv)

# v8 bt
class cli_v8_bt(Command):
    _cxpr = "v8 bt"

    def invoke(self, argv):
        StackVisitor().Backtrace()


""" isolate commands
"""
class cli_isolate(CommandPrefix):
    _cxpr = "isolate"

class cli_isolate_guess_pages(Command):
    _cxpr = "isolate guess page"

    def invoke(self, argv):
        IsolateGuesser().GuessFromPages()

class cli_isolate_guess_stack(Command):
    _cxpr = "isolate guess stack"

    def invoke(self, argv):
        IsolateGuesser().GuessFromStacks()

class cli_isolate_list_pages(Command):
    _cxpr = "isolate list page"

    def invoke(self, argv):
        IsolateGuesser().ListFromPages()


class cli_isolate_list_stack(Command):
    _cxpr = "isolate list stack"

    def invoke(self, argv):
        IsolateGuesser().ListFromStack()

class cli_isolate_set(Command):
    _cxpr = "isolate set"

    def invoke(self, argv):
        IsolateGuesser().Select(argv)


""" heap commands
"""
class cli_heap(CommandPrefix):
    _cxpr = "heap"
    _is_prefix = True

class cli_heap_spaces(Command):
    _cxpr = "heap space"

    def invoke(self, argv):
        HeapVisitor().HeapSpace(argv)

class cli_heap_chunk(Command):
    _cxpr = "heap page"

    def invoke(self, argv):
        if len(argv) == 0:
            print("usage: heap page 0x12345")
            return
        HeapVisitor().DumpChunk(argv)

class cli_heap_dump(Command):
    _cxpr = "heap dump"

    def invoke (self, argv):
        if len(argv) == 0:
            print("""usage: heap dump <options> 
    heap dump : dump all heap objects in summay.
    heap dump <space> : dump all <space> objects in summay.
    heap dump <space> type <name> : dump all objects only match the type name.
    """)
            return
        else:
            HeapVisitor().HeapDump(argv)

class cli_heap_find(Command):
    _cxpr = "heap find"

    def invoke(self, argv):
        if len(argv) < 2:
            print("usage: heap find <space> <object>")
            return
        HeapVisitor().HeapFind(argv)

class cli_heap_snapshot(Command):
    _cxpr = "heap snapshot"

    def invoke (self, argv):
        if len(argv) == 0:
            arg = "core.heapsnapshot"
        else:
            arg = argv[0]
        snap = HeapSnapshot()
        snap.Generate(arg)
        del snap

class cli_heap_global(Command):
    _cxpr = "heap global"

    def invoke (self, argv):
        HeapVisitor().ShowGlobal(argv)

class cli_heap_summary(Command):
    _cxpr = "heap summary"

    def invoke (self, argv):
        HeapVisitor().ShowMapSummary(argv)

class cli_heap_map(Command):
    _cxpr = "heap map"

    def invoke (self, argv):
        HeapVisitor().SearchMapSummary(argv)

class cli_heap_follow(Command):
    _cxpr = "heap follow"

    def invoke (self, argv):
        HeapVisitor().FollowTag(argv)

class cli_heap_string_save(Command):
    _cxpr = 'heap string save' 

    def invoke(self, argv):
        if len(argv) == 0:
            print("heap string save <tag>")
        
        f = StringVisitor.SaveFile(int(argv[0], 16))
        print("Saved %s" % f)

class cli_heap_find_string_save(Command):
    _cxpr = 'heap string startswith-save' 

    def invoke(self, argv):
        if len(argv) != 2:
            print("heap string startswith-save <space> <start_with_str>")

        StringVisitor.StartsWithSave(argv)

# Tail Imports
from andb.shadow import (
    ObjectVisitor, 
    HeapVisitor, 
    IsolateGuesser, 
    HeapSnapshot,
    StackVisitor,
    StringVisitor,
)

from andb.utility import Logging as log

