import modelx as mx
import pytest


@pytest.fixture
def viewtest():
    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        return 2 * x

    @mx.defcells
    def bar(y):
        return foo(y) * y

    @mx.defcells
    def baz(z):
        return bar(z) * 3

    return s


def test_view(viewtest):

    selected = viewtest.cells["foo", "bar"]
    assert len(selected) == 2

    for name, cells in selected.items():
        assert viewtest.cells[name] is cells

    for i, name in enumerate(selected.keys()):
        assert viewtest.cells[name] is getattr(viewtest, name)
    assert i == 1

    for i, value in enumerate(selected.values()):
        pass
    assert i == 1

    assert repr(selected) == "{foo,\n bar}"
