import pytest

import modelx as mx
from modelx import new_model, defcells
from modelx.testing.testutil import SuppressFormulaError

@pytest.fixture
def setitemsample():

    model = mx.new_model(name="samplemodel")
    space = model.new_space(name="samplespace")

    funcdef = """def func(x): return 2 * x"""

    space.new_cells(formula=funcdef)

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo(x - 2)

    @defcells
    def double(x):
        return 2 * x

    @defcells
    def return_last(x):
        return return_last(x - 1)

    @defcells
    def balance(x):
        return balance(x-1) + flow(x-1)

    @defcells
    def flow(x):
        return 10

    yield space
    model._impl._check_sanity()
    model.close()


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
