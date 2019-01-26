import modelx as mx
from modelx import defcells

import pytest


@pytest.fixture
def no_values():

    model = mx.new_model('Model')
    space = model.new_space('Space')

    @defcells
    def param0():
        return 0

    @defcells
    def param1(x):
        return x

    @defcells
    def param2(x, y):
        return x * y

    return space


@pytest.fixture
def has_values(no_values):

    no_values.param0()
    no_values.param1(1)
    no_values.param2(2, 3)

    return no_values


def test_node_repr(no_values):

    s = no_values
    assert repr(s.param0.node()) == "Model.Space.param0()"
    assert repr(s.param1.node(1))  == "Model.Space.param1(x=1)"
    assert repr(s.param2.node(2, 3)) == "Model.Space.param2(x=2, y=3)"


def test_node_repr_has_values(has_values):

    s = has_values
    assert repr(s.param0.node()) == "Model.Space.param0()=0"
    assert repr(s.param1.node(1)) == "Model.Space.param1(x=1)=1"
    assert repr(s.param2.node(2, 3)) == "Model.Space.param2(x=2, y=3)=6"
