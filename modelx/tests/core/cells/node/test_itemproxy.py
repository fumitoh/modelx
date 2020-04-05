import modelx as mx
import pytest



@pytest.fixture
def testspace():

    s = mx.new_space()

    def foo(x):
        return foo(x-1) + 1 if x > 0 else 0

    foo = s.new_cells(formula=foo)

    foo[10]

    return s


def test_node(testspace):
    foo = testspace.foo
    node = foo.node(5)

    assert node.value == 5
    assert node.args == (5,)


def test_preds(testspace):
    foo = testspace.foo
    preds = foo.preds(5)

    assert preds[0].value == 4
    assert preds[0].args == (4,)
    assert preds[0] == foo.node(4)


def test_succs(testspace):
    foo = testspace.foo
    succs = foo.succs(5)

    assert succs[0].value == 6
    assert succs[0].args == (6,)
    assert succs[0] == foo.node(6)

