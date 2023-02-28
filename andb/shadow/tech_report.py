from __future__ import print_function, division

import sys
import os
import json
import re

import andb.dbg as dbg
import andb.v8 as v8
import andb.node as node
from .visitor import StackVisitor, NodeEnvGuesser, AworkerVisitor

from andb.utility import (
    profiler,
    Logging as log,
)

class AndbTechReport(object):

    def __init__(self):
        pass

    def GetEnviron(self):
        env = dbg.Target.GetCurrentThread().GetEnviron()
        
        def omit_secret(line):
            m = re.search("^(.*secret.*?)=(.*)", line, re.IGNORECASE)
            if m is None:
                return line
            return m.group(1) + "=***"

        out = []
        for l in env:
            out.append(omit_secret(l))
        return out 

    @property
    def node_version(self):
        meta = None
        if NodeEnvGuesser.IsNode():
            meta = NodeEnvGuesser.GetMeta()
        elif AworkerVisitor.IsAworker():
            meta = AworkerVisitor.GetMeta()
        return meta

    def GenerateV8Heap(self):
        pass

    def GenerateV8Backtrace(self, out):
        sv = StackVisitor()
        frames = sv.GetV8Frames()
        out['frames'] = frames

    def Generate(self, savefile="core.v8tsr"):
        out = {}

        out['node_version']  = self.node_version

        out['v8'] = {}
        self.GenerateV8Backtrace(out)
        out['environ'] = self.GetEnviron()

        with open(savefile, 'w') as f:
            json.dump(out, f)

