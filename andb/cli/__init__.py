# -*- coding: UTF-8 -*-
from __future__ import print_function, division

from andb.dbg import Command

from .v8 import *
from .node import *
from .shinki import *
from .test import *
from .cfg import *
from .dwf import *

""" register all commands
"""
Command.RegisterAll()

