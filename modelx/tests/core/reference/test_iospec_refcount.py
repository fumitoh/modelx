"""Characterization tests for IOSpec lifecycle tied to ref counting.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
ReferenceManager keeps ``_valid_to_refs`` (id(value) -> [refs]) and
deletes the associated IOSpec exactly when the last ref to a value
disappears.  ValueRegistry (Phase 3) must reproduce this ordering.
"""

import pandas as pd
import numpy as np
import pytest
import modelx as mx


@pytest.fixture
def two_refs_to_pandas():
    """S1.d1 and S2.d2 both reference the same PandasData value."""
    df = pd.DataFrame({"a": np.arange(3), "b": np.arange(3) * 2.0})
    m = mx.new_model()
    s1 = m.new_space("S1")
    s2 = m.new_space("S2")
    s1.new_pandas(
        name="d1", path="files/data.xlsx", data=df, file_type="excel")
    s2.d2 = s1.d1                   # second ref to the same object
    yield m, s1, s2
    m._impl._check_sanity()
    m.close()


def test_two_refs_share_value_and_spec(two_refs_to_pandas):
    m, s1, s2 = two_refs_to_pandas

    assert s1.d1 is s2.d2
    spec = m.get_spec(s1.d1)
    assert spec is not None
    assert spec in m.iospecs
    assert len(m.iospecs) == 1


def test_del_one_ref_keeps_spec(two_refs_to_pandas):
    """Deleting one of two refs to the same PandasData keeps the spec."""
    m, s1, s2 = two_refs_to_pandas

    value = s1.d1
    spec = m.get_spec(value)

    del s1.d1

    assert m._impl.refmgr.has_spec(value)
    assert m.get_spec(s2.d2) is spec
    assert spec in m.iospecs


def test_del_last_ref_drops_spec(two_refs_to_pandas):
    """Deleting the last ref to the PandasData deletes the spec."""
    m, s1, s2 = two_refs_to_pandas

    value = s1.d1

    del s1.d1
    del s2.d2

    assert not m._impl.refmgr.has_spec(value)
    assert m.iospecs == []
    assert id(value) not in m._impl.refmgr._valid_to_refs


def test_change_last_ref_drops_spec(two_refs_to_pandas):
    """Rebinding the last ref to another value also deletes the spec."""
    m, s1, s2 = two_refs_to_pandas

    value = s1.d1

    del s1.d1
    s2.d2 = 42                      # rebinding, not deleting

    assert not m._impl.refmgr.has_spec(value)
    assert m.iospecs == []


def test_del_space_does_not_unregister_refs():
    """Deleting a whole space does NOT decrement the refcounts of the
    values its refs hold; the IOSpec is retained even after every
    space referencing the value is gone.

    Current behavior, frozen: ``del_defined_space`` bypasses
    ReferenceManager entirely (decrements happen only in
    del_ref/change_ref).  Phase 3's ValueRegistry wired into space
    deletion would change observable ``m.iospecs`` -- that must be a
    conscious decision, not an accident.
    """
    df = pd.DataFrame({"a": np.arange(3), "b": np.arange(3) * 2.0})
    m = mx.new_model()
    s1 = m.new_space("S1")
    s2 = m.new_space("S2")
    s1.new_pandas(
        name="d1", path="files/data.xlsx", data=df, file_type="excel")
    s2.d2 = s1.d1
    value = s1.d1
    spec = m.get_spec(value)

    del m.S1

    refmgr = m._impl.refmgr
    assert len(refmgr._valid_to_refs[id(value)]) == 2   # unchanged
    assert m.get_spec(s2.d2) is spec

    del m.S2

    assert refmgr.has_spec(value)                       # spec leaks
    assert id(value) in refmgr._valid_to_refs
    m._impl._check_sanity()                 # the leak passes sanity
    m.close()


def test_registry_tracks_plain_values():
    """The id-keyed registry also tracks non-IO values; entries drop
    when their last ref goes."""
    m = mx.new_model()
    s1 = m.new_space("S1")
    s2 = m.new_space("S2")

    value = [1, 2, 3]
    s1.v1 = value
    s2.v2 = value
    refmgr = m._impl.refmgr
    assert len(refmgr._valid_to_refs[id(value)]) == 2

    del s1.v1
    assert len(refmgr._valid_to_refs[id(value)]) == 1

    del s2.v2
    assert id(value) not in refmgr._valid_to_refs

    m._impl._check_sanity()
    m.close()
