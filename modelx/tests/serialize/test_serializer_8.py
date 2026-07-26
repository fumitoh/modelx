"""Serializer version 8: IO specs as literal tuples in ``_data/iospecs.py``.

Version-8-specific guarantees (see modelx/serialize/serializer_8.py):
the central literal file replaces ``iospecs.pickle``, ref sites carry
readability comments, spec identity is keyed explicitly, per-line
tolerant loading, and the is_hidden flag is dropped. Version-agnostic
write/read behavior is covered by the general suites, which run at the
default (now version-8) format, and by the parametrized determinism and
error-cleanup suites.
"""

import ast
import pathlib
import shutil
import zipfile

import pytest

import modelx as mx
from modelx.core.system import mxsys
from modelx.serialize.serializer_8 import IOSPECS_FILE
from modelx.tests.testdata import XL_TESTDATA
from modelx.tests.testdata.testpkg import testmod

pd = pytest.importorskip("pandas")

from modelx.io.pandasio import PandasData


@pytest.fixture
def sample_df():
    return pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})


def _make_pandas_model(name, df):
    m = mx.new_model(name)
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=df, file_type="csv")
    s.other = 5
    return m


def _assert_no_ios_left(m):
    assert not [io_ for (group, path), io_ in mxsys.iomanager.ios.items()
                if group is m or group is None]


# ---------------------------------------------------------------------------
# The literal file


def test_literal_file_replaces_pickle(tmp_path, sample_df, close_new_models):
    """iospecs.py holds one sorted, literal-parsable declaration per
    spec; iospecs.pickle is gone; data.pickle holds no spec values."""
    m = mx.new_model("V8Literal")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    sr = pd.Series([1.0, 2.0], name="sname")
    m.new_pandas(name="sref", path="files/series.csv",
                 data=sr, file_type="csv")

    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    assert not (path / "_data" / "iospecs.pickle").exists()
    # No pickled values at all in this model: the ref path no longer
    # routes spec values through pickledata
    assert not (path / "_data" / "data.pickle").exists()

    lines = (path / IOSPECS_FILE).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# modelx: iospecs"
    entries = [ast.literal_eval(line) for line in lines
               if line and not line.startswith("#")]
    assert len(entries) == 2
    keys = [e[0] for e in entries]
    assert keys == sorted(keys)
    for key, clsname, version, iopath, io_args, spec_args in entries:
        assert clsname == "PandasData"
        assert version == PandasData.format_version == 1
        assert io_args == {"file_type": "csv"}
    by_path = {e[3]: e[5] for e in entries}
    assert by_path["files/data.csv"] == {
        "sheet": None, "is_series": False, "name": None,
        "index_nlevels": 1, "columns_nlevels": 1}
    assert by_path["files/series.csv"] == {
        "sheet": None, "is_series": True, "name": "sname",
        "index_nlevels": 1, "columns_nlevels": 1}

    m2 = mx.read_model(str(path))
    pd.testing.assert_frame_equal(m2.Space1.pdref, sample_df)
    pd.testing.assert_series_equal(m2.sref, sr)


def test_ref_comment_format_and_roundtrip(tmp_path, sample_df,
                                          close_new_models):
    """Ref sites carry the documented comment, byte-identical across a
    no-op round trip."""
    m = mx.new_model("V8Comment")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/book.xlsx",
                 data=sample_df, file_type="excel", sheet="SheetA")
    path1 = tmp_path / "save1"
    mx.write_model(m, str(path1))
    m.close()

    src = (path1 / "Space1" / "__init__.py").read_text(encoding="utf-8")
    assert ("pdref = (\"IOSpec\", 1)  # PandasData path='files/book.xlsx'"
            " file_type='excel' sheet='SheetA'") in src

    m2 = mx.read_model(str(path1))
    path2 = tmp_path / "save2"
    mx.write_model(m2, str(path2))
    m2.close()

    assert (path1 / "Space1" / "__init__.py").read_bytes() == \
           (path2 / "Space1" / "__init__.py").read_bytes()


def test_numpy_series_name_coerced(tmp_path, close_new_models):
    """A numpy-scalar Series name (ordinary pandas data, e.g. a column
    selected from a DataFrame with numpy-typed labels) is coerced to
    its plain Python equivalent and round-trips."""
    np = pytest.importorskip("numpy")
    m = mx.new_model("V8NpName")
    sr = pd.Series([1.0, 2.0])
    sr.name = np.int64(3)
    m.new_pandas(name="sref", path="files/series.csv",
                 data=sr, file_type="csv")
    path1 = tmp_path / "save1"
    mx.write_model(m, str(path1))
    m.close()

    assert "'name': 3," in (path1 / IOSPECS_FILE).read_text(
        encoding="utf-8")

    m2 = mx.read_model(str(path1))
    assert m2.sref.name == 3
    path2 = tmp_path / "save2"
    mx.write_model(m2, str(path2))
    m2.close()
    assert (path1 / IOSPECS_FILE).read_bytes() == \
           (path2 / IOSPECS_FILE).read_bytes()


