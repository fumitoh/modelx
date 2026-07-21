"""Round-trip determinism of the serializer 6/7 writers.

A no-op save -> load -> save round trip must produce byte-identical
output trees: the writers emit sequential writer-assigned ids instead
of memory addresses (``id()``), so the bytes cannot vary from one
process run to the next.
"""

import zipfile

import pytest

import modelx as mx


def t_arg(t):
    pass


def _build_model(name):
    """Build a model exercising every id-emitting site of the writer.

    Covers cells input values (one value shared between two cells and
    a dynamic input, to test identity dedup), a Pickle-encoded ref, an
    IOSpec ref (new_pandas), an Interface ref to an ItemSpace (tuple
    args), and ItemSpace dynamic inputs.
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

    # Interface ref to an ItemSpace: its idtuple contains an args tuple.
    # Created before the dynamic inputs below so that the ItemSpace
    # creation order matches the reader's restore order (refs are set
    # before dynamic inputs).
    m.new_space("SpaceB", refs={"RefSpaceA": m.Space1(0)})

    s[1].foo[3] = [7, 8]
    s[1].bar[3] = shared

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


@pytest.mark.parametrize("version", [6, 7])
@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_roundtrip_determinism(
        tmp_path, write_method, version, close_new_models):

    m = _build_model("DetModel%s" % version)
    path1 = tmp_path / "save1"
    getattr(mx, write_method)(m, path1, version=version)
    m.close()

    m2 = mx.read_model(path1)

    # Sanity: the model and the identity dedup survived the round trip.
    assert m2.Space1.foo[1] == [1, 2, 3]
    assert m2.Space1.foo[1] is m2.Space1.bar[1]
    assert m2.Space1[1].bar[3] is m2.Space1.foo[1]
    assert m2.Space1[1].foo[3] == [7, 8]
    assert m2.pickle_ref == {"key": (1, 2)}
    assert m2.SpaceB.RefSpaceA is m2.Space1(0)

    path2 = tmp_path / "save2"
    getattr(mx, write_method)(m2, path2, version=version)
    m2.close()

    if write_method == "zip_model":
        _assert_identical_zips(path1, path2)
    else:
        _assert_identical_trees(path1, path2)
