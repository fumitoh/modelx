import pathlib
from modelx.testing.testutil import compare_model
from modelx.serialize import ziputil
import modelx as mx
import pytest

from modelx.tests.testdata import (
    CSV_SINGLE_PARAM,
    CSV_MULTI_PARAMS
)


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_single_param(tmp_path, write_method):

    m, s = mx.new_model(), mx.new_space()

    s.new_cells_from_csv(
        filepath=CSV_SINGLE_PARAM,
        cells=None,
        param=None,
        index_col=0
    )
    modelpath = tmp_path / "csv_single_param"
    getattr(mx, write_method)(m, modelpath)
    assert ziputil.exists(modelpath / s.name / CSV_SINGLE_PARAM.name)
    m2 = mx.read_model(modelpath)
    # Write twice to check copy from renamed backup.
    getattr(mx, write_method)(m2, modelpath)
    m2 = mx.read_model(modelpath)

    # Compare components
    compare_model(m, m2)

    # Compare values
    trg = m2.spaces[s.name]
    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param",)
        for param in range(16):
            assert trg.cells[cells](param) == offset + param


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_multiple_params(tmp_path, write_method):

    m, s = mx.new_model(), mx.new_space()

    s.new_cells_from_csv(
        filepath=CSV_MULTI_PARAMS,
        cells=None,
        param=None,
        index_col=[0, 1]
    )

    modelpath = tmp_path / "csv_mult_params"
    getattr(mx, write_method)(m, modelpath)
    assert ziputil.exists(modelpath / s.name / CSV_MULTI_PARAMS.name)
    m2 = mx.read_model(modelpath)

    # Write twice to check copy from renamed backup.
    getattr(mx, write_method)(m2, modelpath)
    m2 = mx.read_model(modelpath)

    # Compare components
    compare_model(m, m2)

    # Compare values
    trg = m2.spaces[s.name]

    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.cells[cells].parameters == ("Param1", "Param2")
        for param in range(16):
            assert trg.cells[cells](param, param + 100) == offset + param


