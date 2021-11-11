
import modelx as mx
from modelx.tests.testdata import XL_TESTDATA
import itertools
import zipfile
import pytest

# Test patterns
#   Table shape, 1-row, 1-col, matrix
#   with / without keys rows/cols
#   is named range
#   external / internal path
#   Shared by models


testargs = [
    {"name": "table1",
     "range_": "C9:E25",
     "keyids": ["r0", "c0"],
     "expected": {(c, i): 1000 * ((c == 'Cells2') + 1) + i
         for c, i in itertools.product(('Cells1', 'Cells2'), range(16))}},

    {"name": "table2",
     "range_": "H9:K25",
     "keyids": ["r0", "c0", "c1"],
     "expected": {(c, i, 100 + i): 1000 * ((c == 'Cells2') + 1) + i
         for c, i in itertools.product(('Cells1', 'Cells2'), range(16))}},

    {"name": "table3",
     "range_": "N8:R25",
     "keyids": ["r0", "r1", "c0"],
     "expected": {(c, f, i): i + 1000 * ((c == 'Cells2') + (f == 'F') + 1)
         for c, f in itertools.product(('Cells1', 'Cells2'), ('M', 'F'))
            for i in range(16)}},

    {"name": "table4",
     "range_": "U8:Z29",
     "keyids": ["r0", "c1", "r1", "c0"],
     "expected":
         {(c, p, f, i):
              i + 1000 * ((c == 'Cells2') + (p == 'B') + (f == 'F') + 1)
          for c, p, f in itertools.product(
             ('Cells1', 'Cells2'), ('A', 'B'), ('M', 'F')) for i in range(10)}}
]


params = [[*p1, p2, p3] for p1, p2, p3 in
    itertools.product(
        [("new_model", True),
         ("new_space", False)],
        (True, False),
        ("write", "zip", "backup")
    )
]


@pytest.mark.parametrize("meth, is_relative, edit_value, save_meth", params)
def test_new_excel_range(tmp_path, meth, is_relative, edit_value, save_meth):
    """Check data new_excel_range

    Check data before and after value edit before after saving and reloading
    """

    p = getattr(mx, meth)()
    parent_name = p.name

    for kwargs in testargs:

        kwargs = kwargs.copy()

        kwargs["path"] = ("files/testexcel.xlsx"
                          if is_relative else tmp_path / "testexcel.xlsx")
        kwargs["sheet"] = "TestTables"
        kwargs["loadpath"] = XL_TESTDATA
        expected = kwargs.pop("expected").copy()
        p.new_excel_range(**kwargs)

        xlr = getattr(p, kwargs["name"])

        if edit_value:
            for key, val in xlr.items():
                xlr[key] = 2 * val

            for key, val in expected.items():
                expected[key] = 2 * val

        assert xlr == expected

    if save_meth == "backup":
        datapath = tmp_path / "data"
        datapath.mkdir()
        getattr(p.model, save_meth)(tmp_path / "model", datapath=datapath)

        p.model.close()
        m2 = mx.restore_model(tmp_path / "model", datapath=datapath)

    else:
        getattr(p.model, save_meth)(tmp_path / "model")
        p.model.close()
        m2 = mx.read_model(tmp_path / "model")

    p2 = m2 if meth == "new_model" else m2.spaces[parent_name]

    for kwargs in testargs:

        name = kwargs["name"]
        expected = kwargs["expected"].copy()

        if edit_value:
            expected = {key: 2 * val for key, val in expected.items()}

        assert getattr(p2, name) == expected

    m2.close()


testargs_missingkeys = [

    {"name": "table1",
     "range_": "D9:E25",
     "keyids": ["r0"],
     "expected": {(c, i): 1000 * ((c == 'Cells2') + 1) + i
         for c, i in itertools.product(('Cells1', 'Cells2'), range(16))}},

    {"name": "table2",
     "range_": "J10:K25",
     "keyids": None,
     "expected": {(i, c): 1000 * (c + 1) + i
         for i, c in itertools.product(range(16), range(2))}}

]


