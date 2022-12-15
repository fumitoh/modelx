import sys
import modelx as mx
from modelx.core.errors import DeepReferenceError
from modelx.testing.testutil import SuppressFormulaError
import pytest
import psutil

if sys.platform == "win32": # and sys.version_info[:2] == (3, 8):
    if psutil.virtual_memory().total < 8 * 1024**3:
        maxdepth = 30000
    else:
        maxdepth = 50000
elif sys.platform == "darwin":
    # https://bugs.python.org/issue18075
    # https://bugs.python.org/issue34602
    # https://github.com/python/cpython/pull/14546
    if sys.version_info[:2] == (3, 9):
        maxdepth = 3500
    else:
        maxdepth = 4000
else:
    maxdepth = 65000


@pytest.mark.skipif(sys.platform == "darwin", reason="macOS shallow stack")
def test_max_recursion():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    assert foo(maxdepth) == maxdepth

    m._impl._check_sanity()
    m.close()


@pytest.mark.skipif(sys.platform == "darwin", reason="macOS shallow stack")
def test_maxout_recursion():
    
    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    with SuppressFormulaError(maxdepth):
        with pytest.raises(DeepReferenceError):
            foo(maxdepth+1)

    m._impl._check_sanity()
    m.close()