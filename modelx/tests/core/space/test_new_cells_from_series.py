import pytest

from itertools import product
import pandas as pd
import numpy as np
import modelx as mx


def make_sample1(name, param_names):
    """Series with Index"""
    index = pd.Index([1,2,3], name=param_names)
    return pd.Series(np.random.rand(3), index=index, name=name)


# Element of param_sampleN list:
#   sample make function,
#   name arg to pd.Series,
#   name or names args to pd.Index or pd.MultiIndex
#   name arg to new_cells_from_series
#   param arg to new_cells_from_series

param_sample1 = list(product([make_sample1],
                             ['series1', None],
                             ['x', None],
                             ['cells1', None],
                             ['a', None]))


def make_sample2(name, param_names):
    """Series with MultiIndex"""

    arrays = [['bar', 'bar', 'baz', 'baz', 'foo', 'foo', 'qux', 'qux'],
              ['one', 'two', 'one', 'two', 'one', 'two', 'one', 'two']]

    tuples = list(zip(*arrays))
    index = pd.MultiIndex.from_tuples(tuples, names=param_names)
    return pd.Series(np.random.randn(8), index=index, name=name)


param_sample2 = list(product([make_sample2],
                             ['series2', None],
                             [['x', 'y'], None],
                             ['cells2', None],
                             [['a', 'b'], None]))


@pytest.fixture(scope="session")
def sample_model():
    return mx.new_model()


@pytest.fixture(params=param_sample1 + param_sample2)
def sample_series(request):

    make_series, series_name, series_param, cells_name, cells_param = (
        request.param
    )
    return make_series(series_name, series_param), cells_name, cells_param


def test_new_cells_from_series(sample_model, sample_series):
    space = sample_model.new_space()
    series, name, param = sample_series

    if not any(series.index.names) and not param:
        with pytest.raises(ValueError):
            space.new_cells_from_series(series=series,
                                        name=name,
                                        param=param)
    else:
        cells = space.new_cells_from_series(series=series,
                                            name=name,
                                            param=param)
        assert cells.series.equals(series)
        if name:
            assert cells.name == name
        if param:
            assert cells.parameters == tuple(param)
