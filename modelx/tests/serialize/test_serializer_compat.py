"""Load-compatibility gates for models saved by serializer versions 4-7.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
the ``model_v<N>`` directories under
``modelx/tests/testdata/serializer_compat/`` hold the same fixture
model saved with each supported serializer version (see ``generate.py``
there for exactly how each was produced).  Loading them must keep
working while the core is refactored.

Serializers 2-3 are deprecated for loading (and 2-5 for writing), so
only versions 4-7 are gated (design doc revision 2026-07-15).
"""

import pathlib

import pytest

import modelx as mx
from modelx.testing import testutil
from modelx.tests.testdata.serializer_compat import fixturemodel

DATADIR = pathlib.Path(fixturemodel.__file__).parent

VERSIONS = [4, 5, 6, 7]


@pytest.fixture
def close_new_models():
    """Close every model created during the test, including partially
    built ones left behind if a reader raises mid-load."""
    before = set(mx.get_models())
    yield
    for name, model in list(mx.get_models().items()):
        if name not in before:
            model.close()


@pytest.mark.parametrize("version", VERSIONS)
def test_load_fixture_model(version, close_new_models):
    """A model saved by serializer_<version> loads and behaves."""
    m = mx.read_model(str(DATADIR / ("model_v%s" % version)))
    fixturemodel.check_fixture_model(m)


@pytest.mark.parametrize("version", VERSIONS)
def test_loaded_fixture_equals_fresh(version, close_new_models):
    """A loaded fixture is structurally identical to a freshly
    built one."""
    m = mx.read_model(str(DATADIR / ("model_v%s" % version)))
    fresh = fixturemodel.build_fixture_model()
    testutil.compare_model(m, fresh)
    m._impl._check_sanity()
    fresh._impl._check_sanity()
