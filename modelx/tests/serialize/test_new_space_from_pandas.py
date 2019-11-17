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


def test_write_space_from_pandas(tmp_path):

    m = mx.new_model()
    s = m.new_space_from_pandas(
        testdf,
        space_params=[0]
    )

    modelpath = tmp_path / "write_space_from_pandas"
    mx.write_model(m, modelpath)

    m2 = mx.read_model(modelpath)
    s2 = m2.spaces[s.name]

    compare_model(m, m2)

    for first, second in testdf.index:
        assert s[first].frame.equals(s2[first].frame)
