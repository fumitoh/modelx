"""``_direct_bases`` of every kind of Space, and the inheritance graph's
preds of a name that is not a node.

devnotes/ToolAPIDesign.md, section 3.3, F6.

``_direct_bases`` lists the Spaces given as the bases of a Space, in the
order they were added; ``bases`` is the method resolution order.  An
ItemSpace or a DynamicSpace has one base, the UserSpace whose members it
has, and ``bases`` lists it.  From 0.34 ``_direct_bases`` lists the same.

On 0.33 ``_direct_bases`` read the inheritance graph's preds of the
Space's ``_idstr``.  The idstr of a dynamic Space, such as
``'P.__Space1'``, is not a node of the graph, and networkx took the str
for a bunch of nodes, its characters.  So a dynamic Space listed the
bases of every Space named by one character of its idstr.  On the model
below, every dynamic Space under ``P`` listed ``Base1``, ``B`` and
``Base2``, the bases of ``P`` and ``S``; ``P3[1]``, whose Space has no
bases, listed the same; and ``Q[1]``, whose base is ``Base2``, and
``Sub[1]`` listed ``B``.  ``SpaceGraph.ordered_preds`` now returns
``[]`` for a name that is not a node.

The tests of ``_direct_bases`` read only the tool API and the public
API.  The tests of ``SpaceGraph`` build a graph of their own, with no
model.  Each model is torn down by ``_impl._check_sanity()`` and then
``close()``.
"""

import pytest

import modelx as mx
from modelx.core.inheritance.graph import SpaceGraph
from modelx.tests.core.base.test_kind import kind

DYNAMIC = frozenset({"ItemSpace", "DynamicSpace"})


@pytest.fixture
def bases_model():
    """
        DirectBases---Base0
                  |---Base1(Base0)----h()
                  |---Base2
                  |---B---------------h(), r
                  |---S(B)
                  |---P(i)(Base1, Base2)
                  |     +--Child(j)
                  |     |    +--GC
                  |     +--Child2(Base2)
                  |---P3(i)
                  |---Q(i)             formula returns base Base2
                  +---Sub(i)(P)

    ``S`` is named by a character of every dynamic idstr under ``P``,
    such as ``'P.__Space1'``, and so is ``P``.

    Formulas are source text: from a lambda, modelx parses the whole of
    this file for each one.
    """
    m = mx.new_model("DirectBases")
    base0 = m.new_space("Base0")
    base1 = m.new_space("Base1", bases=base0)
    base1.new_cells("h", formula="lambda: 1")
    base2 = m.new_space("Base2")
    b = m.new_space("B")
    b.new_cells("h", formula="lambda: 2")
    b.r = 1
    m.new_space("S", bases=b)
    p = m.new_space("P", bases=[base1, base2], formula="lambda i: None")
    child = p.new_space("Child", formula="lambda j: None")
    child.new_space("GC")
    p.new_space("Child2", bases=base2)
    m.new_space("P3", formula="lambda i: None")
    m.new_space("Q", formula="lambda i: {'base': _model.Base2}")
    m.new_space("Sub", bases=p, formula="lambda i: None")

    yield m
    m._impl._check_sanity()
    m.close()


def assert_spaces(actual, expected):
    """``actual`` is a list holding the Spaces ``expected`` holds, in the
    same order, by identity."""
    assert isinstance(actual, list)
    assert [s._evalrepr for s in actual] == [s._evalrepr for s in expected]
    assert all(a is e for a, e in zip(actual, expected))


# --------------------------------------------------------------------------
# UserSpaces: unchanged

USERSPACES = {
    # label: (getter, getter of the expected _direct_bases)
    "Base0": (lambda m: m.Base0, lambda m: []),
    "Base1(Base0)": (lambda m: m.Base1, lambda m: [m.Base0]),
    "B": (lambda m: m.B, lambda m: []),
    "S(B)": (lambda m: m.S, lambda m: [m.B]),
    "P(Base1, Base2)": (lambda m: m.P, lambda m: [m.Base1, m.Base2]),
    "P.Child": (lambda m: m.P.Child, lambda m: []),
    "P.Child.GC": (lambda m: m.P.Child.GC, lambda m: []),
    "P.Child2(Base2)": (lambda m: m.P.Child2, lambda m: [m.Base2]),
    "P3": (lambda m: m.P3, lambda m: []),
    "Sub(P)": (lambda m: m.Sub, lambda m: [m.P]),
}


@pytest.mark.parametrize("label", list(USERSPACES))
def test_userspace_direct_bases(bases_model, label):
    """A UserSpace lists the bases it was given, in order, as on 0.33."""
    get, expected = USERSPACES[label]
    space = get(bases_model)
    assert kind(space) == "UserSpace"
    assert_spaces(space._direct_bases, expected(bases_model))


