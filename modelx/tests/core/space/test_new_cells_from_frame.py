import pytest

import pandas as pd
import numpy as np

import modelx as mx


method_names = ["new_cells_from_frame", "new_cells_from_pandas"]


@pytest.fixture(scope="session")
def sample_model():
    return mx.new_model()


@pytest.mark.parametrize("method", method_names)
def test_new_cells_from_frame(sample_model, sample_frame, method):

    df, columns, idx_names, cells_names, param_names = sample_frame
    space = sample_model.new_space()
    getattr(space, method)(df, cells=cells_names, param=param_names)

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
