import itertools
import modelx as mx
import pytest


@pytest.fixture
def property_sample():
    """
        m--------Base---------foo
           |            +-----bar
           |            +-----baz
           +-----Sub(Base)

    """

    m = mx.new_model("PropertySample")
    base = m.new_space("Base")
    sub = m.new_space("Sub")

    @mx.defcells(space=base)
    def foo(other, x):
        return other(x)

    @mx.defcells(space=base)
    def bar(x):
        return 2 * x

    @mx.defcells(space=base)
    def baz(x):
        return foo(bar, x)

    base.baz.allow_none = True
    base.foo.is_cached = False

    yield m

    m.close()


@pytest.mark.parametrize("cells, property_name",
                         itertools.product(["foo", "bar", "baz"], ["allow_none", "is_cached"]))
def test_cells_properties(property_sample, cells, property_name):
    m = property_sample
    m.Sub.add_bases(m.Base)

    assert getattr(getattr(m.Sub, cells), property_name) == getattr(getattr(m.Base, cells), property_name)