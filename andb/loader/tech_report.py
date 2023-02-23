
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

class TechReport(object):

    def __init__(self, corefile):
        self._core = corefile 

    @classmethod
    def ShowTextReport(self, filename):
        """Show TSR in Text format.
        """
        with open(filename) as f:
            tsr = json.load(f) 
        
        print("Report")
        print("tsr_file: %s" % tsr['tsr_file'])
        print("created_time: %s" % tsr['create_time'])
       
        print("Corefile")
        print("file: %s" % tsr['file']['name'])
        print("size: %d" % tsr['file']['size'])
        print("md5: %s" % tsr['file']['md5'])
        
        core = tsr['core'] 
        
        print("Signal")
        siginfo = core['siginfo']
        print("si_signo: %d" % siginfo['si_signo']) 
        print("si_code: %d" % siginfo['si_code']) 
        print("si_errno: %d" % siginfo['si_errno']) 
        print("si_addr: %d" % siginfo['addr']) 

        print("Memory Map")
        mmap = core['mmap']
        for m in mmap:
            if m['p_memsz'] == 0: continue
            print("%x-%x %x %d" % (m['p_vaddr'], m['p_vaddr'] + m['p_memsz'], m['p_flags'], m['p_memsz']))

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

    def GenerateAndbInfo(self):
        out = {}
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

