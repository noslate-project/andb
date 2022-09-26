
from __future__ import print_function, division

import andb.dbg as dbg 

class Struct(dbg.Struct):
    pass

class malloc_state(Struct):
    """ struct malloc_state """
    
    _typeName = "void"

    kTopOffset = 0x58
    kBinsOffset = 0x68
    kNextOffset = 0x868
    kSystemMemOffset = 0x880
    kMaxSystemMemOffset = 0x888

    @property
    def _top(self):
       return self.LoadPtr(self.kTopOffset)

    @property
    def _bins(self):
        return self.LoadPtr(self.kBinsOffset)

    @property
    def _next(self):
        return self.LoadPtr(self.kNextOffset)

    @property
    def _system_mem(self):
        return self.LoadU64(self.kSystemMemOffset)

    @property
    def _max_system_mem(self):
        return self.LoadU64(self.kMaxSystemMemOffset)

    def Next(self):
        return malloc_state(self._next)


class heap_info(Struct):
    _typeName = "void"

    @property
    def _ar_ptr(self):
        pass

    @property
    def _prev(self):
        pass
    
    @property
    def _size(self):
        pass
    
    @property
    def _mprotect_size(self):
        pass


class malloc_chunk(Struct):
    """ struct malloc_chunk """
    
    _typeName = "void"

    @property
    def _prev_size(self):
        return self.LoadU64(0)

    @property
    def _size(self):
        return self.LoadU64(8)

    @property
    def _fd(self):
        return self.LoadPtr(16)

    @property
    def _bk(self):
        return self.LoadPtr(24)

    @property
    def _fd_nextsize(self):
        return self.LoadPtr(32)

    @property
    def _bk_nextsize(self):
        return self.LoadPtr(40)

    def GetSize(self):
        return self._size & ~0x7

    def IsPrevInUse(self):
        return self._size & 0x1
    
    def IsMMap(self):
        return self._size & 0x2
    
    def IsNoneMainArena(self):
        return self._size & 0x4

class ArenaVisitor:

    @classmethod
    def ParseArena(self, argv):
        if len(argv) == 0:
            addr = dbg.Target.LookupSymbol('main_arena')
        else:
            addr = int(argv[0], 16)
        
        if addr is None:
            print("Arena not found.")
            return None

        mstat = malloc_state(addr)  
        print("0x%x, 0x%x" % (mstat._top, mstat._next))

        begin = mstat
        nxt = begin
        while 1: 
            print("0x%x: 0x%x %u (%u)" % (nxt, nxt._top, nxt._system_mem, nxt._max_system_mem)) 
            nxt = nxt.Next()
            if nxt.address == begin.address:
                break;

    @classmethod
    def ArenaState(self, addr):
        mstat = malloc_state(addr) 

    @classmethod
    def WalkChunks(self, start, end, only_inuse = 0):
        
        i = start
        size_inuse = 0
        size_freed = 0
        saved_chunk = None
        
        while i < end:
            chunk = malloc_chunk(i)
           
            if saved_chunk is not None:
                if chunk.IsPrevInUse():
                    size_inuse += saved_chunk.GetSize()
                else:
                    size_freed += saved_chunk.GetSize()

            if only_inuse:
                if saved_chunk is not None and chunk.IsPrevInUse() and saved_chunk.GetSize() > 16:
                    print("0x%x : " % int(saved_chunk), saved_chunk.GetSize())
            else: 
                print("0x%x : " % i, chunk.GetSize(), chunk.IsMMap(), chunk.IsPrevInUse())

            saved_chunk = chunk
            i += chunk.GetSize()

        print("total %u, inuse(%u), freed(%u)" %( end - start, size_inuse, size_freed))

Struct.LoadAllDwf()
