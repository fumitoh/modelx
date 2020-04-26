import pytest

import modelx as mx
from modelx import new_model, defcells
from modelx.testing.testutil import SuppressFormulaError

@pytest.fixture
def setitemsample():

    space = new_model(name="samplemodel").new_space(name="samplespace")

    funcdef = """def func(x): return 2 * x"""

    space.new_cells(formula=funcdef)

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo[x - 2]

    @defcells
    def double(x):
        double[x] = 2 * x

    @defcells
    def return_last(x):
        return return_last(x - 1)

    @defcells
    def balance(x):
        return balance(x-1) + flow(x-1)

    @defcells
    def flow(x):
        return 10

    return space


def test_setitem(setitemsample):
    setitemsample.fibo[0] = 1
    setitemsample.return_last[4] = 5
    assert setitemsample.fibo[2] == 2
    assert setitemsample.return_last(5) == 5


def test_setitem_str(setitemsample):
    cells = setitemsample.new_cells(formula="lambda s: 2 * s")
    cells["ABC"] = "DEF"
    assert cells["ABC"] == "DEF"


def test_setitem_in_cells(setitemsample):
    assert setitemsample.double[3] == 6


def test_setitem_in_formula_invalid_assignment_error(setitemsample):

    def invalid_in_formula_assignment(x):
        invalid_in_formula_assignment[x + 1] = 3 * x

    setitemsample.new_cells(formula=invalid_in_formula_assignment)
    with SuppressFormulaError():
        with pytest.raises(KeyError):
            setitemsample.invalid_in_formula_assignment[3]


def test_setitem_in_formula_duplicate_assignment_error(setitemsample):

    def duplicate_assignment(x):
        duplicate_assignment[x] = 4 * x
        return 4 * x

    setitemsample.new_cells(formula=duplicate_assignment)
    with SuppressFormulaError():
        with pytest.raises(ValueError):
            setitemsample.duplicate_assignment[4]


@pytest.mark.parametrize("recalc", [True, False])
def test_setitem_recalc(setitemsample, recalc):

    last_recalc = mx.get_recalc()

    try:
        mx.set_recalc(recalc)

        setitemsample.balance[0] = 0
        assert setitemsample.balance[10] == 100

        setitemsample.balance[0] = 100

        if recalc:
            assert len(setitemsample.balance) == 11
        else:
            assert len(setitemsample.balance) == 1

        assert setitemsample.balance[10] == 200

    finally:
        mx.set_recalc(last_recalc)
