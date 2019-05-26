import sys
import os
import pathlib
import importlib
import pytest
from modelx.core.project import (
    export_model,
    import_model)
import modelx as mx
from modelx.testing import testutil

_PROJECTS = ["simplelife",
             "nestedlife",
             "ifrs17sim",
             "solvency2"]

class SysPath:

    def __init__(self, path_):
        self.path_ = path_

    def __enter__(self):
        sys.path.insert(0, str(self.path_))

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.path.pop(0)


@pytest.fixture
def testpaths(tmp_path):

    path1 = tmp_path / "build"
    path1.mkdir()

    path2 = tmp_path / "write"
    path2.mkdir()

    return path1, path2


# @pytest.mark.skip()
@pytest.mark.parametrize("project", _PROJECTS)
def test_with_lifelib(testpaths, project):

    build_path, write_path = testpaths

    from lifelib.commands import create

    testproj = project + "_test"
    projpath = build_path / testproj

    create.main([
        "--template",
        project,
        str(projpath)
    ])

    with SysPath(str(projpath.parent)):

        module = importlib.import_module(testproj + "." + project)

        with SysPath(str(projpath)):

            m = module.build()
            m.hoge = "hoge"
            m.foo = 1
            m.bar = m.Input
            m.Input.new_cells(formula=lambda x: 3 * x)
            m.none = None

            export_model(m, str(write_path))
            m2 = import_model(str(write_path / project))
            testutil.compare_model(m, m2)