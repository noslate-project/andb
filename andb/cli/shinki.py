# -*- coding: UTF-8 -*-

from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix

class cli_shinki(CommandPrefix):
    _cxpr = "shinki"

class cli_shinki_metadata(Command):
    _cxpr = "shinki metadata"

    def invoke(self, argv):
        pass

class cli_shinki_immortal(Command):
    _cxpr = "shinki immortal"

    def invoke(self, argv):
        AworkerVisitor().GuessImmortalFromV8Context()

from andb.shadow import (
    AworkerVisitor
)
