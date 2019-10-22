import sys
import pytest
import modelx as mx


def foo(x):
    if x == 0:
        return 123
    else:
        return foo(x - 1)


def baz(y, z):
    return y + z


@pytest.fixture
def testmodel():

    model, space = (
        mx.new_model(name="testmodel"),
        mx.new_space(name="testspace"),
    )

    space.new_cells(formula=foo)
    space.bar = 3
    space.new_cells(formula=baz)
    return model


@pytest.fixture
def savetestmodel(testmodel, tmpdir_factory):

    model = testmodel
    old_name = testmodel.name
    file = str(tmpdir_factory.mktemp("data").join("test_open_model.mx"))
    model.save(file)
    return model, file


def test_get_models(testmodel):
    assert mx.get_models() == {testmodel.name: testmodel}


if sys.version_info >= (3, 7):

    def test_getattr_models(testmodel):
        assert mx.models == mx.get_models()

    def test_getattr(testmodel):
        assert testmodel is mx.testmodel

    def test_dir(testmodel):
        assert "testmodel" in dir(mx)


def test_get_object(testmodel):

    assert mx.get_object("testmodel") is testmodel
    assert mx.get_object("testmodel.testspace") is testmodel.testspace
    assert mx.get_object("testmodel.testspace.foo") is testmodel.testspace.foo
    assert mx.get_object("testmodel.testspace.bar") == 3

    objs = [testmodel, testmodel.testspace, testmodel.testspace.foo]

    for obj in objs:
        assert mx.get_object(obj.fullname) is obj

    attrs = ["spaces", "cells", "formula"]

    for obj, attr in zip(objs, attrs):
        assert mx.get_object(obj.fullname + "." + attr) is getattr(obj, attr)


@pytest.mark.parametrize(
    "name, argstr, args",
    [
        ["testmodel.testspace.foo", "3", (3,)],
        ["testmodel.testspace.foo", "3,", (3,)],
        ["testmodel.testspace.baz", "3, 4", (3, 4)],
    ],
)
def test_get_node(testmodel, name, argstr, args):
    from modelx.core.api import _get_node

    assert _get_node(name, argstr).args == args


@pytest.mark.parametrize(
    "name, newname",
    [
        ["new_model", "new_model"],
        ["testmodel", "testmodel"],
        [None, "testmodel"],
    ],
)
def test_open_model_close_old(savetestmodel, name, newname):
    """Test open_model API with/without name args."""

    model, file = savetestmodel
    model.close()
    newmodel = mx.open_model(file, name)
    assert newmodel.name == newname


@pytest.mark.parametrize(
    "name, newname, renamed",
    [
        ["new_model", "new_model", False],
        ["testmodel", "testmodel", True],
        [None, "testmodel", True],
    ],
)
def test_open_model_leave_old(savetestmodel, name, newname, renamed):
    """Test open_model API with/without name args when old model exists.

    Args:
        name: Name passed to open_model
        newname: Name the new model should have
        renamed: True if the old model is renamed
    """
    model, file = savetestmodel
    oldname = model.name
    newmodel = mx.open_model(file, name)
    assert newmodel.name == newname
    assert model.name[: len(oldname)] == oldname
    assert renamed != (len(model.name) == len(oldname))
