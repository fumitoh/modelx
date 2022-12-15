import modelx as mx
from modelx import defcells

import pytest


@pytest.fixture
def no_values():

    model = mx.new_model("Model")
    space = model.new_space("Space")

    @defcells
    def param0():
        return 0

    @defcells
    def param1(x):
        return x

    @defcells
    def param2(x, y):
        return x * y

    space.formula = lambda i: None

    yield space
    model._impl._check_sanity()
    model.close()


@pytest.fixture
def has_values(no_values):

    no_values.param0()
    no_values.param1(1)
    no_values.param2(2, 3)

    return no_values


def test_node_repr(no_values):

    s = no_values
    assert repr(s.param0.node()) == "Model.Space.param0()"
    assert repr(s.param1.node(1)) == "Model.Space.param1(x=1)"
    assert repr(s.param2.node(2, 3)) == "Model.Space.param2(x=2, y=3)"


def test_node_repr_has_values(has_values):

    s = has_values
    assert repr(s.param0.node()) == "Model.Space.param0()=0"
    assert repr(s.param1.node(1)) == "Model.Space.param1(x=1)=1"
    assert repr(s.param2.node(2, 3)) == "Model.Space.param2(x=2, y=3)=6"


def test_node_repr_dynspace(no_values):

    s = no_values[1]

    assert repr(s.param0.node()) == "Model.Space[1].param0()"
    assert repr(s.param1.node(1)) == "Model.Space[1].param1(x=1)"
    assert repr(s.param2.node(2, 3)) == "Model.Space[1].param2(x=2, y=3)"


@pytest.fixture
def str_values():

    m, s = mx.new_model('Model2'), mx.new_space('Space2')

    @defcells
    def a(name):
        return 'Hello ' + name

    @defcells
    def b(name):
        return a(name)

    yield m
    m._impl._check_sanity()
    m.close()


def test_node_repr_str_values(str_values):
    str_values.Space2.b("World")
    assert (repr(str_values.Space2.b.preds("World")) ==
            "[Model2.Space2.a(name='World')='Hello World']")

