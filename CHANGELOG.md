# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).


## [v2024.1.5] - 2024-01-23

[v2024.1.5]: https://github.com/miarec/miarec_sshfs/compare/v2024.1.4...v2024.1.5

### Changes

- Fix a potential race condition when SSHFS object is accessed by multiple threads
- Fix socket leakage in situation when network connection is re-established


## [v2024.1.4] - 2024-01-23

[v2024.1.4]: https://github.com/miarec/miarec_sshfs/compare/v2024.1.3...v2024.1.4

### Changes

- Raise `RemoteConnectionError` rater than `OperationFailed` in case of network issues  (loss of connection, timeout, etc). 
- Automatically try to re-open SSH/SFTP connection on the next operation in case of network issues.
  Previously, the `SSHFS` object was stuck in error state, and any operations on file system, like `openbin()`, `listdir()`, etc. were failing indefinitely.
- Fix a leak in SSH channels (`paramiko.SFTPClient`) when files are opened and closed subsequently over the same SSH socket (`paramiko.SSHClient`).
  Some SFTP servers limit a maximum number of SSH channels that can be opened over the same SSH socket, usually 10.
- Raise `IOError` rather than `FSError` in file methods (`read()`, `write()`, `seek()`). Such methods can be called from the external code, where `FSError` is not catched. 
  For example, when file-like object is passed to Apache `mod_wsgi` module, which streams the file.


## [v2024.1.3] - 2024-01-15

[v2024.1.3]: https://github.com/miarec/miarec_sshfs/compare/v2024.1.2...v2024.1.3

### Changes

- Bump up version to resolve GitHub Actions workflow issues


## [v2024.1.2] - 2024-01-13

[v2024.1.2]: https://github.com/miarec/miarec_sshfs/compare/v2024.1.0...v2024.1.2

### Changed

- For security reasons, do not load SSH configuration from local `~/.ssh/config`.
- For security reasons, do not load SSH private keys from local system `~/.ssh`.
- For security reasons, do not load SSH private keys from SSH Agent.
- Disable by default a prefetch of files in background thread because a client may not need to read a whole file.
- Use protocol prefixes `msftp://` and `mssh://` instead of originals `sftp://` and `ssh://` respectively.
- Fix bug in `move()` when `preferve_time` is `True`.
- By default, do not run any shell commands (like `uname -s`) because some SFTP servers forbid a shell and close forcibly a network connection when the client attemps to run shell commands.
- Add `use_posix_rename` optional parameter to use a more efficient POSIX RENAME command rather than RENAME.
- Fix issue with SSH connection is being closed while `SSHFile` object is stil using it. This occurs because garbage collector may destroy the parent SSHFS object (and the underlying SSH connection) because `SSHFile` objects are not referencing the parent object directly.
- Fix connection leakage when `SSHFile` is opened directly rather than using context manager.



## [v2024.1.0] - 2024-01-05

[v2024.1.0]: https://github.com/miarec/miarec_sshfs/compare/v1.0.2...v2024.1.0

### Changed

- Forked from [fs.sshfs](https://github.com/althonos/fs.sshfs) version 1.0.2
- Rename project from `fs.sshfs` to `miarec_sshfs`


## [v1.0.2] - 2023-08-17

The latest release of the original (forked) [fs.sshfs](https://github.com/althonos/fs.sshfs) repo
