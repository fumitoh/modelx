import numpy as np
import pandas as pd

import pytest

def make_sample1(columns, idx_names):
    """Series with Index"""
    index = pd.Index([1,2,3], name=idx_names)
    return pd.DataFrame(np.random.rand(3, 2), index=index, columns=columns)


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


@pytest.fixture(params=param_sample1 + param_sample2)
def sample_frame(request):

    make_df, columns, idx_names, cells_names, param_names = request.param
    df = make_df(columns, idx_names)

    return df, columns, idx_names, cells_names, param_names