
from __future__ import print_function, division
import gdb

class infoFiles:

    def __init__(self):
        self.maps = self._readMap()

    def _readMap(self):
        maps = []
        files  = gdb.execute("info files", to_string=True)
        for f in files.splitlines():
            f = f.replace("\t", "")
            n = f.split(" ")
            if len(n) > 4 and n[4].find("load") >= 0:
                addr_begin = int(n[0], 16);
                addr_end = int(n[2], 16);
                #print("%s %x-%x (%d)"%(n[4], addr_begin, addr_end, addr_end-addr_begin))
                maps.append({'begin':addr_begin, 'end':addr_end, 'name':n[4]})
        return maps

    def getMaps(self):
        return self.maps

    def findMap(self, addr):
        for f in self.maps:
            if addr >= f['begin'] and addr <= f['end']:
                return f
        return None

class cli_mem(gdb.Command):

    def __init__(self):
        gdb.Command.__init__ (self, "mm", gdb.COMMAND_USER, prefix=True)

class cli_mm_find(gdb.Command):
    
    def __init__(self):
        gdb.Command.__init__ (self, "mm find", gdb.COMMAND_USER)

    def invoke (self, arg, tty):
        args = arg.split(" ") 
        nf = infoFiles()
        maps = nf.maps
        for m in maps:
            if (m['begin'] == m['end']):
                continue
            
            v = gdb.execute("find %s %s, %s, %s"%(args[0], m['begin'], m['end'], args[1]), to_string=True)
            if (v.find("pattern found") >0):
                print v

        return None

class cli_mm_addr(gdb.Command):
    
    def __init__(self):
        gdb.Command.__init__ (self, "mm address", gdb.COMMAND_USER)

    def invoke(self, arg, tty):
        nf = infoFiles()
        addr = int(arg, 16)
        map = nf.findMap(addr)
        if map:
            print(map)

class cli_mm_sum(gdb.Command):
   
    def __init__(self):
        gdb.Command.__init__ (self, "mm sum", gdb.COMMAND_USER)

    def invoke (self, arg, tty):
        nf = infoFiles()
        maps = nf.maps
        size = 0
        for m in maps:
            size += m['end'] - m['begin']
        print("virtual memory:", size)
        return None

cli_mem()
cli_mm_find()
cli_mm_sum()
cli_mm_addr()
