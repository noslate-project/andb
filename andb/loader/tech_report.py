
from __future__ import print_function, division

import os
import sys
import json
import time

class TechReport(object):

    def __init__(self, corefile):
        self._core = corefile 

    def ShowTextReport(self, filename):
        """Show TSR in Text format.
        """
        with open(filename, "") as f
            tsr = json.load(f) 
        
        print("Core")
        print("filename: %s" % tsr['corefile'])
        print("filesize: %d" % tsr['coresize'])
        print("created_time: %s" % tsr['create_time'])
        print("Signal Info")
        

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
        
        out['corefile'] = self._core.filename
        out['coresize'] = self._core.filesize
        out['create_time'] = time.strftime("%Y-%m-%d %H:%M:%S %z")
        out['coreinfo'] = self.GenerateCoreInfo()
        out['andb'] = self.GenerateAndbInfo()

        with open(savefile, 'w') as f:
            json.dump(out, f)

