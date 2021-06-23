
import itertools
import pandas as pd
import numpy as np
import modelx as mx
import pytest

from modelx.io.baseio import BaseDataClient

# Modified from the sample code on
# https://pandas.pydata.org/docs/user_guide/advanced.html

cols = [
    ["bar", "bar", "baz", "baz", "foo", "foo", "qux", "qux"],
    ["one", "two", "one", "two", "one", "two", "one", "two"]
]
cols = list(zip(*cols))
cols = pd.MultiIndex.from_tuples(cols, names=["first", "second"])
idx = pd.MultiIndex.from_product([["A", "B"], ["c", "d", "e"]])

S_IDX1 = pd.Series(np.random.randn(8), index=range(8))
S_IDX1.index.name = "Idx"
S_IDX2 = pd.Series(np.random.randn(8), index=cols)
DF_COL2_IDX2 = pd.DataFrame(np.random.randn(6, 8), index=idx, columns=cols)

params = [[p1, *p2, p3, p4, p5] for p1, p2, p3, p4, p5 in
          itertools.product(
              [S_IDX1, S_IDX2, DF_COL2_IDX2],
              [("new_model", True), ("new_space", False)],
              ("write", "zip", "backup"),
              ("excel", "csv"),
              (False, True)
            )
          ]


@pytest.mark.parametrize(
    "pdobj, meth, is_relative, save_meth, filetype, expose_data",
    params)
def test_new_pandas(
        tmp_path, pdobj, meth, is_relative, save_meth, filetype, expose_data):

    p = getattr(mx, meth)()
    parent_name = p.name

    path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    p.new_pandas(name="pdref", path=path,
                 data=pdobj, filetype=filetype,
                 expose_data=expose_data)

    if expose_data:
        assert isinstance(p.pdref._mx_dataclient, BaseDataClient)

    if save_meth == "backup":
        getattr(p.model, save_meth)(tmp_path / "model")

        p.model.close()
        m2 = mx.restore_model(tmp_path / "model")

    else:
        getattr(p.model, save_meth)(tmp_path / "model")
        p.model.close()
        m2 = mx.read_model(tmp_path / "model")

    p2 = m2 if meth == "new_model" else m2.spaces[parent_name]

    if expose_data:
        if isinstance(pdobj, pd.DataFrame):
            pd.testing.assert_frame_equal(p2.pdref, pdobj)
            assert isinstance(p2.pdref._mx_dataclient, BaseDataClient)
        elif isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(getattr(p2, "pdref"), pdobj)
            assert isinstance(p2.pdref._mx_dataclient, BaseDataClient)
    else:
        if isinstance(pdobj, pd.DataFrame):
            pd.testing.assert_frame_equal(p2.pdref(), pdobj)
            pd.testing.assert_frame_equal(getattr(p2, "pdref").value, pdobj)
        elif isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(p2.pdref(), pdobj)
            pd.testing.assert_series_equal(getattr(p2, "pdref").value, pdobj)

    m2.close()


params2 = [[*p1, p2] for p1, p2 in itertools.product(
    zip([S_IDX1, S_IDX2, DF_COL2_IDX2], ["B2:B9", "C2:C9", "C4:J9"]),
    (False, True)
)]

@pytest.mark.parametrize("pdobj, range_, expose_data", params2)
def test_new_pandas_change_excel(tmp_path, pdobj, range_, expose_data):

    p = mx.new_model().new_space("SpaceA")

    path = "files/testpandas.xlsx"
    p.new_pandas(name="pdref", path=path, data=pdobj, filetype="excel",
                 expose_data=expose_data)

    p.model.write(tmp_path / "model")
    p.model.close()

    import openpyxl as pyxl

    wb = pyxl.load_workbook(tmp_path / "model" / path)
    ws = wb.worksheets[0]

    for row in ws[range_]:
        for cel in row:
            cel.value += 1

    wb.save(tmp_path / "model" / path)

    m2 = mx.read_model(tmp_path / "model")
    p2 = m2.spaces["SpaceA"]

    if expose_data:
        if isinstance(pdobj, pd.DataFrame):
            pd.testing.assert_frame_equal(p2.pdref, pdobj + 1)
        elif isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(p2.pdref, pdobj + 1)
    else:
        if isinstance(pdobj, pd.DataFrame):
            pd.testing.assert_frame_equal(p2.pdref(), pdobj + 1)
            pd.testing.assert_frame_equal(p2.pdref.value, pdobj + 1)
        elif isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(p2.pdref(), pdobj + 1)
            pd.testing.assert_series_equal(p2.pdref.value, pdobj + 1)

    m2.close()
