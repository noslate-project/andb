
from __future__ import print_function

from mmap import mmap, ACCESS_READ, ACCESS_WRITE, PAGESIZE
import struct

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

class Elf:

    class SHTYPE(Enum):
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
        NOTE = 0x00000004

    class NTYPE(Enum):
        NT_GNU_BUILD_ID = 3

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

    def ReadEhdr(self, fd, elfhdr):
        """ parse elf header """

        sd = '2HI3QI6H'
        size = struct.calcsize(sd)
        t = struct.unpack(sd, fd.read(size))
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
        return size

    def ReadShdr(self, fd, elfhdr, sechdrs, offset=0):
        """ parse all sections header """

        off = elfhdr['e_shoff'] + offset
        num = elfhdr['e_shnum']
        size = elfhdr['e_shentsize']
        fd.seek(off)

        for i in range(num):
            t = struct.unpack('2I4Q2I2Q', fd.read(size))
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
        return 0

    def ReadPhdr(self, fd, elfhdr, proghdrs, offset=0):
        """ parse all program header """

        off = elfhdr['e_phoff'] + offset
        num = elfhdr['e_phnum']
        size = elfhdr['e_phentsize']
        fd.seek(off)

        for i in range(num):
            # uint32_t   p_type;
            # uint32_t   p_flags;
            # Elf64_Off  p_offset;
            # Elf64_Addr p_vaddr;
            # Elf64_Addr p_paddr;
            # uint64_t   p_filesz;
            # uint64_t   p_memsz;
            # uint64_t   p_align;
            t = struct.unpack('2I6Q', fd.read(size))
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
        return 0

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
        """ get Section by name """
        for s in self._I_shdrs:
            sh_name = self._I_strtab.Str(s['sh_name'])
            if sh_name == name:
                return Elf.Section(self, sh_name, s['sh_offset'], s['sh_size'])
        return None

    # TODO: refreform to a independent class to represent it
    def ReadNote(self, phNoteHdr):
        m = self._I_mmap
        m.seek(self._I_offset+phNoteHdr['p_offset']);
        noteContent = m.read(phNoteHdr['p_memsz']);
        notes = []
        offset = 0
        while offset < len(noteContent):
            t = struct.unpack('3I', noteContent[offset:offset + 12])
            n_namesz = t[0]
            n_descsz = t[1]
            n_type = t[2]
            offset = offset + 12
            name = noteContent[offset:offset+n_namesz]
            offset = offset+n_namesz
            desc = noteContent[offset:offset+n_descsz]
            offset = offset+n_descsz
            notes.append((name, desc, n_type))
        return notes

    def getProgHdrs(self):
        return self._I_phdrs

    def Load(self, filename, offset=0):

        # open file
        f = open(filename, 'rb')
        self._I_file = f
        self._I_offset = offset

        # get file size
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)

        # mmap
        m = mmap(f.fileno(), size, access = ACCESS_READ)

        self._I_mmap = m

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
        elfhdr = {}
        size = self.ReadEhdr(m, elfhdr)

        self._I_ehdr = elfhdr

        # read section headers
        sechdrs = []
        size = self.ReadShdr(m, elfhdr, sechdrs)
        self._I_shdrs = sechdrs
        
        # get strtab, strtab maybe not when elf is corefile 
        for s in sechdrs:
            if s['sh_type'] == Elf.SHTYPE.STRTAB:
                self._I_strtab = Elf.StrTab(self, '.shstrtab', s['sh_offset'], s['sh_size'])
                break
        # if self._I_strtab is None:
        #     raise Exception

        # read Program header
        proghdrs = []
        size = self.ReadPhdr(m, elfhdr, proghdrs, offset)
        self._I_phdrs = proghdrs
    
    def LoadCorefileProgElf(self, filename, offset=0):

        # open file
        f = open(filename, 'rb')
        self._I_file = f
        self._I_offset = offset

        # get file size
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)

        # mmap
        m = mmap(f.fileno(), size, access = ACCESS_READ)

        self._I_mmap = m

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
        elfhdr = {}
        size = self.ReadEhdr(m, elfhdr)

        self._I_ehdr = elfhdr
        
        # read Program header
        proghdrs = []
        size = self.ReadPhdr(m, elfhdr, proghdrs, offset)
        self._I_phdrs = proghdrs        
      
    def Unload(self):
        self._I_mmap.close()
        self._I_file.close()
        self._I_mmap = None
        self._I_file = None
        print('Elf Unloaded')