def test_direct_bases_are_not_the_mro(bases_model):
    """``bases`` is the method resolution order, and ``_direct_bases``
    only the Spaces given as bases."""
    m = bases_model
    assert_spaces(m.P._direct_bases, [m.Base1, m.Base2])
    assert_spaces(m.P.bases, [m.Base1, m.Base0, m.Base2])
    assert_spaces(m.Sub._direct_bases, [m.P])
    assert_spaces(m.Sub.bases, [m.P, m.Base1, m.Base0, m.Base2])


# --------------------------------------------------------------------------
# ItemSpaces and DynamicSpaces: [the UserSpace whose members they have]

DYNAMIC_SPACES = {
    # label: (getter, kind, getter of the expected _direct_bases)
    "P[1]": (lambda m: m.P[1], "ItemSpace", lambda m: [m.P]),
    "P[1].Child": (
        lambda m: m.P[1].Child, "DynamicSpace", lambda m: [m.P.Child]),
    "P[1].Child.GC": (
        lambda m: m.P[1].Child.GC, "DynamicSpace",
        lambda m: [m.P.Child.GC]),
    "P[1].Child2": (
        lambda m: m.P[1].Child2, "DynamicSpace", lambda m: [m.P.Child2]),
    "P[1].Child[2]": (
        lambda m: m.P[1].Child[2], "ItemSpace", lambda m: [m.P.Child]),
    "P[1].Child[2].GC": (
        lambda m: m.P[1].Child[2].GC, "DynamicSpace",
        lambda m: [m.P.Child.GC]),
    "P[1][5]": (lambda m: m.P[1][5], "ItemSpace", lambda m: [m.P]),
    "P[1][5].Child": (
        lambda m: m.P[1][5].Child, "DynamicSpace", lambda m: [m.P.Child]),
    "P3[1]": (lambda m: m.P3[1], "ItemSpace", lambda m: [m.P3]),
    "Q[1]": (lambda m: m.Q[1], "ItemSpace", lambda m: [m.Base2]),
    "Sub[1]": (lambda m: m.Sub[1], "ItemSpace", lambda m: [m.Sub]),
}


@pytest.mark.parametrize("label", list(DYNAMIC_SPACES))
def test_dynamic_direct_bases(bases_model, label):
    """An ItemSpace or a DynamicSpace lists its one base, as ``bases``
    does: the Space it is an item of, the Space's child it stands for,
    or the base its Space formula chose (``Q[1]``).  On 0.33 the
    Spaces under ``P`` and ``P3[1]`` listed ``Base1``, ``B`` and
    ``Base2``, and ``Q[1]`` and ``Sub[1]`` listed ``B``."""
    get, expected_kind, expected = DYNAMIC_SPACES[label]
    space = get(bases_model)
    assert kind(space) == expected_kind
    assert_spaces(space._direct_bases, expected(bases_model))
    assert_spaces(space.bases, expected(bases_model))


def iter_spaces(parent):
    """Every Space under ``parent``, ItemSpaces of ItemSpaces included,
    through ``spaces`` and ``_named_itemspaces``."""
    for space in parent.spaces.values():
        yield space
        yield from iter_spaces(space)
    if kind(parent) != "Model":
        for item in parent._named_itemspaces.values():
            yield item
            yield from iter_spaces(item)


def test_every_dynamic_space_lists_its_bases(bases_model):
    """Over every Space of the model, an ItemSpace or a DynamicSpace
    lists in ``_direct_bases`` the one UserSpace ``bases`` lists.

    So spymx's kernel, which adds the ``_idstr`` of each of
    ``_direct_bases`` to a Space's record and reads ``bases`` instead
    for a dynamic Space on 0.33 (design C3), gets the same list either
    way from 0.34.
    """
    m = bases_model
    for get, _, _ in DYNAMIC_SPACES.values():
        get(m)

    dynamic = []
    for space in iter_spaces(m):
        direct = space._direct_bases
        if kind(space) in DYNAMIC:
            dynamic.append(space._evalrepr)
            assert len(direct) == 1
            assert kind(direct[0]) == "UserSpace"
            assert_spaces(direct, space.bases)
        else:
            assert kind(space) == "UserSpace"
        assert ([s._idstr for s in direct]
                == [s._idstr for s in (
                    space.bases if kind(space) in DYNAMIC
                    else space._direct_bases)])

    # The 11 Spaces of the table, and P[1][5].Child.GC and P[1][5].Child2,
    # which modelx made with P[1][5].Child.
    assert sorted(dynamic) == sorted([
        "DirectBases.P(1)", "DirectBases.P(1).Child",
        "DirectBases.P(1).Child.GC", "DirectBases.P(1).Child2",
        "DirectBases.P(1).Child(2)", "DirectBases.P(1).Child(2).GC",
        "DirectBases.P(1)(5)", "DirectBases.P(1)(5).Child",
        "DirectBases.P(1)(5).Child.GC", "DirectBases.P(1)(5).Child2",
        "DirectBases.P3(1)", "DirectBases.Q(1)", "DirectBases.Sub(1)"])


