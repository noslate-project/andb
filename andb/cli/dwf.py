# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import sys
from andb.dbg import (
    Command, 
    CommandPrefix,
    Dwf
)


class cli_dwf(CommandPrefix):
    _cxpr = "dwf"

class cli_dwf_const(Command):
    _cxpr = "dwf const"

    def invoke(self, argv):
        consts = Dwf.ReadAllConsts(argv[0])
        for k,v in consts.items():
            print(" - %s = %d" % (k,v))

class cli_dwf_inherit(Command):
    _cxpr = "dwf inherit"

    def invoke(self, argv):
        Dwf.ShowInherits(argv[0])

class cli_dwf_layout(Command):
    _cxpr = "dwf layout"

    def invoke(self, argv):
        cla = argv[0].split('.') 
        c = getattr(sys.modules['andb.v8'], cla[0])
        for i in range(1, len(cla)):
            c = getattr(c, cla[i])
        c.DebugLayout()

