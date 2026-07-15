"""Characterization tests for SpaceGraph.get_relative and refmode resolution.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
these tests freeze the current relative-reference resolution behavior
before the inheritance subsystem moves to modelx/core/inheritance/.
"""

import modelx as mx
import pytest


# ----------------------------------------------------------------------------
# SpaceGraph.get_relative resolution matrix (impl level)

@pytest.fixture
def shared_parent_model():
    """
        P---Base---C---D
        |
        +---Sub(Base)---C(Base.C)
    """
    m = mx.new_model()
    P = m.new_space("P")
    Base = P.new_space("Base")
    C = Base.new_space("C")
    C.new_space("D")
    Sub = P.new_space("Sub", bases=Base)
    Sub.new_space("C", bases=C)
    m.new_space("X")                # disjoint top-level tree
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "subspace, basespace, basevalue, expected",
    [
        # Resolution within the sub's own subtree
        ("P.Sub", "P.Base", "P.Base", "P.Sub"),
        ("P.Sub", "P.Base", "P.Base.C", "P.Sub.C"),
        ("P.Sub", "P.Base", "P.Base.C.D", "P.Sub.C.D"),
        # Nested sub resolving against its nested base
        ("P.Sub.C", "P.Base.C", "P.Base.C", "P.Sub.C"),
        ("P.Sub.C", "P.Base.C", "P.Base.C.D", "P.Sub.C.D"),
        # Target above the base but still within the inheritance scope:
        # resolution climbs to the sub-side counterpart
        ("P.Sub.C", "P.Base.C", "P.Base", "P.Sub"),
        # Target outside the shared scope: not relatively reachable
        ("P.Sub", "P.Base", "P", None),
        # Target in a tree disjoint from the base: the early
        # no-shared-parent exit (distinct from the final None branch)
        ("P.Sub", "P.Base", "X", None),
    ],
)
def test_get_relative_shared_parent(
        shared_parent_model, subspace, basespace, basevalue, expected):
    graph = shared_parent_model._impl.spmgr._graph
    assert graph.get_relative(subspace, basespace, basevalue) == expected


