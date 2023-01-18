# -*- coding: UTF-8 -*-
from __future__ import print_function, division

from andb.utility import to_bool
from andb.dbg import Command, CommandPrefix
from andb.config import Config

class cli_andb(CommandPrefix):
    _cxpr = "andb"


class cli_andb_config(Command):
    _cxpr = "andb config"

    def invoke(self, argv):
        Config.Show()


class cli_andb_set(Command):
    _cxpr = "andb set"

    def invoke(self, argv):
        Config.SetValue(argv[0], argv[1])


class cli_andb_opt(CommandPrefix):
    _cxpr = "andb option"


class cli_andb_opt_chunk_cache(Command):
    _cxpr = "andb option chunk_cache"

    # default not enabled.
    on_off = False
    
    @classmethod
    def show_value(cls):
        if cls.on_off: print("on")
        else: print("off")

    @classmethod
    def set_value(cls, v):
        import andb.v8 as v8
        if v:
            iso = v8.Isolate.GetCurrent()
            iso.MakeChunkCache()
        cls.on_off = v
       
    def invoke(self, argv):
        if len(argv) < 1:
            self.show_value()
            return
        
        v = to_bool(argv[0])
        self.set_value(v)

