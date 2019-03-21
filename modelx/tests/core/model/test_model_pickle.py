from textwrap import dedent
import pytest
import pickle

from modelx.core.api import *
from modelx.core import mxsys


# ---- Test impl ----


@pytest.fixture
def pickletest():

    model = new_model("TestModel")
    space = model.new_space()

    func1 = dedent(
        """\
    def single_value(x):
        return 5 * x
    """
    )

    func2 = dedent(
        """\
    def mult_single_value(x):
        return 2 * single_value(x)
    """
    )

    func1 = space.new_cells(formula=func1)
    func2 = space.new_cells(formula=func2)

    func2(5)

    byte_obj = pickle.dumps(model._impl)
    unpickled = pickle.loads(byte_obj)

    return [model._impl, unpickled]


def test_unpickled_model(pickletest):

    model, unpickeld = pickletest

    errors = []

    if not model.name == unpickeld.name:
        errors.append("name did not match")

    if not hasattr(model, "interface"):
        errors.append("no interface")

    if not hasattr(model, "cellgraph"):
        errors.append("no cellgraph")

    assert not errors, "errors:\n{}".format("\n".join(errors))


@pytest.fixture(scope="module")
def pickletest_dynamicspace():

    param = dedent(
        """\
    def param(x):
        return {'bases': _self}
    """
    )

    fibo = dedent(
        """\
    def fibo(n):
        return x * n"""
    )

    model, space = new_model(), new_space(name="Space1", formula=param)
    space.new_cells(formula=fibo)

    check = space[2].fibo(3)

    byte_obj = pickle.dumps(model._impl)
    unpickled = pickle.loads(byte_obj)
    unpickled.restore_state(mxsys)
    model = unpickled.interface

    return (model, check)


def test_pickle_dynamicspace(pickletest_dynamicspace):

    model, check = pickletest_dynamicspace
    assert model.Space1[2].fibo(3) == check


def test_pickle_argvalues(pickletest_dynamicspace):

    model, check = pickletest_dynamicspace
    assert model.Space1[2].argvalues == (2,)


def test_pickle_argvalues_none(pickletest_dynamicspace):

    model, check = pickletest_dynamicspace
    with pytest.raises(AttributeError):
        model.Space1.argvalues is None


def test_pickle_parameters(pickletest_dynamicspace):

    model, check = pickletest_dynamicspace
    assert model.Space1.parameters == ("x",)
