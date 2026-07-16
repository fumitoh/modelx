"""Characterization tests for notification propagation on ref changes.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
these tests guard the observable effect of the per-mutation
``on_notify`` fan-out — cells values computed in subs are invalidated
and recalculated after a ref changes in a base — before notification
is batched in the pipeline (Phase 4).
"""

import modelx as mx
import pytest


@pytest.fixture
def inheritance_chain():
    """
        Base---foo(x) = x * mult,  mult = 2
          ^
        Mid(Base)
          ^
        Leaf(Mid)
    """
    m = mx.new_model()
    Base = m.new_space("Base")
    Base.new_cells(name="foo", formula=lambda x: x * mult)
    Base.mult = 2
    Mid = m.new_space("Mid", bases=Base)
    Leaf = m.new_space("Leaf", bases=Mid)
    yield m, Base, Mid, Leaf
    m._impl._check_sanity()
    m.close()


def test_recalc_all_subs_on_base_ref_change(inheritance_chain):
    """A ref change in the base invalidates values already computed in
    every sub down the chain."""
    m, Base, Mid, Leaf = inheritance_chain

    # Compute and cache values in all three spaces
    assert Base.foo(3) == 6
    assert Mid.foo(3) == 6
    assert Leaf.foo(3) == 6

    Base.mult = 10

    # The caches were actually invalidated (not recomputed lazily on
    # value comparison)
    assert (3,) not in Base.foo._impl.data
    assert (3,) not in Mid.foo._impl.data
    assert (3,) not in Leaf.foo._impl.data

    assert Base.foo(3) == 30
    assert Mid.foo(3) == 30
    assert Leaf.foo(3) == 30


def test_recalc_stops_at_overriding_sub(inheritance_chain):
    """A sub that overrides the ref is not affected by the base change,
    and neither are its own subs."""
    m, Base, Mid, Leaf = inheritance_chain

    Mid.mult = 3                    # override in the middle of the chain
    assert Base.foo(3) == 6
    assert Mid.foo(3) == 9
    assert Leaf.foo(3) == 9

    Base.mult = 10

    # The shielded subs' caches SURVIVE the base edit (no
    # over-invalidation): asserting only the recomputed values could
    # not distinguish shielding from clear-everything-and-recompute.
    assert (3,) not in Base.foo._impl.data
    assert Mid.foo._impl.data.get((3,)) == 9
    assert Leaf.foo._impl.data.get((3,)) == 9

    assert Base.foo(3) == 30
    assert Mid.foo(3) == 9          # shielded by the override
    assert Leaf.foo(3) == 9


def test_recalc_on_apex_ref_delete():
    """Deleting the ref on the apex propagates down the whole chain
    (the derived refs are removed and the global fallback takes over)."""
    m = mx.new_model()
    m.mult = 1                      # global fallback
    Base = m.new_space("Base")
    Base.new_cells(name="foo", formula=lambda x: x * mult)
    Base.mult = 2
    Mid = m.new_space("Mid", bases=Base)
    Leaf = m.new_space("Leaf", bases=Mid)

    assert (Base.foo(3), Mid.foo(3), Leaf.foo(3)) == (6, 6, 6)

    del Base.mult

    assert (Base.foo(3), Mid.foo(3), Leaf.foo(3)) == (3, 3, 3)
    m._impl._check_sanity()
    m.close()


def test_recalc_on_override_delete_direct(inheritance_chain):
    """Deleting an overriding ref re-exposes the base value in the
    space that held the override."""
    m, Base, Mid, Leaf = inheritance_chain

    Mid.mult = 3
    assert Mid.foo(3) == 9

    del Mid.mult

    assert Mid.foo(3) == 6


def test_recalc_on_override_delete_deeper_sub(inheritance_chain):
    """Deleting an overriding ref must also re-expose the base value in
    subs further down the chain.

    Was xfail(strict=True) before Phase 4: the pre-pipeline
    ``UserSpaceImpl.on_inherit`` rewrote sub containers without
    ``on_notify``, so Leaf's ``own_refs['mult']`` was re-derived to 2
    but Leaf.foo kept evaluating with the stale namespace binding (3).
    The pipeline's batched notify (CoreRefactorDesign.md §5.4) marks
    rebound refs' containers dirty and invalidates their namespaces.
    """
    m, Base, Mid, Leaf = inheritance_chain

    Mid.mult = 3
    assert Leaf.foo(3) == 9

    del Mid.mult

    assert Leaf._impl.own_refs["mult"].interface == 2   # ref re-derived
    assert Leaf.foo(3) == 6


def test_recalc_on_global_ref_change():
    """Changing a model-global ref invalidates dependent cells values
    in all spaces reading it."""
    m = mx.new_model()
    m.gmult = 2
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x * gmult)
    B = m.new_space("B", bases=A)

    assert A.foo(3) == 6
    assert B.foo(3) == 6

    m.gmult = 10

    assert A.foo(3) == 30
    assert B.foo(3) == 30

    m._impl._check_sanity()
    m.close()


def test_derived_ref_object_replaced_on_change(inheritance_chain):
    """Changing a base ref replaces the derived ReferenceImpl objects in
    subs (they are re-created, not mutated in place)."""
    m, Base, Mid, Leaf = inheritance_chain

    mid_ref_before = Mid._impl.own_refs["mult"]
    assert mid_ref_before.is_derived()

    Base.mult = 10

    mid_ref_after = Mid._impl.own_refs["mult"]
    assert mid_ref_after is not mid_ref_before
    assert mid_ref_after.is_derived()
    assert mid_ref_after.interface == 10
