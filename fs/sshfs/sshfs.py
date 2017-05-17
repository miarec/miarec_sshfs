# coding: utf-8
from __future__ import unicode_literals
from __future__ import absolute_import

import stat
import six
import paramiko

from .error_tools import convert_sshfs_errors
from .. import errors
from ..base import FS
from ..info import Info
from ..enums import ResourceType
from ..iotools import RawWrapper
from ..path import basename
from ..permissions import Permissions
from ..osfs import OSFS
from ..mode import Mode


class _SSHFileWrapper(RawWrapper):

    def seek(self, offset, whence=0):
        if whence > 2:
            raise ValueError("invalid whence "
                             "({}, should be 0, 1 or 2)".format(whence))
        return self._f.seek(offset, whence)

    def read(self, size=-1):
        size = None if size==-1 else size
        return self._f.read(size)

    def readline(self, size=-1):
        size = None if size==-1 else size
        return self._f.readline(size)

    def truncate(self, size=None):
        size = size or self._f.tell()   # SFTPFile doesn't support
        return self._f.truncate(size)   # truncate without argument

    def readlines(self, hint=-1):
        hint = None if hint==-1 else hint
        return self._f.readlines(hint)

    def __iter__(self):
        return iter(self._f)

    def __next__(self):
        return next(self._f)

    def next(self):
        return next(self._f)


class SSHFS(FS):

    _meta = {
        'case_insensitive': False,
        'invalid_path_chars': '\0',
        'network': True,
        'read_only': False,
        'thread_safe': True,
        'unicode_paths': True,
        'virtual': False,
    }

    def __init__(self,
                 host,
                 user=None,
                 passwd=None,
                 pkey=None,
                 timeout=10,
                 port=22):
        """
        connect(self, hostname, port=22, username=None, password=None,
                pkey=None, key_filename=None, timeout=None, allow_agent=True,
                look_for_keys=True, compress=False, sock=None, gss_auth=False,
                gss_kex=False, gss_deleg_creds=True, gss_host=None,
                banner_timeout=None)
        """
        super(SSHFS, self).__init__()

        # TODO: add more options
        self._client = _client = paramiko.SSHClient()
        _client.load_system_host_keys()
        _client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _client.connect(
            host, port, user, passwd, pkey,
            look_for_keys=True if pkey is None else False
        )
        self._sftp = _client.open_sftp()

    def getinfo(self, path, namespaces=None):
        self.check()
        namespaces = namespaces or ()
        _path = self.validatepath(path)

        with convert_sshfs_errors('getinfo', path):
            _stat = self._sftp.lstat(_path)
            _stat.st_ctime = None

        info = {
            'basic': {
                'name': basename(_path),
                'is_dir': stat.S_ISDIR(_stat.st_mode)
            }
        }
        if 'details' in namespaces:
            info['details'] = OSFS._make_details_from_stat(_stat)
        if 'stat' in namespaces:
            info['stat'] = {
                k: getattr(stat, k)
                for k in dir(stat) if k.startswith('st_')
            }
        if 'access' in namespaces:
            info['access'] = OSFS._make_access_from_stat(_stat)

        return Info(info)

    def listdir(self, path):
        self.check()
        _path = self.validatepath(path)

        _type = self.gettype(_path)
        if _type is not ResourceType.directory:
            raise errors.DirectoryExpected(path)

        with convert_sshfs_errors('listdir', path):
            return self._sftp.listdir(_path)

    def makedir(self, path, permissions=None, recreate=False):
        self.check()
        _permissions = permissions or Permissions(mode=0o755)
        _path = self.validatepath(path)

        try:
            info = self.getinfo(_path)
        except errors.ResourceNotFound:
            with self._lock:
                with convert_sshfs_errors('makedir', path):
                    self._sftp.mkdir(_path, _permissions.mode)
        else:
            if (info.is_dir and not recreate) or info.is_file:
                six.raise_from(errors.DirectoryExists(path), None)

        return self.opendir(path)

    def openbin(self, path, mode='r', buffering=-1, **options):
        """

        Buffering follows the paramiko spec, not the fs one
        (only difference is that buffering=1 means line based buffering,
        not an actual buffer size of 1.
        """
        self.check()
        _path = self.validatepath(path)
        _mode = Mode(mode)
        _mode.validate_bin()

        with self._lock:
            if _mode.exclusive and self.exists(_path):
                raise errors.FileExists(path)
            elif _mode.reading and not _mode.create and not self.exists(_path):
                raise errors.ResourceNotFound(path)
            elif self.isdir(_path):
                raise errors.FileExpected(path)
            with convert_sshfs_errors('openbin', path):
                return _SSHFileWrapper(self._sftp.open(
                    _path,
                    mode=_mode.to_platform_bin(),
                    bufsize=buffering))

    def remove(self, path):
        self.check()
        _path = self.validatepath(path)

        # NB: this will raise ResourceNotFound
        # and as expected by the specifications
        _type = self.gettype(_path)
        if _type is ResourceType.directory:
            raise errors.FileExpected(path)

        with convert_sshfs_errors('remove', path):
            with self._lock:
                self._sftp.remove(_path)

    def removedir(self, path):
        self.check()
        _path = self.validatepath(path)

        # NB: this will raise ResourceNotFound
        # and DirectoryExpected as expected by
        # the specifications
        if not self.isempty(path):
            raise errors.DirectoryNotEmpty(path)

        with convert_sshfs_errors('removedir', path):
            with self._lock:
                self._sftp.rmdir(path)

    def setinfo(self, path, info):
        self.check()
        _path = self.validatepath(path)

        if not self.exists(path):
            raise errors.ResourceNotFound(path)

        access = info.get('access', {})
        details = info.get('details', {})

        with convert_sshfs_errors('setinfo', path):
            if 'accessed' in details or 'modified' in details:
                self._utime(path,
                            details.get("modified"),
                            details.get("accessed"))
            if 'uid' in access or 'gid' in access:
                self._chown(path,
                            access.get('uid'),
                            access.get('gid'))
            if 'permissions' in access:
                self._chmod(path, access['permissions'].mode)

    def _chmod(self, path, mode):
        self._sftp.chmod(path, mode)

    def _chown(self, path, uid, gid):
        if uid is None or gid is None:
            info = self.getinfo(path, namespaces=('access',))
            uid = uid or info.get('access', {}).get('uid')
            gid = gid or info.get('access', {}).get('gid')
        if uid and gid:
            self._sftp.chown(path, uid, git)

    def _utime(self, path, modified, accessed):
        accessed = int(accessed or modified)
        modified = int(modified or accessed)
        self._sftp.utime(path, (accessed, modified))