def test_non_literal_param_fails_before_output(tmp_path,
                                               close_new_models):
    """A parameter that cannot be represented as a literal fails the
    save with a clear error before any output is touched: no partial
    tree, no backup rotation of the previous good save."""
    m = mx.new_model("V8NonLiteral")
    s = m.new_space("Space1")
    sr = pd.Series([1.0, 2.0], name="good")
    expected = sr.copy()
    s.new_pandas(name="sref", path="files/series.csv",
                 data=sr, file_type="csv")
    path = tmp_path / "model"
    mx.write_model(m, str(path))               # good save

    s.sref.name = object()                     # not literal-representable
    with pytest.raises(TypeError, match="literal-representable"):
        mx.write_model(m, str(path))
    m.close()

    assert not (tmp_path / "model_BAK1").exists()
    m2 = mx.read_model(str(path))              # previous save intact
    pd.testing.assert_series_equal(m2.Space1.sref, expected)


def test_unsupported_spec_class_fails_before_output(tmp_path,
                                                    close_new_models):
    """A BaseIOSpec subclass outside the registry fails the save with
    the designed clean TypeError, before any output is written."""
    from modelx.io.moduleio import ModuleData

    class FancyData(ModuleData):
        pass

    m = mx.new_model("V8FancySpec")
    s = m.new_space("Space1")
    spec = mxsys.iomanager.new_spec(
        FancyData, io_group=m, path="modules/fancy.py",
        spec_args={"module": testmod}, io_args={"module": testmod})
    s.fancy = spec.value

    path = tmp_path / "model"
    with pytest.raises(TypeError,
                       match="does not support IO spec type 'FancyData'"):
        mx.write_model(m, str(path))
    assert not path.exists()


# ---------------------------------------------------------------------------
# Round trips per spec type and identity


def test_excel_range_roundtrip(tmp_path, close_new_models):
    pytest.importorskip("openpyxl")
    m = mx.new_model("V8XlRange")
    s = m.new_space("Space1")
    s.new_excel_range(name="xlr", path="files/testexcel.xlsx",
                      range_="C9:E25", sheet="TestTables",
                      keyids=["r0", "c0"], loadpath=XL_TESTDATA)
    s.same = s.xlr
    expected = dict(s.xlr)

    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    m2 = mx.read_model(str(path))
    assert dict(m2.Space1.xlr) == expected
    assert m2.Space1.xlr.keyids == ("r0", "c0")
    assert m2.Space1.same is m2.Space1.xlr

    src = (path / "Space1" / "__init__.py").read_text(encoding="utf-8")
    assert ("# ExcelRange path='files/testexcel.xlsx' range='C9:E25' "
            "sheet='TestTables' keyids=('r0', 'c0')") in src


def test_module_roundtrip(tmp_path, close_new_models):
    m = mx.new_model("V8Module")
    s = m.new_space("Space1")
    s.new_module(name="Foo", path="modules/foo", module=testmod)
    s.Bar = s.Foo

    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    m2 = mx.read_model(str(path))
    assert m2.Space1.Foo.modbar(2) == 4
    assert m2.Space1.Bar is m2.Space1.Foo

    lines = (path / IOSPECS_FILE).read_text(encoding="utf-8").splitlines()
    entries = [ast.literal_eval(line) for line in lines
               if line and not line.startswith("#")]
    assert entries == [(1, "ModuleData", 1, "modules/foo", {}, {})]


def test_value_shared_by_ref_and_cells_input(tmp_path, sample_df,
                                             close_new_models):
    """A spec value that is also a cells input is stored once and its
    identity survives the reload (the DataValue persistent-id path)."""
    m = mx.new_model("V8DataValue")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_cells(name="foo", formula=lambda x: x)
    s.foo[1] = s.pdref
    s.nested = [s.pdref]

    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    m2 = mx.read_model(str(path))
    assert m2.Space1.foo[1] is m2.Space1.pdref
    assert m2.Space1.nested[0] is m2.Space1.pdref
    pd.testing.assert_frame_equal(m2.Space1.pdref, sample_df)


