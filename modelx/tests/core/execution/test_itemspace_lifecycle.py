"""Characterization tests for the ItemSpace lifecycle.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
freezes how itemspaces are created and deleted through the trace graph
(``clear_with_descs`` -> ``on_clear_trace`` -> ``_del_itemspace``),
how ``dynamic_cache`` reuses interface objects, and which edits trigger
``clear_subs_rootitems`` — before the invalidation policy moves to
``ItemSpaceManager`` (Phases 4 and 7).
"""

import modelx as mx
import pytest


@pytest.fixture
def param_depends_on_cells():
    """
        A[i]---foo(i)       A's formula: {"refs": {"bar": foo(i)}}

    Each itemspace's creation evaluates ``foo(i)``, so the itemspace
    node depends on the ``foo(i)`` node in the trace graph.
    """
    m = mx.new_model()
    A = m.new_space("A")
    foo = A.new_cells(name="foo", formula=lambda i: i * 2)

    def param(i):
        return {"refs": {"bar": foo(i)}}

    A.formula = param
    yield m, A
    m._impl._check_sanity()
    m.close()


def test_itemspace_deleted_via_trace_clearing(param_depends_on_cells):
    """Clearing a cells the itemspace depends on deletes the itemspace."""
    m, A = param_depends_on_cells

    s1 = A[1]
    assert s1.bar == 2
    assert len(A._named_itemspaces) == 1

    A.foo.clear()

    assert len(A._named_itemspaces) == 0
    assert not s1._is_valid()


def test_itemspace_node_in_tracegraph(param_depends_on_cells):
    """The itemspace is represented in the trace graph as a node keyed
    (parent_impl, args) depending on the cells node it evaluated."""
    m, A = param_depends_on_cells

    A[1]
    tracegraph = m._impl.tracegraph
    itemspace_node = (A._impl, (1,))
    cells_node = (A.foo._impl, (1,))
    assert itemspace_node in tracegraph
    assert (cells_node, itemspace_node) in tracegraph.edges


def test_itemspace_deletion_clears_dependents(param_depends_on_cells):
    """Deleting an itemspace invalidates values computed inside it and
    the objects hanging off it."""
    m, A = param_depends_on_cells

    s1 = A[1]
    s1foo = s1.foo      # derived cells inside the itemspace
    assert s1foo(5) == 10

    del A[1]

    assert len(A._named_itemspaces) == 0
    assert not s1._is_valid()
    assert not s1foo._is_valid()


def test_dynamic_cache_reuses_held_interface():
    """While the user holds an itemspace interface, re-creating the same
    itemspace after deletion reuses the identical interface object."""
    m = mx.new_model()
    A = m.new_space("A", formula=lambda i: None)
    A.new_cells(name="foo", formula=lambda x: x)

    s1 = A[1]
    A.clear_items()
    assert not s1._is_valid()

    s2 = A[1]
    assert s2 is s1                 # same interface object, revived
    assert s2._is_valid()
    assert s2.foo(3) == 3

    m._impl._check_sanity()
    m.close()


def test_dynamic_cache_reuse_after_trace_clearing(param_depends_on_cells):
    """Interface reuse also applies when deletion flows through the
    trace graph rather than an explicit clear."""
    m, A = param_depends_on_cells

    s1 = A[1]
    A.foo.clear()       # deletes A[1] via clear_with_descs
    assert not s1._is_valid()

    s2 = A[1]
    assert s2 is s1
    assert s2._is_valid()               # rebound to the new impl
    assert s2.bar == 2                  # and usable
    assert s2.foo(5) == 10


def test_dynamic_cache_reuses_nested_interfaces():
    """Interfaces of spaces nested under an itemspace are also revived."""
    m = mx.new_model()
    A = m.new_space("A", formula=lambda i: None)
    Child = A.new_space("Child")
    Child.new_cells(name="bar", formula=lambda x: x)

    c1 = A[1].Child
    A.clear_items()
    assert not c1._is_valid()

    c2 = A[1].Child
    assert c2 is c1
    assert c2.bar(4) == 4

    m._impl._check_sanity()
    m.close()


# ----------------------------------------------------------------------------
# clear_subs_rootitems triggers: edits on a dynbase clear the root
# itemspaces of its dynamic subs

@pytest.fixture
def dynbase_model():
    """
        Base---foo(x)
        P[j]                P's formula: {"base": bs}; P.bs = Base

    P[j] is an itemspace whose dynamic tree uses Base as dynbase.
    """
    m = mx.new_model()
    Base = m.new_space("Base")
    Base.new_cells(name="foo", formula=lambda x: x)

    def param(j):
        return {"base": bs}

    P = m.new_space("P", formula=param)
    P.bs = Base
    yield m, Base, P
    m._impl._check_sanity()
    m.close()


