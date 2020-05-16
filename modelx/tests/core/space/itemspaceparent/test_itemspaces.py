import modelx as mx
from types import MappingProxyType
import inspect
import pytest

@pytest.mark.parametrize(
    "paramfunc",
    [lambda i: None,
     lambda i, j: None]
)
def test_namespaces(paramfunc):

    m, s = mx.new_model(), mx.new_space(formula=paramfunc)

    @mx.defcells
    def foo(x):
        return x

    for i in range(10):
        paramlen = len(inspect.signature(paramfunc).parameters)
        assert s(*((i,) * paramlen)).foo(i) == i

    items = s.itemspaces

    assert isinstance(items, MappingProxyType)
    assert len(items) == 10
    for k, v in items.items():
        assert s[k] is v