def test_hidden_spec_reloads_as_ordinary(tmp_path, sample_df,
                                         close_new_models):
    """The v4-era is_hidden flag is dropped: a hidden spec in a v7 model
    resaved as v8 comes back as an ordinary spec."""
    m = mx.new_model("V8Hidden")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    m.iospecs[0]._is_hidden = True
    path7 = tmp_path / "model_v7"
    mx.write_model(m, str(path7), version=7)
    m.close()

    m7 = mx.read_model(str(path7))          # v7 restores the flag
    assert m7.iospecs[0]._is_hidden
    assert hasattr(m7.Space1.pdref, "_mx_dataclient")
    path8 = tmp_path / "model_v8"
    mx.write_model(m7, str(path8))
    m7.close()

    assert "is_hidden" not in (path8 / IOSPECS_FILE).read_text(
        encoding="utf-8")
    m8 = mx.read_model(str(path8))
    assert not m8.iospecs[0]._is_hidden
    assert not hasattr(m8.Space1.pdref, "_mx_dataclient")
    pd.testing.assert_frame_equal(m8.Space1.pdref, sample_df)


def test_v7_model_resaves_as_v8(tmp_path, sample_df, close_new_models):
    """The natural migration path: a v7 model loads via the v7 reader
    and resaves in the v8 format."""
    m = _make_pandas_model("V8Migrate", sample_df)
    path7 = tmp_path / "model_v7"
    mx.write_model(m, str(path7), version=7)
    m.close()

    m7 = mx.read_model(str(path7))
    path8 = tmp_path / "model_v8"
    mx.write_model(m7, str(path8))
    m7.close()

    assert (path7 / "_data" / "iospecs.pickle").exists()
    assert not (path8 / "_data" / "iospecs.pickle").exists()
    assert (path8 / IOSPECS_FILE).exists()

    m8 = mx.read_model(str(path8))
    pd.testing.assert_frame_equal(m8.Space1.pdref, sample_df)


# ---------------------------------------------------------------------------
# Tolerant paths


def test_missing_io_file(tmp_path, sample_df, close_new_models):
    """Deleting the file behind a spec: the ref becomes None, the other
    spec survives, and no orphan IO is left behind."""
    m = mx.new_model("V8MissingFile")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_pandas(name="kept", path="files/kept.csv",
                 data=sample_df * 2, file_type="csv")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    (path / "files" / "data.csv").unlink()

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.pdref is None
    pd.testing.assert_frame_equal(m2.Space1.kept, sample_df * 2)
    assert len(m2.iospecs) == 1
    m2.close()
    _assert_no_ios_left(m2)


def test_missing_io_file_zip(tmp_path, sample_df, close_new_models):
    """Same as above for a zipped model."""
    m = _make_pandas_model("V8MissingZip", sample_df)
    path = tmp_path / "model.zip"
    mx.zip_model(m, str(path))
    m.close()

    trimmed = tmp_path / "trimmed.zip"
    with zipfile.ZipFile(str(path)) as zin, \
            zipfile.ZipFile(str(trimmed), "w") as zout:
        for item in zin.infolist():
            if not item.filename.endswith("data.csv"):
                zout.writestr(item, zin.read(item.filename))

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(trimmed))
    assert m2.Space1.pdref is None
    assert m2.Space1.other == 5
    assert m2.iospecs == []
    m2.close()
    _assert_no_ios_left(m2)


def test_malformed_literal_line(tmp_path, sample_df, close_new_models):
    """A line that does not parse fails individually: its refs are set
    to None with a warning and the other declarations load."""
    m = mx.new_model("V8Malformed")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_pandas(name="kept", path="files/kept.csv",
                 data=sample_df * 2, file_type="csv")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    specfile = path / IOSPECS_FILE
    lines = specfile.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = ["(1, 'PandasData', broken !!\n" if line.startswith("(1,")
             else line for line in lines]
    specfile.write_text("".join(lines), encoding="utf-8")

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))

    lost, kept = (("pdref", "kept")
                  if m2.Space1.pdref is None else ("kept", "pdref"))
    assert getattr(m2.Space1, lost) is None
    assert isinstance(getattr(m2.Space1, kept), pd.DataFrame)
    assert len(m2.iospecs) == 1
    m2.close()
    _assert_no_ios_left(m2)


def test_duplicate_key_line_skipped(tmp_path, sample_df,
                                    close_new_models):
    """A duplicated declaration line (e.g. a merge artifact) is skipped
    with a warning; the first occurrence's spec survives intact."""
    m = _make_pandas_model("V8DupKey", sample_df)
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    specfile = path / IOSPECS_FILE
    content = specfile.read_text(encoding="utf-8")
    dupline = next(line for line in content.splitlines()
                   if line.startswith("("))
    specfile.write_text(content + dupline + "\n", encoding="utf-8")

    with pytest.warns(UserWarning, match="invalid or duplicate"):
        m2 = mx.read_model(str(path))

    pd.testing.assert_frame_equal(m2.Space1.pdref, sample_df)
    assert len(m2.iospecs) == 1
    m2.close()
    _assert_no_ios_left(m2)


