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


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_write_space_from_pandas(tmp_path, write_method):

    m = mx.new_model()
    s = m.new_space_from_pandas(
        testdf,
        space_params=[0]
    )

    modelpath = tmp_path / "write_space_from_pandas"
    getattr(mx, write_method)(m, modelpath)

    m2 = mx.read_model(modelpath)
    s2 = m2.spaces[s.name]

    compare_model(m, m2)

    for first, _ in testdf.index:
        # Row order does not match
        pd.testing.assert_frame_equal(s[first].frame, s2[first].frame, check_like=True)

