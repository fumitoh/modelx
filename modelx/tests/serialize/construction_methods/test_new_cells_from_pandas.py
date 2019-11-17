import pytest

import pandas as pd
import numpy as np
import modelx as mx
from modelx.testing.testutil import compare_model

arrays = [['bar', 'bar', 'baz', 'baz', 'foo', 'foo', 'qux', 'qux'],
          ['one', 'two', 'one', 'two', 'one', 'two', 'one', 'two']]


index = pd.MultiIndex.from_tuples(
    tuple(zip(*arrays)),
    names=['first', 'second'])

testdf = pd.DataFrame(np.random.randn(8, 4), index=index)
testdf.columns = ["Foo", "Bar", "Baz", "Qux"]


def test_write_cells_from_pandas(tmp_path):

    m, space = mx.new_model(), mx.new_space()
    space.new_cells_from_pandas(testdf)

    modelpath = tmp_path / "write_cells_from_pandas"
    mx.write_model(m, modelpath)

    m2 = mx.read_model(modelpath)

    compare_model(m, m2)

    assert space.frame.equals(m2.spaces[space.name].frame)