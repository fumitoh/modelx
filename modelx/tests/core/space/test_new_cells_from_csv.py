import pytest

import sys
import os

from modelx import *

test_path = (
    os.path.dirname(sys.modules[__name__].__file__) + "/../data/"
)
ONE_PARAM_SAMPLE = test_path + "single_param.csv"
TWO_PARAMS_SAMPLE = test_path + "multi_params.csv"
ONE_PARAM_ONE_COL_SAMPLE = test_path + "single_param_single_col.csv"
IRIS_SAMPLE = test_path + "iris.csv"


@pytest.fixture(scope="session")
def testmodel():
    return new_model()


@pytest.mark.parametrize(
    "param, index_col, usecols", [[None, 0, None],
                                  ["Param", None, [1, 2]]]
)
def test_one_param(testmodel, param, index_col, usecols):

    space = testmodel.new_space()
    space.new_cells_from_csv(
        ONE_PARAM_SAMPLE,
        param=param,
        index_col=index_col,
        usecols=usecols
    )
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert space.cells[cells].parameters == ("Param",)
        for param in range(16):
            assert space.cells[cells](param) == offset + param


@pytest.mark.parametrize(
    "param, index_col, usecols", [[None, [0, 1], None],
                                  [["Param1", "Param2"], [0, 1], None]]
)
def test_two_params(testmodel, param, index_col, usecols):

    space = testmodel.new_space()
    space.new_cells_from_csv(
        TWO_PARAMS_SAMPLE,
        param=param,
        index_col=index_col,
        usecols=usecols
    )
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert space.cells[cells].parameters == ("Param1", "Param2")
        for param in range(16):
            assert space.cells[cells](param, param + 100) == offset + param


@pytest.mark.parametrize(
    "param, index_col", [[None, 0],
                         ["Param", None]]
)
def test_one_param_one_col(testmodel, param, index_col):

    space = testmodel.new_space()
    space.new_cells_from_csv(
        ONE_PARAM_ONE_COL_SAMPLE,
        param=param,
        index_col=index_col,
    )
    assert space.cells["Cells1"].parameters == ("Param",)
    for param in range(16):
        assert space.cells["Cells1"](param) == 1000 + param


def test_iris(testmodel):

    import pandas as pd
    df = pd.read_csv(IRIS_SAMPLE)
    df.index.name = "Param"

    space = testmodel.new_space()
    space.new_cells_from_csv(IRIS_SAMPLE, param="Param")

    assert df.equals(space.frame)
