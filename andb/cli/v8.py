# -*- coding: UTF-8 -*-

from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix, Target 

""" V8 commands
"""
class cli_v8(CommandPrefix):
    """V8 engine commands.


"""
    _cxpr = "v8"

class cli_v8_version(Command):
    """Show V8 engine version information.
"""
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
    """Inspect a Tagged Object.
"""
    _cxpr = "v8 inspect"

    def invoke(self, argv):
        ObjectVisitor.inspect(argv)

# v8 object cli
class cli_v8_object(Command):
    """Inspect an Object from address.
"""
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
    """Print backtrace of all V8 stack frames.
"""
    _cxpr = "v8 bt"

    def invoke(self, argv):
        StackVisitor().Backtrace()


""" isolate commands
"""
class cli_isolate_prefix(CommandPrefix):
    """Find and select an Isolate in process.

An Isolate represents an Isolated instance of the V8 engine. 
V8 isolates have completely separate states. 
Objects from one isolate must not be used in other isolates. 
When V8 is initialized a default isolate is implicitly created and entered. 
The embedder can create additional isolates and use them in parallel in multiple threads. 
An isolate can be entered by at most one thread at any given time. 
Thus, typically node process may have one main thread Isolate and several worker thread Isolates.

'isolate guess' : Find and select the only first Isolate.
'isolate list'  : List all the Isolates the process/corefile has.
'isolate <id>'  : Select one as current Isolate to debug. 
'isolate apply' : Apply a command to a list of Isolates.

the current Isolate can be referenced simply through convenience value '$isolate'.

For more information about 'isolate' commands, please run 'isolate ?'.
"""
    _cxpr = "isolate"

class cli_isolate(Command):
    """Switch between Isolates.

For multiple Isolates process, ONLY one Isolate can be set at a time.

Syntax: 'isolate [<id>]'
    <id>    : integer number, Select specifed Isolate.
    
without '<id>' shows the current Isolate.

For more information about v8 Isolate, please run 'help isolate'.
"""
    _cxpr = "isolate"

    def invoke(self, argv):
        IsolateGuesser().SelectIndex(argv)

class cli_isolate_guess_pages(Command):
    """Guess Isolate from V8 Heap pages.

Syntax: 'isolate guess stack'

"""
    _cxpr = "isolate guess page"

    def invoke(self, argv):
        IsolateGuesser().GuessFromPages()

class cli_isolate_guess_stack(Command):
    """Guess Isolate from all thread stacks.

Syntax: 'isolate guess stack'

"""
    _cxpr = "isolate guess stack"

    def invoke(self, argv):
        IsolateGuesser().GuessFromStack()

class cli_isolate_list(Command):
    """List all Isolates with summary.

Syntax: 'isolate list [page|stack]'
    page    : guess from pages.
    stack   : guess from stacks.
    
    default method is 'stack'.

The command will cache the Isolates found.

Uses 'isolate <id>' to select an Isolate listed.

"""
    _cxpr = "isolate list"

    def invoke(self, argv):
        IsolateGuesser().ListIsolates()

class cli_isolate_list_pages(Command):
    """List all Isolates from pages.

Syntax: 'isolate list page'
"""
    _cxpr = "isolate list page"

    def invoke(self, argv):
        IsolateGuesser().ListFromPages()

class cli_isolate_list_stack(Command):
    """List all Isolates from stacks.

Syntax: 'isolate list page'
"""
    _cxpr = "isolate list stack"

    def invoke(self, argv):
        IsolateGuesser().ListFromStack()

class cli_isolate_set(Command):
    """Set current isolate to address.

Syntax: 'isolate set <addr>'
    <addr> : hex value, memory address.

"""
    _cxpr = "isolate set"

    def invoke(self, argv): 
        IsolateGuesser().SetAddress(argv)

class cli_isolate_apply_heap_snapshot(Command):
    """Generate HeapSnapshot for all Isolates. 

Syntax: isolate apply all heap snapshot

output files will be named to "isolate_<id>.heapsnapshot".
"""
    _cxpr = "isolate apply all heap snapshot"

    def invoke(self, argv):
        IsolateGuesser().BatchHeapSnapshot()

""" heap commands
"""
class cli_heap(CommandPrefix):
    """V8 Heap commands.
"""
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

