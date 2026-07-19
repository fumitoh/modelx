"""Tolerant unpickling: models load even when pickled values cannot be
restored in the current environment.

Serializers 4-7 substitute None for references whose pickled values fail
to unpickle, skip unrestorable cells inputs and dynamic inputs, and warn
about every substitution, instead of aborting the whole load
(see modelx/serialize/tolerant_pickle.py).
"""

import pathlib
import pickle
import shutil
import sys
import textwrap
import zipfile

import pytest

import modelx as mx
from modelx.core.system import mxsys
from modelx.tests.testdata.serializer_compat import fixturemodel

DATADIR = pathlib.Path(fixturemodel.__file__).parent

VERSIONS = [4, 5, 6, 7]


class Unrestorable:
    """Pickles cleanly but always fails to unpickle."""

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        raise RuntimeError("unrestorable object")


@pytest.fixture(params=["write_model", "zip_model"])
def write_meth(request):
    return getattr(mx, request.param)


def test_lost_ref_and_input(tmp_path, write_meth, close_new_models):
    """Poisoned refs become None and poisoned cells inputs are skipped;
    healthy values survive, and the loaded model can be saved again."""
    m = mx.new_model()
    s = m.new_space("Space1")
    s.new_cells(name="foo", formula=lambda x: x * 2)
    s.foo[0] = 100
    s.foo[1] = Unrestorable()
    s.bad = Unrestorable()
    s.shared = s.bad
    s.good = [1, 2, 3]
    s.lit = 42

    path = tmp_path / "model"
    write_meth(m, str(path))
    m.close()

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.bad is None
    assert m2.Space1.shared is None
    assert m2.Space1.good == [1, 2, 3]
    assert m2.Space1.lit == 42
    assert m2.Space1.foo[0] == 100
    assert m2.Space1.foo[1] == 2    # skipped input recomputed by formula

    # A model loaded with holes can be saved and loaded again
    path2 = tmp_path / "model2"
    write_meth(m2, str(path2))
    m3 = mx.read_model(str(path2))
    assert m3.Space1.bad is None
    assert m3.Space1.foo[0] == 100


