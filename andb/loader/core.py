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

class Corefile:

    _coreElf = None
    _progElf = None;

    def Load(self, filename):
        
        # load core elf
        self._coreElf = Elf()
        self._coreElf.Load(filename)


        proghdrs = self._coreElf.getProgHdrs()

        ## TODO: find progSegOffset from sec .note.maps

        #load prog elf
        progSegOffet = proghdrs[1]['p_offset'];
        self._progElf = Elf()
        self._progElf.LoadCorefileProgElf(filename, progSegOffet)
        
    
    def GetBuildId(self):

        progElfProgHdrs = self._progElf.getProgHdrs()

        # find phNote
        phNoteHdr = None
        for p in progElfProgHdrs:
            if p['p_type'] == Elf.PHTYPE.NOTE:
                phNoteHdr = p

        # read note via phNoteHdr
        notes = self._progElf.ReadNote(phNoteHdr)

        noteBuildId = None
        for (name, desc, n_type) in notes:
            if name == b'GNU\x00' and n_type == Elf.NTYPE.NT_GNU_BUILD_ID:
                noteBuildId = (name, desc, n_type)

        return "".join("{:02x}".format(py23.byte2int(c)) for c in noteBuildId[1])


class CorefileAuxiliaryDownloader:

    _ossBase = 'https://alinode-debugger-info.oss-cn-zhangjiakou.aliyuncs.com/dwf'
    _place = None

    def __init__(self, place = os.path.expanduser('~/.andb-dwf')):
        self._place = place

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

    def DownloadVersion(self, buildId, checkSum=None): 
        bid = self._url_by_buildid(buildId)
        try:
            version = urlopen(bid).readline().decode('utf-8').rstrip()
        except Exception:
            return None

        # download all files
        if self._curl_version_file(version, "md5sum.txt"): return None
        if self._curl_version_file(version, "metadata.json"): return None
        if self._curl_version_file(version, "node.typ.gz"): return None
        if self._curl_version_file(version, "node.gz"): return None
        if os.system("gzip -f -d %s" % self._local_version_path(version, "node.typ.gz")): return None
        if os.system("gzip -f -d %s" % self._local_version_path(version, "node.gz")): return None
        
        # create buildid link 
        os.symlink(version, self._local_version_path(buildId)) 

        return version  

    def GetBuildIdVersion(self, buildId):
        """ return the version string of specified BuildId.
        """
        # 1. read local cached 
        lnk = self._local_version_path(buildId)
        if os.path.exists(lnk):
            return os.readlink(lnk) 

        # 2. request remote download
        return self.DownloadVersion(buildId)

    def Download(self, buildId):
        """ return buildId record, download if necessary.
        """
        # 1. find buildId (download if local not found.) 
        version = self.GetBuildIdVersion(buildId)
        if version is None:
            raise Exception("BuildId not found.")

        # 2. tell loader uses local version 
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
