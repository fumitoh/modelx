"""Characterization tests for the two-phase inheritance order.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
``InstructionList.execute`` iterates a plain list while
``SpaceUpdater._update_derived_space`` appends the ref-sync instructions
mid-iteration, so all 'cells' syncs across the affected subgraph run
before all 'own_refs' syncs.  Relative-reference resolution relies on the
targets (derived cells) already existing when refs are derived.  Any
replacement pipeline (Phase 6) must preserve this ordering explicitly;
these tests freeze its observable effect.
"""

import modelx as mx
import pytest


def test_ref_resolves_to_derived_cells_same_edit():
    """new_space(bases=...): the derived relative ref binds to the
    derived cells created by the same edit."""
    m = mx.new_model()
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    A.set_ref("bar", A.foo, "relative")

    D = m.new_space("D", bases=A)

    assert D.bar is D.foo           # not A.foo
    assert D.foo._impl.is_derived()
    m._impl._check_sanity()
    m.close()


def test_ref_resolves_across_subgraph_on_add_bases():
    """add_bases on a space with existing subs: every space in the
    affected subgraph gets its derived ref bound to its own derived
    cells, even though the cells of all spaces are created before any
    ref is derived."""
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    B.new_cells(name="foo", formula=lambda x: x)
    B.set_ref("bar", B.foo, "relative")

    S1 = m.new_space("S1")
    S2 = m.new_space("S2", bases=S1)
    S3 = m.new_space("S3", bases=S2)

    S1.add_bases(B)

    for sub in (S1, S2, S3):
        assert sub.bar is sub.foo
        assert sub.foo._impl.is_derived()
    assert S3.bar is not S1.foo
    m._impl._check_sanity()
    m.close()


def test_auto_ref_resolves_to_derived_cells_same_edit():
    """Same as above with refmode 'auto': resolution prefers the
    sub-side derived cells over the base object."""
    m = mx.new_model()
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    A.bar = A.foo                   # plain assignment: refmode 'auto'

    D = m.new_space("D", bases=A)

    assert D.bar is D.foo
    m._impl._check_sanity()
    m.close()


def test_formula_using_derived_ref_and_cells_same_edit():
    """A formula evaluated right after the edit sees both the derived
    cells and the derived ref of the new space."""
    m = mx.new_model()
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x + offset)
    A.new_cells(name="qux", formula=lambda x: foo(x) * 2)
    A.offset = 5

    D = m.new_space("D", bases=A)
    D.offset = 100                  # override; qux must use D's members

    assert D.qux(1) == 202
    assert A.qux(1) == 12
    m._impl._check_sanity()
    m.close()
