import andb 
import traceback

class Struct(andb.Struct):
    pass

class Enum(andb.Enum):
    pass

class Isolate(Struct):
    _typeName = 'v8::internal::Isolate'

class MemoryChunk(Struct):
    _typeName = 'v8::internal::MemoryChunk'

class InstanceType(Enum):
    _typeName = 'v8::internal::InstanceType'

class cli_v8(andb.CommandPrefix):
    _cxpr = "v8"

class cli_v8_version(andb.Command):
    _cxpr = "v8 version"

    def invoke(self, argv):
        print 'hello world', argv

class cli_v8_isolate_guess(andb.Command):
    _cxpr = "v8 isolate guess"

    def invoke(self, argv):
        print "isolate guess", argv

class cli_v8_inspect(andb.Command):
    _cxpr = "v8 inspect"

    def invoke(self, argv):
        print "inspect ", argv


Struct.LoadAllDwf()
Enum.LoadAllDwf()
andb.Command.RegisterAll()

a = Isolate(0x416ec60)['heap_']['gc_state_']
print(a)

andb.dbg.MemoryRegions.Load()


