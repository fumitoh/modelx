import modelx as mx
import pytest

def test_is_derived():

    s = mx.new_model().new_space()
    c = s.new_space(name='ChildSpace')
    c.new_cells('foo')

    s.formula = lambda i: None

    space1 = s[1]

    assert space1._is_derived()
    assert space1.ChildSpace._is_derived()
    assert space1.ChildSpace.foo._is_derived()