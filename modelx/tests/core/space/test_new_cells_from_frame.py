from itertools import product
import pytest

import pandas as pd
import numpy as np

import modelx as mx


def make_sample1(columns, idx_names):
    """Series with Index"""
    index = pd.Index([1,2,3], name=idx_names)
    return pd.DataFrame(np.random.rand(3, 2), index=index, columns=columns)


method_names = ["new_cells_from_frame", "new_cells_from_pandas"]

param_sample1 = [
    [make_sample1, ["Col1", "Col2"], "x", None, None],
    [make_sample1, None, None, ["Col1", "Col2"], "x"],
    [make_sample1, ["Col1", None], None, [None, "Col2"], ["x"]],
]


def make_sample2(columns, idx_names):
    """Series with MultiIndex"""

    arrays = [['bar', 'bar', 'baz', 'baz', 'foo', 'foo', 'qux', 'qux'],
              ['one', 'two', 'one', 'two', 'one', 'two', 'one', 'two']]

    tuples = list(zip(*arrays))
    index = pd.MultiIndex.from_tuples(tuples, names=idx_names)

    return pd.DataFrame(np.random.randn(8, 2), index=index, columns=columns)


param_sample2 = [
    [make_sample2, ["Col1", "Col2"], ["x", "y"], None, None],
    [make_sample2, None, None, ["Col1", "Col2"], ["x", "y"]],
    [make_sample2, ["Col1", None], [None, "y"], [None, "Col2"], ["x", None]],
]

param_list = [
    [m] + p for m, p
    in product(method_names, param_sample1 + param_sample2)]


@pytest.fixture(scope="session")
def sample_model():
    return mx.new_model()


@pytest.mark.parametrize(
    "method, make_df, columns, idx_names, cells_names, param_names",
    param_list)
def test_new_cells_from_frame(
        sample_model,
        method, make_df, columns, idx_names, cells_names, param_names):

    df = make_df(columns, idx_names)
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
