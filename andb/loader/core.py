from __future__ import print_function
from .elf import Elf
import json
import os
import errno
import andb.py23 as py23

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

class Prog(Elf):
    """Represents a Elf file.
    """
    def __init__(self, addr):
        pass

    def GetBuildId(self):
        pass

    def LoadNotes(self):
        pass


class Corefile(object):

    # holds corefile's Elf
    _coreElf = None

    # holds process's Elf (usually node)
    _progElf = None

    def Load(self, filename):
        # load core elf
        self._corefile = filename
        self._coreElf = Elf()
        self._coreElf.Load(filename)

        # load prog elf
        self.LoadProgElf()

    @property
    def filename(self):
        return self._coreElf.filename

    @property
    def filesize(self):
        return self._coreElf.filesize

    def LoadProgElf(self):
        if self._progElf:
            return self._progElf

        ## TODO: find progSegOffset from sec .note.maps
        proghdrs = self._coreElf.GetPhdrs()

        #load prog elf
        progSegOffet = proghdrs[1]['p_offset'];
        self._progElf = Elf()
        self._progElf.LoadOffset(self._coreElf, progSegOffet)
        return self._progElf

    def LoadNotes(self):
        if self._notes:
            return self._notes
 
        # find phNote
        phNoteHdr = None
        for p in self._coreElf.GetPhdrs():
            if p['p_type'] == Elf.PHTYPE.NOTE:
                phNoteHdr = p

        # read note via phNoteHdr
        notes = self._progElf.ReadNotes(phNoteHdr)
        self._notes = notes
        return notes

    def GetFilesInfo(self):
        """Get NT_FILE info from corefile.
        """
        files = self._coreElf.GetNtFiles()
        if files is None:
            return []

        shared_libs = {}
        for f in files:
            if len(f['name']) < 3:
                continue
            name = f['name']
            if name not in shared_libs:
                lib = {}
                lib['start_addr'] = f['start_addr']
                lib['end_addr'] = f['end_addr']
                shared_libs[name] = lib 
            else:
                lib = shared_libs[name]
                if f['end_addr'] > lib['end_addr']:
                    lib['end_addr'] = f['end_addr']
                if f['start_addr'] < lib['start_addr']:
                    lib['start_addr'] = f['start_addr']

        out = []
        for k,f in sorted(shared_libs.items(), key=lambda x: x[1]['start_addr']):
            build_id = ''
            try:
                elf = self._coreElf.AttachV(f['start_addr'])
                if elf:
                    build_id = elf.GetBuildId()
            except:
                pass

            out.append({'start_addr':f['start_addr'], 'end_addr':f['end_addr'], 'name':k, 'build_id':build_id})
        
        return out

    def GetBuildId(self):
        """Get Prog's BuildId
        """
        prog = self.LoadProgElf()
        return prog.GetBuildId()

    def GetSigInfo(self):
        """Get Corefile's Signal Info
        """
        return self._coreElf.GetNtSigInfo()

    def GetPrStatus(self):
        """Get Corefile's Process Status
        """
        return self._coreElf.GetNtPrStatus()

    def GetPrPsInfo(self):
        """Get Corefile's NT_PRPSINFO
        """
        return self._coreElf.GetNtPrPsInfo()

    def GetMemMap(self):
        phdrs = self._coreElf.GetPhdrs()
        return phdrs

    def ArchName(self):
        machine = self._coreElf.GetEhdr()['e_machine']
        if machine == Elf.EMTYPE.EM_X86_64:
            return "x86_64"
        elif machine == Elf.EMTYPE.EM_AARCH64:
            return "aarch64"
        return None

