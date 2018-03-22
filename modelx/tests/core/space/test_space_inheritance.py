import pytest

from modelx import *

def create_testmodel():

    # base<------------derived
    #  |                  |
    # subspace          subspace
    #  |     |            |    |
    # fibo  nestedsub    fibo  nestedsub
    #        |                  |
    #       fibo               fibo

    model, base = new_model(), new_space('base')
    subspace = base.new_space('subspace')
    nestedsub = subspace.new_space('nestedsub')
    derived = model.new_space('derived', bases=base)

    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo(x - 2)

    subspace.new_cells(formula=fibo)
    nestedsub.new_cells(formula=fibo)

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
    assert 'fibo' in model.derived.subspace.cells
    assert 'fibo' in model.derived.subspace.nestedsub.cells

def test_del_cells_in_nestedspace():
    """Test deletion of cells in derived nested spaces."""

    model = create_testmodel()
    del model.base.subspace.fibo
    del model.base.subspace.nestedsub.fibo

    assert 'fibo' not in model.derived.subspace
    assert 'fibo' not in model.derived.subspace.nestedsub

def test_new_space_in_nestedspace():
    """Test creation of spaces in derived nested space."""

    # base<----------------------------derived
    #  |                                 |
    # subspace                         subspace
    #  |                                 |
    # nestedsub                        nestedsub
    #  |                                 |
    # supernested<-Create this         supernested<-Test this if created!

    model = create_testmodel()
    model.base.subspace.nestedsub.new_space('supernested')

    assert 'supernested' in model.derived.subspace.nestedsub.spaces


def test_delattr_space_in_nestedspace():
    """Test deletion of a space in a derived nested space."""

    # base<----------------------------derived
    #  |                                 |
    # subspace                         subspace
    #  |                                 |
    # nestedsub<-Delete this          nestedsub<-Test this if deleted!

    model = create_testmodel()
    del model.base.subspace.nestedsub
    assert 'nestedsub' not in model.base.subspace.spaces
    assert 'nestedsub' not in model.derived.subspace.spaces


def test_delitem_space_in_nestedspace():
    """Test deletion of a space in a derived nested space."""

    model = create_testmodel()
    del model.base.subspace.spaces['nestedsub']
    assert 'nestedsub' not in model.base.subspace.spaces
    assert 'nestedsub' not in model.derived.subspace.spaces


def test_override_cells():
    """Test overriding a cells in derived space."""

    model = create_testmodel()
    assert 'fibo' in model.derived.subspace.derived_cells

    def fibo_new(x):
        if x == 0 or x == 1:
            return x + 1
        else:
            return fibo(x - 1) + fibo(x - 2)

    cells = model.derived.subspace.new_cells(name='fibo', formula=fibo_new)

    assert 'fibo' not in model.derived.subspace.derived_cells
    assert model.derived.subspace.self_cells['fibo'] is cells
    assert cells(2) == 3
