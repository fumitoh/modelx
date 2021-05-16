import sys
import modelx as mx
from modelx.core.errors import DeepReferenceError
from modelx.testing.testutil import SuppressFormulaError
import pytest

if sys.platform == "win32" and sys.version_info[:2] == (3, 8):
    maxdepth = 57000
elif sys.platform == "darwin":
    maxdepth = 19000
else:
    maxdepth = 65000


def test_max_recursion():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    assert foo(maxdepth) == maxdepth


def test_maxout_recursion():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        if x == 0:
            return 0
        else:
            return foo(x-1) + 1

    with SuppressFormulaError():
        with pytest.raises(DeepReferenceError):
            foo(maxdepth+1)
