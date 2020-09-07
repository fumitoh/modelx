import modelx as mx
import pytest

@pytest.fixture
def refmode_model():
    """
        A---B---C---foo <-+
            |   |         |
            |   +---bar --+
            D
    """
    import modelx as mx

    m = mx.new_model()
    A = mx.new_space('A')
    B = A.new_space('B')
    C = B.new_space('C')

    @mx.defcells
    def foo(x):
        return x

    D = m.new_space('D')
    D.add_bases(B)
    return m


def test_refmode_change(refmode_model):

    m = refmode_model

    m.A.B.C.bar = m.A.B.C.foo
    assert m.D.C.bar is m.D.C.foo

    m.A.B.C.absref(bar=m.A.B.C.foo)
    assert m.D.C.bar is m.A.B.C.foo

    m.A.B.C.relref(bar=m.A.B.C.foo)
    assert m.D.C.bar is m.D.C.foo

    m.A.B.C.absref(bar=m.A.B.C.foo)
    assert m.D.C.bar is m.A.B.C.foo