"""
Test patterns
    test_cellsmapproxy_contains
    test_space_delattr_cells
    test_space_new_cells_override_derived_cells
"""

import modelx as mx
import pytest


def fibo(x):
    if x == 0 or x == 1:
        return x
    else:
        return fibo(x - 1) + fibo(x - 2)


@pytest.fixture
def testmodel():
    """
        derived<-----------base
         |  +---fibo       | +----fibo
        child---fibo      child---fibo
         |                 |
        nested--fibo      nested--fibo
    """
    model, base = mx.new_model(), mx.new_space("base")
    child = base.new_space("child")
    nested = child.new_space("nested")
    derived = model.new_space("derived", bases=base)
    base.new_cells(formula=fibo)
    child.new_cells(formula=fibo)
    nested.new_cells(formula=fibo)
    return model


pickleparam = [False, True]


@pytest.fixture(params=pickleparam)
def unpickled_model(request, testmodel, tmpdir_factory):

    model = testmodel
    if request.param:
        file = str(tmpdir_factory.mktemp("data").join("testmodel.mx"))
        model.save(file)
        model.close()
        model = mx.open_model(file)

    yield model
    model.close()


def test_model_delattr_basespace(unpickled_model):
    model = unpickled_model

    assert "base" in model.spaces
    # with pytest.raises(ValueError):
    #     del model.base
    del model.base
    assert "base" not in model.spaces


def test_model_delitem_basespace(unpickled_model):
    model = unpickled_model

    assert "base" in model.spaces
    # with pytest.raises(ValueError):
    #     del model.spaces['base']
    del model.spaces["base"]
    assert "base" not in model.spaces


def test_space_delattr_space(unpickled_model):
    """Test deletion of a space in a derived nested space."""
    model = unpickled_model
    assert "nested" in model.derived.child.spaces
    del model.base.child.nested
    assert "nested" not in model.base.child.spaces
    assert "nested" not in model.derived.child.spaces


def test_space_delitem_space(unpickled_model):
    model = unpickled_model
    assert "nested" in model.derived.child.spaces
    del model.base.child.spaces["nested"]
    assert "nested" not in model.base.child.spaces
    assert "nested" not in model.derived.child.spaces


def test_spacemapproxy_contains(unpickled_model):
    """Test spaces, self_spaces, derived_spaces """
    model = unpickled_model
    assert "child" in model.derived.spaces


@pytest.fixture(params=["derived", "derived.child", "derived.child.nested"])
def testspaces(request, unpickled_model):
    trgname = request.param.split(".")
    srcname = trgname.copy()
    srcname[0] = "base"
    target = source = unpickled_model
    for space in trgname:
        target = target.spaces[space]
    for space in srcname:
        source = source.spaces[space]

    return target, source


def test_inheritance(testspaces):

    target, source = testspaces

    assert source.is_base(target)
    assert target.is_sub(source)


def test_properties(testspaces):

    target, source = testspaces

    assert target.is_static()
    assert source.is_static()

    assert not source.is_dynamic()
    assert not target.is_dynamic()

    assert source.is_defined()
    assert not source.is_derived()

    if source.name == "base":
        assert target.is_defined()
        assert not target.is_derived()
    else:
        assert not target.is_defined()
        assert target.is_derived()


def test_cellsmapproxy_contains(testspaces):
    """Test creation of cells in derived nested spaces."""
    target, _ = testspaces

    assert "fibo" in target.cells


def test_space_delattr_cells(testspaces):
    """Test deletion of cells in derived nested spaces."""

    target, source = testspaces
    del source.fibo
    assert "fibo" not in target.cells


def test_space_new_space(testspaces):
    target, source = testspaces
    space = source.new_cells(name="tempspace")
    assert space is source.tempspace
    assert space is not target.tempspace


def test_space_new_cells(testspaces):
    target, source = testspaces
    cells = source.new_cells(name="tempcells")
    assert cells is source.tempcells
    assert cells is not target.tempcells


def test_space_new_cells_override(testspaces):
    """Test overriding a cells in derived space."""

    target, source = testspaces

    def fibo_new(x):
        if x == 0 or x == 1:
            return x + 1
        else:
            return fibo(x - 1) + fibo(x - 2)

    # cells = target.new_cells(name='fibo', formula=fibo_new)
    cells = target.cells["fibo"]
    cells.set_formula(fibo_new)

    # assert 'fibo' not in target.derived_cells
    # assert target.self_cells['fibo'] is cells
    # assert not cells.is_derived()
    assert cells(2) == 3