def test_lost_input_key(tmp_path, write_meth, close_new_models):
    """A cells input whose key cannot be restored is skipped."""
    m = mx.new_model()
    s = m.new_space("Space1")
    s.new_cells(name="foo", formula=lambda x: 0)
    s.foo[Unrestorable()] = 3
    s.foo["ok"] = 4

    path = tmp_path / "model"
    write_meth(m, str(path))
    m.close()

    with pytest.warns(UserWarning, match="input value.*could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.foo["ok"] == 4
    assert len(m2.Space1.foo._impl.input_keys) == 1


def test_lost_dynamic_input(tmp_path, write_meth, close_new_models):
    """A dynamic (itemspace) input whose value cannot be restored is
    skipped."""
    m = mx.new_model()
    s = m.new_space("Space1", formula=lambda i: None)
    s.new_cells(name="foo", formula=lambda x: x)
    s[1].foo[0] = Unrestorable()
    s[2].foo[0] = "kept"

    path = tmp_path / "model"
    write_meth(m, str(path))
    m.close()

    with pytest.warns(UserWarning, match="dynamic input.*could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1[2].foo[0] == "kept"
    assert m2.Space1[1].foo[0] == 0     # recomputed by formula


def test_unimportable_module(tmp_path, write_meth, close_new_models):
    """A ref whose class's module no longer exists becomes None."""
    moddir = tmp_path / "mods"
    moddir.mkdir()
    (moddir / "ghost_mod_tolerant.py").write_text(textwrap.dedent("""\
        class Ghost:
            pass
    """))
    sys.path.insert(0, str(moddir))
    try:
        import ghost_mod_tolerant
        m = mx.new_model()
        s = m.new_space("Space1")
        s.gref = ghost_mod_tolerant.Ghost()
        s.lit = 1
        path = tmp_path / "model"
        write_meth(m, str(path))
        m.close()
    finally:
        sys.path.remove(str(moddir))
        sys.modules.pop("ghost_mod_tolerant", None)

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.gref is None
    assert m2.Space1.lit == 1


def test_corrupt_data_pickle(tmp_path, close_new_models):
    """A truncated data.pickle loses all pickled values but the model
    still loads."""
    m = mx.new_model()
    s = m.new_space("Space1")
    s.ref1 = [1, 2, 3]
    s.lit = 7
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    dfile = path / "_data" / "data.pickle"
    dfile.write_bytes(dfile.read_bytes()[:5])

    with pytest.warns(UserWarning, match="could not be read"):
        m2 = mx.read_model(str(path))

    assert m2.Space1.ref1 is None
    assert m2.Space1.lit == 7


@pytest.mark.parametrize("version", VERSIONS)
def test_poisoned_fixture_model(version, tmp_path, close_new_models):
    """Serializer-4 to -7 models with an unrestorable pickled value load
    with a warning and keep everything else."""
    src = DATADIR / ("model_v%s" % version)
    dst = tmp_path / src.name
    shutil.copytree(str(src), str(dst))

    # The fixtures' data.pickle contains no persistent ids, so it can be
    # rewritten with the plain pickle module.
    pfile = dst / "_data" / "data.pickle"
    with pfile.open("rb") as f:
        data = pickle.load(f)
    data[999999001] = Unrestorable()
    with pfile.open("wb") as f:
        pickle.dump(data, f)

    with pytest.warns(UserWarning, match="unrestorable object"):
        m = mx.read_model(str(dst))
    fixturemodel.check_fixture_model(m)


def _make_pandas_model(name):
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    m = mx.new_model(name)
    s = m.new_space("Space1")
    s.new_pandas(name="pdref", path="files/data.xlsx",
                 data=df, file_type="excel")
    s.other = 5
    return m


def _assert_pandas_ref_lost(m):
    assert m.Space1.pdref is None
    assert m.Space1.other == 5
    assert m.iospecs == []
    assert not [io_ for (group, path), io_ in mxsys.iomanager.ios.items()
                if group is m or group is None]


def test_iospec_data_file_missing_dir(tmp_path, close_new_models):
    """Deleting the file behind an IO spec: the ref becomes None and no
    orphan IO is left behind."""
    pytest.importorskip("openpyxl")
    m = _make_pandas_model("IOModelDir")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    (path / "files" / "data.xlsx").unlink()

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))
    _assert_pandas_ref_lost(m2)


def test_iospec_data_file_missing_zip(tmp_path, close_new_models):
    """Same as above for a zipped model (archive rebuilt without the
    member)."""
    pytest.importorskip("openpyxl")
    m = _make_pandas_model("IOModelZip")
    path = tmp_path / "model.zip"
    mx.zip_model(m, str(path))
    m.close()

    trimmed = tmp_path / "trimmed.zip"
    with zipfile.ZipFile(str(path)) as zin, \
            zipfile.ZipFile(str(trimmed), "w") as zout:
        for item in zin.infolist():
            if not item.filename.endswith("data.xlsx"):
                zout.writestr(item, zin.read(item.filename))

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(trimmed))
    _assert_pandas_ref_lost(m2)


def test_iospecs_pickle_corrupt(tmp_path, close_new_models):
    """A truncated iospecs.pickle loses the specs but the model loads."""
    pytest.importorskip("openpyxl")
    m = _make_pandas_model("IOModelCorrupt")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    iofile = path / "_data" / "iospecs.pickle"
    iofile.write_bytes(iofile.read_bytes()[:10])

    with pytest.warns(UserWarning, match="could not be read"):
        m2 = mx.read_model(str(path))
    _assert_pandas_ref_lost(m2)


def test_iospecs_pickle_missing(tmp_path, close_new_models):
    """With iospecs.pickle deleted, DataValue references in data.pickle
    resolve to None."""
    pytest.importorskip("openpyxl")
    m = _make_pandas_model("IOModelMissing")
    path = tmp_path / "model"
    mx.write_model(m, str(path))
    m.close()

    (path / "_data" / "iospecs.pickle").unlink()

    with pytest.warns(UserWarning, match="could not be restored"):
        m2 = mx.read_model(str(path))
    _assert_pandas_ref_lost(m2)
