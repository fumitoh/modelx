import pytest

from modelx import *
from modelx.tests.testdata import (
    CSV_SINGLE_PARAM,
    CSV_MULTI_PARAMS,
    CSV_SINGLE_PARAM_SINGLE_COL,
    CSV_IRIS)


@pytest.fixture #(scope="module")
def testmodel():
    m = new_model()
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "parent, param, index_col, usecols", [
        ["model", None, 0, None],
        ["space", "Param", None, [1, 2]]]
)
def test_one_param(testmodel, parent, param, index_col, usecols):

    parent = testmodel if parent == "model" else testmodel.new_space()
    space = parent.new_space_from_csv(
        CSV_SINGLE_PARAM,
        param=param,
        index_col=index_col,
        usecols=usecols
    )
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert space.cells[cells].parameters == ("Param",)
        for param in range(16):
            assert space.cells[cells](param) == offset + param


@pytest.mark.parametrize(
    "parent, param, index_col, usecols", [
        ["model", None, [0, 1], None],
        ["space", ["Param1", "Param2"], [0, 1], None]]
)
def test_two_params(testmodel, parent, param, index_col, usecols):

    parent = testmodel if parent == "model" else testmodel.new_space()
    space = parent.new_space_from_csv(
        CSV_MULTI_PARAMS,
        param=param,
        index_col=index_col,
        usecols=usecols
    )
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert space.cells[cells].parameters == ("Param1", "Param2")
        for param in range(16):
            assert space.cells[cells](param, param + 100) == offset + param


@pytest.mark.parametrize(
    "parent, param, space_params, index_col, usecols", [
        ["model", None, [0], [0, 1], None],
        ["space", ["Param1", "Param2"], [1], [0, 1], None]]
)
def test_space_param(
        testmodel, parent, param, space_params, index_col, usecols):
    parent = testmodel if parent == "model" else testmodel.new_space()
    space = parent.new_space_from_csv(
        CSV_MULTI_PARAMS,
        param=param,
        space_params=space_params,
        index_col=index_col,
        usecols=usecols
    )
    spidx = space_params[0]
    param_names = ("Param1", "Param2")
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert space.parameters[0] == param_names[spidx]
        assert space.cells[cells].parameters[0] == param_names[spidx ^ 1]
        for param in range(16):
            sparam = spidx * 100 + param
            cparam = (spidx ^ 1) * 100 + param
            assert space[sparam].cells[cells](cparam) == offset + param


@pytest.mark.parametrize(
    "parent, param, index_col", [
        ["model", None, 0],
        ["space", "Param", None]]
)
def test_one_param_one_col(testmodel, parent, param, index_col):

    parent = testmodel if parent == "model" else testmodel.new_space()
    space = parent.new_space_from_csv(
        CSV_SINGLE_PARAM_SINGLE_COL,
        param=param,
        index_col=index_col,
    )
    assert space.cells["Cells1"].parameters == ("Param",)
    for param in range(16):
        assert space.cells["Cells1"](param) == 1000 + param


@pytest.mark.parametrize(
    "parent", ["model", "space"]
)
def test_iris(testmodel, parent):

    import pandas as pd
    df = pd.read_csv(CSV_IRIS)
    df.index.name = "Param"

    parent = testmodel if parent == "model" else testmodel.new_space()
    space = parent.new_space_from_csv(CSV_IRIS, param="Param")

    assert df.equals(space.frame)
