import numpy as np
import pandas as pd
import modelx as mx

import pytest

@pytest.fixture
def make_testmodel_for_clear():
    """
        model-Parent-----Child---Bar
                |     +--Foo |
              Parent[1]      +---Child[1]
    """
    m = mx.new_model()
    p = m.new_space("Parent")
    c = p.new_space("Child")

    @mx.defcells(space=p)
    def Foo(x):
        return x

    @mx.defcells(space=c)
    def Bar(x):
        return 2 * x

    p.parameters = ('a',)
    c.parameters = ('n',)

    Foo(1)
    Foo[2] = 10
    Bar(1)
    Bar[2] = 20
    p[1].Foo(1)
    p.Child[1].Bar(1)

    assert len(m.Parent.itemspaces) == 1
    assert len(m.Parent.Child.itemspaces) == 1
    assert len(m.Parent.Foo) == 2
    assert m.Parent.Foo.is_input(2)
    assert m.Parent.Child.Bar.is_input(2)

    yield m
    m._impl._check_sanity()
    m.close()


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


@pytest.fixture(scope="session", params=param_sample1 + param_sample2)
def sample_frame(request):

    make_df, columns, idx_names, cells_names, param_names = request.param
    df = make_df(columns, idx_names)

    return df, cells_names, param_names


@pytest.fixture(scope="session", params=param_sample2)
def sample_frame_multindex(request):

    make_df, columns, idx_names, cells_names, param_names = request.param
    df = make_df(columns, idx_names)

    return df, cells_names, param_names