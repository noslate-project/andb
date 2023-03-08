
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
    print('[ %s ]' % title.upper())

class TechReportText(object):

    def __init__(self, filename):
        with open(filename) as f:
            self._tsr = json.load(f) 
  
    @classmethod
    def ShowDict(cls, core, path):
        d = xpath(core, path)
        if d is None:
            return
        title(path)
        def _showDict(d, tab=0):
            for k,v in d.items():
                if isinstance(v, dict):
                    print("%*s%s:"%(tab, '', k))
                    _showDict(v, tab=tab+2)
                else:
                    print("%*s%s: %s"%(tab, '', k, v))
        _showDict(d)
        print("")

    @classmethod
    def ShowList(cls, core, path):
        x = xpath(core, path)
        if x is None:
            return 
        title(path) 
        for i in range(len(x)):
            d = x[i]
            print("%d %s" % (i, d))

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
        def descStr(f):
            fname = f['function_name']
            if fname is None or fname == '':
                fname = "(anonymous)"
            
            if fname[0] == '<':
                return fname
            
            args = [] 
            for arg in f['args']:
                args.append("%s=%s" % (arg[0], arg[1]))
            
            pos = ""
            if f['position'] and f['position'][0]:
                pos = "at %s:%s" % (f['position'][0], f['position'][1])
            return "%s(%s) %s" %(fname, ", ".join(args), pos)

        frames = xpath(andb, 'frames') 
        if frames is None:
            return
        title("v8 backtrace")
        for i, f in enumerate(frames):
            print("#%d"%i, descStr(f))
        print("")

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
        print("")

        title("Corefile")
        print("file: %s" % xpath(tsr, 'file/name'))
        print("size: %d" % xpath(tsr, 'file/size'))
        print("md5: %s" % xpath(tsr, 'file/md5'))
        print("")

        if 'core' in tsr:
            core = tsr['core']
            self.ShowDict(core, 'siginfo')
            self.ShowDict(core, 'prstatus')
            self.ShowDict(core, 'prpsinfo')
            #self.MMap(core)

        if 'andb' in tsr:
            andb = tsr['andb']
            self.ShowDict(andb, 'node_version')
            self.V8Backtrace(andb)
            self.ShowList(andb, 'environ')

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

