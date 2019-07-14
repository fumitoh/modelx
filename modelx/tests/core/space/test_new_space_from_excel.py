import pytest

import sys
import os

from modelx import *

test_path = (
    os.path.dirname(sys.modules[__name__].__file__) + "/../data/testdata.xlsx"
)


@pytest.fixture
def testmodel():
    return new_model()

# -- SpaceContainer --

@pytest.mark.parametrize(
    "range_, transpose", [("C3:H24", False), ("C32:X37", True)]
)
def test_new_space_from_excel(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=test_path,
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
        book=test_path,
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
