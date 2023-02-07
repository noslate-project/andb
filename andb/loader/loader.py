from __future__ import print_function
import os

class FileWrap(object):
    """ warp object for file input.
    """
    def __init__(self, f):
        self._file = f
    
    def FileName(self):
        return str(self._file)

class Loader(object):
    """ Loader base for all debuggers 
    """

    # binary to debug
    _exec = None

    # node.typ file path
    _typ = None

    # corefile path
    _core = None

    # pid of live process
    _pid = None

    # commands array after initialized (batch mode)
    _commands = None 

    # debugger raw arguments (passthrough)
    _args = None

    # in batch mode
    _is_batch = None 

    def __init__(self, andb_dir):
        # for init files
        self._andb_dir = andb_dir

    def SetPid(self, pid):
        assert self._core is None
        assert self._pid is None
        self._pid = pid

    def SetCore(self, core):
        assert self._core is None
        self._core = core

    def SetTyp(self, typ):
        assert self._typ is None
        self._typ = typ

    def SetExec(self, exe):
        assert self._exec is None
        self._exec = exe

    def BatchOn(self):
        self._is_batch = True 

    def AddArgs(self, args):
        if self._args is None:
            self._args = []
        #print(args)
        self._args.extend(args)

    def AddCommandLine(self, l):
        self.AddCommands([l.split()])

    def AddCommandFile(self, f):
        self.AddCommands([[FileWrap(f)]])

    def AddCommands(self, cmds):
        if self._commands is None:
            self._commands = []
        for a in cmds:
            #print(a)
            if isinstance(a[0], FileWrap):
                cmd = a[0]
            else:
                cmd = a
            self._commands.append(cmd)

    def default(self):
        raise NotImplementedError

    def Opts(self):
        raise NotImplementedError

    def CmdLine(self):
        return " ".join(slef.Opts())

class GdbLoader(Loader):
    """ GDB loader
    """

    @property
    def default(self):
        return ['gdb', 
            '--nh',  # no ~/.gdbinit
            '--nx',  # no .gdbinit 
            '-ix', '%s/init/gdbinit.cmd' % self._andb_dir,  # gdbinit commands
            '-x', '%s/init/gdbinit.py' % self._andb_dir,    # gdbinit python script
           ]

    def Opts(self):
        opts = self.default
        if self._exec:
            opts.append(self._exec)
        
        if self._core:
            opts.extend(['--core', '%s' % self._core])
        
        if self._typ:
            os.environ['ANDB_TYP'] = self._typ 

        if self._pid:
            opts.extend(['--pid', '%d' % self._pid])

        if self._is_batch:
            opts.append('--batch')

        if self._commands:
            for i in self._commands:
                if isinstance(i, FileWrap):
                    opts.extend(["-x", '%s' % i.FileName()])
                else:
                    opts.extend(["-ex", " ".join(i)])
        
        if self._args:
            opts.extend(self._args)
        
        print(opts)
        return opts


class LldbLoader(Loader):
    """ GDB loader
    """

    @property
    def default(self):
        return ['lldb', 
            '-x',  # no any .lldbinit
            '-o', "com sc im %s/init/lldbinit.py" % self._andb_dir,  # lldbinit python script
            '-s', "%s/init/lldbinit.cmd" % self._andb_dir,             # lldbinit command
           ]

    def Opts(self):
        opts = self.default
        if self._exec:
            opts.extend(["-f", self._exec])
        
        if self._core:
            opts.extend(['-c', self._core])
        
        if self._typ:
            os.environ['ANDB_TYP'] = self._typ 
        
        if self._pid:
            opts.extend(['-p', '%d' % self._pid])

        if self._is_batch:
            opts.append('-b')

        if self._commands:
            for i in self._commands:
                if isinstance(i, FileWrap):
                    opts.extend(["-s", "%s" % i.FileName()])
                else:
                    opts.extend(["-o", " ".join(i)])
 
        if self._args:
            opts.extend(self._args)
        
        print(opts)
        return opts

