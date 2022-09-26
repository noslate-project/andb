from __future__ import print_function

import lldb

import locale
import sys
from os import path

# add andb library
directory, file = path.split(__file__)
directory       = path.expanduser(directory)
directory       = path.abspath(directory + "/../")

if not directory in sys.path:
    sys.path.insert(0, directory)

if not "." in sys.path:
    sys.path.append(".")

#print(sys.path)

# warn if the user has different encoding than utf-8
encoding = locale.getpreferredencoding()

if encoding != 'UTF-8':
    print('******')
    print('Your encoding ({}) is different than UTF-8. might not work properly.'.format(encoding))
    print('You might try launching gdb with:')
    print('    LC_ALL=en_US.UTF-8 PYTHONIOENCODING=UTF-8 gdb')
    print('Make sure that en_US.UTF-8 is activated in /etc/locale.gen and you called locale-gen')
    print('******')

#import andb

# And the initialization code to add your commands
def __lldb_init_module(debugger, internal_dict):
    """ Work around
        
        lldb can't find cli due to topest andb is missing, 
        so I import andb in debugger's command manually,
        needs to investigate more. 
    """
    print('init lldb module')
    #lldb.debugger.HandleCommand('script import andb')

    # lldb loads andb here.
    #andb.Load()

print("lldbinit end")
