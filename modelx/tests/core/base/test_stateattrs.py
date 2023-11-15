from modelx.core.base import get_mixin_slots
import pytest


class Base:
    __slots__ = ('base', 'no_base')


class Mixin:
    __slots__ = ()
    __mixin_slots = ('mixin', 'no_mixin')


class Sub(Mixin, Base):
    __slots__ = ('sub', 'no_sub') + get_mixin_slots(Mixin, Base)


class Sub2(Base, Mixin):
    __slots__ = ('sub', 'no_sub') + get_mixin_slots(Base, Mixin)


@pytest.mark.parametrize("klass", [Sub, Sub2])
def test_add_stateattrs(klass):
    assert klass.__slots__ == ('sub', 'no_sub', 'mixin', 'no_mixin')

