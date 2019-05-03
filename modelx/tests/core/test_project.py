import pytest
from modelx.core.project import (
    export_model,
    import_model)
from modelx.testing import testutil
import modelx as mx


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

    s.v = m
    s.w = foo

    return m


def test_export_import(testmodel, tmp_path):

    path_ = tmp_path / "testdir"
    path_.mkdir()
    export_model(testmodel, path_)
    m = import_model(path_ / testmodel.name)

    testutil.compare_model(testmodel, m)




