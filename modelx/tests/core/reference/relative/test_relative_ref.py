import modelx as mx
import pytest


@pytest.fixture
def basic_relref():
    """
        Base----ChildA---foo
                |
                +-ChildB----A---> ChildA
                    +-------f---> foo
    """
    m = mx.new_model()
    Base = mx.new_space("Base")
    BaseChildA = Base.new_space("ChildA")

    @mx.defcells
    def foo():
        return c

    BaseChildB = Base.new_space("ChildB")
    BaseChildB.A = BaseChildA
    BaseChildB.f = foo

    yield m
    m._impl._check_sanity()
    m.close()

@pytest.mark.skip   # TODO: Redesign relative reference to child spaces
def test_relative_reference(basic_relref):
    """
        Base----ChildA---foo
                |
                +-ChildB----A---> ChildA
                    +-------f---> foo

        Sub(Base)--B(Base.B)
    """

    m = basic_relref
    Base = m.Base
    Sub = m.new_space("Sub", bases=Base)
    Sub.new_space('ChildB', bases=Base.ChildB)

    assert Sub.ChildB.A is Sub.ChildA
    assert Sub.ChildB.f is Sub.ChildA.foo

    Base.ChildA.c = 3
    Sub.ChildA.c = 4

    assert Base.ChildB.f() == 3
    assert Sub.ChildB.f() == 4


def test_absolute_reference(basic_relref):
    """Sub->Base.ChildB"""

    Base = basic_relref.Base
    Sub = mx.new_space("Sub", bases=Base.ChildB)

    assert Sub.A is Base.ChildA
    assert Sub.f is Base.ChildA.foo

    Base.ChildA.c = 3

    assert Sub.f() == 3


@pytest.fixture
def derived_relref():
    """
        Base----A----B----C---foo<-A.B
                          |
        Sub-----A----B---C
                         |
        GSub---A---B----C

    """
    import modelx as mx

    m = mx.new_model()

    m.new_space('Base').new_space('A').new_space('B').new_space('C')
    m.new_space('Sub').new_space('A').new_space('B').new_space(
        'C', bases=m.Base.A.B.C)
    m.new_space('GSub').new_space('A').new_space('B').new_space(
        'C', bases=m.Sub.A.B.C)

    yield m
    m._impl._check_sanity()
    m.close()


def test_ref_assign(derived_relref):
    m = derived_relref

    m.Base.A.B.C.foo = m.Base.A
    assert m.GSub.A.B.C.foo is m.Base.A

    m.Base.A.B.C.foo = m.Base.A.B
    assert m.GSub.A.B.C.foo is m.Base.A.B


@pytest.fixture
def derived_relref2():
    """
        Base----Child-------GChild----GGChild---Ref<-Child/GChild
                               |
        Sub-----SubChild----SubGChild
         |
        GSub
    """
    import modelx as mx
    m = mx.new_model()

    GGChild = m.new_space('Base').new_space(
        'Child').new_space('GChild').new_space('GGChild')

    SubGChild = m.new_space('Sub').new_space('SubChild').new_space('SubGChild')
    SubGChild.add_bases(m.Base.Child.GChild)
    m.new_space('GSub')
    m.GSub.add_bases(m.Sub)

    yield m
    m._impl._check_sanity()
    m.close()

@pytest.mark.skip
def test_ref_assign2(derived_relref2):

    m = derived_relref2

    m.Base.Child.GChild.GGChild.Ref = m.Base.Child
    assert (m.GSub.SubChild.SubGChild.GGChild.Ref
            is m.Base.Child)

    m.Base.Child.GChild.GGChild.Ref = m.Base.Child.GChild
    assert (m.GSub.SubChild.SubGChild.GGChild.Ref
            is m.GSub.SubChild.SubGChild)


@pytest.mark.skip
def test_derived_relref3():
    """
        Base----Child-------GChild----GGChild---Ref<-GChild
                  |
        Sub----SubChild-----GChild----GGChild
                                         |
                                       GSub
    """
    import modelx as mx
    m = mx.new_model()

    GGChild = m.new_space('Base').new_space(
        'Child').new_space('GChild').new_space('GGChild')

    GGChild.Ref = m.Base.Child.GChild.GGChild
    SubChild = m.new_space('Sub').new_space('SubChild')
    GSub = m.new_space('GSub')
    SubChild.add_bases(m.Base.Child)
    GSub.add_bases(m.Sub.SubChild.GChild.GGChild)

    assert GSub.Ref is GSub

    GGChild.Ref = m.Base.Child.GChild

    assert GSub.Ref is GGChild.Ref
    assert SubChild.GChild.GGChild.Ref is SubChild.GChild
    m._impl._check_sanity()
    m.close()

def test_inherit_mutual_reference():
    """
        A---B---foo <- C
          +-C---bar <- B
    """
    m = mx.new_model()
    A = m.new_space('A')
    B = A.new_space('B')
    C = A.new_space('C')

    B.foo = C
    C.bar = B

    D = m.new_space('D', bases=A)
    m._impl._check_sanity()
    m.close()