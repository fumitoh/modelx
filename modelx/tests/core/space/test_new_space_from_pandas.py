import pytest

import pandas as pd
import numpy as np

import modelx as mx


@pytest.fixture(scope="session")
def sample_model():
    return mx.new_model()


def test_new_space_from_pandas_no_dynamic(sample_model, sample_frame):

    df, columns, idx_names, cells_names, param_names = sample_frame
    space = sample_model.new_space_from_pandas(
        df, cells=cells_names, param=param_names)

    if int(pd.__version__.split(".")[0]) < 24:
        assert np.array_equal(space.frame.values, df.values)
    else:
        assert np.array_equal(space.frame.to_numpy(), df.to_numpy())

    if columns:
        names = tuple(c or cells_names[i] for i, c in enumerate(columns))
    else:
        names = tuple(cells_names)

    if idx_names:
        params = tuple(p or param_names[i] for i, p in enumerate(idx_names))
    else:
        params = tuple(param_names)

    assert tuple(space.frame.columns) == names
    assert tuple(space.frame.index.names) == params


@pytest.mark.parametrize("space_params, cells_params",
                         [[["x"], None],
                          [["x"], ["y"]],
                          [["y"], None],
                          [["y"], ["x"]]])
def test_new_space_from_pandas_dynamic(
        sample_model, sample_frame_multindex, space_params, cells_params):

    df, columns, idx_names, cells_names, param_names = sample_frame_multindex

    space = sample_model.new_space_from_pandas(
        df, cells=cells_names, param=param_names,
        space_params=space_params, cells_params=cells_params
    )
    assert space.parameters == (space_params[0],)

    cp = ["x", "y"]
    cp.remove(space_params[0])

    for c in space.cells.values():
        assert c.parameters == tuple(cp)



