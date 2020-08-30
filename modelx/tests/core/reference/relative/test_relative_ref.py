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

    return m


def test_relative_reference(basic_relref):
    """Sub->Base"""

    Base = basic_relref.Base
    Sub = mx.new_space("Sub", bases=Base)

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
        Base----Child-------GChild----GGChild---Ref<-Child/GChild
                               |
        Sub-----SubChild----SubGChild
                   |
        GSub---GSubChild

    """
    import modelx as mx

    m = mx.new_model()

    GGChild = m.new_space('Base').new_space(
        'Child').new_space('GChild').new_space('GGChild')

    SubGChild = m.new_space('Sub').new_space('SubChild').new_space('SubGChild')
    GSubChild = m.new_space('GSub').new_space('GSubChild')
    SubGChild.add_bases(m.Base.Child.GChild)
    GSubChild.add_bases(m.Sub.SubChild)

    return m


def test_ref_assign(derived_relref):
    m = derived_relref

    # Inside
    m.Base.Child.GChild.GGChild.Ref = m.Base.Child.GChild
    assert m.GSub.GSubChild.SubGChild.GGChild.Ref is m.GSub.GSubChild.SubGChild

    # Outside
    m.Base.Child.GChild.GGChild.Ref = m.Base.Child
    assert m.GSub.GSubChild.SubGChild.GGChild.Ref is m.Base.Child


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

    return m


def test_ref_assign2(derived_relref2):

    m = derived_relref2

    m.Base.Child.GChild.GGChild.Ref = m.Base.Child
    assert (m.GSub.SubChild.SubGChild.GGChild.Ref
            is m.Base.Child)

    m.Base.Child.GChild.GGChild.Ref = m.Base.Child.GChild
    assert (m.GSub.SubChild.SubGChild.GGChild.Ref
            is m.GSub.SubChild.SubGChild)


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