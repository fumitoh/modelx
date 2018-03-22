import pytest

from modelx.core.formula import *

funcdef = """def foo(x):
    return 2 * x
"""

def test_init_from_str():
    f = Formula(funcdef)
    assert f.name == 'foo'
    assert f.func(1) == 2
    assert f.source == funcdef

