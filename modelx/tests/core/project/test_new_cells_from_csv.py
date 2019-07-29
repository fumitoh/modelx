
from modelx.testing.testutil import compare_model
import modelx as mx

from .. import (
    CSV_SINGLE_PARAM,
    CSV_MULTI_PARAMS
)


def test_single_param(tmp_path):

    m, s = mx.new_model(), mx.new_space()

    s.new_cells_from_csv(
        filepath=CSV_SINGLE_PARAM,
        cells=None,
        param=None,
        index_col=0
    )
    modelpath = tmp_path / "csv_single_param"
    mx.write_model(m, modelpath)
    m2 = mx.read_model(modelpath)

    # Compare components
    compare_model(m, m2)

    # Compare values
    trg = m2.spaces[s.name]
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param",)
        for param in range(16):
            assert trg.cells[cells](param) == offset + param


def test_multiple_params(tmp_path):

    m, s = mx.new_model(), mx.new_space()

    s.new_cells_from_csv(
        filepath=CSV_MULTI_PARAMS,
        cells=None,
        param=None,
        index_col=[0, 1]
    )

    modelpath = tmp_path / "csv_mult_params"
    mx.write_model(m, modelpath)
    m2 = mx.read_model(modelpath)

    # Compare components
    compare_model(m, m2)

    # Compare values
    trg = m2.spaces[s.name]

    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param1", "Param2")
        for param in range(16):
            assert trg.cells[cells](param, param + 100) == offset + param


