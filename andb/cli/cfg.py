# -*- coding: UTF-8 -*-
from __future__ import print_function, division

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

class cli_andb_flag(Command):
    _cxpr = "andb flag"

    def invoke(self, argv):
        pass

class cli_andb_flag_set(Command):
    _cxpr = "andb flag set"

    def invoke(self, argv):
        pass

