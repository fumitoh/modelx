import sys
from textwrap import dedent

import pytest

from modelx.core.api import *
from modelx.tests.testdata import testmodule


@pytest.fixture
def testmodel():

    model, space = new_model(name="testmodel"), new_space(name="testspace")
    space.parameters = ("a",)

    @defcells(space)
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    @defcells(space)
    def get_parent():
        return _space._parent

    space.bar = 3

    yield model
    model._impl._check_sanity()
    model.close()


def test_refs(testmodel):
    assert "bar" in testmodel.testspace.refs


def test_dir(testmodel):
    assert {"foo", "bar", "get_parent",
            "_self", "_space", "__builtins__", "_model"} == set(
        dir(testmodel.testspace)
    )


def test_parent(testmodel):
    assert cur_space().parent == testmodel
    assert cur_space().get_parent() is testmodel._impl.namespace
    assert cur_space()[1].get_parent() is cur_space()._impl.namespace


def test_create(testmodel):
    assert cur_space() in cur_model().spaces.values()


def test_get_cells_by_cells(testmodel):
    assert cur_space().cells["foo"][10] == 123


def test_get_cells_by_getattr(testmodel):
    assert cur_space().foo[10] == 123


def test_new_cells_from_module(testmodel):
    cells = cur_space().new_cells_from_module(testmodule)
    assert set(testmodule.funcs) == set(cells.keys())


def test_import_funcs(testmodel):
    cells = cur_space().import_funcs(testmodule)
    assert set(testmodule.funcs) == set(cells.keys())


def test_new_cells_from_modulename(testmodel):
    cells = cur_space().import_funcs(testmodule.__name__)
    assert set(testmodule.funcs) == set(cells.keys())


def test_derived_spaces(testmodel):

    model = testmodel
    space_a = model.new_space()

    @defcells
    def cells_a(x):
        if x == 0:
            return 1
        else:
            return cells_a(x - 1)

    space_b = model.new_space(bases=space_a)

    space_b.cells_a[0] = 2

    assert space_a.cells_a[2] == 1
    assert space_b.cells_a(2) == 2


def test_formula(testmodel):

    model = testmodel
    base = model.new_space(formula=lambda x, y: {"bases": _self})

    distance_def = dedent(
        """\
    def distance():
        return (x ** 2 + y ** 2) ** 0.5
    """
    )

    base.new_cells(formula=distance_def)

    assert base[3, 4].distance() == 5


def test_named_itemspaces(testmodel):

    model = testmodel
    space = model.new_space(formula=lambda n: {"bases": _self})

    @defcells
    def foo(x):
        return x * n

    assert space[1].foo(2) == 2
    assert space[2].foo(4) == 8


def test_new_cells_refs(testmodel):

    space = testmodel.new_space(refs={"x": 1})
    assert space.x == 1


def test_ref(testmodel):

    space = new_space()

    @defcells
    def foo(x):
        return x * n

    space.n = 3
    assert foo(2) == 6


def test_setref_derived(testmodel):
    """Test if base/derived refs are property updated on their assignments"""

    base = new_space()
    derived = new_space(bases=base)

    @defcells(base)
    def foo():
        return x

    base.x = 3
    assert derived.foo() == 3
    derived.x = 5
    assert base.foo() == 3
    assert derived.foo() == 5


def test_named_spaces(testmodel):

    space = new_space()
    child = space.new_space("Child")
    assert space.named_spaces == {"Child": child}



# ----- Test SpaceView -----
space_names = list("ABCDEFGHI")


@pytest.fixture
def spacemap_model():
    model, parent = new_model(), new_space("Parent")
    for name in space_names:
        parent.new_space(name)
    yield model
    model._impl._check_sanity()
    model.close()

if sys.version_info >= (3, 6, 0):

    def test_spacemapproxy_order(spacemap_model):
        parent = spacemap_model.spaces["Parent"]
        assert list(parent.spaces) == space_names

    def test_spacemapproxy_del(spacemap_model):
        parent = spacemap_model.spaces["Parent"]

        names = space_names.copy()
        names.remove("C")
        del parent.spaces["C"]
        assert list(parent.spaces) == names

    def test_spacemapproxy_add(spacemap_model):
        parent = spacemap_model.spaces["Parent"]
        names = space_names.copy()
        names.append("X")
        parent.new_space("X")
        assert list(parent.spaces) == names


# ----- Testing _impl  ----


def test_fullname(testmodel):
    assert cur_space().fullname == "testmodel.testspace"


def test_fullname_omit_model(testmodel):
    assert cur_space()._impl.get_fullname(omit_model=True) == "testspace"
