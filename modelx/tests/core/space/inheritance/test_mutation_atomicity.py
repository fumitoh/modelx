"""Characterization tests for failed-mutation atomicity.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
a mutation that raises must leave the model bit-identical to its state
before the edit.

Currently only ``new_space`` rolls back (and does so completely for the
scenarios below), while ``add_bases`` has no rollback at all.  The broken
cases are marked ``xfail(strict=True)``; they become acceptance tests for
Phase 6 (transactions), at which point the markers must be removed.
"""

import modelx as mx
import pytest


def snapshot_space(space):
    """Snapshot of one space's member dicts, member identities and flags."""
    impl = space._impl
    return {
        "cells": [
            (name, id(c), c.is_derived()) for name, c in impl.cells.items()
        ],
        "own_refs": [
            (name, id(r), r.is_derived(), id(r.interface))
            for name, r in impl.own_refs.items()
        ],
        "named_spaces": [
            (name, id(s)) for name, s in impl.named_spaces.items()
        ],
        "formula": None if impl.formula is None else impl.formula.source,
    }


def snapshot_model(model):
    """Full member-dict snapshot of a model, including the
    inheritance graph."""
    impl = model._impl
    graph = impl.spmgr._graph
    result = {
        "named_spaces": [
            (name, id(s)) for name, s in impl.named_spaces.items()
        ],
        "global_refs": [
            (name, id(r), id(r.interface))
            for name, r in impl.global_refs.items()
        ],
        "graph_nodes": sorted(graph.nodes),
        "graph_edges": sorted(
            (t, h, graph.edges[t, h]["index"]) for t, h in graph.edges
        ),
        "spaces": {},
    }

    def walk(space):
        result["spaces"][space.fullname] = snapshot_space(space)
        for child in space.spaces.values():
            walk(child)

    for s in model.spaces.values():
        walk(s)
    return result


@pytest.fixture
def base_with_bad_relref():
    """
        A---B---foo         B.bar --> A ('relative', out of scope for
                            any sub created outside A)
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    B.new_cells(name="foo", formula=lambda x: x)
    B.set_ref("bar", A, "relative")
    yield m, A, B
    m._impl._check_sanity()
    m.close()


def test_new_space_failed_ref_inherit_rolls_back(base_with_bad_relref):
    """new_space failing during ref inheritance restores the model."""
    m, A, B = base_with_bad_relref

    before = snapshot_model(m)
    with pytest.raises(ValueError):
        m.new_space("D", bases=B)
    assert snapshot_model(m) == before
    m._impl._check_sanity()


def test_new_space_failed_can_recreate(base_with_bad_relref):
    """After a failed new_space, the same name is usable again."""
    m, A, B = base_with_bad_relref

    with pytest.raises(ValueError):
        m.new_space("D", bases=B)

    assert "D" not in m._impl.spmgr._graph.nodes
    D = m.new_space("D")
    assert m.D is D


@pytest.mark.xfail(
    strict=True,
    reason="add_bases has no rollback: phase-A derived cells and a"
           " partially inherited ref survive the failed edit"
           " (CoreRefactorDesign.md problem 1; fixed in Phase 6)",
)
def test_add_bases_failed_ref_inherit_atomic(base_with_bad_relref):
    """add_bases failing during ref inheritance must restore the model.

    The failure happens after derived cells were already created across
    the affected subgraph (two-phase inheritance), so without rollback
    S1 and S2 keep a phantom derived cells 'foo' and S1 a placeholder
    ref 'bar'.
    """
    m, A, B = base_with_bad_relref
    S1 = m.new_space("S1")
    S1.new_cells(name="own1", formula=lambda x: x)
    S2 = m.new_space("S2", bases=S1)

    before = snapshot_model(m)
    with pytest.raises(ValueError):
        S1.add_bases(B)
    assert snapshot_model(m) == before


@pytest.mark.xfail(
    strict=True,
    reason="add_bases does not detect member-name conflicts: the check in"
           " SpaceUpdater.add_bases is dead code, so a cells silently"
           " shadows an existing child space"
           " (CoreRefactorDesign.md problem 1; fixed in Phase 6)",
)
def test_add_bases_name_conflict_atomic():
    """add_bases with a cells/space name conflict must raise and leave
    the model unchanged.

    Currently it neither raises nor rolls back: the sub ends up with
    both a child space 'clash' and a derived cells 'clash'.
    """
    m = mx.new_model()
    base = m.new_space("base")
    base.new_cells(name="clash", formula=lambda: 1)
    sub = m.new_space("sub")
    sub.new_space("clash")

    before = snapshot_model(m)
    try:
        with pytest.raises((ValueError, NameError)):
            sub.add_bases(base)
        assert snapshot_model(m) == before
        m._impl._check_sanity()
    finally:
        m.close()
