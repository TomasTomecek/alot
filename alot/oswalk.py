"""
Alternative implementation of os.walk. The problem with os.walk
is that it calls os.stat on every file it finds.
This is a real problem if you have tenths of thousands of files.

This implementation is focusing on finding directories only,
while allowing to ignore folders (which is exactly what we need
for imap folders, since we can blacklist tmp, cur and new).

It is heavily inspired by:

https://github.com/benhoyt/betterwalk

Thank you for sharing the implementation.
"""
import os
import stat
import logging


def iterdir_stat(path, ignore_dirs=None):
    if not ignore_dirs:
        ignore_dirs = []
    names = os.listdir(path)
    for name in names:
        st = os.stat(os.path.join(path, name))
        if name not in ignore_dirs:
            yield (name, st)


def walk(top, ignore_dirs=None):
    dirs = []
    dir_stats = []
    if not ignore_dirs:
        ignore_dirs = []
    try:
        for name, st in iterdir_stat(top, ignore_dirs):
            if stat.S_ISDIR(st.st_mode):
                dirs.append(name)
                dir_stats.append(st)
    except OSError as err:
        logging.error('Error during filesystem walk: %s', repr(err))

    yield top

    for name, st in zip(dirs, dir_stats):
        new_path = os.path.join(top, name)
        if not stat.S_ISLNK(st.st_mode):
            for x in walk(new_path, ignore_dirs):
                yield x
