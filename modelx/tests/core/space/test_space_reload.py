import sys
import os.path
import modelx as mx
import modelx.tests.testdata
import pytest
import pathlib

datadir = pathlib.Path(os.path.dirname(mx.tests.testdata.__file__))


@pytest.fixture
def reloadtest(tmp_path):

    with open(tmp_path / "__init__.py", "w") as f:
        f.write("")

    sys.path.insert(0, str(tmp_path))
    sample = "reloadtest"

    model = mx.new_model()
    yield model, sample, tmp_path

    model._impl._check_sanity()
    model.close()

    if sys.path[0] == str(tmp_path):
        del sys.path[0]


def test_space_reload(reloadtest):
    import shutil

    model, samplename, tempdir = reloadtest
    sample = str(tempdir.joinpath(samplename + ".py"))

    shutil.copy(str(datadir.joinpath(samplename + "_before.py")), sample)
    # import reloadtest as src
    import importlib

    src = importlib.import_module(samplename)

    space = model.import_module(module=src)
    assert space.foo(3) == 0
    assert "baz" in space.cells

    shutil.copy(str(datadir.joinpath(samplename + "_after.py")), sample)
    space.reload()

    assert space.foo(3) == 1
    assert space.bar(3) == 1
    assert len(space.baz) == 0
