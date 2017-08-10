import pytest

from modelx.core.formula import *

funcdef = """def foo(x):
    return 2 * x
"""

def test_init_from_str():
    f = Formula(funcdef)
    assert (f.name == 'foo' and
            f.func(1) == 2 and
            f.source == funcdef)

