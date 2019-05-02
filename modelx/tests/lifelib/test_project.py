import sys
import pathlib
import pytest
from modelx.core.project import (
    export_model,
    import_model)
import modelx as mx
from modelx.testing import testutil

class SysPath:

    def __init__(self, module):

        self.module = module
        self.parent_path = pathlib.Path(module.__file__).parent

    def __enter__(self):
        sys.path.insert(0, str(self.parent_path))

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.path.pop(0)


def test_with_lifelib(tmp_path):

    from lifelib.projects.ifrs17sim import ifrs17sim

    with SysPath(ifrs17sim):

        m = ifrs17sim.build()
        m.hoge = "hoge"
        m.foo = 1
        m.bar = m.OuterProj
        m.OuterProj.new_cells(formula=lambda x: 3 * x)
        m.none = None

        path_ = tmp_path / "temp"
        path_.mkdir()

        export_model(m, path_)
        m2 = import_model(path_ / "ifrs17sim")
        testutil.compare_model(m, m2)