def test_rootitems_cleared_on_formula_change(dynbase_model):
    """Changing a cells formula on the dynbase deletes dependent
    itemspaces, and re-created ones see the new formula."""
    m, Base, P = dynbase_model

    item = P[1]
    assert item.foo(3) == 3

    Base.foo.formula = lambda x: x + 1

    assert len(P._named_itemspaces) == 0
    assert not item._is_valid()
    assert P[1].foo(3) == 4


def test_rootitems_cleared_on_new_cells(dynbase_model):
    """Creating a new cells on the dynbase deletes dependent itemspaces."""
    m, Base, P = dynbase_model

    item = P[1]
    assert item.foo(3) == 3

    Base.new_cells(name="baz", formula=lambda x: x * 10)

    assert len(P._named_itemspaces) == 0
    assert not item._is_valid()
    assert P[1].baz(3) == 30


def test_rootitems_cleared_on_ref_change_in_dynbase(dynbase_model):
    """Changing a ref on the dynbase deletes dependent itemspaces and
    re-created ones see the new value."""
    m, Base, P = dynbase_model

    Base.mult = 2
    Base.new_cells(name="scaled", formula=lambda x: x * mult)

    item = P[1]
    assert item.scaled(3) == 6

    Base.mult = 5

    assert len(P._named_itemspaces) == 0
    assert not item._is_valid()
    assert P[1].scaled(3) == 15


# ----------------------------------------------------------------------------
# Invalidation granularity: the current policy is nuke-at-parent for
# namespace changes (``DynamicBase.on_notify`` calls
# ``r.parent.del_all_itemspaces()``, space.py:2140-2145) but selective
# per dynbase for formula changes (``clear_subs_rootitems``,
# space.py:2153-2156).  Phase 4 must lift this policy verbatim; Phase 7
# replaces it with closure-based selective invalidation.  These tests
# pin the granularity so the two policies are distinguishable.

@pytest.fixture
def two_dynbase_model():
    """
        Bs1---foo(x)    P[1] built on Bs1 (P's formula picks by arg)
        Bs2---foo(x)    P[2] built on Bs2
        Bs3---foo(x)    Q[1] built on Bs3 (unrelated parent)
    """
    m = mx.new_model()

    spaces = []
    for name in ("Bs1", "Bs2", "Bs3"):
        s = m.new_space(name)
        s.mult = 2
        s.new_cells(name="foo", formula=lambda x: x * mult)
        spaces.append(s)
    Bs1, Bs2, Bs3 = spaces

    def pparam(j):
        return {"base": bs1 if j == 1 else bs2}

    P = m.new_space("P", formula=pparam)
    P.bs1 = Bs1
    P.bs2 = Bs2

    def qparam(k):
        return {"base": bs3}

    Q = m.new_space("Q", formula=qparam)
    Q.bs3 = Bs3

    yield m, Bs1, Bs2, Bs3, P, Q
    m._impl._check_sanity()
    m.close()


def test_new_cells_on_dynbase_nukes_at_parent(two_dynbase_model):
    """new_cells on one dynbase deletes ALL itemspaces of the parents
    using that dynbase -- including items built on other dynbases --
    while itemspaces of unrelated parents survive."""
    m, Bs1, Bs2, Bs3, P, Q = two_dynbase_model
    p1, p2, q1 = P[1], P[2], Q[1]

    Bs1.new_cells(name="baz", formula=lambda x: x)

    assert len(P._named_itemspaces) == 0    # P[2] deleted too
    assert not p1._is_valid()
    assert not p2._is_valid()
    assert len(Q._named_itemspaces) == 1    # unrelated parent untouched
    assert q1._is_valid()


def test_ref_change_on_dynbase_nukes_at_parent(two_dynbase_model):
    """A ref change on one dynbase likewise deletes all itemspaces of
    the affected parent, not only those built on that dynbase."""
    m, Bs1, Bs2, Bs3, P, Q = two_dynbase_model
    p1, p2, q1 = P[1], P[2], Q[1]

    Bs1.mult = 5

    assert len(P._named_itemspaces) == 0    # P[2] deleted too
    assert not p1._is_valid()
    assert not p2._is_valid()
    assert q1._is_valid()
    assert P[1].foo(3) == 15
    assert P[2].foo(3) == 6                 # Bs2.mult unchanged


def test_formula_change_on_dynbase_clears_selectively(two_dynbase_model):
    """A cells formula change flows through ``clear_subs_rootitems``,
    which is selective: only itemspaces whose dynamic tree uses the
    changed dynbase are deleted."""
    m, Bs1, Bs2, Bs3, P, Q = two_dynbase_model
    p1, p2, q1 = P[1], P[2], Q[1]

    Bs1.foo.formula = lambda x: x * mult + 1

    assert not p1._is_valid()
    assert p2._is_valid()                   # built on Bs2: survives
    assert q1._is_valid()
    assert P[1].foo(3) == 7
    assert P[2].foo(3) == 6
