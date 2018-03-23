import pytest

from modelx import *

def create_testmodel():

    # derived<-----------base
    #  |                  |
    # child--+          child--+
    #  |     |            |    |
    # fibo  nested      fibo  nested
    #        |                 |
    #       fibo              fibo

    model, base = new_model(), new_space('base')
    child = base.new_space('child')
    nested = child.new_space('nested')
    derived = model.new_space('derived', bases=base)

    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo(x - 2)

    child.new_cells(formula=fibo)
    nested.new_cells(formula=fibo)

    return model


def test_delattr_space_in_model():

    model = create_testmodel()

    assert 'base' in model.spaces
    del model.base
    assert 'base' not in model.spaces


def test_delitem_space_in_model():

    model = create_testmodel()
    assert 'base' in model.spaces
    del model.spaces['base']
    assert 'base' not in model.spaces

def test_new_cells_in_nestedspace():
    """Test creation of cells in derived nested spaces."""

    model = create_testmodel()
    assert 'fibo' in model.derived.child.cells
    assert 'fibo' in model.derived.child.nested.cells

def test_del_cells_in_nestedspace():
    """Test deletion of cells in derived nested spaces."""

    model = create_testmodel()
    del model.base.child.fibo
    del model.base.child.nested.fibo

    assert 'fibo' not in model.derived.child
    assert 'fibo' not in model.derived.child.nested

def test_new_space_in_nestedspace():
    """Test creation of spaces in derived nested space."""

    # base<----------------------------derived
    #  |                                 |
    # child                            child
    #  |                                 |
    # nested                           nested
    #  |                                 |
    # supernested<-Create this         supernested<-Test this if created!

    model = create_testmodel()
    model.base.child.nested.new_space('supernested')

    assert 'supernested' in model.derived.child.nested.spaces


def test_delattr_space_in_nestedspace():
    """Test deletion of a space in a derived nested space."""

    # base<----------------------------derived
    #  |                                 |
    # child                            child
    #  |                                 |
    # nested<-Delete this          nested<-Test this if deleted!

    model = create_testmodel()
    del model.base.child.nested
    assert 'nested' not in model.base.child.spaces
    assert 'nested' not in model.derived.child.spaces


def test_delitem_space_in_nestedspace():
    """Test deletion of a space in a derived nested space."""

    model = create_testmodel()
    del model.base.child.spaces['nested']
    assert 'nested' not in model.base.child.spaces
    assert 'nested' not in model.derived.child.spaces


def test_override_cells():
    """Test overriding a cells in derived space."""

    model = create_testmodel()
    assert 'fibo' in model.derived.child.derived_cells

    def fibo_new(x):
        if x == 0 or x == 1:
            return x + 1
        else:
            return fibo(x - 1) + fibo(x - 2)

    cells = model.derived.child.new_cells(name='fibo', formula=fibo_new)

    assert 'fibo' not in model.derived.child.derived_cells
    assert model.derived.child.self_cells['fibo'] is cells
    assert cells(2) == 3
