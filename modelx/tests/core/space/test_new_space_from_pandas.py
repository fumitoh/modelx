import pytest

import pandas as pd
import numpy as np

import modelx as mx
from modelx.core.util import is_valid_name

@pytest.fixture(scope="module")
def sample_model():
    m = mx.new_model()
    yield m
    m._impl._check_sanity()
    m.close()


def test_new_space_from_pandas_no_dynamic(sample_model, sample_frame):

    df, cells_names, param_names = sample_frame
    space = sample_model.new_space_from_pandas(
        df, cells=cells_names, param=param_names)

    if int(pd.__version__.split(".")[0]) < 24:
        assert np.array_equal(space.frame.values, df.values)
    else:
        assert np.array_equal(space.frame.to_numpy(), df.to_numpy())

    names = tuple(c if is_valid_name(c) else cells_names[i]
                  for i, c in enumerate(df.columns))
    params = tuple(p or param_names[i] for i, p in enumerate(df.index.names))

    assert tuple(space.frame.columns) == names
    assert tuple(space.frame.index.names) == params


@pytest.mark.parametrize("space_params, cells_params",
                         [[["x"], None],
                          [["x"], ["y"]],
                          [["y"], None],
                          [["y"], ["x"]]])
def test_new_space_from_pandas_dynamic(
        sample_model, sample_frame_multindex, space_params, cells_params):

    df, cells_names, param_names = sample_frame_multindex

    space = sample_model.new_space_from_pandas(
        df, cells=cells_names, param=param_names,
        space_params=space_params, cells_params=cells_params
    )
    assert space.parameters == tuple(space_params)

    cparam = ["x", "y"]
    for p in space_params:
        cparam.remove(p)

    for c in space.cells.values():
        assert c.parameters == tuple(cparam)

    if param_names is not None:
        params = [m or n for m, n in zip(param_names, df.index.names)]
    else:
        params = df.index.names

    if cells_names is not None:
        cells = [m or n for m, n in zip(cells_names, df.columns)]
    else:
        cells = df.columns

    def idx_to_args(idx):

        sargs = [idx[params.index(p)] for p in space_params]
        cargs = [idx[params.index(p)] for p in cparam]

        return sargs, cargs

    for i, col in enumerate(df.columns):
        for idx in df.index:
            sargs, cargs = idx_to_args(idx)
            assert space(*sargs).cells[cells[i]](*cargs) == df.loc[idx, col]




