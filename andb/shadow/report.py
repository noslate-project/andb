from __future__ import print_function, division

import sys
import os
import json

import andb.dbg as dbg
import andb.v8 as v8
import andb.node as node
from .visitor import StackVisitor, NodeEnvGuesser, AworkerVisitor, IsolateGuesser 

from andb.utility import (
    profiler,
    Logging as log,
)

class V8IsolateReport(object):

    def __init__(self, iso):
        self._isolate = iso
        self._out = {}

    def Generate(self):
        heap = self._isolate.Heap()
        self._out['address'] = self._isolate.address
        self._out['id'] = self._isolate.id
        self._out['external_memory_size'] = self._isolate.external_memory_
        self._out['heap'] = heap.Flatten()
        return self._out

class AndbTechReport(object):

    def __init__(self):
        self._out = {}

    @classmethod
    def _omit_secret(cls, line):
        lower = line.lower()
        if not 'secret' in lower:
            return line
        arr = line.split('=')
        return arr[0] + "=***"

    def GenerateEnviron(self):
        """ Dynamic Envrion Variables, libc saves it in process heap.
        """
        arr = []
        try:
            env_t = dbg.Type.LookupType('char').GetPointerType().GetPointerType()
            addr = dbg.Target.ReadSymbolValue('__environ')
            env = dbg.Value.CreateTypedAddress(env_t, addr)
            for i in range(1000):
                v = env[i]
                if v == 0:
                    break
                arr.append(self._omit_secret(v.GetCString()))
        except Exception as e:
            print('__environ cannot located.', e)
        if len(arr) <= 0:
            return
        self._out['environ'] = arr

    def GenerateInitialEnviron(self):
        """ Initial Environ Variables (can't change), saved in thread stack top,
            can be read in /proc fs.
        """
        env = dbg.Target.GetCurrentThread().GetEnviron()
        arr = []
        for i in env:
            arr.append(self._omit_secret(i))
        if len(arr) <= 0:
            return
        self._out['init_environ'] = arr

    def GenerateNodeVersion(self):
        meta = None
        if NodeEnvGuesser.IsNode():
            meta = NodeEnvGuesser.GetMeta()
        elif AworkerVisitor.IsAworker():
            meta = AworkerVisitor.GetMeta()
        if meta is None:
            return
        self._out['node_version'] = meta

    def GenerateV8IsolateList(self):
        guess = IsolateGuesser()
        iso_list = guess.ListFromPages()
        arr = []
        for k,v in iso_list.items():
            iso_rpt = V8IsolateReport(v)
            arr.append(iso_rpt.Generate())
        self._out['isolates'] = arr

    def GenerateV8Backtrace(self):
        sv = StackVisitor()
        frames = sv.GetV8Frames()
        self._out['frames'] = frames

    def Generate(self, savefile="core.v8tsr"):
        self.GenerateNodeVersion()
        self.GenerateV8Backtrace()
        self.GenerateEnviron()
        self.GenerateInitialEnviron()
        self.GenerateV8IsolateList()

        with open(savefile, 'w') as f:
            json.dump(self._out, f)

