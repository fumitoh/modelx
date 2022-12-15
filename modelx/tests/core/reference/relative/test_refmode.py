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
    yield m
    m._impl._check_sanity()
    m.close()

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


@pytest.mark.parametrize("mode", ["relative", "auto"])
def test_refer_sibling(mode):
    """
        A---B-------foo <-+
            |   |         |
            |   +---bar --+
            D
    """
    import modelx as mx

    m = mx.new_model()
    A = mx.new_space('A')
    B = A.new_space('B')

    @mx.defcells
    def foo(x):
        return x

    B.set_ref("bar", foo, mode)
    D = m.new_space('D', bases=B)

    assert D.bar is D.foo
    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize("mode", ["absolute", "auto"])
def test_refer_parent(mode):
    """
        A---B-------foo
            |   |
            |   +---bar --> A
            D
    """
    import modelx as mx

    m = mx.new_model()
    A = mx.new_space('A')
    B = A.new_space('B')

    @mx.defcells
    def foo(x):
        return x

    B.set_ref("bar", A, mode)
    D = m.new_space('D', bases=B)

    assert D.bar is A

    m._impl._check_sanity()
    m.close()

def test_refer_parent_error():
    """
        A---B-------foo
            |   |
            |   +---bar --> A
            D
    """
    import modelx as mx

    m = mx.new_model()
    A = m.new_space('A')
    B = A.new_space('B')

    @mx.defcells
    def foo(x):
        return x

    B.set_ref("bar", A, "relative")

    with pytest.raises(ValueError):
        D = m.new_space('D', bases=B)

    m._impl._check_sanity()
    m.close()