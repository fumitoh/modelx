import sys
import importlib
import itertools
import pytest
from modelx.testing import testutil
import modelx as mx
import numpy as np


def _compare_results_simplelife(src, trg):

    for pol in (100, 200, 300):
        for t in range(50):
            assert (src.Projection[pol].PV_NetCashflow[t]
                    == trg.Projection[pol].PV_NetCashflow[t])


def _compare_results_nestedlife(src, trg):
    pass


def _compare_results_ifrs17sim(src, trg):

    for pol in (100, 200, 300):
        for t in range(3):
            assert (src.OuterProj[pol].ProfitBefTax[t]
                    == trg.OuterProj[pol].ProfitBefTax[t])


def _compare_results_solvency2(src, trg):

    for pol in (100, 200, 300):
        assert (src.SCR_life[0, pol].SCR_life()
                == trg.SCR_life[0, pol].SCR_life())


_PROJECTS = {"simplelife": _compare_results_simplelife,
             "nestedlife": _compare_results_nestedlife,
             "ifrs17sim": _compare_results_ifrs17sim,
             "solvency2": _compare_results_solvency2}


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

    path3 = tmp_path / "zip"
    path3.mkdir()

    return path1, path2, path3


# @pytest.mark.skip()
@pytest.mark.parametrize("project", _PROJECTS.keys())
def test_with_lifelib(testpaths, project):

    build_path, write_path, zip_path = testpaths

    import lifelib

    testproj = project + "_test"
    projpath = build_path / testproj

    lifelib.create(project, projpath)
    scriptpath = projpath / "scripts"

    with SysPath(str(scriptpath)):

        module = importlib.import_module(project)

        with SysPath(str(projpath)):

            m = module.build()
            # Assigning refs in 'm' will remove input values in dynamic cells
            # so don't update m here
            mx.write_model(m, str(write_path / project))
            mx.zip_model(m, str(zip_path / project))

            m2 = mx.read_model(str(write_path / project))
            testutil.compare_model(m, m2)

            m3 = mx.read_model(str(zip_path / project))
            testutil.compare_model(m, m3)

    _PROJECTS[project](m, m2)
    _PROJECTS[project](m, m3)
    for mn in [m, m2, m3]:
        mn.close()


def test_back_compat_fastlife(tmp_path):

    import lifelib

    projpath = tmp_path / "fastlife"
    lifelib.create("fastlife", projpath)

    m = mx.read_model(projpath / "model")

    assert np.isclose(sum(m.Projection.PV_NetCashflow(0)), 288922348.168899)
    m.close()


