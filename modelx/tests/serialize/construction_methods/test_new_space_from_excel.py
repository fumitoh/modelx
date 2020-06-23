import pytest

import sys
import os

from modelx.testing.testutil import compare_model
import modelx as mx

from modelx.tests.testdata import XL_TESTDATA


@pytest.fixture(params=[("C3:H24", False, "write_model"),
                        ("C32:X37", True, "zip_model")])
def extra_params(request, tmp_path):
    range_, orientation, write_method = request.param
    model = mx.new_model()
    space = model.new_space_from_excel(
        book=XL_TESTDATA,
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

    getattr(mx, write_method)(model, tmp_path)
    # Write twice to check copy from renamed backup.
    m2 = mx.read_model(tmp_path)
    getattr(mx, write_method)(m2, tmp_path)

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


@pytest.fixture(params=[("K3:M5", False, "write_model"),
                        ("C41:E43", True, "zip_model")])
def consts(request, tmp_path):
    range_, orientation, write_method = request.param
    model = mx.new_model()
    space = model.new_space_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestSpaceTables",
        name="TestSpace",
        names_row=0,
        param_cols=[0],
        space_param_order=[0],
        cells_param_order=[],
        transpose=orientation,
    )

    getattr(mx, write_method)(model, tmp_path)
    # Write twice to check copy from renamed backup.
    m2 = mx.read_model(tmp_path)
    getattr(mx, write_method)(m2, tmp_path)
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