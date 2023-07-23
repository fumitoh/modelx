import modelx as mx
import numpy as np
import pandas as pd


def test_write_multiple_models(tmp_path):
    # GH81 https://github.com/fumitoh/modelx/issues/81

    names = ['MultiModelIO1', 'MultiModelIO2']
    dfs = [pd.DataFrame(np.ones([10, 10]) * i) for i in range(1, 3)]

    models = []
    for n, name in enumerate(names):
        m = mx.new_model(name)
        models.append(m)
        s = m.new_space('Foo')
        s.new_pandas('df', 'df.xlsx', dfs[n], 'excel')

    for m in models:
        m.write(tmp_path / m.name)

    for m in models:
        m.close()

    for n, name in enumerate(names):
        df = mx.read_model(tmp_path / name).Foo.df
        pd.testing.assert_frame_equal(df, dfs[n], check_dtype=False)