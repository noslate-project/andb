
from __future__ import print_function

import os
from mmap import mmap, ACCESS_READ, ACCESS_WRITE, PAGESIZE
import struct

import andb.py23 as py23

class Enum:
   
    @classmethod
    def Name(cls, num):
        for i in dir(cls):
            v = getattr(cls, i)
            if isinstance(v, int):
                if v == num:
                    return i
        return "unknown(0x%x)" % num

def ReadCStr(sec):
    """ read section offset as c-style string """
    sz = []
    while True:
        c = sec.Read(1)
        c = c.decode('utf-8')
        #c = str(c, 'utf-8')
        if c == chr(0):
            return "".join(sz) 
        sz.append(c)

def roundup(x, up):
    y = (x - 1) // 4 + 1
    return y*up 


class Elf:
    
    # file opened
    _I_file = None
  
    # mmap fd 
    _I_mmap = None
    
    # instance base offset from mmap front
    _I_offset = None 

    # last saved offset
    _saved_offset = 0

    # elf header
    _ehdr = None

    # program headers
    _phdrs = None

    # section headers
    _shdrs = None

    # string table
    _strtab = None

    # notes
    _notes = None

    class SHTYPE(Enum):
        """Section Header Type
        """
        NULL_TYPE = 0
        PROGBITS = 1
        SYMTAB = 2
        STRTAB = 3
        RELA = 4
        HASH = 5
        DYNAMIC = 6
        NOTE = 7
        NOBITS = 8
        REL = 9
        SHLIB = 10
        DYNSYM = 11
        INIT_ARRAY = 14
        FINI_ARRAY = 15
        PREINIT_ARRAY = 16
        GROUP = 17
        SYMTAB_SHNDX = 18

    class PHTYPE(Enum):
        """Program Header Type
        """
        NOTE = 0x00000004

    class NTYPE(Enum):
        """Note Header Type
        """
        NT_GNU_BUILD_ID = 3
        NT_PRSTATUS = 1
        NT_PRFPREG = 2
        NT_PRPSINFO = 3
        NT_TASKSTRUCT = 4
        NT_AUXV = 6
        NT_SIGINFO = 0x53494749
        NT_FILE = 0x46494c45
    
    class Section:
        """ represents a Section in Elf file. """

        def __init__(self, elf, name, offset, size):
            self._elf = elf
            self._name = name
            self._offset = offset
            self._size = size

        def Seek(self, offset):
            off = self._offset + offset
            self._elf._I_mmap.seek(off)

        def Tell(self):
            off = self._elf._I_mmap.tell()
            return off - self._offset

        def Read(self, size):
            return self._elf._I_mmap.read(size) 

        def ReadU8(self):
            return struct.unpack('B', self.Read(1))[0] 
        
        def ReadU16(self):
            return struct.unpack('H', self.Read(2))[0] 
        
        def ReadU32(self):
            return struct.unpack('I', self.Read(4))[0] 
        
        def ReadU64(self):
            return struct.unpack('Q', self.Read(8))[0] 
        
        def ReadI8(self):
            return struct.unpack('b', self.Read(1))[0] 
        
        def ReadI16(self):
            return struct.unpack('h', self.Read(2))[0] 
        
        def ReadI32(self):
            return struct.unpack('i', self.Read(4))[0] 
        
        def ReadI64(self):
            return struct.unpack('q', self.Read(8))[0] 
        
        def ReadUleb128(self):
            """ Extract a ULEB128 value """
            byte = self.ReadU8()
            if byte & 0x80:
                result = byte & 0x7f
                shift = 7
                while byte & 0x80:
                    byte = self.ReadU8()
                    result |= (byte & 0x7f) << shift
                    shift += 7
                return result
            else:
                return byte

        def ReadSleb128(self):
            """ Extract a SLEB128 value """
            result = 0
            shift = 0
            size = 64
            byte = 0
            bytecount = 0
            while 1:
                bytecount += 1
                byte = self.ReadU8()
                result |= (byte & 0x7f) << shift
                shift += 7
                if (byte & 0x80) == 0:
                    break
            # Sign bit of byte is 2nd high order bit (0x40)
            if (shift < size and (byte & 0x40)):
                result |= - (1 << shift)
            return result

    class StrTab(Section):
        """ strtab is a special secion holds all elf strings """ 

        def Str(self, index):
            self.Seek(index)
            return ReadCStr(self) 

    """Begin Elf methods.
    """
    def Seek(self, offset):
        """Seek in relative offset with retore.
        """
        m = self._I_mmap
        self._saved_offset = m.tell()
        x = self._I_offset + offset
        m.seek(x)
        return m

    def Restore(self):
        """Retore last seek.
        """
        m = self._I_mmap
        m.seek(self._saved_offset)
        return m

    def GetEhdr(self):
        """parse elf header 
        """
        if self._ehdr:
            return self._ehdr

        sd = '2HI3QI6H'
        size = struct.calcsize(sd)

        m = self.Seek(16) 
        t = struct.unpack(sd, m.read(size))
        elfhdr = {}
        elfhdr['e_type']= t[0]
        elfhdr['e_machine'] = t[1]
        elfhdr['e_version'] = t[2]
        elfhdr['e_entry'] = t[3]
        elfhdr['e_phoff'] = t[4]
        elfhdr['e_shoff'] = t[5]
        elfhdr['e_flags'] = t[6]
        elfhdr['e_ehsize'] = t[7]
        elfhdr['e_phentsize'] = t[8]
        elfhdr['e_phnum'] = t[9]
        elfhdr['e_shentsize'] = t[10]
        elfhdr['e_shnum'] = t[11]
        elfhdr['e_shstrndx'] = t[12]
        self.Restore() 
        
        self._ehdr = elfhdr
        return elfhdr 

    def GetShdrs(self):
        """parse all sections header 
        """
        if self._shdrs:
            return self._shdrs

        elfhdr = self.GetEhdr()
        off = elfhdr['e_shoff'] 
        num = elfhdr['e_shnum']
        size = elfhdr['e_shentsize']
        
        sechdrs = []
        m = self.Seek(off)
        for i in range(num):
            t = struct.unpack('2I4Q2I2Q', m.read(size))
            sec = {}
            sec['sh_name'] = t[0]
            sec['sh_type'] = t[1]
            sec['sh_flags'] = t[2]
            sec['sh_addr'] = t[3]
            sec['sh_offset'] = t[4]
            sec['sh_size'] = t[5]
            sec['sh_link'] = t[6]
            sec['sh_info'] = t[7]
            sec['sh_addralign'] = t[8]
            sec['sh_entsize'] = t[9]
            sechdrs.append(sec)
        self.Restore()

        self._shdrs = sechdrs
        return sechdrs 

    def GetPhdrs(self):
        """ parse all program header """

        if self._phdrs:
            return self._phdrs

        elfhdr = self.GetEhdr()
        off = elfhdr['e_phoff']
        num = elfhdr['e_phnum']
        size = elfhdr['e_phentsize']
        
        proghdrs = []
        m = self.Seek(off)
        for i in range(num):
            # uint32_t   p_type;
            # uint32_t   p_flags;
            # Elf64_Off  p_offset;
            # Elf64_Addr p_vaddr;
            # Elf64_Addr p_paddr;
            # uint64_t   p_filesz;
            # uint64_t   p_memsz;
            # uint64_t   p_align;
            t = struct.unpack('2I6Q', m.read(size))
            hdr = {}
            hdr['p_type'] = t[0]
            hdr['p_flags'] = t[1]
            hdr['p_offset'] = t[2]
            hdr['p_vaddr'] = t[3]
            hdr['p_paddr'] = t[4]
            hdr['p_filesz'] = t[5]
            hdr['p_memsz'] = t[6]
            hdr['p_align'] = t[7]
            proghdrs.append(hdr)
        self.Restore()

        self._phdrs = proghdrs 
        return hdr 

    def SecEntry(self):
        """ for elf shares one mmap entry,
            SecEntry() is used for section switch.
            save current Section.Tell() and restore after Section finish.

            e.g.
            save = SecEntry()
            sec.Seek(xxx)
            SecExit(save)
        """
        return self._I_mmap.tell()

    def SecExit(self, save):
        self._I_mmap.seek(save)

    def GetSection(self, name):
        """get Section by name
        """
        for s in self._I_shdrs:
            sh_name = self._I_strtab.Str(s['sh_name'])
            if sh_name == name:
                return Elf.Section(self, sh_name, s['sh_offset'], s['sh_size'])
        return None

    # TODO: refreform to a independent class to represent it
    def GetNotes(self):
        if self._notes:
            return self._notes

        phNoteHdr = None
        for p in self.GetPhdrs():
            if p['p_type'] == Elf.PHTYPE.NOTE:
                phNoteHdr = p
        if phNoteHdr is None:
            return None

        m = self.Seek(phNoteHdr['p_offset'])
        size = phNoteHdr['p_memsz']
        if size == 0:
            size = phNoteHdr['p_filesz']
        noteContent = m.read(size);

        notes = []
        offset = 0
        while offset < len(noteContent):
            t = struct.unpack('3I', noteContent[offset:offset + 12])
            n_namesz = t[0]
            n_descsz = t[1]
            n_type = t[2]
            offset = offset + 12
            name = noteContent[offset:offset + n_namesz]
            offset = offset + roundup(n_namesz, 4)
            desc = noteContent[offset:offset + n_descsz]
            offset = offset + roundup(n_descsz, 4)
            notes.append((name, desc, n_type))
        self.Restore()

        self._notes = notes
        return notes

    @staticmethod
    def NtFiles(note):
        o = [] 

        def cstr(note, offset):
            a = note[offset:]
            i = a.index('\0')
            assert i > offset
            return a[:i]

        off = 0
        t = struct.unpack_from('2Q', note, off)
        size = t[0]
        #o['page_size'] = t[1]

        off = 16

        for i in range(size):
            assert off < len(note)
            t = struct.unpack_from('3Q', note, off)
            
            f = {}
            f['start_addr'] = t[0]
            f['end_addr'] = t[1]
            f['offset'] = t[2]
            off = off + 24
            o.append(f)

        names = note[off:].decode('utf8').split('\0')

        for i in range(size):
            t = names[i]
            o[i]['name'] = t

        return o

    @staticmethod
    def NtSigInfo(note):
        o = {}
        off = 0
        t = struct.unpack_from('2Ii', note, off)
        o['si_signo'] = t[0]
        o['si_code'] = t[1]
        o['si_errno'] = t[2]
        off = off + 16 

        import signal
        # SIGILL, SIGFPE, SIGSEGV, SIGBUS, SIGTRAP, SIGEMT
        if o['si_signo'] == signal.SIGILL or \
            o['si_signo'] == signal.SIGFPE or \
            o['si_signo'] == signal.SIGSEGV or \
            o['si_signo'] == signal.SIGBUS or \
            o['si_signo'] == signal.SIGTRAP:
            t = struct.unpack_from('Q', note, off)
            o['addr'] = t[0]
        else:
            t = struct.unpack_from('3I', note, off)
            o['sender_pid'] = t[0]
            o['sender_uid'] = t[1]
            o['status'] = t[2]
        
        return o

    @staticmethod
    def timeval(note, off):
        t = struct.unpack_from('2Q', note, off)
        return t

    @staticmethod
    def NtPrStatus(note):
        o = {}
        
        off = 0
        fmt = '3Ih2x2Q4I8Q'
        t = struct.unpack_from(fmt, note, off)
        off = off + struct.calcsize(fmt) 
        
        o['si_signo'] = t[0]
        o['si_code'] = t[1]
        o['si_errno'] = t[2]
        o['pr_cursig'] = t[3]
        o['pr_sigpend'] = t[4]
        o['pr_sighold'] = t[5]
        o['pr_pid'] = t[6]
        o['pr_ppid'] = t[7]
        o['pr_pgrp'] = t[8]
        o['pr_sid'] = t[9]
        o['pr_utime'] = t[10] + t[11] / 1000000.0
        o['pr_stime'] = t[12] + t[13] / 1000000.0
        o['pr_cutime'] = t[14] + t[15] / 1000000.0 
        o['pr_cstime'] = t[16] + t[17] / 1000000.0
        return o
    
    @staticmethod
    def NtPrPsInfo(note):
        o = {}
        off = 0
        fmt = 'bc2bQ2I4i16s80s'
        t = struct.unpack_from(fmt, note, off)
        o['pr_state'] = t[0]
        o['pr_sname'] = t[1].decode('utf8')
        o['pr_zomb'] = t[2]
        o['pr_nice'] = t[3]
        o['pr_flag'] = t[4]
        o['pr_uid'] = t[5]
        o['pr_gid'] = t[6]
        o['pr_pid'] = t[7]
        o['pr_ppid'] = t[8]
        o['pr_pgrp'] = t[9]
        o['pr_sid'] = t[10]
        o['pr_fname'] = t[11].decode('utf8').split('\0')[0]
        o['pr_psargs'] = t[12].decode('utf8').split('\0')[0]
        return o
    
    @staticmethod
    def NtGnuBuildId(note):
        return "".join("{:02x}".format(py23.byte2int(c)) for c in note)

    def GetNtFiles(self):
        for (name, desc, n_type) in self.GetNotes():
            if n_type == Elf.NTYPE.NT_FILE:
                return self.NtFiles(desc)
        return None 

    def GetNtSigInfo(self):
        for (name, desc, n_type) in self.GetNotes():
            if n_type == Elf.NTYPE.NT_SIGINFO:
                return self.NtSigInfo(desc)
        return None 

    def GetNtPrStatus(self):
        for (name, desc, n_type) in self.GetNotes():
            if n_type == Elf.NTYPE.NT_PRSTATUS:
                return self.NtPrStatus(desc)
        return None 

    def GetNtPrPsInfo(self):
        for (name, desc, n_type) in self.GetNotes():
            if n_type == Elf.NTYPE.NT_PRPSINFO:
                return self.NtPrPsInfo(desc)
        return None 
    
    def GetBuildId(self):
        noteBuildId = None
        for (name, desc, n_type) in self.GetNotes():
            if name == b'GNU\x00' and n_type == Elf.NTYPE.NT_GNU_BUILD_ID:
                return self.NtGnuBuildId(desc)
        return None

    def Load(self, filename):
        """ Load Elf file to memory
        """

        # open file
        f = open(filename, 'rb')
        self._I_file = f
        self._I_offset = 0 

        # get file size
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)

        # mmap
        m = mmap(f.fileno(), size, access = ACCESS_READ)
        self._I_mmap = m

        m.seek(0)
        magic = m.read(16)
        
        # compact py2 and py3
        if isinstance(magic, str):
            magic = [ord(i) for i in magic]

        if magic[0] != 127 or \
           magic[1] != ord('E') or \
           magic[2] != ord('L') or \
           magic[3] != ord('F'):
            print ("error: not a valid elf file.")
            return

        # read elf header
        elfhdr = self.GetEhdr()

        # read section headers
        sechdrs = self.GetShdrs()
        
        # get strtab, strtab maybe not when elf is corefile 
        for s in sechdrs:
            if s['sh_type'] == Elf.SHTYPE.STRTAB:
                self._strtab = Elf.StrTab(self, '.shstrtab', s['sh_offset'], s['sh_size'])
                break
        # if self._I_strtab is None:
        #     raise Exception

        # read Program header
        proghdrs = self.GetPhdrs()

    def AttachV(self, vaddr):

        phdrs = self.GetPhdrs()
        for i in phdrs:
            if i['p_flags'] & 0x1 and \
               vaddr >= i['p_vaddr'] and \
               vaddr <= i['p_vaddr'] + i['p_memsz']:
                #print("0x%x %d %d" % (i['p_vaddr'], i['p_filesz'], i['p_offset']))
                elf = Elf()
                elf.LoadOffset(self, i['p_offset'])
                return elf 

        return None

    def LoadOffset(self, elf, offset=0):
        """Attach an Elf in memory with offset as a new Elf.
        """
        assert isinstance(elf, Elf)
        # as we didn't opened Elf file, _I_file is not saved.
        self._I_mmap = elf._I_mmap
        self._I_offset = offset
   
        #def LoadCorefileProgElf(self, filename, offset=0):
        m = self._I_mmap
        m.seek(offset)

        magic = m.read(16)
        
        # compact py2 and py3
        if isinstance(magic, str):
            magic = [ord(i) for i in magic]

        if magic[0] != 127 or \
           magic[1] != ord('E') or \
           magic[2] != ord('L') or \
           magic[3] != ord('F'):
            print ("error: not a valid elf file.")
            return

        # read elf header
        elfhdr = self.GetEhdr()
        
        # read Program header
        proghdrs = self.GetPhdrs()
      
    def Unload(self):
        """Unload Elf created by Load or Attach.
        """
        if self._I_file:
            self._I_mmap.close()
            self._I_file.close()
        self._I_mmap = None
        self._I_file = None
        print('Elf Unloaded')

    @property
    def filename(self):
        if self._I_file:
            return self._I_file.name
        return None

    @property
    def filesize(self):
        f = self.filename
        if f:
            st = os.stat(f)
            return st.st_size
        return 0
