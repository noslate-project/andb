# -*- coding: UTF-8 -*-
from __future__ import print_function

""" Functions
"""
def Load():
    """ Load andb in debugger
    """
    from time import time
    t1 = time()

    from . import dbg
    # load dwf file 
    dbg.LoadDwf()

    # load v8
    from . import v8
    v8.LoadDwf()

    # load node or shinki 
    from . import node
    from . import shinki
    # load node
    if node.LoadDwf():
        print("node loaded.") 
    
    # load shinki
    elif shinki.LoadDwf():
        print("shinki loaded.") 

    # register all commands
    from . import cli
    cli.CommandPrefix.RegisterAll()
    cli.Command.RegisterAll()

    t2 = time()
    print("andb loaded, cost %0.3f seconds." % (t2 - t1))

print("andb.__init__ end")
