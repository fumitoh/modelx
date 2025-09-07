import sys
import os
import pathlib
import modelx as mx
import modelx.tests.testdata
from modelx.core.errors import DeepReferenceError
from modelx.testing.testutil import ConfigureExecutor
import pytest
datadir = pathlib.Path(os.path.dirname(mx.tests.testdata.__file__))

def is_github_actions():
    """Check if the test is running on GitHub Actions."""
    return os.getenv('GITHUB_ACTIONS') == 'true'


if sys.version_info >= (3, 12):
    maxdepth = 100_000
else:
    if sys.platform == "win32":
        if sys.version_info[:2] > (3, 10):  # Python 3.11 or newer
            maxdepth = 100_000
        else:
            if is_github_actions():
                maxdepth = 10000
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


@pytest.mark.skipif(sys.platform == "darwin" and sys.version_info < (3, 12),
                    reason="macOS shallow stack")
def test_max_recursion():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    maxdepth_saved = mx.get_recursion()
    try:
        if maxdepth_saved < maxdepth:
            mx.set_recursion(maxdepth)
        assert foo(maxdepth) == maxdepth
    finally:
        if maxdepth_saved < maxdepth:
            mx.set_recursion(maxdepth_saved)

    m._impl._check_sanity()
    m.close()


@pytest.mark.skipif(sys.platform == "darwin" and sys.version_info < (3, 12),
                    reason="macOS shallow stack")
def test_maxout_recursion():
    
    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    with ConfigureExecutor(maxdepth):
        with pytest.raises(DeepReferenceError):
            foo(maxdepth+1)

    m._impl._check_sanity()
    m.close()


def test_maxout_recursion_referred_as_space_attr():

    m = mx.read_model(datadir / "CircularRefSample")

    with ConfigureExecutor(10000):
        with pytest.raises(DeepReferenceError):
            m.Foo[1].foo(1)

    assert len(mx.get_traceback()) == 10000 + 1

    m._impl._check_sanity()
    m.close()


def test_deep_uncached():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        return foo(x+1) + 1

    foo.is_cached = False

    with ConfigureExecutor(maxdepth=10):
        with pytest.raises(DeepReferenceError):
            foo(maxdepth+1)

    m._impl._check_sanity()
    m.close()
