import pytest

import sys
import os

from modelx import *
from modelx.tests.testdata import XL_TESTDATA


@pytest.fixture(scope="module")
def testmodel():
    m = new_model()
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "range_, transpose", [("C9:E25", False),
                          ("C36:S38", True)]
)
def test_single_param(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        transpose=transpose
    )

    for i in range(16):
        assert space.Cells1[i] == 1000 + i
        assert space.Cells2[i] == 2000 + i


@pytest.mark.parametrize(
    "range_, transpose", [("H9:K25", False),
                          ("C42:S45", True)]
)
def test_multi_param(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        param_cols=[0, 1],
        transpose=transpose
    )

    for i in range(16):
        assert space.Cells1[i, 100+i] == 1000 + i
        assert space.Cells2[i, 100+i] == 2000 + i



@pytest.mark.parametrize(
    "range_, transpose", [("C3:H24", False), ("C32:X37", True)]
)
def test_new_space_from_excel(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestSpaceTables",
        names_row=0,
        param_cols=[0, 1],
        names_col=1,
        param_rows=[1],
        space_param_order=[1],
        cells_param_order=[2, 0],
        transpose=transpose,
    )

    for product, offset1 in zip(["A", "B"], [0, 1000]):

        child = space[product]
        assert child.Product == product

        for cells, offset2 in zip(["Cells1", "Cells2"], [1000, 2000]):
            assert child.cells[cells].parameters == ("Sex", "Year")

            for sex, offset3 in zip(["M", "F"], [0, 1000]):
                for year in range(10):
                    assert (
                        child.cells[cells](sex, year)
                        == year + offset1 + offset2 + offset3
                    )


@pytest.mark.parametrize(
    "range_, transpose", [("K3:M5", False), ("C41:E43", True)]
)
def test_new_space_from_excel_const(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestSpaceTables",
        names_row=0,
        param_cols=[0],
        space_param_order=[0],
        cells_param_order=[],
        transpose=transpose,
    )

    for product, offset in zip(["A", "B"], [0, 1]):
        for cells, value in zip(["Cells1", "Cells2"], [1, 2]):
            assert space[product].cells[cells]() == value + offset