def test_non_int_key_line_skipped(tmp_path, sample_df,
                                  close_new_models):
    """A line whose key is not an int (even an unhashable one) fails
    per line instead of aborting the read."""
    m = mx.new_model("V8BadKey")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_pandas(name="kept", path="files/kept.csv",
                 data=sample_df * 2, file_type="csv")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    specfile = path / IOSPECS_FILE
    lines = specfile.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = ["([1]" + line[2:] if line.startswith("(1,")
             else line for line in lines]
    specfile.write_text("".join(lines), encoding="utf-8")

    with pytest.warns(UserWarning, match="invalid or duplicate"):
        m2 = mx.read_model(str(path))

    lost, kept = (("pdref", "kept")
                  if m2.Space1.pdref is None else ("kept", "pdref"))
    assert getattr(m2.Space1, lost) is None
    assert isinstance(getattr(m2.Space1, kept), pd.DataFrame)
    assert len(m2.iospecs) == 1
    m2.close()
    _assert_no_ios_left(m2)


def test_future_format_version(tmp_path, sample_df, close_new_models):
    """An entry whose class format version is newer than the running
    class supports degrades to a lost ref instead of aborting the
    read; no IO is registered for it."""
    m = mx.new_model("V8FutureVer")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_pandas(name="kept", path="files/kept.csv",
                 data=sample_df * 2, file_type="csv")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    specfile = path / IOSPECS_FILE
    content = specfile.read_text(encoding="utf-8").replace(
        "(1, 'PandasData', 1,", "(1, 'PandasData', 99,")
    specfile.write_text(content, encoding="utf-8")

    with pytest.warns(UserWarning, match="newer version of modelx"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.pdref is None
    pd.testing.assert_frame_equal(m2.Space1.kept, sample_df * 2)
    assert len(m2.iospecs) == 1
    m2.close()
    _assert_no_ios_left(m2)


def test_unknown_spec_class(tmp_path, sample_df, close_new_models):
    """A declaration naming a spec type this modelx does not know (e.g.
    written by a future version) degrades to a lost ref."""
    m = _make_pandas_model("V8UnknownCls", sample_df)
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    specfile = path / IOSPECS_FILE
    content = specfile.read_text(encoding="utf-8").replace(
        "'PandasData'", "'FutureData'")
    specfile.write_text(content, encoding="utf-8")

    with pytest.warns(UserWarning, match="unknown IO spec type"):
        m2 = mx.read_model(str(path))
    assert m2.Space1.pdref is None
    assert m2.Space1.other == 5
    m2.close()
    _assert_no_ios_left(m2)


def test_iospecs_file_unreadable(tmp_path, sample_df, monkeypatch,
                                 close_new_models):
    """An iospecs.py that cannot be read at all loses the specs but the
    model still loads (parity with the unreadable-iospecs.pickle
    behavior of versions 4-7)."""
    from modelx.serialize import serializer_8

    m = _make_pandas_model("V8Unreadable", sample_df)
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    orig = serializer_8.ziputil.read_file_utf8

    def failing(callback, path_, mode, **kwargs):
        if pathlib.Path(path_).name == "iospecs.py":
            raise OSError("simulated read failure")
        return orig(callback, path_, mode, **kwargs)

    monkeypatch.setattr(serializer_8.ziputil, "read_file_utf8", failing)

    with pytest.warns(UserWarning, match="could not be read"):
        m2 = mx.read_model(str(path))
    assert m2.Space1.pdref is None
    assert m2.Space1.other == 5
    assert m2.iospecs == []
    m2.close()
    _assert_no_ios_left(m2)


def test_iospecs_file_missing(tmp_path, sample_df, close_new_models):
    """With iospecs.py deleted, references and DataValue stubs in
    data.pickle resolve to None and inputs are skipped."""
    m = mx.new_model("V8SpecsMissing")
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=sample_df, file_type="csv")
    s.new_cells(name="foo", formula=lambda x: x)
    s.foo[1] = s.pdref              # DataValue stub in data.pickle
    s.other = 5
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    (path / IOSPECS_FILE).unlink()

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.pdref is None
    assert m2.Space1.foo[1] == 1        # skipped input recomputed
    assert m2.Space1.other == 5
    assert m2.iospecs == []
    m2.close()
    _assert_no_ios_left(m2)


# ---------------------------------------------------------------------------
# Version dispatch


def test_unknown_version_clean_error(tmp_path, sample_df, close_new_models):
    """A model saved by an unknown (newer) serializer version fails with
    a clean error, not an import stack trace."""
    m = _make_pandas_model("V8Future", sample_df)
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    sysfile = path / "_system.json"
    sysfile.write_text(sysfile.read_text().replace(
        '"serializer_version": 8', '"serializer_version": 99'))

    with pytest.raises(ValueError, match="newer version of modelx"):
        mx.read_model(str(path))
