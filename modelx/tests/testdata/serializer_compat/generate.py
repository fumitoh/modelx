"""Regenerate the serializer-compat fixture models.

The ``model_v<N>`` directories next to this module hold the fixture
model of ``fixturemodel.py`` saved with serializer versions 4-7.  They
are load-compatibility gates for the core refactoring (Phase 0 of
devnotes/CoreRefactorDesign.md): later modelx versions must keep
loading these exact files, so they are normally never regenerated.

Serializers 2-3 are deprecated for loading and 2-5 for writing (design
doc revision 2026-07-15), so only 4-7 are gated and only 6-7 are
writable by this script.

How the fixtures were generated (2026-07-14):

- ``model_v6``, ``model_v7``: by this script against current master
  (v0.31.1, commit e71cbd6 + Phase 0 tests)::

      python -m modelx.tests.testdata.serializer_compat.generate

- ``model_v5``: current master cannot *write* formats 2-5 (the old
  writers rotted when ``source`` was removed from cells in v0.22.0
  development, commit e1cb313).  It was written by running
  ``build_fixture_model()`` under historic modelx source at commit
  ``d503083`` (v0.21.0, the last state where that writer worked), on
  Python 3.12 with ``ast.Str``/``ast.Num`` aliased to ``ast.Constant``.

- ``model_v4``: the serializer_4 writer was already broken at
  ``d503083`` (its ``ModelPickler`` call predates the ``writer``
  argument), so it was written the same way at tag ``v0.17.0``, the
  last release whose default format was 4.

Each fixture is verified by ``tests/serialize/test_serializer_compat.py``,
which loads it with the modelx under test and runs
``check_fixture_model`` plus a comparison against a freshly built
fixture.
"""

import pathlib
import shutil

import modelx as mx
from modelx.serialize import HIGHEST_VERSION
from modelx.tests.testdata.serializer_compat.fixturemodel import (
    build_fixture_model,
    check_fixture_model,
)

# Formats current master can still write (see module docstring for 4-5)
WRITABLE_VERSIONS = range(6, HIGHEST_VERSION + 1)


def generate(datadir=None):
    datadir = pathlib.Path(datadir) if datadir else pathlib.Path(
        __file__).parent

    for version in WRITABLE_VERSIONS:
        path = datadir / ("model_v%s" % version)
        if path.exists():
            shutil.rmtree(path)

        m = build_fixture_model()
        try:
            mx.write_model(m, str(path), backup=False, version=version)
        finally:
            m.close()

        m = mx.read_model(str(path))
        try:
            check_fixture_model(m)
        finally:
            m.close()

        print("written and verified:", path)


if __name__ == "__main__":
    generate()
