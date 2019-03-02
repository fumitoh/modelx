from modelx import *
import pytest

# --------------------------------------------------------------------------
# Test Interface.__repr__


@pytest.fixture
def repr_test():

    model, space = new_model("ReprModel"), new_space("ReprSpace")

    @defcells
    def Foo(x, y):
        return x * y

    child = space.new_space("ReprChild")

    @defcells
    def Bar(x, y):
        return x * y

    def params(m, n):
        return {"bases": _self}

    model.new_space("DynSpace", bases=space, formula=params)

    return model


def test_repr_model(repr_test):
    assert repr(repr_test) == "<Model ReprModel>"


def test_repr_space(repr_test):
    assert repr(repr_test.ReprSpace) == "<StaticSpace ReprSpace in ReprModel>"


def test_repr_suspace(repr_test):
    assert (
        repr(repr_test.ReprSpace.ReprChild)
        == "<StaticSpace ReprChild in ReprModel.ReprSpace>"
    )


def test_repr_cells(repr_test):
    cells = repr_test.ReprSpace.Foo
    assert repr(cells) == "<Cells Foo(x, y) in ReprModel.ReprSpace>"


def test_repr_cells_in_child(repr_test):
    cells = repr_test.ReprSpace.ReprChild.Bar
    repr_ = "<Cells Bar(x, y) in ReprModel.ReprSpace.ReprChild>"
    assert repr(cells) == repr_


def test_repr_dynspace(repr_test):
    space = repr_test.DynSpace(1, 2)
    assert repr(space) == "<DynamicSpace DynSpace[1, 2] in ReprModel>"


def test_repr_cells_in_dynspace(repr_test):
    cells = repr_test.DynSpace(1, 2).Foo
    assert repr(cells) == "<Cells Foo(x, y) in ReprModel.DynSpace[1, 2]>"
