"""
Testing functions.



"""

import os
import shutil
import tempfile
from unittest import TestCase
from yt.config import ytcfg


def check_path(filename):
    """
    Check file exists in place or in test data dir.
    """

    if os.path.exists(filename):
        return filename
    test_data_dir = ytcfg.get("yt", "test_data_dir")
    tfn = os.path.join(test_data_dir, filename)
    if os.path.exists(tfn):
        return tfn
    raise IOError("File does not exist: %s." % filename)


def get_path(filename):
    """
    Get a path or list of paths.
    """

    if isinstance(filename, (list, tuple)):
        path = [check_path(fn) for fn in filename]
    else:
        path = check_path(filename)
    return path


def requires_file(filename):
    def ffalse(func):
        return None

    def ftrue(func):
        return func

    if not isinstance(filename, list):
        filename = [filename]
    try:
        [get_path(fn) for fn in filename]
    except IOError:
        return ffalse
    return ftrue


class TempDirTest(TestCase):
    """
    A test class that runs in a temporary directory and
    removes it afterward.
    """

    def setUp(self):
        self.curdir = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.curdir)
        shutil.rmtree(self.tmpdir)