class CorefileAuxiliaryDownloader:

    _ossBase = None
    _place = None

    def __init__(self, arch):
        print(arch)

        if arch == "x86_64":
            self._place = os.path.expanduser('~/.andb-dwf')
            self._ossBase = 'https://alinode-debugger-info.oss-cn-zhangjiakou.aliyuncs.com/dwf'
        
        elif arch == "aarch64":
            self._place = os.path.expanduser('~/.andb-dwf/aarch64')
            self._ossBase = 'https://alinode-debugger-info.oss-cn-zhangjiakou.aliyuncs.com/dwf/aarch64'
       
        else:
            raise Exception('Arch %s is supported.' % arch);

    def _url_by_version(self, ver):
        """ return url by-version
        """
        return self._ossBase + "/by-version/" + ver

    def _url_by_buildid(self, buildid):
        """ return url by-buildid
        """
        return self._ossBase + "/by-buildid/" + buildid

    def _local_version_path(self, ver, fil=None):
        """ return the path of local versioned file/dir.
        """
        if fil:
            return "%s/%s/%s" % (self._place, ver, fil)
        return "%s/%s" % (self._place, ver)

    def _curl_version_file(self, version, file_name):
        """ download versioned file from remote
        """
        local_dir = self._local_version_path(version)
        if not os.path.exists(local_dir):
            mkdir_p(local_dir)
        url = "%s/%s" % (self._url_by_version(version), file_name)
        outf = self._local_version_path(version, file_name)
        print('Downloading %s / %s' % (version, outf))
        return os.system('curl %s -o %s' % (url, outf))

    def DownloadVersion(self, buildId, version, checkSum=None):
        # download all files
        if self._curl_version_file(version, "md5sum.txt"): return None
        if self._curl_version_file(version, "metadata.json"): return None
        if self._curl_version_file(version, "node.typ.gz"): return None
        if self._curl_version_file(version, "node.gz"): return None
        if os.system("gzip -f -d %s" % self._local_version_path(version, "node.typ.gz")): return None
        if os.system("gzip -f -d %s" % self._local_version_path(version, "node.gz")): return None

        # create buildid link
        lnk = self._local_version_path(buildId)
        if len(lnk) > 5 and lnk[-1] != '/' and os.path.exists(lnk):
            # some protect
            os.remove(lnk)
        os.symlink(version, lnk)

        return version

    def GetOrDownloadBuildId(self, buildId):
        """ return the version string of specified BuildId.
        """
        # read local cached
        lnk = self._local_version_path(buildId)
        if os.path.exists(lnk):
            return os.readlink(lnk)

        # find buildId (download if local not found.)
        bid = self._url_by_buildid(buildId)
        try:
            version = urlopen(bid).readline().decode('utf-8').rstrip()
        except Exception:
            print("Check remote buildid failed.")
            return None

        # request remote download
        return self.DownloadVersion(buildId, version)

    def GetOrDownloadTag(self, version):
        lnk = self._local_version_path(version)
        if os.path.exists(lnk):
            return version

        # find tag in remote (download if local not found.)
        bid = self._url_by_version(version) + "/metadata.json"
        try:
            # get buildid from metadata
            meta = json.loads(urlopen(bid).read())
        except Exception:
            print("Check remote version failed.")
            return None

        return self.DownloadVersion(meta['buildid'], version)

    def FetchByBuildId(self, buildId):
        version = self.GetOrDownloadBuildId(buildId)
        if version is None:
            raise Exception("BuildId '%s' not found." % buildId)

        record = {}
        record['typ'] = self._local_version_path(version, "node.typ")
        record['bin'] = self._local_version_path(version, "node")
        return record

    def FetchByTag(self, tag):
        # Get
        version = self.GetOrDownloadTag(tag)
        if version is None:
            raise Exception("version '%s' not found." % tag)

        record = {}
        record['typ'] = self._local_version_path(version, "node.typ")
        record['bin'] = self._local_version_path(version, "node")
        return record


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        # possibly handle other errno cases here, otherwise finally:
        else:
            raise


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('corefile', type=str, help="which 'core' file to read")
    args = parser.parse_args()

    corefile = Corefile()
    corefile.Load(args.corefile)
    buildId = corefile.GetBuildId()

    corefileAuxiliaryDownloader = CorefileAuxiliaryDownloader()
    corefileAuxiliaryDownloader.Download(buildId)
