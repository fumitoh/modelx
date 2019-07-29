import pytest

import sys
import os

from modelx.testing.testutil import compare_model
import modelx as mx
from .. import XL_TESTDATA

@pytest.fixture(
    params=[("C9:E25", False), ("C36:S38", True)])
def single_param(request, tmp_path):
    range_, orientation = request.param

    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[0],
        param_order=[0],
        transpose=orientation,
    )

    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]

    return space, target


def test_single_param(single_param):

    # Compare values
    src, trg = single_param
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param",)
        for param in range(16):
            assert trg.cells[cells](param) == offset + param

    # Compare components
    compare_model(src.model, trg.model)


@pytest.fixture(params=[("H9:K25", False), ("C42:S45", True)])
def multiple_prams(request, tmp_path):

    range_, orientation = request.param
    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[0, 1],
        param_order=[0, 1],
        transpose=orientation,
    )
    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]

    return space, target


def test_multiple_params(multiple_prams):

    # Compare values
    src, trg = multiple_prams

    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param1", "Param2")
        for param in range(16):
            assert trg.cells[cells](param, param + 100) == offset + param

    # Compare components
    compare_model(src.model, trg.model)


@pytest.fixture(params=[("N8:R25", False), ("C49:T53", True)])
def extra_params(request, tmp_path):

    range_, orientation = request.param
    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[0],
        names_col=0,
        param_rows=[1],
        param_order=[1, 0],
        transpose=orientation,
    )
    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]
    return space, target


def test_extra_params(extra_params):

    # Compare values
    src, trg = extra_params

    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Sex", "Param")
        for param in range(16):
            assert trg.cells[cells]("M", param) == offset + param
            assert trg.cells[cells]("F", param) == offset + param + 1000

    # Compare components
    compare_model(src.model, trg.model)


@pytest.fixture(params=[("U8:Z29", False), ("C57:X62", True)])
def extra_multiple_prams(request, tmp_path):

    range_, orientation = request.param
    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[0, 1],
        names_col=1,
        param_rows=[1],
        param_order=[1, 2, 0],
        transpose=orientation,
    )
    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]
    return space, target


def test_extra_multiple_prams(extra_multiple_prams):

    # Compare values
    src, trg = extra_multiple_prams

    for cells, offset1 in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Product", "Sex", "Year")
        for product, offset2 in zip(["A", "B"], [0, 1000]):
            for sex, offset3 in zip(["M", "F"], [0, 1000]):
                for year in range(10):
                    assert (
                        trg.cells[cells](product, sex, year)
                        == year + offset1 + offset2 + offset3
                    )

    # Compare components
    compare_model(src.model, trg.model)


@pytest.fixture(params=[("AC8:AD9", False), ("C66:D67", True)])
def consts(request, tmp_path):

    range_, orientation = request.param
    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[],
        param_order=[],
        transpose=orientation,
    )
    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]
    return space, target


def test_consts(consts):

    # Compare values
    src, trg = consts
    for cells, value in zip(["Cells1", "Cells2"], [1, 2]):
        assert trg.cells[cells]() == value

    # Compare components
    compare_model(src.model, trg.model)


@pytest.fixture(params=[("AG8:AJ11", False), ("C71:F74", True)])
def empty_params(request, tmp_path):

    range_, orientation = request.param
    model, space = mx.new_model(), mx.new_space()
    space.new_cells_from_excel(
        book=XL_TESTDATA,
        range_=range_,
        sheet="TestTables",
        names_row=0,
        param_cols=[0, 1],
        param_order=[0, 1],
        transpose=orientation,
    )
    mx.write_model(model, tmp_path)
    target = mx.read_model(tmp_path).spaces[space.name]
    return space, target


def test_empty_params(empty_params):

    # Compare values
    src, trg = empty_params

    for cells, offset in zip(["Cells1", "Cells2"], [0, 1]):
        assert trg.cells[cells]() == 0 + offset
        assert trg.cells[cells](1) == 1 + offset
        assert trg.cells[cells](None, 2) == 2 + offset

    # Compare components
    compare_model(src.model, trg.model)