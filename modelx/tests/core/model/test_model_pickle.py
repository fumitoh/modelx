from textwrap import dedent
import pytest
import builtins
import io

import modelx as mx
from modelx.testing import testutil
from modelx.core.api import *
from modelx.core import mxsys
from modelx.core.system import SystemPickler, SystemUnpickler

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

    f = io.BytesIO()
    SystemPickler(f).dump(model._impl)
    f.seek(0)
    unpickled = SystemUnpickler(f, mxsys).load()

    return [model._impl, unpickled]


def test_unpickled_model(pickletest):

    model, unpickeld = pickletest

    errors = []

    if not model.name == unpickeld.name:
        errors.append("name did not match")

    if not hasattr(model, "interface"):
        errors.append("no interface")

    if not hasattr(model, "tracegraph"):
        errors.append("no tracegraph")

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

    f = io.BytesIO()
    SystemPickler(f).dump(model._impl)
    f.seek(0)
    unpickled = SystemUnpickler(f, mxsys).load()
    unpickled.restore_state()
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


def test_pickle_module(tmp_path):

    import numpy
    m, s = new_model(), new_space("TestModule")
    m.np = numpy
    m.save(tmp_path / "pickle_module.mx")
    m = restore_model(tmp_path / "pickle_module.mx")
    assert m.np is numpy
    assert m.TestModule.np is numpy
    assert m.__builtins__ is builtins
    assert m.TestModule.__builtins__ is builtins


def test_null_object(tmp_path):
    """
        m---A---B
            +---b <- B
            |
            C(A)
    """
    m = mx.new_model()
    A = m.new_space('A')
    B = A.new_space('B')
    A.b = B
    C = m.new_space('C', bases=A)

    del A.B
    assert not A.b._is_valid()
    assert not C.b._is_valid()

    m.backup(tmp_path / "model")
    m2 = mx.restore_model(tmp_path / "model")

    assert not m2.A.b._is_valid()
    assert not m2.C.b._is_valid()

    testutil.compare_model(m, m2)