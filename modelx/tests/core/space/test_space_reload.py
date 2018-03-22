import sys
import os.path
from textwrap import dedent
import modelx as mx
import pytest


@pytest.fixture
def reloadtest():
    import pathlib

    datadir = pathlib.Path(__file__).parents[1].joinpath('data')
    sys.path.insert(0, str(datadir))
    sample = 'reloadtest'

    model = mx.new_model()
    yield model, sample, datadir

    os.remove(str(datadir.joinpath(sample + '.py')))
    if sys.path[0] == str(datadir):
        del sys.path[0]


def test_space_reload(reloadtest):
    import shutil
    model, samplename, datadir = reloadtest
    sample = str(datadir.joinpath(samplename + '.py'))
    sample_before = os.path.splitext(sample)[0] + '_before.py'
    sample_after = os.path.splitext(sample)[0] + '_after.py'

    shutil.copy(sample_before, sample)
    # import reloadtest as src
    import importlib
    src = importlib.import_module(samplename)

    space = model.new_space_from_module(module_=src)
    assert space.foo(3) == 0
    assert 'baz' in space.cells

    shutil.copy(sample_after, sample)
    space.reload()

    assert (space.foo(3) == 1)
    assert (space.bar(3) == 1)
    assert (len(space.baz) == 0)
