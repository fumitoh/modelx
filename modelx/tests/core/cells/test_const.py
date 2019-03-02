import pytest
from modelx import defcells, new_model, new_space

# --------------------------------------------------------------------------
# Test comparison


@pytest.fixture
def constcells():

    model, space = new_model(), new_space()

    @defcells
    def bar():
        return 3

    @defcells
    def baz():
        return 4

    return space


def test_lt(constcells):
    assert constcells.bar < constcells.baz
    assert not constcells.baz < constcells.bar
    assert 3 < constcells.baz
    assert constcells.bar < 4


def test_le(constcells):
    assert constcells.bar <= constcells.baz
    assert not constcells.baz <= constcells.bar
    assert 3 <= constcells.baz
    assert constcells.bar <= 4


def test_gt(constcells):
    assert not constcells.bar > constcells.baz
    assert constcells.baz > constcells.bar
    assert not 3 > constcells.baz
    assert not constcells.bar > 4


def test_ge(constcells):
    assert not constcells.bar >= constcells.baz
    assert constcells.baz >= constcells.bar
    assert not 3 >= constcells.baz
    assert not constcells.bar >= 4


# --------------------------------------------------------------------------
# Test value property


def test_set_value(constcells):
    cells = constcells.new_cells()
    cells.value = 5
    assert cells() == 5


def test_get_value(constcells):
    cells = constcells.new_cells(formula="lambda: 3")
    assert cells.value == 3


def test_del_value(constcells):
    cells = constcells.new_cells()
    cells.allow_none = True
    cells.value = 2
    del cells.value
    assert cells.value is None


def test_bool(constcells):
    assert bool(constcells.bar)
