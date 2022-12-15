import modelx as mx
import pytest


@pytest.fixture(scope="module")
def sample():
    m, s = mx.new_model(), mx.new_space()
    c = s.new_cells()

    yield m, s, c
    m._impl._check_sanity()
    m.close()

def test_has_ascendant(sample):
    m, s, c = sample

    assert c._impl.has_ascendant(s._impl)
    assert c._impl.has_ascendant(m._impl)
    assert s._impl.has_ascendant(m._impl)


def test_has_descendant(sample):
    m, s, c = sample

    assert m._impl.has_descendant(s._impl)
    assert m._impl.has_descendant(c._impl)
    assert s._impl.has_descendant(c._impl)


def test_has_linealrel(sample):
    m, s, c = sample

    assert m._impl.has_linealrel(s._impl)
    assert s._impl.has_linealrel(c._impl)
    assert c._impl.has_linealrel(m._impl)