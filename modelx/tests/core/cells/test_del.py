import modelx as mx
import pytest


@pytest.fixture
def testmodel():
    m = mx.new_model()

    base = m.new_space("Base")
    m.new_space("Sub", bases=base)
    base.new_cells("Foo")
    yield m
    m._impl._check_sanity()
    m.close()


def test_del_defined(testmodel):
    """del Space.Cells when Cells is defined"""

    sub = testmodel.Sub

    assert "Foo" in sub.cells   # Sub.Foo is defined
    sub.new_cells("Foo")

    del sub.Foo

    assert "Foo" in sub.cells
    assert sub.Foo._is_derived()


def test_del_derived(testmodel):

    sub = testmodel.Sub

    assert "Foo" in sub.cells   # Sub.Foo is defined

    with pytest.raises(ValueError):
        del sub.Foo