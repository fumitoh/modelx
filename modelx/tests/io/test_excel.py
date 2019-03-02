import os
import sys
import modelx.io.excel as xl

import pytest
import openpyxl as opxl

test_path = os.path.dirname(sys.modules[__name__].__file__)
sample_book = test_path + "/test_xl_range.xlsx"


@pytest.fixture
def book_with_namedranges():
    return opxl.load_workbook(sample_book, data_only=True)


@pytest.mark.parametrize(
    "range_expr, sheet", [("NamedRange1", None), ("C3:E5", "SHEET1")]
)
def test_get_xlrange_booklevel(range_expr, sheet):
    result = xl.read_range(sample_book, range_expr, sheet)

    keys = ((r, c) for r in range(3) for c in range(3))

    check = True
    for r, c in keys:
        check = check and result[(r, c)] == (r + 3) * 10 + (c + 3)

    assert check


@pytest.mark.parametrize("range_expr", ["NamedRange1", "C3:E5"])
def test_get_xlrange_sheetlevel(range_expr):
    result = xl.read_range(sample_book, range_expr, "SHEET 2")

    keys = ((r, c) for r in range(3) for c in range(3))

    check = True
    for r, c in keys:
        check = check and result[(r, c)] == (r + 3) * 100 + (c + 3) * 10

    assert check


@pytest.mark.parametrize(
    "range_expr, sheet", [("SingleCell", None), ("C8", "SHEET1")]
)
def test_get_xlrange_booklevel_singlecell(range_expr, sheet):
    result = xl.read_range(sample_book, range_expr, sheet)
    assert result == "string"


def test_get_namedrange_booklevel(book_with_namedranges):

    book = book_with_namedranges
    range1 = xl._get_namedrange(book, "NamedRange1")

    check = range1[0][0].parent.title == "Sheet1"
    for row_ind, row in enumerate(range1):
        for col_ind, cell in enumerate(row):
            check = check and (
                cell.value == (row_ind + 3) * 10 + (col_ind + 3)
            )
    assert check


def test_get_namedrange_sheetlevel(book_with_namedranges):

    book = book_with_namedranges
    range1_local = xl._get_namedrange(book, "NamedRange1", sheetname="Sheet 2")

    check = range1_local[0][0].parent.title == "Sheet 2"
    for row_ind, row in enumerate(range1_local):
        for col_ind, cell in enumerate(row):
            check = check and (
                cell.value == (row_ind + 3) * 100 + (col_ind + 3) * 10
            )
    assert check


def test_get_namedranges_multipleranges(book_with_namedranges):

    book = book_with_namedranges
    multrange = xl._get_namedrange(book, "NamedMultiRanges")

    check = multrange[0].value == "ABC"
    for i in range(3):
        check = check and multrange[1][i][0].value == i + 1
    assert check


@pytest.mark.parametrize(
    "valid_range_address", ["A1", "XFD1048576", "A1:B3", "A1:XFD1048576"]
)
def test_is_range_address_valid(valid_range_address):
    assert xl._is_range_address(valid_range_address)


@pytest.mark.parametrize(
    "invalid_range_address", ["XFE1", "XFD1048577", "B3:A1", "A1:XFE1048577"]
)
def test_is_range_address_invalid(invalid_range_address):
    assert not xl._is_range_address(invalid_range_address)
