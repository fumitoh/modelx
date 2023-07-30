import pytest
from modelx import defcells, new_model, new_space

# --------------------------------------------------------------------------
# Test comparison


@pytest.fixture
def constcells():

    model, space = new_model(), new_space()


    @defcells
    def foo():
        return 2

    @defcells
    def bar():
        return 3

    @defcells
    def baz():
        return 4

    yield space
    model._impl._check_sanity()
    model.close()

def test_lt(constcells):
    with pytest.warns(UserWarning):
        assert constcells.bar < constcells.baz
    with pytest.warns(UserWarning):
        assert not constcells.baz < constcells.bar
    with pytest.warns(UserWarning):
        assert 3 < constcells.baz
    with pytest.warns(UserWarning):
        assert constcells.bar < 4


def test_le(constcells):
    with pytest.warns(UserWarning):
        assert constcells.bar <= constcells.baz
    with pytest.warns(UserWarning):
        assert not constcells.baz <= constcells.bar
    with pytest.warns(UserWarning):
        assert 3 <= constcells.baz
    with pytest.warns(UserWarning):
        assert constcells.bar <= 4


def test_gt(constcells):
    with pytest.warns(UserWarning):
        assert not constcells.bar > constcells.baz
    with pytest.warns(UserWarning):
        assert constcells.baz > constcells.bar
    with pytest.warns(UserWarning):
        assert not 3 > constcells.baz
    with pytest.warns(UserWarning):
        assert not constcells.bar > 4


def test_ge(constcells):
    with pytest.warns(UserWarning):
        assert not constcells.bar >= constcells.baz
    with pytest.warns(UserWarning):
        assert constcells.baz >= constcells.bar
    with pytest.warns(UserWarning):
        assert not 3 >= constcells.baz
    with pytest.warns(UserWarning):
        assert not constcells.bar >= 4


# --------------------------------------------------------------------------
# Test value property

def test_call(constcells):
    assert constcells.foo() == 2


def test_eq(constcells):
    with pytest.warns(UserWarning):
        assert constcells.foo == 2
    with pytest.warns(UserWarning):
        assert 2 == constcells.foo


def test_setattr_value(constcells):
    cells = constcells.new_cells()
    cells.value = 5
    assert cells() == 5


def test_getattr_value(constcells):
    cells = constcells.new_cells(formula="lambda: 3")
    assert cells.value == 3


def test_delattr_value(constcells):
    cells = constcells.new_cells()
    cells.allow_none = True
    cells.value = 2
    del cells.value
    assert cells.value is None


def test_bool(constcells):
    with pytest.warns(UserWarning):
        assert bool(constcells.bar)
