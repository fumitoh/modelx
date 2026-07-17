"""Selective itemspace invalidation (Phase 7, CoreRefactorDesign §5.8).

An edit deletes an itemspace iff it dirties a UserSpace in the
itemspace's closure:

- a dynbase recorded from the itemspace's dynamic tree at creation,
- an MRO base of such a dynbase, or
- the nearest UserSpace ancestor of the itemspace's parent.

Everything else survives. Model-global ref edits conservatively delete
all itemspaces (nuke-all kept for v1).
"""

import modelx as mx
import pytest


# ----------------------------------------------------------------------------
# Itemspaces survive edits to unrelated spaces

@pytest.fixture
def nested_and_unrelated():
    """
        A[i]---B[j]     A's formula: {"refs": {"bar": foo}}; A.foo = 3
        |               B's formula: {"refs": {"baz": qux}}; B.qux = 5
        C---cc(x), r=1  unrelated space

    Creates A[1] and the nested A[1].B[1].
    """
    def param(i):
        return {"refs": {"bar": foo}}

    def param2(j):
        return {"refs": {"baz": qux}}

    m = mx.new_model()
    A = m.new_space("A", formula=param)
    B = A.new_space("B", formula=param2)
    A.foo = 3
    B.qux = 5

    C = m.new_space("C")
    C.new_cells(name="cc", formula=lambda x: x)
    C.r = 1

    a1 = A[1]
    b1 = a1.B[1]
    yield m, A, B, C, a1, b1
    m._impl._check_sanity()
    m.close()


def assert_alive(A, a1, b1):
    assert len(A._named_itemspaces) == 1
    assert a1._is_valid()
    assert b1._is_valid()
    assert len(a1.B._named_itemspaces) == 1


def test_survive_new_cells_in_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    C.new_cells(name="cc2", formula=lambda x: 2 * x)
    assert_alive(A, a1, b1)


def test_survive_ref_change_in_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    C.r = 2
    assert_alive(A, a1, b1)


def test_survive_del_cells_in_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    del C.cc
    assert_alive(A, a1, b1)


def test_survive_formula_change_in_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    C.cc.formula = lambda x: 3 * x
    assert_alive(A, a1, b1)


def test_survive_rename_of_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    C.rename("C2")
    assert_alive(A, a1, b1)


