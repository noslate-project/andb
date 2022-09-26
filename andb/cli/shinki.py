# -*- coding: UTF-8 -*-

from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix

class cli_shinki(CommandPrefix):
    _cxpr = "shinki"

class cli_shinki_metadata(Command):
    _cxpr = "shinki metadata"

    def invoke(self, argv):
        pass

class cli_shinki_immortal(CommandPrefix):
    _cxpr = "shinki immortal"

class cli_shinki_immortal_guess(Command):
    _cxpr = "shinki immortal guess"

    def invoke(self, argv):
        pass

