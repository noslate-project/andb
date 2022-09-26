#!/usr/bin/env python
# -*- coding: utf-8 -*-

import locale
import sys
from os import path
import gdb

directory, file = path.split(__file__)
directory       = path.expanduser(directory)
directory       = path.abspath(directory + "/../")

if not directory in sys.path:
    sys.path.insert(0, directory)

if not "." in sys.path:
    sys.path.append(".")

# load gdbinit commands
#gdb.execute('source %s/gdbinit.cmd' % directory) 

# warn if the user has different encoding than utf-8
encoding = locale.getpreferredencoding()
if encoding != 'UTF-8':
    print('******')
    print('Your encoding ({}) is different than UTF-8. might not work properly.'.format(encoding))
    print('You might try launching gdb with:')
    print('    LC_ALL=en_US.UTF-8 PYTHONIOENCODING=UTF-8 gdb')
    print('Make sure that en_US.UTF-8 is activated in /etc/locale.gen and you called locale-gen')
    print('******')

# load alinode debugger
import andb
andb.Load()