def test_survive_deletion_of_unrelated_space(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    del m.C
    assert_alive(A, a1, b1)


def test_survive_new_space_in_model(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated
    m.new_space("D")
    assert_alive(A, a1, b1)


def test_survive_new_base_pair_edit(nested_and_unrelated):
    """Inheritance activity between spaces outside the closure is
    irrelevant to live itemspaces."""
    m, A, B, C, a1, b1 = nested_and_unrelated
    S = m.new_space("S")
    T = m.new_space("T", bases=S)
    S.new_cells(name="sc", formula=lambda x: x)
    assert_alive(A, a1, b1)


# ----------------------------------------------------------------------------
# Itemspaces are cleared when their closure is dirtied

def test_cleared_on_dynbase_ref_change_via_dynbase_refs(nested_and_unrelated):
    """B's own refs are baked into A[1].B's ``_dynbase_refs`` at tree
    creation, so a rebind of B.qux invalidates A[1] wholesale."""
    m, A, B, C, a1, b1 = nested_and_unrelated

    B.qux = 4

    assert len(A._named_itemspaces) == 0    # checked before re-access
    assert not a1._is_valid()
    assert not b1._is_valid()
    assert A[1].B[1].baz == 4


def test_cleared_on_dynbase_ref_deletion(nested_and_unrelated):
    m, A, B, C, a1, b1 = nested_and_unrelated

    del B.qux

    assert len(A._named_itemspaces) == 0
    assert not a1._is_valid()
    assert not b1._is_valid()


def test_cleared_on_parent_ref_change(nested_and_unrelated):
    """A is the nearest UserSpace of its own itemspaces: an edit on A
    deletes them (the param formula evaluates in A's namespace)."""
    m, A, B, C, a1, b1 = nested_and_unrelated

    A.foo = 4

    assert len(A._named_itemspaces) == 0
    assert not a1._is_valid()
    assert A[1].bar == 4


@pytest.fixture
def base_of_dynbase():
    """
        S---scaled(x), mult=2
        T(bases=S)
        P[j]                    P's formula: {"base": bs}; P.bs = T

    P[1]'s tree records T; S is in the closure as T's MRO base.
    """
    m = mx.new_model()
    S = m.new_space("S")
    S.mult = 2
    S.new_cells(name="scaled", formula=lambda x: x * mult)
    T = m.new_space("T", bases=S)

    def param(j):
        return {"base": bs}

    P = m.new_space("P", formula=param)
    P.bs = T
    p1 = P[1]
    assert p1.scaled(3) == 6
    yield m, S, T, P, p1
    m._impl._check_sanity()
    m.close()


def test_cleared_on_new_cells_in_base_of_dynbase(base_of_dynbase):
    m, S, T, P, p1 = base_of_dynbase

    S.new_cells(name="sc2", formula=lambda x: x + 1)

    assert len(P._named_itemspaces) == 0
    assert not p1._is_valid()
    assert P[1].sc2(3) == 4


def test_cleared_on_ref_change_in_base_of_dynbase(base_of_dynbase):
    m, S, T, P, p1 = base_of_dynbase

    S.mult = 5

    assert len(P._named_itemspaces) == 0
    assert not p1._is_valid()
    assert P[1].scaled(3) == 15


def test_cleared_on_dynbase_deletion(base_of_dynbase):
    """Deleting a recorded dynbase invalidates the trees built on it
    (fixed in Phase 7: the stale tree used to survive)."""
    m, S, T, P, p1 = base_of_dynbase

    del m.T

    assert len(P._named_itemspaces) == 0
    assert not p1._is_valid()


def test_cleared_on_parent_edit_with_foreign_dynbase():
    """The parent-chain leg of the closure: an edit on the itemspace
    parent P deletes P's itemspaces even when their dynbase is another
    space that the edit does not touch."""
    m = mx.new_model()
    X = m.new_space("X")
    X.new_cells(name="foo", formula=lambda x: x)

    def param(j):
        return {"base": bs}

    P = m.new_space("P", formula=param)
    P.bs = X
    p1 = P[1]

    P.anyref = 7        # X untouched

    assert len(P._named_itemspaces) == 0
    assert not p1._is_valid()

    m._impl._check_sanity()
    m.close()


def test_cleared_on_parent_formula_change(nested_and_unrelated):
    """Changing the parameter formula itself deletes the itemspaces
    (direct ``del_formula`` path, unchanged by Phase 7)."""
    m, A, B, C, a1, b1 = nested_and_unrelated

    def param(i, j):
        return None

    A.formula = param

    assert len(A._named_itemspaces) == 0
    assert not a1._is_valid()


def test_global_ref_edit_keeps_nuke_all(nested_and_unrelated):
    """Model-global ref edits conservatively delete every itemspace,
    including nested ones referencing nothing global."""
    m, A, B, C, a1, b1 = nested_and_unrelated

    m.g = 42

    assert len(A._named_itemspaces) == 0
    assert not a1._is_valid()
    assert not b1._is_valid()


@pytest.fixture
def dynbase_of_nested_only():
    """
        Z---zc(x)
        A[i]---B[j]     A's formula: param -> None
                        B's formula: {"base": bs}; B.bs = Z

    Z is only in b1's closure, so reaching b1 requires recursing into
    a1's dynamic tree (a1.B is an in-tree ItemSpaceParent).
    """
    m = mx.new_model()
    Z = m.new_space("Z")
    Z.new_cells(name="zc", formula=lambda x: x)

    def param(i):
        return None

    A = m.new_space("A", formula=param)

    def param2(j):
        return {"base": bs}

    B = A.new_space("B", formula=param2)
    B.bs = Z

    a1 = A[1]
    b1 = a1.B[1]
    assert b1.zc(3) == 3
    yield m, Z, A, a1, b1
    m._impl._check_sanity()
    m.close()


def test_nested_itemspace_cleared_while_root_survives(dynbase_of_nested_only):
    """An edit to a dynbase used only by a nested itemspace clears that
    nested itemspace but spares the enclosing root itemspace."""
    m, Z, A, a1, b1 = dynbase_of_nested_only

    Z.new_cells(name="zc2", formula=lambda x: x + 1)

    assert a1._is_valid()
    assert len(A._named_itemspaces) == 1
    assert not b1._is_valid()
    assert a1.B[1].zc2(3) == 4


# ----------------------------------------------------------------------------
# Formula changes and renames keep their per-dynbase selectivity even
# for the edited space's own itemspaces built on foreign dynbases

@pytest.fixture
def foreign_dynbase_parent():
    """
        X---xc(x)
        P[j]---foo(x)   P's formula: {"base": xs}; P.xs = X

    P[1]'s tree records X only; P's own cells foo is not part of it.
    """
    m = mx.new_model()
    X = m.new_space("X")
    X.new_cells(name="xc", formula=lambda x: x)

    def param(j):
        return {"base": xs}

    P = m.new_space("P", formula=param)
    P.xs = X
    P.new_cells(name="foo", formula=lambda x: x)
    p1 = P[1]
    yield m, X, P, p1
    m._impl._check_sanity()
    m.close()


def test_survive_formula_change_on_parent_cells(foreign_dynbase_parent):
    """Changing a formula of the parent's own cells cannot affect its
    itemspaces built on a foreign dynbase — they survive."""
    m, X, P, p1 = foreign_dynbase_parent

    P.foo.formula = lambda x: x + 1

    assert p1._is_valid()
    assert len(P._named_itemspaces) == 1


def test_survive_rename_of_parent_cells(foreign_dynbase_parent):
    m, X, P, p1 = foreign_dynbase_parent

    P.foo.rename("bar")

    assert p1._is_valid()
    assert len(P._named_itemspaces) == 1


def test_cleared_on_formula_change_in_foreign_dynbase(foreign_dynbase_parent):
    """Control: the same edit family on the recorded dynbase clears."""
    m, X, P, p1 = foreign_dynbase_parent

    X.xc.formula = lambda x: x + 1

    assert not p1._is_valid()
    assert P[1].xc(3) == 4


# ----------------------------------------------------------------------------
# Cross-model dynbases: itemspaces of other models built on this
# model's spaces are invalidated through _dynamic_subs

@pytest.fixture
def cross_model_dynbase():
    """
        m2.G---foo(x), mult=2
        m1.P[j]     P's formula: {"base": gref}; P.gref = m2.G
    """
    m2 = mx.new_model("CrossBase")
    G = m2.new_space("G")
    G.mult = 2
    G.new_cells(name="foo", formula=lambda x: x * mult)

    m1 = mx.new_model("CrossUser")
    def param(j):
        return {"base": gref}

    P = m1.new_space("P", formula=param)
    P.gref = G
    p1 = P[1]
    assert p1.foo(3) == 6
    yield m1, m2, G, P, p1
    m1._impl._check_sanity()
    m2._impl._check_sanity()
    m1.close()
    m2.close()


def test_cross_model_cleared_on_new_cells(cross_model_dynbase):
    m1, m2, G, P, p1 = cross_model_dynbase

    G.new_cells(name="foo2", formula=lambda x: x + 1)

    assert not p1._is_valid()
    assert P[1].foo2(3) == 4


def test_cross_model_cleared_on_formula_change(cross_model_dynbase):
    m1, m2, G, P, p1 = cross_model_dynbase

    G.foo.formula = lambda x: x * mult + 1

    assert not p1._is_valid()
    assert P[1].foo(3) == 7


def test_cross_model_cleared_on_ref_change(cross_model_dynbase):
    m1, m2, G, P, p1 = cross_model_dynbase

    G.mult = 5

    assert not p1._is_valid()
    assert P[1].foo(3) == 15


def test_cross_model_survives_unrelated_edit(cross_model_dynbase):
    """An edit to an unrelated space of the base model spares the
    foreign itemspace."""
    m1, m2, G, P, p1 = cross_model_dynbase

    other = m2.new_space("Other")
    other.new_cells(name="oc", formula=lambda x: x)

    assert p1._is_valid()


# ----------------------------------------------------------------------------
# Mechanics

def test_tree_dynbases_recorded_at_creation(nested_and_unrelated):
    """The itemspace records the dynbase of each node of its tree."""
    m, A, B, C, a1, b1 = nested_and_unrelated

    assert set(a1._impl.tree_dynbases) == {A._impl, B._impl}
    assert set(b1._impl.tree_dynbases) == {B._impl}


def test_dynamic_cache_reuse_on_selective_deletion(base_of_dynbase):
    """Held interfaces are revived when the itemspace is re-created
    after a closure-based deletion."""
    m, S, T, P, p1 = base_of_dynbase

    S.mult = 5
    assert not p1._is_valid()

    p2 = P[1]
    assert p2 is p1
    assert p2._is_valid()
    assert p2.scaled(3) == 15
