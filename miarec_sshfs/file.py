# coding: utf-8
"""Implementation of `SSHFile`.
"""
import io

from fs.iotools import RawWrapper

import typing
if typing.TYPE_CHECKING:
    from .sshfs import SSHFS
    from paramiko import SFTPClient

from .error_tools import ignore_network_errors, convert_sshfs_errors


class SSHFile(RawWrapper):
    """A file on a remote SSH server.
    """

    def __init__(self, handler, mode, path: str, fs: 'SSHFS', sftp_client: 'SFTPClient'):
        self._fs = fs
        self._sftp_client = sftp_client
        self._path = path
        super(SSHFile, self).__init__(handler)
        self.mode = mode

    def __del__(self):
        # Close this file and release a network connection when the object is destroyed by garbage collector
        # Otherwise, we may have a connection leakage
        with ignore_network_errors('closing file'):
            self.close()
            # Close SFTPClient (ssh channel) to avoid leak of connections
            # Some SFTP servers set limits on how many SSH channels are opened over a single SSH socket
            self._sftp_client.close()   
        

    def seek(self, offset, whence=0):  # noqa: D102
        if whence > 2:
            raise ValueError("invalid whence "
                             "({}, should be 0, 1 or 2)".format(whence))
        with convert_sshfs_errors(fs=self._fs, path=self._path, op='seek', connection_error=IOError):
            self._f.seek(offset, whence)
            return self.tell()

    def read(self, size=-1):  # noqa: D102
        with convert_sshfs_errors(fs=self._fs, path=self._path, op='seek', connection_error=IOError):
            size = None if size==-1 else size
            return self._f.read(size)

    def readline(self, size=-1):  # noqa: D102
        with convert_sshfs_errors(fs=self._fs, path=self._path, op='seek', connection_error=IOError):
            size = None if size==-1 else size
            return self._f.readline(size)

    def truncate(self, size=None):  # noqa: D102
        with convert_sshfs_errors(fs=self._fs, path=self._path, op='seek', connection_error=IOError):
            size = size if size is not None else self._f.tell()  # SFTPFile doesn't support
            self._f.truncate(size)                               # truncate without argument
            return size

    def readlines(self, hint=-1):  # noqa: D102
        with convert_sshfs_errors(fs=self._fs, path=self._path, op='seek', connection_error=IOError):
            hint = None if hint==-1 else hint
            return self._f.readlines(hint)

    @staticmethod
    def fileno():  # noqa: D102
        raise io.UnsupportedOperation('fileno')
