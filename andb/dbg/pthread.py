# -*- coding: UTF-8 -*-

from __future__ import print_function, division

import gdb
import re

class key_data:

    def __init__(self, addr):
        self._val = addr

    @property
    def seq(self):
        return self._val['seq']

    @property
    def data(self):
        return self._val['data']
    
    def __str__(self):
        return "seq(%d), data(0x%x)\n" % (self._val['seq'], self._val['data'])

class pthread:
   
    def __init__(self, addr):
        self.addr = gdb.Value(addr)

    def __str__(self):
        o = "(%s) %s" % (self.addr.type, self.addr)
        o += '\ntid: %d' % (self.addr['tid'])
        o += '\npid: %d' % (self.addr['pid'])
        o += '\ntls: %d' % (self.tls.Count)
        o += '\nlock: %d' % (self.addr['lock'])
        return o

    @staticmethod
    def Current():
        v = gdb.execute('thread', to_string = True)
        r = re.findall('\(Thread (.+?) \(LWP', v) 
        if r:
            v = gdb.parse_and_eval("(struct pthread *)%s" % (r[0]))
            return pthread(v)
        return None

    @property
    class tls:
         
        def __init__ (self, addr):
            self._pthread = addr

        def __getitem__(self, key):
            v = self._pthread.addr['specific_1stblock'][key]
            if v:
                return key_data(v)
            return None

        def __str__(self):
            v = self._pthread.addr['specific_1stblock']
            o = ""
            for i in range(0, 32):
                k = v[i]
                if k['seq'] % 2 == 1:
                    o += "[%d] seq(%d), data(0x%x)\n" % (i, k['seq'], k['data'])
            return o
        
        def Walk(self):
            v = self._pthread.addr['specific_1stblock']
            for i in range(0, 32):
                k = v[i]
                if k['seq'] % 2 == 1:
                    yield

        @property
        def Count(self):
            c = 0
            for k in self.Walk():
                c += 1
            return c 
        
        # TBD: pretty-printer

class cli_tls(gdb.Command):

    def __init__(self):
        gdb.Command.__init__ (self, "pthread tls", gdb.COMMAND_USER)

    def invoke (self, arg, tty):
        t = pthread.Current()
        if arg:
            print(t.tls[int(arg)])
        else:
            print(str(t.tls))
        return None
 
class cli_pthread(gdb.Command):

    def __init__(self):
        super (cli_pthread, self).__init__ ("pthread", gdb.COMMAND_USER, prefix=True)

    def invoke (self, arg, tty):
        t = pthread.Current()
        print (str(t))
        return t

cli_pthread()
cli_tls()

