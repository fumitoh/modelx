from textwrap import dedent
import pytest
import builtins
import io

import modelx as mx
from modelx.testing import testutil
from modelx.core.api import *
from modelx.core import mxsys

# ---- Test impl ----


@pytest.fixture
def pickletest(tmpdir_factory):

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

    file = str(tmpdir_factory.mktemp("data").join("pickletest"))
    model.write(file)
    unpickled = mx.read_model(file)

    yield [model._impl, unpickled]
    model._impl._check_sanity()
    model.close()


def test_unpickled_model(pickletest):

    model, unpickeld = pickletest

    errors = []

    if not hasattr(model, "interface"):
        errors.append("no interface")

    if not hasattr(model, "tracegraph"):
        errors.append("no tracegraph")

    assert not errors, "errors:\n{}".format("\n".join(errors))


@pytest.fixture(scope="module")
def pickletest_dynamicspace(tmpdir_factory):

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

    file = str(tmpdir_factory.mktemp("model").join(model.name))
    model.write(file)
    model.close()
    model = mx.read_model(file)

    yield (model, check)
    model._impl._check_sanity()
    model.close()


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
    m.write(tmp_path / "pickle_module")
    m.close()
    m = read_model(tmp_path / "pickle_module")
    assert m.np is numpy
    assert m.TestModule.np is numpy
    assert m.__builtins__ is builtins
    assert m.TestModule.__builtins__ is builtins
    m.close()


def test_null_object(tmp_path):
    """
        m---A---B
        |   +---b <- B
        |
        +---C(A)
    """
    m = mx.new_model()
    A = m.new_space('A')
    B = A.new_space('B')
    A.b = B
    C = m.new_space('C', bases=A)

    del A.B
    assert not A.b._is_valid()
    assert not C.b._is_valid()

    m.write(tmp_path / "model")
    m2 = mx.read_model(tmp_path / "model")

    assert not m2.A.b._is_valid()
    assert not m2.C.b._is_valid()

    testutil.compare_model(m, m2)

    m._impl._check_sanity()
    m.close()
    m2.close()