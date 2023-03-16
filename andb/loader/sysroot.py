
from __future__ import print_function, division
from .tsr import TechReport

import os
import re

try:
    from urllib.request import Request, urlopen 
except ImportError:
    from urllib2 import Request, urlopen
import json

class SysrootMaker(object):

    # holds tsr 
    _tsr = None

    # holds node version, guessed from binary
    _node_version = None

    # sysroot dir name
    _sysroot_dir = None

    # binary path
    _binary = None

    def __init__(self, binPath, coreFmt, sysRoot="sysroot"):
        self._binary = binPath
        self._tsr = TechReport(coreFmt)
        self._node_version = self.GuessNodeVersionFromBinary(binPath)
        self._sysroot_dir = sysRoot
        self._dwf_sysr_dir = os.path.expanduser("~/.andb-dwf/sysr")

    @classmethod
    def GuessNodeVersionFromBinary(cls, binary_path):
        p = os.popen('strings "%s" | grep -o -E "node-v([0-9\.]+).tar.gz"' % binary_path)
        out = p.read()
        p.close()
        m = re.findall("node-v(\d+\.\d+\.\d+)\.*", out)
        if len(m) > 0:
            return m[0]
        return None

    def dwf_sysr_buildid(self, buildId):
        return "%s/%s" % (self._dwf_sysr_dir, buildId)

    def system(self, args):
        print("CMD:", args)
        return os.system(args)

    def BuildId(self, path_file):
        p = os.popen('file -L "%s"' % path_file)
        out = p.read()
        p.close()
        m = re.findall("BuildID\[sha1\]=([0-9a-f]+),", out)
        if len(m) > 0:
            return m[0]
        return None

    def FetchMeta(self, buildId):
        url = 'https://alinode-debugger-info.oss-cn-zhangjiakou.aliyuncs.com/dwf/sysr/%s' % buildId
        req = Request(url)
        meta = urlopen(req).read().decode('utf8')
        jm = json.loads(meta)
        dm = self.dwf_sysr_buildid(buildId)
        if not os.path.exists(dm):
            os.makedirs(dm)
        outf = "%s/%s" % (dm, jm['name'])
        self.system("curl %s -o %s" % (jm['url'], outf))
        jm['local_file'] = outf
        fm = "%s/metadata.json" % dm
        with open(fm, 'w') as f: 
            json.dump(jm, f)
        return jm

    def GetMeta(self, buildId):
        dm = self.dwf_sysr_buildid(buildId)
        fm = "%s/metadata.json" % dm
        if os.path.exists(fm):
            with open(fm) as f:
                return json.load(f)
        return self.FetchMeta(buildId)

    def InstallDeb(self, meta):
        rpm = meta['local_file']
        self.system('cd sysroot && rpm2cpio "%s" | cpio -divm' % rpm) 

    def InstallRpm(self, meta):
        rpm = meta['local_file']
        lib_d = "sysroot/%s.d" % meta['name']
        if not os.path.exists(lib_d):
            os.makedirs(lib_d)
        self.system('cd "%s" && rpm2cpio "%s" | cpio -divm' % (lib_d, rpm)) 

    def InstallLibc(self, f):
        """Install libc package"""
        try:
            meta = self.GetMeta(f['build_id']) 
            if meta['type'] == 'rpm':
                self.InstallRpm(meta)
            elif meta['type'] == 'deb':
                self.InstallDeb(meta)
        except:
            pass

    def InstallNpm(self, f):
        """Install npm package"""
        paths = f['name'].split("/")
        if len(paths) < 1:
            return

        dname = None
        for i in range(len(paths)-1, 0, -1):
            e = paths[i]
            if e == 'node_modules':
                dname = paths[i+1]
                break
        
        if dname is None:
            return
       
        vers = dname.split('@')
        print(vers)
        
        npm = os.environ.get('NPM')
        if npm is None:
            npm = 'npm'

        if self._node_version is None:
            return 

        # only support tnpm style, for version was in folder name.
        if len(vers) == 3:
            self.system("cd sysroot && %s i --target=%s --target_arch=x64 --target_platform=linux %s@%s" % (npm, self._node_version, vers[2], vers[1]))
        elif len(vers) == 5:
            pkgver = "@%s/%s@%s" % (vers[4], paths[i+2], vers[2])
            self.system("cd sysroot && %s i --target=%s --target_arch=x64 --target_platform=linux %s" % (npm, self._node_version, pkgver))

    def InstallLinks(self):
        dest = 'sysroot/lib64'
        if not os.path.exists(dest):
            os.makedirs(dest)
        for d in os.listdir('sysroot'):
            if d == 'lib64':
                continue
            if not os.path.isdir("%s/%s" % ('sysroot', d)):
                continue
            print("install %s" % d)
            cmd = 'cd "%s" && ' % dest

            for i in ['*.so', '*.so.*', '*.node']:
                cmd = cmd + 'find "../%s" -name "%s" -exec ln -sf {} \; ; ' % (d, i)
            self.system(cmd)

    def ValidateFiles(self, files):
        print("%-30s %-40s %s" % ("FILE", "ORIGIN BUILDID", "INSTALLED BUILDID"))
        for f in self._files:
            fname = f['name'].split('/')[-1]
            bid = self.BuildId("sysroot/lib64/%s" % fname)
            fbid = f['build_id']
            match = bid
            if bid is not None:
                if bid == fbid:
                    match = '(matched)'
            else:
                match = ''
            print("%-30s %40s %s" % (fname, fbid, match))

    def Makeup(self):

        if not os.path.exists('sysroot'):
            os.makedirs('sysroot')
     
        # let npm install in sysroot.
        with open('sysroot/package.json', 'w') as f:
            f.write('{}')

        print("node version:", self._node_version)
        self._files = self._tsr.GetFilesInfo()

        for f in self._files:
            if f['name'].find('libc-') > 0:
                self.InstallLibc(f) 
            elif f['name'].find('node_modules') > 0:
                self.InstallNpm(f) 
       
        print('install softlinks')
        self.InstallLinks()

        print('validate files')
        self.ValidateFiles(self._files)

        print('sysroot makeup done.')
