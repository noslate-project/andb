from __future__ import print_function, division

import sys
import os
import json

import andb.dbg as dbg
import andb.v8 as v8
import andb.node as node
from .visitor import StackVisitor, NodeEnvGuesser

from andb.utility import (
    profiler,
    Logging as log,
)

class AndbTechReport(object):

    def __init__(self):
        pass

    def GetThreadList(self):
        pass

    def v8bt(self):
        """Return V8 Backtrace
        """
        pass

    def GetIsolateList(self):
        pass

    def GetGlobalObjects(self):
        pass

    def GetHeapInfo(self):
        pass

    @property
    def node_version(self):
        meta = NodeEnvGuesser.GetMeta()
        return meta

    def GenerateV8Heap(self):
        pass

    def GenerateV8Backtrace(self, out):
        sv = StackVisitor()
        frames = sv.GetV8Frames()
        for f in frames:
            print(f)
        out['frames'] = frames

    def Generate(self, savefile="core.v8tsr"):
        out = {}

        out['node_version']  = self.node_version

        out['v8'] = {}
        self.GenerateV8Backtrace(out)

        with open(savefile, 'w') as f:
            json.dump(out, f)

