import modelx as mx
import pytest

@pytest.fixture
def dynref_model():
    """
        A---B---C---foo <-+
            |   |         |
            |   +---bar --+
            |
            D[a]--baz <- D.C
    """
    m = mx.new_model()
    A = mx.new_space('A')
    B = A.new_space('B')
    C = B.new_space('C')

    @mx.defcells
    def foo(x):
        return x

    D = m.new_space('D')
    D.add_bases(B)
    D.parameters = ('a',)
    yield m
    m._impl._check_sanity()
    m.close()


def test_dynref(dynref_model):

    m = dynref_model

    m.A.B.C.bar = m.A.B.C.foo
    m.D.baz = m.D.C
    assert m.D[1].C.bar is m.D[1].C.foo
    assert m.D[1].baz is m.D[1].C

    m.A.B.C.absref(bar=m.A.B.C.foo)
    m.D.absref(baz=m.D.C)
    assert m.D[1].C.bar is m.A.B.C.foo
    assert m.D[1].baz is m.D.C

    m.A.B.C.relref(bar=m.A.B.C.foo)
    assert m.D[1].C.bar is m.D[1].C.foo

    m.A.B.C.absref(bar=m.A.B.C.foo)
    assert m.D[1].C.bar is m.A.B.C.foo


@pytest.fixture
def dynautoref_model():
    """
        A---B---C---bar <- A
            |
            D[a]--baz <- A
    """
    m = mx.new_model()
    C = m.new_space('A').new_space('B').new_space('C')
    D = m.new_space('D', bases=m.A.B)
    D.parameters = ('a',)

    yield m
    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize("refmode", ["auto", "absolute"])
def test_dynref_absolute(dynautoref_model, refmode):
    m = dynautoref_model
    m.A.B.C.set_ref('bar', m.A, refmode=refmode)

    assert m.D[1].C.bar is m.A


def test_dynref_error(dynautoref_model):
    m = dynautoref_model
    with pytest.raises(ValueError):
        m.A.B.C.set_ref('bar', m.A, refmode="relative")


def test_change_dynbase_ref():

    m = mx.new_model()
    A = m.new_space('A')
    A.parameters = ('i',)

    @mx.defcells
    def foo(x):
        return x

    A.absref(bar=foo)
    A.bar = foo

    assert A[1].bar.parent is A[1]
    m._impl._check_sanity()
    m.close()