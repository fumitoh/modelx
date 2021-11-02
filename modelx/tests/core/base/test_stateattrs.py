from modelx.core.base import get_mixin_slots, add_stateattrs
import pytest


class Base:
    __slots__ = ('base', 'no_base')
    __no_state = ('no_base',)


class Mixin:
    __slots__ = ()
    __mixin_slots = ('mixin', 'no_mixin')
    __no_state = ('no_mixin',)


class Sub(Mixin, Base):
    __slots__ = ('sub', 'no_sub') + get_mixin_slots(Mixin, Base)
    __no_state = ('no_sub',)


class Sub2(Base, Mixin):
    __slots__ = ('sub', 'no_sub') + get_mixin_slots(Base, Mixin)
    __no_state = ('no_sub',)


@pytest.mark.parametrize("klass", [Sub, Sub2])
def test_add_stateattrs(klass):
    add_stateattrs(klass)
    assert klass.__slots__ == ('sub', 'no_sub', 'mixin', 'no_mixin')
    assert Sub.stateattrs == ('sub', 'mixin', 'base')

