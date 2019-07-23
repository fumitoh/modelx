import pytest

import pandas as pd
import numpy as np

import modelx as mx
from modelx.core.util import is_valid_name

method_names = ["new_cells_from_frame", "new_cells_from_pandas"]


@pytest.fixture(scope="session")
def sample_model():
    return mx.new_model()


@pytest.mark.parametrize("method", method_names)
def test_new_cells_from_frame(sample_model, sample_frame, method):

    df, cells_names, param_names = sample_frame
    space = sample_model.new_space()
    getattr(space, method)(df, cells=cells_names, param=param_names)

    if int(pd.__version__.split(".")[0]) < 24:
        assert np.array_equal(space.frame.values, df.values)
    else:
        assert np.array_equal(space.frame.to_numpy(), df.to_numpy())

    names = tuple(c if is_valid_name(c) else cells_names[i]
                  for i, c in enumerate(df.columns))
    params = tuple(p or param_names[i] for i, p in enumerate(df.index.names))

    assert tuple(space.frame.columns) == names
    assert tuple(space.frame.index.names) == params