@pytest.mark.parametrize(
    "meth, is_relative, save_meth",
    [
        ("new_model", True, "write"),
        ("new_space", False, "zip")
    ])
def test_missing_keys(tmp_path, meth, is_relative, save_meth):

    p = getattr(mx, meth)()
    parent_name = p.name

    for kwargs in testargs_missingkeys:

        kwargs = kwargs.copy()

        kwargs["path"] = ("files/testexcel.xlsx"
                          if is_relative else tmp_path / "testexcel.xlsx")
        kwargs["sheet"] = "TestTables"
        kwargs["loadpath"] = XL_TESTDATA
        expected = kwargs.pop("expected").copy()
        p.new_excel_range(**kwargs)

        xlr = getattr(p, kwargs["name"])

        for key, val in xlr.items():
            xlr[key] = 2 * val

        for key, val in expected.items():
            expected[key] = 2 * val

        assert xlr == expected

    getattr(p.model, save_meth)(tmp_path / "model")
    p.model.close()
    m2 = mx.read_model(tmp_path / "model")

    p2 = m2 if meth == "new_model" else m2.spaces[parent_name]

    for kwargs in testargs_missingkeys:

        name = kwargs["name"]
        expected = kwargs["expected"].copy()
        expected = {key: 2 * val for key, val in expected.items()}

        assert getattr(p2, name) == expected

    m2.close()

    assert not mx.core.mxsys._check_sanity()


@pytest.mark.parametrize(
    "parent, save_meth",
    [
        ("model", "write"),
        ("space", "zip")
    ]
)
def test_shared_data(tmp_path, parent, save_meth):

    for i in range(2):

        m = mx.new_model("SharedDataTest" + str(i))

        if parent == "model":
            p = m
        else:
            p = m.new_space("SharedDataTest")

        parent_name = p.name

        kwargs = testargs[i].copy()

        kwargs["path"] = tmp_path / "testexcel.xlsx"
        kwargs["sheet"] = "TestTables"
        kwargs["loadpath"] = XL_TESTDATA
        expected = kwargs.pop("expected").copy()
        p.new_excel_range(**kwargs)

        xlr = getattr(p, kwargs["name"])

        for key, val in xlr.items():
            xlr[key] = 2 * val

        for key, val in expected.items():
            expected[key] = 2 * val

        getattr(m, save_meth)(tmp_path / ("model" + str(i)))
        assert xlr == expected

    for i in range(2):
        m = mx.get_models()["SharedDataTest" + str(i)]
        m.close()

    for i in range(2):
        m2 = mx.read_model(tmp_path / ("model" + str(i)))
        p2 = m2 if parent == "model" else m2.spaces["SharedDataTest"]
        kwargs = testargs[i]
        name = kwargs["name"]
        expected = kwargs["expected"].copy()
        expected = {key: 2 * val for key, val in expected.items()}

        assert getattr(p2, name) == expected

    for i in range(2):
        m = mx.get_models()["SharedDataTest" + str(i)]
        m.close()

    assert not mx.core.mxsys._check_sanity()


testargs_scalars = [

    {"name": "scalar1",
     "range_": "C10:D25",
     "keyids": ["c0"],
     "expected": {i: 1000 + i for i in range(16)}},

    {"name": "scalar2",
     "range_": "J10:J25",
     "keyids": None,
     "expected": {i: 1000 + i for i in range(16)}},

    {"name": "scalar3",
     "range_": "D36:S37",
     "keyids": ["r0"],
     "expected": {i: 1000 + i for i in range(16)}},

    {"name": "scalar4",
     "range_": "D44:S44",
     "keyids": None,
     "expected": {i: 1000 + i for i in range(16)}}
]


