import pytest

import sys
import os

from modelx import *


test_path = os.path.dirname(sys.modules[__name__].__file__) \
    + '\\data\\testdata.xlsx'


@pytest.fixture
def testmodel():
    return create_model()


@pytest.mark.parametrize("range_, orientation", [
    ('C9:E25', False),
    ('C36:S38', True)
])
def test_create_cells_from_excel(testmodel, range_, orientation):

    space = testmodel.create_space()
    space.create_cells_from_excel(file_=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0],
                                  param_order=[0],
                                  transpose=orientation)

    check = True
    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):

        check = check and \
                list(space.cells[cells]._impl.parameters.keys()) == ['Param']

        for param in range(16):
            check = check and space.cells[cells](param) == offset + param

    assert check


@pytest.mark.parametrize("range_, orientation", [
    ('H9:K25', False),
    ('C42:S45', True)
])
def test_create_cells_from_excel_multparams(testmodel, range_, orientation):

    space = testmodel.create_space()
    space.create_cells_from_excel(file_=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0, 1],
                                  param_order=[0, 1],
                                  transpose=orientation)

    check = True
    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):

        check = check and \
                list(space.cells[cells]._impl.parameters.keys()) == ['Param1',
                                                                     'Param2']
        for param in range(16):
            check = check and \
                    space.cells[cells](param, param + 100) == offset + param

    assert check


@pytest.mark.parametrize("range_, orientation", [
    ('N8:R25', False),
    ('C49:T53', True)
])
def test_create_cells_from_excel_extparams(testmodel, range_, orientation):

    space = testmodel.create_space()
    space.create_cells_from_excel(file_=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0],
                                  names_col=0, param_rows=[1],
                                  param_order=[1, 0],
                                  transpose=orientation)

    check = True
    for cells, offset in zip(['Cells1', 'Cells2'], [1000, 2000]):
        check = check and \
                list(space.cells[cells]._impl.parameters.keys()) == ['Sex',
                                                                     'Param']
        for param in range(16):
            check = check and \
                space.cells[cells]('M', param) == offset + param
            check = check and \
                space.cells[cells]('F', param) == offset + param + 1000

    assert check


@pytest.mark.parametrize("range_, orientation", [
    ('U8:Z29', False),
    ('C57:X62', True)
])
def test_create_cells_from_excel_multextparams(testmodel, range_, orientation):

    space = testmodel.create_space()
    space.create_cells_from_excel(file_=test_path,
                                  range_=range_,
                                  sheet='TestTables',
                                  names_row=0, param_cols=[0, 1],
                                  names_col=1, param_rows=[1],
                                  param_order=[1, 2, 0],
                                  transpose=orientation)

    check = True
    for cells, offset1 in zip(['Cells1', 'Cells2'], [1000, 2000]):
        check = check and \
                list(space.cells[cells]._impl.parameters.keys()) == ['Product',
                                                                     'Sex',
                                                                     'Year']
        for product, offset2 in zip(['A', 'B'], [0, 1000]):
            for sex, offset3 in zip(['M', 'F'], [0, 1000]):
                for year in range(10):
                    check = check and \
                        space.cells[cells](product, sex, year) \
                        == year + offset1 + offset2 + offset3

    assert check



