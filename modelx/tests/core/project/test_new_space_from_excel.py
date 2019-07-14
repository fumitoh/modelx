import pytest

import sys
import os

from modelx.testing.testutil import compare_model
import modelx as mx

test_path = (
    os.path.dirname(sys.modules[__name__].__file__) + "/../data/testdata.xlsx"
)


@pytest.fixture(params=[("C3:H24", False), ("C32:X37", True)])
def extra_params(request, tmp_path):
    range_, orientation = request.param
    model = mx.new_model()
    space = model.new_space_from_excel(
        book=test_path,
        range_=range_,
        sheet="TestSpaceTables",
        name="TestSpace",
        names_row=0,
        param_cols=[0, 1],
        names_col=1,
        param_rows=[1],
        space_param_order=[1],
        cells_param_order=[2, 0],
        transpose=orientation,
    )

    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path)

    return model, target


def test_extra_params(extra_params):

    # Compare values
    src, trg = extra_params
    for product, offset1 in zip(["A", "B"], [0, 1000]):

        child = trg.TestSpace[product]
        assert child.Product == product

        for cells, offset2 in zip(["Cells1", "Cells2"], [1000, 2000]):
            assert child.cells[cells].parameters == ("Sex", "Year")

            for sex, offset3 in zip(["M", "F"], [0, 1000]):
                for year in range(10):
                    assert (
                        child.cells[cells](sex, year)
                        == year + offset1 + offset2 + offset3
                    )
    # Compare components
    compare_model(src, trg)


@pytest.fixture(params=[("K3:M5", False), ("C41:E43", True)])
def consts(request, tmp_path):
    range_, orientation = request.param
    model = mx.new_model()
    space = model.new_space_from_excel(
        book=test_path,
        range_=range_,
        sheet="TestSpaceTables",
        name="TestSpace",
        names_row=0,
        param_cols=[0],
        space_param_order=[0],
        cells_param_order=[],
        transpose=orientation,
    )

    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path)

    return model, target


def test_consts(consts):

    # Compare values
    src, trg = consts
    for product, offset in zip(["A", "B"], [0, 1]):
        for cells, value in zip(["Cells1", "Cells2"], [1, 2]):
            assert trg.TestSpace[product].cells[cells]() == value + offset

    # Compare components
    compare_model(src, trg)