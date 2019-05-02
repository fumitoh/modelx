import json
import pytest
from modelx.core.project import (
    _RefViewEncoder,
    _decode_refs,
    _export_space,
    export_model,
    import_model)
from modelx.core.base import Interface
from modelx.testing import testutil
import modelx as mx


def test_encode_decode_refs(tmp_path):

    m, s = mx.new_model(), mx.new_space()
    c = s.new_cells()

    result = {
        "a": 1,
        "b": "abc",
        "c": [1, "2"],
        "d": (
            1, 2, "藍上夫", (3, 4.33), [5, None, (7, 8, [9, 10], "ABC")]
        ),
        "e": {
            3: '4',
            '5': ['6', 7]
        },
        "f": m,
        "g": s,
        "h": c
    }

    path_ = tmp_path / "testdir"
    path_.mkdir()
    file = tmp_path / "testrefs"

    with open(file, "w") as f:
        f.write(_RefViewEncoder().encode(result))

    with open(file, "r") as f:
        decoded = json.load(f, object_hook=_decode_refs)

    for (key0, val0), (key1, val1) in zip(result.items(), decoded.items()):
        assert key0 == key1
        if isinstance(val0, Interface):
            val0 = val0.fullname
            val1 = val1.evalrepr
        assert val0 == val1


@pytest.fixture
def testmodel():
    m, s = mx.new_model("TestModel"), mx.new_space(name='TestSpace')

    @mx.defcells
    def foo(x):
        # Comment
        return x # Comment

    s.formula = lambda a: None

    s.m = 1
    s.n = "abc"
    s.o = [1, "2"]
    s.t = (1, 2, "藍上夫", (3, 4.33), [5, None, (7, 8, [9, 10], "ABC")])
    s.u = {3: '4',
           '5': ['6', 7]}

    return m


def test_export_import(testmodel, tmp_path):

    path_ = tmp_path / "testdir"
    path_.mkdir()
    export_model(testmodel, path_)
    m = import_model(path_ / testmodel.name)

    testutil.compare_model(testmodel, m)




