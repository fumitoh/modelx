import modelx as mx
import pytest
import itertools


@pytest.fixture(params=["foo", "bar"])
def samplecells(request):

    m, s = mx.new_model(), mx.new_space("Source")

    @mx.defcells
    def foo(x):
        return x

    foo[0] = 1
    s.new_cells("bar", lambda x: 2 * x)
    s.bar[0] = 1
    yield s.cells[request.param]
    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize(
    "to_another_model, name",
    list(itertools.product([False, True], [None, "baz"])))
def test_copy(samplecells, to_another_model, name):

    src = samplecells
    m = mx.new_model() if to_another_model else samplecells.model
    s2 = m.new_space()
    samplecells.copy(s2, name=name)

    assert s2.cells[name or src.name](0) == 1
    assert s2.cells[name or src.name](1) == src[1]