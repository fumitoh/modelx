import modelx as mx
from modelx.core.reference import ReferenceNode
import pytest

@pytest.fixture(scope='module')
def precedstest():

    m = mx.new_model('Preceds')
    space = m.new_space('Space1')
    space.new_space('Child')
    space.Child.new_space('GrandChild')

    space.x = 1
    space.Child.y = 2
    space.Child.GrandChild.z = 3

    @mx.defcells(space=space)
    def foo(t):
        return t

    @mx.defcells(space=space)
    def bar(t):
        return foo(t) + x + Child.y + Child.GrandChild.z

    space.bar(3)
    return space


def test_precedents(precedstest):

    bar = precedstest.bar
    foo = precedstest.foo

    preceds = bar.node(3).precedents
    x = mx.get_object("Preceds.Space1.x", as_proxy=True)
    z = mx.get_object("Preceds.Space1.Child.GrandChild.z", as_proxy=True)
    y = mx.get_object("Preceds.Space1.Child.y", as_proxy=True)

    assert preceds[0] == foo.node(3)
    assert preceds[1] == ReferenceNode((x._impl,))
    assert preceds[2] == ReferenceNode((z._impl,))
    assert preceds[3] == ReferenceNode((y._impl,))

    assert repr(preceds[0]) == "Preceds.Space1.foo(t=3)=3"
    assert repr(preceds[1]) == "Preceds.Space1.x=1"
    assert repr(preceds[2]) == "Preceds.Space1.Child.GrandChild.z=3"
    assert repr(preceds[3]) == "Preceds.Space1.Child.y=2"