@pytest.mark.parametrize(
    "save_meth", ["write", "zip"]
)
def test_scalar_range(tmp_path, save_meth):

    m = mx.new_model()
    s = m.new_space()

    for i in range(len(testargs_scalars)):

        kwargs = testargs_scalars[i].copy()
        kwargs["path"] = tmp_path / "testexcel.xlsx"
        kwargs["sheet"] = "TestTables"
        kwargs["loadpath"] = XL_TESTDATA
        expected = kwargs.pop("expected")

        xlr = s.new_excel_range(**kwargs)
        assert dict(xlr) == expected

    assert not mx.core.mxsys._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "parent, is_relative, erroneous",
    itertools.product(
        ["new_model", "new_space"], [True, False], [True, False])
)
def test_range_conflict_error(tmp_path, parent, is_relative, erroneous):

    m_or_s = getattr(mx, parent)()
    s = m_or_s.new_space()

    kwargs = testargs[0].copy()
    expected = kwargs.pop("expected")

    kwargs["path"] = ("files/testexcel.xlsx"
                      if is_relative else tmp_path / "testexcel.xlsx")
    kwargs["sheet"] = "TestTables"
    kwargs["loadpath"] = XL_TESTDATA

    xlr = m_or_s.new_excel_range(**kwargs)

    assert xlr == expected

    # Select value range
    kwargs["range_"] = "D10:E25"
    kwargs["keyids"] = None

    if erroneous:
        with pytest.raises(ValueError):
            s.new_excel_range(**kwargs)
        del m_or_s.table1
    else:
        del m_or_s.table1
        xlr = s.new_excel_range(**kwargs)
        assert set(xlr.values()) == set(expected.values())
        del s.table1


def test_dataclients(tmp_path):

    m = mx.new_model()
    s = m.new_space()

    kwargs = testargs[0].copy()
    expected = kwargs.pop("expected")

    kwargs["path"] = "files/testexcel.xlsx"
    kwargs["sheet"] = "TestTables"
    kwargs["loadpath"] = XL_TESTDATA

    xlr = s.new_excel_range(**kwargs)

    assert m.dataclients
    m.x = s.table1
    del m.x
    assert m.dataclients
    del s.table1
    assert not m.dataclients


@pytest.mark.parametrize("meth_or_func, compression",
                         itertools.product(["meth", "func"],
                                           [zipfile.ZIP_DEFLATED,
                                            zipfile.ZIP_STORED]))
def test_zip_compression(tmp_path, meth_or_func, compression):

    m = mx.new_model()
    s = m.new_space()

    kwargs = testargs[0].copy()
    expected = kwargs.pop("expected")

    kwargs["path"] = "files/testexcel.xlsx"
    kwargs["sheet"] = "TestTables"
    kwargs["loadpath"] = XL_TESTDATA

    xlr = s.new_excel_range(**kwargs)

    assert xlr == expected

    if meth_or_func == "meth":
        m.zip(tmp_path / "model.zip",
              compression=compression)
    else:
        mx.zip_model(m, tmp_path / "model.zip",
                     compression=compression)

    archive = zipfile.ZipFile(tmp_path / "model.zip")

    for info in archive.infolist():
        assert info.compress_type == compression


@pytest.mark.parametrize("save_meth", ["write", "zip"])
def test_consecutive_writes(tmp_path, save_meth):

    m = mx.new_model()
    s = m.new_space("SpaceA")

    kwargs = testargs[0].copy()
    expected = kwargs.pop("expected")

    kwargs["path"] = "files/testexcel.xlsx"
    kwargs["sheet"] = "TestTables"
    kwargs["loadpath"] = XL_TESTDATA

    s.new_excel_range(**kwargs)

    getattr(m, save_meth)(tmp_path / "model")
    getattr(m, save_meth)(tmp_path / "model")

    m.close()
    m2 = mx.read_model(tmp_path / "model")
    assert m2.SpaceA.table1 == expected
    m2.close()
