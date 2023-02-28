
from __future__ import print_function, division

import os
import sys
import json
import time

def md5(fname):
    import hashlib
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def xpath(tsr, path, default=None):
    x = tsr
    try:
        for i in path.split('/'):
            if i != "":
                x = x[i]
        return x 
    except:
        pass
    return default 

def title(title):
    print('[ %s ]' % title)

class TechReportText(object):

    def __init__(self, filename):
        with open(filename) as f:
            self._tsr = json.load(f) 
  
    @classmethod
    def ShowDict(cls, core, path):
        siginfo = xpath(core, path)
        if siginfo is None:
            return
        title(path)
        for k,v in siginfo.items():
            print("%s:"%k, v)
        print("")

    @classmethod
    def xflags(cls, x):
        y = ''
        y = y + ('r' if x & 4 else '-')
        y = y + ('w' if x & 2 else '-')
        y = y + ('x' if x & 1 else '-')
        y = y + ('s' if x & 8 else 'p')
        return y

    @classmethod
    def MMap(cls, core):
        mmap = xpath(core, 'mmap')
        if mmap is None:
            return
        title("mmap")
        print("#  ADDRESS        FLAG SIZE")
        for i, m in enumerate(mmap):
            if m['p_memsz'] == 0: continue
            print("%d: %x-%x %s %d" % (i, m['p_vaddr'], m['p_vaddr'] + m['p_memsz'], cls.xflags(m['p_flags']), m['p_memsz']))
        print("")

    @classmethod
    def V8Backtrace(cls, andb):
        pass

    @classmethod
    def NodeVersion(cls, andb):
        nver = xpath(andb, '')

    @classmethod
    def AndbEnv(cls, andb):
        env = xpath(andb, 'envrion')
        if env is None:
            return 
        title("env")
        for i, m in enumerate(env):
            print("%d: %s" % (i, m))
        print("")

    def ShowAll(self):
        """Show TSR in Text format.
        """
        tsr = self._tsr
        title("Noslate Debugger Corefile Report")
        print("tsr_file: %s" % xpath(tsr, 'tsr_file'))
        print("created_time: %s" % xpath(tsr, 'create_time'))

        title("Corefile")
        print("file: %s" % xpath(tsr, 'file/name'))
        print("size: %d" % xpath(tsr, 'file/size'))
        print("md5: %s" % xpath(tsr, 'file/md5'))

        if 'core' in tsr:
            core = tsr['core']
            self.ShowDict(core, 'siginfo')
            self.ShowDict(core, 'prstatus')
            self.ShowDict(core, 'prpsinfo')
            self.MMap(core)

        if 'andb' in tsr:
            andb = tsr['andb']
            self.ShowDict(andb, 'node_version')
        
class TechReport(object):

    def __init__(self, corefile):
        self._core = corefile

    def GenerateFileInfo(self):
        out = {}
        out['name'] = self._core.filename
        out['size'] = self._core.filesize
        out['md5'] = md5(self._core.filename)
        return out

    def GenerateCoreInfo(self):
        """Generate Corefile Info.
        """
        out = {}
        out['files'] = self._core.GetFilesInfo()
        out['siginfo'] = self._core.GetSigInfo()
        out['prstatus'] = self._core.GetPrStatus()
        out['prpsinfo'] = self._core.GetPrPsInfo()
        out['mmap'] = self._core.GetMemMap()

        filesz = 0
        memsz = 0
        for i in out['mmap']:
            filesz = filesz + i['p_filesz']
            memsz = memsz + i['p_memsz']
        out['summay'] = {"dump_size":filesz, "vmem_size":memsz}

        return out

    def GenerateAndbInfo(self, fname='core.v8tsr'):
        out = {}
        if os.path.exists(fname):
            with open(fname) as f:
                out = json.load(f)
        return out

    def Generate(self, savefile="core.tsr"):
        """Generate the TSR.
        """
        out = {}

        out['tsr_file'] = savefile
        out['create_time'] = time.strftime("%Y-%m-%d %H:%M:%S %z")

        out['file'] = self.GenerateFileInfo()
        out['core'] = self.GenerateCoreInfo()
        out['andb'] = self.GenerateAndbInfo()

        with open(savefile, 'w') as f:
            json.dump(out, f)

