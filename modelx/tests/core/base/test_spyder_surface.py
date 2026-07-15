"""Snapshot gate for the spyder-modelx attribute surface.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md,
section 8, compatibility gate 3): spyder-modelx consumes
``Interface._baseattrs`` and ``_get_attrdict(extattrs=["get_referents"])``
to populate its widgets.  This test compares their output for a
representative model (the serializer-compat fixture) against a golden
snapshot recorded from the pre-refactoring master (v0.31.1), so any of
Phases 1-6 silently changing that surface fails here.

Volatile fields are normalized: ``id`` values (memory addresses) are
zeroed and non-JSON leaf objects (nodes, builtins) are reduced to their
``repr``.

If the surface changes *intentionally*, regenerate the golden with::

    python -m modelx.tests.core.base.test_spyder_surface --write

and call out the diff in the commit message.
"""

import json
import pathlib
import sys

import modelx.tests.testdata
from modelx.tests.testdata.serializer_compat import fixturemodel

SNAPSHOT_PATH = (
    pathlib.Path(modelx.tests.testdata.__file__).parent
    / "spyder_surface_snapshot.json"
)


def normalize(obj):
    if isinstance(obj, dict):
        return {
            str(k): (0 if k == "id" else normalize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [normalize(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def build_snapshot():
    m = fixturemodel.build_fixture_model()
    try:
        m.Params[3]     # cover the itemspace surface too
        return {
            "model_baseattrs": normalize(m._baseattrs),
            "space_baseattrs": normalize(m.Base._baseattrs),
            "attrdict": normalize(
                m._get_attrdict(extattrs=["get_referents"], recursive=True)),
        }
    finally:
        m.close()


def test_spyder_surface_snapshot():
    with SNAPSHOT_PATH.open(encoding="utf-8") as f:
        golden = json.load(f)

    snapshot = build_snapshot()

    for key in golden:
        assert snapshot[key] == golden[key], (
            "spyder-modelx surface %r changed; if intentional,"
            " regenerate with"
            " 'python -m modelx.tests.core.base.test_spyder_surface"
            " --write'" % key
        )
    assert snapshot.keys() == golden.keys()


if __name__ == "__main__":
    if "--write" in sys.argv:
        with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
            json.dump(build_snapshot(), f, indent=1, sort_keys=True)
        print("written:", SNAPSHOT_PATH)
    else:
        print("pass --write to regenerate", SNAPSHOT_PATH)
