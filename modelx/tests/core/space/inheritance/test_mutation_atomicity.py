"""Characterization tests for failed-mutation atomicity.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
a mutation that raises must leave the model bit-identical to its state
before the edit.

The ``add_bases`` cases were marked ``xfail(strict=True)`` until the
graph mutations moved into the transactional edit pipeline (Phase 6),
which rolls back both the component dicts and the inheritance graph on
failure.
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


def test_add_bases_name_conflict_atomic():
    """add_bases with a cells/space name conflict must raise and leave
    the model unchanged.

    Without the check the sub would end up with both a child space
    'clash' and a derived cells 'clash' silently shadowing it.
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


def test_add_bases_no_conflict_with_base_child_space():
    """A base's child-space name may equal a sub's cells name.

    Child spaces are not inherited into subs, so no namespace collision
    arises. The conflict check must not fire here: deserialization
    replays bases via add_bases, so rejecting this shape would make
    legitimately saved models unloadable.
    """
    m = mx.new_model()
    base = m.new_space("base")
    base.new_space("x")
    base.new_cells(name="foo", formula=lambda: 1)
    sub = m.new_space("sub")
    sub.new_cells(name="x", formula=lambda: 2)

    try:
        sub.add_bases(base)
        assert sub.foo() == 1
        assert sub.x() == 2
        assert not sub.spaces
        m._impl._check_sanity()
    finally:
        m.close()
