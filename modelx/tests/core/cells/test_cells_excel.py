import pytest

import sys
import os

from modelx import *

test_path = os.path.dirname(sys.modules[__name__].__file__) \
    + '/../data/testdata.xlsx'


@pytest.fixture
def testmodel():
    return new_model()


@pytest.mark.parametrize("range_, orientation", [
    ('C9:E25', False),
    ('C36:S38', True)
])
def test_new_cells_from_excel(testmodel, range_, orientation):

    space = testmodel.new_space()
    space.new_cells_from_excel(book=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0],
                                  param_order=[0],
                                  transpose=orientation)

    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):
        assert space.cells[cells].parameters == ('Param',)
        for param in range(16):
            assert space.cells[cells](param) == offset + param



@pytest.mark.parametrize("range_, orientation", [
    ('H9:K25', False),
    ('C42:S45', True)
])
def test_new_cells_from_excel_multparams(testmodel, range_, orientation):

    space = testmodel.new_space()
    space.new_cells_from_excel(book=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0, 1],
                                  param_order=[0, 1],
                                  transpose=orientation)


    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):

        assert space.cells[cells].parameters == ('Param1', 'Param2')
        for param in range(16):
            assert space.cells[cells](param, param + 100) == offset + param



@pytest.mark.parametrize("range_, orientation", [
    ('N8:R25', False),
    ('C49:T53', True)
])
def test_new_cells_from_excel_extparams(testmodel, range_, orientation):

    space = testmodel.new_space()
    space.new_cells_from_excel(book=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0],
                                  names_col=0, param_rows=[1],
                                  param_order=[1, 0],
                                  transpose=orientation)


    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):
        assert space.cells[cells].parameters == ('Sex', 'Param')
        for param in range(16):
            assert space.cells[cells]('M', param) == offset + param
            assert space.cells[cells]('F', param) == offset + param + 1000



@pytest.mark.parametrize("range_, orientation", [
    ('U8:Z29', False),
    ('C57:X62', True)
])
def test_new_cells_from_excel_multextparams(testmodel, range_, orientation):

    space = testmodel.new_space()
    space.new_cells_from_excel(book=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0, 1],
                                  names_col=1, param_rows=[1],
                                  param_order=[1, 2, 0],
                                  transpose=orientation)

    for cells, offset1 in zip(['Cells1', 'Cells2'], [1000, 2000]):

        assert space.cells[cells].parameters == ('Product', 'Sex', 'Year')
        for product, offset2 in zip(['A', 'B'], [0, 1000]):
            for sex, offset3 in zip(['M', 'F'], [0, 1000]):
                for year in range(10):
                    assert space.cells[cells](product, sex, year) \
                        == year + offset1 + offset2 + offset3



@pytest.mark.parametrize("range_, transpose", [
    ('AC8:AD9', False),
    ('C66:D67', True)
])
def test_new_cells_from_excel_const(testmodel, range_, transpose):

    space = testmodel.new_space()
    space.new_cells_from_excel(
        book=test_path,
        range_=range_,
        sheet='TestTables',
        names_row=0, param_cols=[],
        param_order=[],
        transpose=transpose)

    for cells, value in zip(['Cells1', 'Cells2'], [1, 2]):
        assert space.cells[cells]() == value


@pytest.mark.parametrize("range_, transpose", [
    ('AG8:AJ11', False),
    ('C71:F74', True)
])
def test_new_cells_from_excel_empty_prams(testmodel, range_, transpose):

    space = testmodel.new_space()
    space.new_cells_from_excel(
        book=test_path,
        range_=range_,
        sheet='TestTables',
        names_row=0, param_cols=[0, 1],
        param_order=[0, 1],
        transpose=transpose
    )

    for cells, offset in zip(['Cells1', 'Cells2'], [0, 1]):
        assert space.cells[cells]() == 0 + offset
        assert space.cells[cells](1) == 1 + offset
        assert space.cells[cells](None, 2) == 2 + offset


# -- SpaceContainer --

@pytest.mark.parametrize("range_, transpose", [
    ('C3:H24', False),
    ('C32:X37', True)
])
def test_new_space_from_excel(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=test_path,
        range_=range_,
        sheet='TestSpaceTables',
        names_row=0, param_cols=[0, 1],
        names_col=1, param_rows=[1],
        space_param_order=[1],
        cells_param_order=[2, 0],
        transpose=transpose)

    for product, offset1 in zip(['A', 'B'], [0, 1000]):

        child = space[product]
        assert child.Product == product

        for cells, offset2 in zip(['Cells1', 'Cells2'], [1000, 2000]):
            assert child.cells[cells].parameters == ('Sex', 'Year')

            for sex, offset3 in zip(['M', 'F'], [0, 1000]):
                for year in range(10):
                    assert child.cells[cells](sex, year) \
                            == year + offset1 + offset2 + offset3


@pytest.mark.parametrize("range_, transpose", [
    ('K3:M5', False),
    ('C41:E43', True)
])
def test_new_space_from_excel_const(testmodel, range_, transpose):

    space = testmodel.new_space_from_excel(
        book=test_path,
        range_=range_,
        sheet='TestSpaceTables',
        names_row=0, param_cols=[0],
        space_param_order=[0],
        cells_param_order=[],
        transpose=transpose)

    for product, offset in zip(['A', 'B'], [0, 1]):
        for cells, value in zip(['Cells1', 'Cells2'], [1, 2]):
            assert space[product].cells[cells]() == value + offset