def test_child_of_item_does_not_name_bases_of_parent():
    """The case toolapi.rst gave as a known limitation on 0.33: for a
    Space ``P`` with the bases ``Base1`` and ``Base2`` and a child Space
    ``Child``, ``P[1].Child._direct_bases`` named ``Base1`` and
    ``Base2``, and so did ``P[1]._direct_bases``."""
    m = mx.new_model("DirectBasesChild")
    base1 = m.new_space("Base1")
    base2 = m.new_space("Base2")
    p = m.new_space("P", bases=[base1, base2], formula="lambda i: None")
    p.new_space("Child")

    assert_spaces(p[1].Child._direct_bases, [p.Child])
    assert_spaces(p[1]._direct_bases, [p])
    assert_spaces(p._direct_bases, [base1, base2])
    assert_spaces(p.Child._direct_bases, [])

    m._impl._check_sanity()
    m.close()


def test_item_does_not_name_bases_of_one_letter_space():
    """The case found while implementing PR 1 (design section 9): on
    0.33, ``P3[1]._direct_bases`` was ``[B]``, the base of ``S``, a
    Space named by a character of the idstr ``'P3.__Space1'``."""
    m = mx.new_model("DirectBasesLetter")
    b = m.new_space("B")
    m.new_space("S", bases=b)
    p3 = m.new_space("P3", formula="lambda i: None")

    assert_spaces(p3[1]._direct_bases, [p3])
    assert_spaces(p3._direct_bases, [])

    m._impl._check_sanity()
    m.close()


@pytest.mark.parametrize("label", ["P(Base1, Base2)", "P[1].Child"])
def test_direct_bases_is_a_new_list(bases_model, label):
    """Changing the list returned changes neither the Space nor the next
    list returned."""
    m = bases_model
    get = (USERSPACES.get(label) or DYNAMIC_SPACES[label])[0]
    space = get(m)
    before = [s._evalrepr for s in space._direct_bases]
    space._direct_bases.append(m.B)
    space._direct_bases.clear()
    assert [s._evalrepr for s in space._direct_bases] == before
    assert before


# --------------------------------------------------------------------------
# SpaceGraph: the preds of a name that is not a node

@pytest.fixture
def graph():
    """``P`` with the bases ``Base1`` and ``Base2``, and ``S`` with the
    base ``B``.  The edges of ``P`` are added in the reverse of their
    ``index``."""
    g = SpaceGraph()
    g.add_edge("Base2", "P", index=2)
    g.add_edge("Base1", "P", index=1)
    g.add_edge("B", "S", index=1)
    return g


def test_ordered_preds_of_a_node(graph):
    """A node's preds are ordered by the edges' ``index``."""
    assert graph.ordered_preds("P") == ["Base1", "Base2"]
    assert graph.ordered_preds("S") == ["B"]
    assert graph.ordered_preds("B") == []


@pytest.mark.parametrize("name", [
    "P.__Space1",           # on 0.33: ['Base1', 'B', 'Base2']
    "P3.__Space1",          # on 0.33: ['Base1', 'B', 'Base2']
    "P.__Space1.Child",     # on 0.33: ['Base1', 'B', 'Base2']
    "SP",                   # on 0.33: ['B', 'Base1', 'Base2']
    "Base",                 # on 0.33: []
    "",
])
def test_ordered_preds_of_a_name_not_in_graph(graph, name):
    """A name that is not a node has no preds, whatever its characters
    are, and asking adds no node."""
    nodes = sorted(graph.nodes)
    assert graph.ordered_preds(name) == []
    assert sorted(graph.nodes) == nodes


def test_get_mro_of_a_name_not_in_graph(graph):
    """The MRO of a name that is not a node is the name alone; on 0.33,
    ``get_mro('P.__Space1')`` gave ``['P.__Space1', 'Base1', 'B',
    'Base2']`` on this graph."""
    assert graph.get_mro("P.__Space1") == ["P.__Space1"]
    assert graph.get_mro("P") == ["P", "Base1", "Base2"]
