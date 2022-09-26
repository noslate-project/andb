# -*- coding: UTF-8 -*-
from __future__ import print_function, division

from andb.dbg import Command, CommandPrefix, Target
from andb.shadow import NodeEnvGuesser

class cli_node(CommandPrefix):
    _cxpr = "node"

class cli_node_metadata(Command):
    _cxpr = "node metadata"

    def invoke(self, argv):
        pass

class cli_node_env(Command):
    _cxpr = "node environment"

    def invoke(self, argv):
        NodeEnvGuesser().GuessFromV8Context()