@pytest.fixture
def sibling_bases_model():
    """
        A---B---C---foo
        |
        +---D---C(A.B.C)    D.add_bases(A.B) after D.C is created
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    C.new_cells(name="foo", formula=lambda x: x)
    D = A.new_space("D")
    D.new_space("C", bases=C)
    D.add_bases(B)
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "subspace, basespace, basevalue, expected",
    [
        # Sub and base sharing the parent A; resolution into child members
        ("A.D", "A.B", "A.B.C", "A.D.C"),
        ("A.D", "A.B", "A.B.C.foo", "A.D.C.foo"),
        ("A.D.C", "A.B.C", "A.B.C.foo", "A.D.C.foo"),
        # Target above the base within the shared scope
        ("A.D.C", "A.B.C", "A.B", "A.D"),
        # Shared ancestor itself is out of relative scope
        ("A.D.C", "A.B.C", "A", None),
    ],
)
def test_get_relative_sibling_bases(
        sibling_bases_model, subspace, basespace, basevalue, expected):
    graph = sibling_bases_model._impl.spmgr._graph
    assert graph.get_relative(subspace, basespace, basevalue) == expected


@pytest.fixture
def child_only_bases_model():
    """
        A---B---C---foo
        |
        +---D---C(A.B.C)    D itself NOT based on B

    Resolution from A.D.C against A.B.C cannot succeed at the parent
    level (A.B is not in A.D's MRO), so ``get_relative`` must take its
    climb loop (model.py:1549-1559), descending the shared right part
    one level to find A.B.C in A.D.C's MRO.
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    C.new_cells(name="foo", formula=lambda x: x)
    D = A.new_space("D")
    D.new_space("C", bases=C)
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize(
    "subspace, basespace, basevalue, expected",
    [
        ("A.D.C", "A.B.C", "A.B.C", "A.D.C"),
        ("A.D.C", "A.B.C", "A.B.C.foo", "A.D.C.foo"),
        # climbing above the base is out of scope when only the
        # children are in a bases relation
        ("A.D.C", "A.B.C", "A.B", None),
    ],
)
def test_get_relative_child_only_bases(
        child_only_bases_model, subspace, basespace, basevalue, expected):
    graph = child_only_bases_model._impl.spmgr._graph
    assert graph.get_relative(subspace, basespace, basevalue) == expected


# ----------------------------------------------------------------------------
# Refmode resolution matrix (interface level)

def make_base_with_ref(refmode):
    """
        A---B---foo         B.bar --> B.foo (refmode)
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    B.new_cells(name="foo", formula=lambda x: x)
    B.set_ref("bar", B.foo, refmode)
    return m, A, B


@pytest.mark.parametrize("refmode", ["relative", "auto"])
def test_sibling_cells_resolves_relative(refmode):
    """Ref to a sibling cells rebinds to the sub's derived cells."""
    m, A, B = make_base_with_ref(refmode)
    D = m.new_space("D", bases=B)
    assert D.bar is D.foo
    assert D.bar is not B.foo
    m._impl._check_sanity()
    m.close()


def test_sibling_cells_absolute_keeps_base_object(refmode="absolute"):
    """An absolute ref keeps pointing at the base's cells in subs."""
    m, A, B = make_base_with_ref(refmode)
    D = m.new_space("D", bases=B)
    assert D.bar is B.foo
    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize("refmode", ["absolute", "auto"])
def test_out_of_scope_target_falls_back_to_absolute(refmode):
    """Ref to the base's parent: 'auto' falls back to the base object."""
    m, A, B = make_base_with_ref("auto")
    B.set_ref("above", A, refmode)
    D = m.new_space("D", bases=B)
    assert D.above is A
    m._impl._check_sanity()
    m.close()


def test_out_of_scope_relative_raises_on_new_space():
    """Ref with refmode 'relative' to an out-of-scope target:
    deriving a sub raises ValueError."""
    m, A, B = make_base_with_ref("auto")
    B.set_ref("above", A, "relative")
    with pytest.raises(ValueError):
        m.new_space("D", bases=B)
    m._impl._check_sanity()
    m.close()


def test_out_of_scope_relative_raises_on_set_ref():
    """Creating a relative ref on a base whose existing sub cannot
    resolve it raises ValueError (SpaceManager._check_subs_relrefs)."""
    m, A, B = make_base_with_ref("auto")
    m.new_space("D", bases=B)
    with pytest.raises(ValueError):
        B.set_ref("above", A, "relative")
    m._impl._check_sanity()
    m.close()


def test_child_space_member_resolves_relative():
    """Ref into a child space's cells resolves to the sub-side tree
    when the sub has a matching derived child."""
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    C.new_cells(name="foo", formula=lambda x: x)
    B.set_ref("cfoo", C.foo, "relative")

    D = A.new_space("D")
    D.new_space("C", bases=C)
    D.add_bases(B)

    assert D.cfoo is D.C.foo
    assert D.cfoo is not B.C.foo
    m._impl._check_sanity()
    m.close()


def test_ref_in_child_only_sub_resolves_via_climb():
    """A relative ref carried by a child space derived on its own
    (parents not in a bases relation) binds to the sub-side member."""
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    C.new_cells(name="foo", formula=lambda x: x)
    C.set_ref("cfoo", C.foo, "relative")

    D = A.new_space("D")
    DC = D.new_space("C", bases=C)

    assert DC.cfoo is DC.foo
    assert DC.cfoo is not C.foo
    m._impl._check_sanity()
    m.close()


def test_disjoint_target_auto_falls_back_absolute():
    """An 'auto' ref to a member of a disjoint tree keeps pointing at
    the base-side object in subs (no shared ancestor, so no relative
    resolution)."""
    m, A, B = make_base_with_ref("auto")
    X = m.new_space("X")
    X.new_cells(name="xfoo", formula=lambda x: x)
    B.set_ref("far", X.xfoo, "auto")

    D = m.new_space("D", bases=B)

    assert D.far is X.xfoo
    m._impl._check_sanity()
    m.close()


def test_disjoint_target_relative_raises():
    """A 'relative' ref to a member of a disjoint tree cannot resolve
    in a sub: deriving one raises ValueError."""
    m, A, B = make_base_with_ref("auto")
    X = m.new_space("X")
    X.new_cells(name="xfoo", formula=lambda x: x)
    B.set_ref("far", X.xfoo, "relative")

    with pytest.raises(ValueError):
        m.new_space("D", bases=B)
    m._impl._check_sanity()
    m.close()


def test_space_valued_ref_resolves_relative():
    """A relative ref whose value is a child space rebinds to the
    sub-side counterpart space."""
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    C.new_cells(name="foo", formula=lambda x: x)
    B.set_ref("csp", C, "relative")

    D = A.new_space("D")
    D.new_space("C", bases=C)
    D.add_bases(B)

    assert D.csp is D.C
    assert D.csp is not B.C
    m._impl._check_sanity()
    m.close()


def test_space_valued_ref_missing_counterpart_binds_null():
    """A relative ref resolving to an idstr with no impl silently binds
    a null-impl interface instead of raising.

    Current behavior of ``get_relative_interface`` (model.py:1698-1703):
    ``get_relative`` succeeds path-wise, ``get_impl_from_name`` finds
    nothing, and the derived ref gets ``interface_cls(null_impl)``.
    Frozen here so the pipeline phases reproduce or consciously change
    it (with this test updated in the same commit).
    """
    m = mx.new_model()
    A = m.new_space("A")
    B = A.new_space("B")
    C = B.new_space("C")
    B.set_ref("csp", C, "relative")

    D = A.new_space("D")    # no D.C counterpart
    D.add_bases(B)          # does not raise

    assert not D.csp._is_valid()
    m._impl._check_sanity()
    m.close()


def test_refmode_reported_by_proxy():
    """ReferenceProxy reports the refmode of derived refs."""
    m, A, B = make_base_with_ref("relative")
    D = m.new_space("D", bases=B)
    base_proxy = mx.get_object(B.fullname + ".bar", as_proxy=True)
    sub_proxy = mx.get_object(D.fullname + ".bar", as_proxy=True)
    assert base_proxy.refmode == "relative"
    assert sub_proxy.refmode == "relative"
    assert sub_proxy.is_derived()
    m._impl._check_sanity()
    m.close()
