import modelx as mx
from modelx.testing.testutil import ConfigureExecutor
import pytest


def test_change_attrref():
    """
        m---s---bar<-m.bar
        |
        +--bar[a]---x
    """
    m = mx.new_model()
    s = m.new_space()

    @mx.defcells
    def foo(x):
        return bar.x

    @mx.defcells
    def qux(y):
        return bar[1].x

    s2 = mx.new_space("bar", formula=lambda a: None)
    s.bar = s2

    s2.x = "bar"
    assert foo(3) == qux(3) == "bar"

    s2.x = "baz"
    assert foo(3) == qux(3) == "baz"

    m._impl._check_sanity()
    m.close()


# https://github.com/fumitoh/modelx/issues/43
def test_change_attrref2():

    model = mx.new_model()
    inputs = model.new_space("Inputs")

    inputs.a = 2
    inputs.b = 3

    calc = model.new_space("Pythagoras")

    @mx.defcells
    def pythagoras():
        return (Inputs.a ** 2 + Add.add2() ** 2) ** .5

    calc2 = model.new_space("Add")

    @mx.defcells
    def add2():
        return Inputs.a + Inputs.b

    calc.Inputs = inputs
    calc.Add = calc2
    calc2.Inputs = inputs

    assert model.Pythagoras.pythagoras() == (2 ** 2 + (2+3) ** 2) ** .5
    model.Inputs.a = 5
    assert model.Pythagoras.pythagoras() == (5 ** 2 + (5+3) ** 2) ** .5

    model._impl._check_sanity()
    model.close()


def test_change_ref_on_reassinged_formula():

    m = mx.new_model()
    s = mx.new_space()

    @mx.defcells
    def foo():
        return bar

    def temp():
        return baz

    foo.formula = temp

    s.baz = 4
    assert foo() == 4

    s.baz = 5
    assert foo() == 5

    m._impl._check_sanity()
    m.close()


def test_del_global_attrref():
    """
    m-----SpaceA-----foo
       +--SpaceB  +--s2
       +--x
    """
    m = mx.new_model()
    s = mx.new_space("SpaceA")

    @mx.defcells
    def foo(i):
        return s2.x

    s2 = mx.new_space(name="SpaceB", formula=lambda a: None)
    s.s2 = s2
    m.x = 3
    assert foo(3) == 3
    del m.x

    with ConfigureExecutor():
        with pytest.raises(AttributeError):
            foo(3)

    m._impl._check_sanity()
    m.close()


def test_del_attrref():
    """
    m-----A-----B---x
       |     +----foo
       +--C(A)
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    B.x = 3

    def foo():
        return B.x

    A.new_cells(formula=foo)
    C = m.new_space("C", bases=A)

    assert A.foo() == 3

    with ConfigureExecutor():
        with pytest.raises(NameError):
            C.foo() == 3

    del B.x

    with ConfigureExecutor():
        with pytest.raises(AttributeError):
            A.foo()

        with pytest.raises(NameError):
            C.foo()

    m._impl._check_sanity()
    m.close()