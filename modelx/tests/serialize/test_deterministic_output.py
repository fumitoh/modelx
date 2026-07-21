"""Round-trip determinism of the serializer 6/7 writers.

A no-op save -> load -> save round trip must produce byte-identical
output trees: the writers emit sequential writer-assigned ids instead
of memory addresses (``id()``), assign them in orders derived from the
model state rather than from session history, and avoid iterating sets
whose order depends on the process hash seed. (Values whose own pickle
is hash-order dependent, such as sets of strings, are outside the
writers' control and can still vary across processes.)
"""

import os
import subprocess
import sys
import zipfile

import pytest

import modelx as mx


def t_arg(t):
    pass


def _build_model(name):
    """Build a model exercising every id-emitting site of the writer.

    Covers cells input values (one value shared between two cells and
    a dynamic input, to test identity dedup), a Pickle-encoded ref,
    IOSpec refs (new_pandas), an Interface ref to an ItemSpace (tuple
    args), and ItemSpace dynamic inputs, including a str cells key.

    The creation orders are deliberately adversarial: the space-level
    iospec is created before the model-level one, although the writer
    traverses the model's refs first, and the dynamic inputs are set
    before the Interface ref although the reader re-creates the ref'd
    ItemSpace first. Reloading therefore reorders both
    ``model.iospecs`` and ``_named_itemspaces`` relative to this
    build, and only state-derived (not history-derived) id assignment
    keeps the resave byte-identical.
    """
    pd = pytest.importorskip("pandas")

    m = mx.new_model(name)
    s = m.new_space("Space1", formula=t_arg)

    @mx.defcells
    def foo(x):
        return x

    @mx.defcells
    def bar(x):
        return x

    shared = [1, 2, 3]
    s.foo[1] = shared
    s.bar[1] = shared
    s.foo[2] = 100

    m.pickle_ref = {"key": (1, 2)}

    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    s.new_pandas(name="pdref", path="files/data.csv",
                 data=df, file_type="csv")
    m.new_pandas(name="pdref_model", path="files/data_model.csv",
                 data=df * 2, file_type="csv")

    s[1].foo[3] = [7, 8]
    s[1].bar[3] = shared
    s[1].foo["alpha"] = 9
    s[2].foo["bravo"] = 10

    m.new_space("SpaceB", refs={"RefSpaceA": m.Space1(0)})

    return m


def _assert_identical_trees(path1, path2):
    files1 = sorted(p.relative_to(path1) for p in path1.rglob("*")
                    if p.is_file())
    files2 = sorted(p.relative_to(path2) for p in path2.rglob("*")
                    if p.is_file())
    assert files1 == files2
    for rel in files1:
        assert (path1 / rel).read_bytes() == (path2 / rel).read_bytes(), \
            "file differs between saves: %s" % rel


def _assert_identical_zips(path1, path2):
    # Compare entry bytes, not archive bytes: zip headers embed
    # timestamps that legitimately differ between the two saves.
    with zipfile.ZipFile(path1) as z1, zipfile.ZipFile(path2) as z2:
        names1 = sorted(z1.namelist())
        names2 = sorted(z2.namelist())
        assert names1 == names2
        for name in names1:
            assert z1.read(name) == z2.read(name), \
                "zip entry differs between saves: %s" % name


def _assert_loaded_model(m2):
    """The model and the identity dedup survived the round trip."""
    assert m2.Space1.foo[1] == [1, 2, 3]
    assert m2.Space1.foo[1] is m2.Space1.bar[1]
    assert m2.Space1[1].bar[3] is m2.Space1.foo[1]
    assert m2.Space1[1].foo[3] == [7, 8]
    assert m2.Space1[1].foo["alpha"] == 9
    assert m2.Space1[2].foo["bravo"] == 10
    assert m2.pickle_ref == {"key": (1, 2)}
    assert m2.SpaceB.RefSpaceA is m2.Space1(0)


@pytest.mark.parametrize("version", [6, 7])
@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_roundtrip_determinism(
        tmp_path, write_method, version, close_new_models):

    m = _build_model("DetModel%s" % version)
    path1 = tmp_path / "save1"
    getattr(mx, write_method)(m, path1, version=version)
    m.close()

    m2 = mx.read_model(path1)
    _assert_loaded_model(m2)

    path2 = tmp_path / "save2"
    getattr(mx, write_method)(m2, path2, version=version)
    m2.close()

    if write_method == "zip_model":
        _assert_identical_zips(path1, path2)
    else:
        _assert_identical_trees(path1, path2)


_RESAVE_SCRIPT = """\
import sys
sys.path.insert(0, sys.argv[3])
import modelx as mx
m = mx.read_model(sys.argv[1])
mx.write_model(m, sys.argv[2])
"""


def test_cross_process_determinism(tmp_path, close_new_models):
    """Resaving in fresh processes with different hash seeds must
    reproduce the original save byte for byte."""
    m = _build_model("XProcDetModel")
    path1 = tmp_path / "save1"
    mx.write_model(m, path1)
    m.close()

    script = tmp_path / "resave.py"
    script.write_text(_RESAVE_SCRIPT)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(mx.__file__)))

    resaved = []
    for seed in ("1", "2"):
        out = tmp_path / ("resave_seed" + seed)
        env = dict(os.environ, PYTHONHASHSEED=seed)
        subprocess.run(
            [sys.executable, str(script), str(path1), str(out), repo_root],
            check=True, env=env, capture_output=True)
        resaved.append(out)

    _assert_identical_trees(path1, resaved[0])
    _assert_identical_trees(resaved[0], resaved[1])
