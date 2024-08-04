import itertools
import modelx as mx
import pytest

@pytest.fixture
def duplicate_inheritance_model():
    """
        Sub <------------------- Base1
         |                        |
        Child <--------- Base2  Child
         |                |       |
        GChild <--Base3  GChild  GChild
                   |      |       |
                  foo    foo     foo
    """
    m = mx.new_model()
    m.new_space("Sub").new_space("Child").new_space("GChild")
    m.new_space("Base1").new_space("Child").new_space("GChild").new_cells(
        "foo", formula=lambda: "Under Base1")
    m.new_space("Base2").new_space("GChild").new_cells(
        "foo", formula=lambda: "Under Base2")
    m.new_space("Base3").new_cells(
        "foo", formula=lambda: "Under Base3")

    yield m
    m._impl._check_sanity()
    m.close()

@pytest.mark.skip
def test_nearest_first(duplicate_inheritance_model):
    m = duplicate_inheritance_model
    m.Sub.add_bases(m.Base1)
    m.Sub.Child.add_bases(m.Base2)
    m.Sub.Child.GChild.add_bases(m.Base3)
    assert "Under Base3" == m.Sub.Child.GChild.foo()

@pytest.mark.skip
def test_farthest_first(duplicate_inheritance_model):
    m = duplicate_inheritance_model
    m.Sub.Child.GChild.add_bases(m.Base3)
    m.Sub.Child.add_bases(m.Base2)
    m.Sub.add_bases(m.Base1)
    assert "Under Base3" == m.Sub.Child.GChild.foo()


@pytest.fixture(scope="module")
def property_sample():

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