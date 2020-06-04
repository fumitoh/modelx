import modelx as mx
import pytest


@pytest.fixture(params=["foo", "bar"])
def samplecells(request):

    m, s = mx.new_model(), mx.new_space("Source")

    @mx.defcells
    def foo(x):
        return x

    s.new_cells("bar", lambda x: 2 * x)

    return s.cells[request.param]


@pytest.mark.parametrize("name", [None, "baz"])
def test_copy(samplecells, name):

    src = samplecells
    m = samplecells.model
    s2 = m.new_space()
    samplecells.copy(s2, name=name)

    assert s2.cells[name or src.name](1) == src[1]