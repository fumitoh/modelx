import pytest
from modelx.testing.testutil import compare_model
import modelx as mx
from modelx.serialize import ziputil

from modelx.tests.testdata import (
    CSV_SINGLE_PARAM,
    CSV_MULTI_PARAMS
)


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_single_param(tmp_path, write_method):

    m = mx.new_model()

    s = m.new_space_from_csv(
        filepath=CSV_SINGLE_PARAM,
        space=None,
        cells=None,
        param=None,
        space_params=None,
        index_col=0
    )
    modelpath = tmp_path / "csv_single_param"
    getattr(mx, write_method)(m, modelpath)
    assert ziputil.exists(modelpath.joinpath(CSV_SINGLE_PARAM.name))
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

    m = mx.new_model()

    s = m.new_space_from_csv(
        filepath=CSV_MULTI_PARAMS,
        space=None,
        cells=None,
        param=None,
        space_params=[0],
        index_col=[0, 1]
    )

    modelpath = tmp_path / "csv_mult_params"
    getattr(mx, write_method)(m, modelpath)
    assert ziputil.exists(modelpath.joinpath(CSV_MULTI_PARAMS.name))
    m2 = mx.read_model(modelpath)
    # Write twice to check copy from renamed backup.
    getattr(mx, write_method)(m2, modelpath)
    m2 = mx.read_model(modelpath)

    # Compare components
    compare_model(m, m2)

    # Compare values
    trg = m2.spaces[s.name]

    for cells, offset in zip(["Cells1", "Cells2"], [1000, 2000]):
        assert trg.parameters == ("Param1",)
        for param in range(16):
            assert trg[param].cells[cells].parameters == ("Param2",)
            assert trg(param).cells[cells](param + 100) == offset + param


