import modelx as mx
import pytest

@pytest.fixture
def testmodel():
    """
        SpaceA[i]---foo(x)

        SpaceB---RefSpaceA
               +-bar(x)
    """
    m = mx.new_model()
    A = m.new_space("SpaceA")
    A.formula = lambda i: None

    @mx.defcells
    def foo(x):
        return x * i

    B = m.new_space("SpaceB")
    B.RefSpaceA = A

    @mx.defcells
    def bar(x):
        return x * RefSpaceA[5].foo(10)
    
    bar(5)

    yield m
    m._impl._check_sanity()
    m.close()

def test_space_preds(testmodel):

    bar = testmodel.SpaceB.bar

    preds = set(bar.preds(5))
    expected = {testmodel.SpaceA.node(5), testmodel.SpaceA[5].foo.node(10)}

    assert preds == expected


def test_space_succs(testmodel):

    succs = set(testmodel.SpaceA.succs(5))
    expected = {testmodel.SpaceB.bar.node(5)}

    assert succs == expected