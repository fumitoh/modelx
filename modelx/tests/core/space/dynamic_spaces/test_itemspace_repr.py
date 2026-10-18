"""Display names of ItemSpaces, of what is in them, and of nodes.

devnotes/ToolAPIDesign.md, section 6, PR 2.

F1.  An ItemSpace shows its arguments whatever ``add_params`` is, and an
ItemSpace of an ItemSpace is shown by its parent's arguments and its
own, so ``_get_repr(fullname=True, add_params=False)`` is the display
name of every object: ``'Syn.P[1]'``, ``'Syn.P[1][5]'`` and
``'Syn.P[1].Child[2]'``.  On 0.33 they were ``'Syn.__Space1'``,
``'Syn.__Space2'`` (``P[1]`` left out altogether) and
``'Syn.P[1].__Space1'``, and the default display of ``P[1][5]`` was
``'Syn.__Space1[5]'``.  The display of an object inside an item follows,
and so do ``repr()``, ``.info`` and the ``'repr'`` and ``'repr_parent'``
keys of ``_get_attrdict``.  Only the display changes: ``_name``,
``_idstr``, ``_idtuple`` and ``_evalrepr`` are as on 0.33.

T7.  ``node._get_repr(fullname=True, add_value=False)`` is the display
name of a node with its arguments by parameter name, as in
``'Syn.P[1][5].h(x=3)'``; with ``add_value=True`` it is the node's
``repr()``.  It is defined once, on BaseNode, and ``repr()`` of every
node class uses it.

The tests read only the tool API and the public API.  Each model is
torn down by ``_impl._check_sanity()`` and then ``close()``.
"""

import pytest

import modelx as mx
from modelx.tests.core.base.test_kind import kind


class MultiLine:
    """A value whose repr spans two lines."""

    def __repr__(self):
        return "first\nsecond"


@pytest.fixture
def repr_model():
    """
        Syn--P(i)---------h(x), gk(), k=5
          |  +--Child(j)--w(t)
          |
          +--Q(i, j=0)----c(), g(a, b)
          +--N()----------c()
          +--B1-----------foo(x)
          +--B2-----------bar()
          +--MI(i)(B1, B2)
          glob = 7

    Formulas are source text: from a lambda, modelx parses the whole of
    this file for each one.
    """
    m = mx.new_model("Syn")
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda x: x * i")
    p.new_cells("gk", formula="lambda: glob + k")
    p.k = 5
    child = p.new_space("Child", formula="lambda j: None")
    child.new_cells("w", formula="lambda t: t + j")
    q = m.new_space("Q", formula="lambda i, j=0: None")
    q.new_cells("c", formula="lambda: i + j")
    q.new_cells("g", formula="lambda a, b: (a, b)")
    n = m.new_space("N", formula="lambda: None")
    n.new_cells("c", formula="lambda: 1")
    b1 = m.new_space("B1")
    b1.new_cells("foo", formula="lambda x: x")
    b2 = m.new_space("B2")
    b2.new_cells("bar", formula="lambda: 2")
    m.new_space("MI", bases=[b1, b2], formula="lambda i: None")
    m.glob = 7

    yield m
    m._impl._check_sanity()
    m.close()


# --------------------------------------------------------------------------
# F1: ItemSpaces

ITEMSPACES = {
    # label: (getter, display name, display name without fullname)
    "P[1]": (lambda m: m.P[1], "Syn.P[1]", "P[1]"),
    "P[1][5]": (lambda m: m.P[1][5], "Syn.P[1][5]", "P[1][5]"),
    "P[1][5][7]": (lambda m: m.P[1][5][7], "Syn.P[1][5][7]", "P[1][5][7]"),
    "P[1].Child[2]": (lambda m: m.P[1].Child[2], "Syn.P[1].Child[2]",
                      "Child[2]"),
    "P[1].Child[2][3]": (lambda m: m.P[1].Child[2][3],
                         "Syn.P[1].Child[2][3]", "Child[2][3]"),
    "P[1][5].Child[2]": (lambda m: m.P[1][5].Child[2],
                         "Syn.P[1][5].Child[2]", "Child[2]"),
    "P['a']": (lambda m: m.P["a"], "Syn.P['a']", "P['a']"),
    "P[B1]": (lambda m: m.P[m.B1], "Syn.P[<UserSpace Syn.B1>]",
              "P[<UserSpace Syn.B1>]"),
    "Q[1, 2]": (lambda m: m.Q[1, 2], "Syn.Q[1, 2]", "Q[1, 2]"),
    "Q[1]": (lambda m: m.Q[1], "Syn.Q[1, 0]", "Q[1, 0]"),
    "N[]": (lambda m: m.N(), "Syn.N[]", "N[]"),
    "MI[5]": (lambda m: m.MI[5], "Syn.MI[5]", "MI[5]"),
}


@pytest.mark.parametrize("label", list(ITEMSPACES))
def test_itemspace_display(repr_model, label):
    """An ItemSpace shows its arguments whatever ``add_params`` is, and
    an item of an item shows its parent's arguments too."""
    get, display, short = ITEMSPACES[label]
    item = get(repr_model)
    assert kind(item) == "ItemSpace"
    for add_params in (True, False):
        assert item._get_repr(fullname=True, add_params=add_params) == display
        assert item._get_repr(fullname=False, add_params=add_params) == short
    assert item._get_repr() == short
    assert repr(item) == "<ItemSpace %s>" % display
    assert repr(item.info).splitlines()[0] == "ItemSpace: " + display
    assert item._get_attrdict(recursive=False)["repr"] == short


OBJECTS = {
    # label: (getter, display name, display with parameters)
    # Not in an item: as on 0.33.
    "P": (lambda m: m.P, "Syn.P", "Syn.P"),
    "P.h": (lambda m: m.P.h, "Syn.P.h", "Syn.P.h(x)"),
    "P.Child": (lambda m: m.P.Child, "Syn.P.Child", "Syn.P.Child"),
    "MI.foo": (lambda m: m.MI.foo, "Syn.MI.foo", "Syn.MI.foo(x)"),
    # DynamicSpaces
    "P[1].Child": (lambda m: m.P[1].Child, "Syn.P[1].Child",
                   "Syn.P[1].Child"),
    "P[1][5].Child": (lambda m: m.P[1][5].Child, "Syn.P[1][5].Child",
                      "Syn.P[1][5].Child"),
    # Cells
    "P[1].h": (lambda m: m.P[1].h, "Syn.P[1].h", "Syn.P[1].h(x)"),
    "P[1][5].h": (lambda m: m.P[1][5].h, "Syn.P[1][5].h",
                  "Syn.P[1][5].h(x)"),
    "P[1][5][7].h": (lambda m: m.P[1][5][7].h, "Syn.P[1][5][7].h",
                     "Syn.P[1][5][7].h(x)"),
    "P[1].Child.w": (lambda m: m.P[1].Child.w, "Syn.P[1].Child.w",
                     "Syn.P[1].Child.w(t)"),
    "P[1].Child[2].w": (lambda m: m.P[1].Child[2].w,
                        "Syn.P[1].Child[2].w", "Syn.P[1].Child[2].w(t)"),
    "P[1][5].Child[2].w": (lambda m: m.P[1][5].Child[2].w,
                           "Syn.P[1][5].Child[2].w",
                           "Syn.P[1][5].Child[2].w(t)"),
    "Q[1, 2].c": (lambda m: m.Q[1, 2].c, "Syn.Q[1, 2].c", "Syn.Q[1, 2].c()"),
    "Q[1, 2].g": (lambda m: m.Q[1, 2].g, "Syn.Q[1, 2].g",
                  "Syn.Q[1, 2].g(a, b)"),
    "N[].c": (lambda m: m.N().c, "Syn.N[].c", "Syn.N[].c()"),
    "MI[5].foo": (lambda m: m.MI[5].foo, "Syn.MI[5].foo",
                  "Syn.MI[5].foo(x)"),
    "MI[5].bar": (lambda m: m.MI[5].bar, "Syn.MI[5].bar",
                  "Syn.MI[5].bar()"),
    # Proxies: an argument, and a Space Reference seen through an item,
    # which is the Space's own.
    "P[1].i": (lambda m: m.P[1]._get_object("i", as_proxy=True),
               "Syn.P[1].i", "Syn.P[1].i"),
    "P[1][5].i": (lambda m: m.P[1][5]._get_object("i", as_proxy=True),
                  "Syn.P[1][5].i", "Syn.P[1][5].i"),
    "P[1][5].k": (lambda m: m.P[1][5]._get_object("k", as_proxy=True),
                  "Syn.P.k", "Syn.P.k"),
}


@pytest.mark.parametrize("label", list(OBJECTS))
def test_object_display(repr_model, label):
    """What is in an item is shown under the item's display name, and
    ``repr()`` and ``.info`` show the same string."""
    get, display, with_params = OBJECTS[label]
    obj = get(repr_model)
    assert obj._get_repr(fullname=True, add_params=False) == display
    assert obj._get_repr(fullname=True, add_params=True) == with_params
    assert obj._get_repr(fullname=True) == with_params
    assert repr(obj) == "<%s %s>" % (kind(obj), with_params)
    assert repr(obj.info).splitlines()[0] == "%s: %s" % (
        kind(obj), with_params)


def build_items(m):
    """Create the items of ITEMSPACES and of OBJECTS."""
    for get, _, _ in ITEMSPACES.values():
        get(m)
    for get, _, _ in OBJECTS.values():
        get(m)


def expected_display(obj):
    """The display name of ``obj`` built from its parents: the Model's
    name, then ``'.'`` and a name for each member, and the arguments in
    brackets for each item, each formatted by :func:`repr`."""
    if kind(obj) == "Model":
        return obj.name
    parent = expected_display(obj._parent)
    if kind(obj) == "ItemSpace":
        return parent + "[%s]" % ", ".join(repr(a) for a in obj.argvalues)
    return parent + "." + obj.name


def walk(obj):
    """Yield ``obj`` and every Space and Cells in it, ItemSpaces
    included, through ``spaces``, ``_named_itemspaces`` and ``cells``."""
    yield obj
    for space in obj.spaces.values():
        yield from walk(space)
    if kind(obj) != "Model":
        for item in obj._named_itemspaces.values():
            yield from walk(item)
        yield from obj.cells.values()


def test_display_name_of_every_object(repr_model):
    """``_get_repr(fullname=True, add_params=False)`` is the display name
    of every Space and Cells: it is built from the parents, it never
    shows a ``__SpaceN`` name, and no two objects share it."""
    m = repr_model
    build_items(m)
    seen = {}
    kinds = {}
    for obj in walk(m):
        display = obj._get_repr(fullname=True, add_params=False)
        assert display == expected_display(obj)
        assert "__Space" not in display
        assert display not in seen, (display, seen.get(display))
        seen[display] = obj
        kinds[kind(obj)] = kinds.get(kind(obj), 0) + 1
    # The walk reached every kind, nested items included.
    assert kinds == {"Model": 1, "UserSpace": 7, "ItemSpace": 12,
                     "DynamicSpace": 5, "Cells": 10, "DynamicCells": 25}
    assert "Syn.P[1][5][7]" in seen and "Syn.P[1].Child[2][3]" in seen


def test_attrdict_shows_no_space_name(repr_model):
    """In a whole-model ``_get_attrdict``, the ``'repr'`` of no record
    shows a ``__SpaceN`` name, and that of an item of an item shows its
    parent's arguments."""
    m = repr_model
    build_items(m)
    reprs = []

    def collect(record):
        reprs.append(record["repr"])
        for key in ("spaces", "_named_itemspaces", "cells"):
            for child in record.get(key, {}).get("items", {}).values():
                collect(child)

    collect(m._get_attrdict(recursive=True))
    assert len(reprs) == 60
    assert not [r for r in reprs if "__Space" in r]
    assert "P[1][5]" in reprs and "Child[2][3]" in reprs


def test_identity_unchanged(repr_model):
    """F1 changes the display only.  An item keeps its ``__SpaceN``
    ``_name`` and ``_idstr``, which still resolve, and its ``_idtuple``
    and ``_evalrepr`` are as on 0.33."""
    m = repr_model
    nested = m.P[1][5]
    assert nested._name.startswith("__Space")
    assert nested._idstr == "P.%s.%s" % (m.P[1]._name, nested._name)
    assert m._get_from_name(nested._idstr) is nested
    assert m.P[1]._named_itemspaces[nested._name] is nested
    assert nested._idtuple == ("Syn", "P", (1,), (5,))
    assert nested._evalrepr == "Syn.P(1)(5)"
    assert nested.h._evalrepr == "Syn.P(1)(5).h"


# --------------------------------------------------------------------------
# T7: nodes

NODES = {
    # label: (getter, display, display without fullname, value repr)
    "B1.foo(3)": (lambda m: m.B1.foo.node(3), "Syn.B1.foo(x=3)",
                  "foo(x=3)", "3"),
    "P(1)": (lambda m: m.P.node(1), "Syn.P(i=1)", "P(i=1)",
             "<ItemSpace Syn.P[1]>"),
    "P[1](5)": (lambda m: m.P[1].node(5), "Syn.P[1](i=5)", "P[1](i=5)",
                "<ItemSpace Syn.P[1][5]>"),
    "P[1].h(3)": (lambda m: m.P[1].h.node(3), "Syn.P[1].h(x=3)", "h(x=3)",
                  "3"),
    "P[1][5].h(3)": (lambda m: m.P[1][5].h.node(3), "Syn.P[1][5].h(x=3)",
                     "h(x=3)", "15"),
    "P[1].Child(2)": (lambda m: m.P[1].Child.node(2),
                      "Syn.P[1].Child(j=2)", "Child(j=2)",
                      "<ItemSpace Syn.P[1].Child[2]>"),
    "P[1].Child[2].w(4)": (lambda m: m.P[1].Child[2].w.node(4),
                           "Syn.P[1].Child[2].w(t=4)", "w(t=4)", "6"),
    "Q[1, 2].c()": (lambda m: m.Q[1, 2].c.node(), "Syn.Q[1, 2].c()", "c()",
                    "3"),
    "Q[1, 2].g(1, 'x')": (lambda m: m.Q[1, 2].g.node(1, "x"),
                          "Syn.Q[1, 2].g(a=1, b='x')", "g(a=1, b='x')",
                          "(1, 'x')"),
    "N[].c()": (lambda m: m.N().c.node(), "Syn.N[].c()", "c()", "1"),
    "MI[5].foo(2)": (lambda m: m.MI[5].foo.node(2), "Syn.MI[5].foo(x=2)",
                     "foo(x=2)", "2"),
    # ReferenceNodes: no arguments.  An argument of an item of an item,
    # and a global and a Space Reference read through an item.
    "P[1][5].i": (lambda m: m.P[1][5].h.precedents(3)[0], "Syn.P[1][5].i",
                  "i", "5"),
    "glob": (lambda m: ref_node(m.P[1].gk, "glob"), "Syn.glob", "glob", "7"),
    "P.k": (lambda m: ref_node(m.P[1].gk, "k"), "Syn.P.k", "k", "5"),
}


def ref_node(cells, name):
    """The node of the Reference ``name`` that ``cells()`` reads."""
    [node] = [n for n in cells.precedents() if n.obj.name == name]
    return node


def calculate(m):
    """Calculate the values of NODES."""
    m.B1.foo(3)
    m.P[1][5].h(3)
    m.P[1].h(3)
    m.P[1].Child[2].w(4)
    m.Q[1, 2].c()
    m.Q[1, 2].g(1, "x")
    m.N().c()
    m.MI[5].foo(2)
    m.P[1].gk()


@pytest.mark.parametrize("label", list(NODES))
def test_node_display(repr_model, label):
    """A node's ``_get_repr()`` is its object's display name with its
    arguments by parameter name, and with ``add_value=True`` it is the
    node's ``repr()``."""
    m = repr_model
    calculate(m)
    get, display, short, value = NODES[label]
    node = get(m)
    assert node.has_value()
    assert node._get_repr() == display
    assert node._get_repr(fullname=True, add_value=False) == display
    assert node._get_repr(fullname=False) == short
    assert node._get_repr(add_value=True) == display + "=" + value
    assert node._get_repr(fullname=False, add_value=True) == (
        short + "=" + value)
    assert repr(node) == display + "=" + value


def test_node_without_value(repr_model):
    """A node with no value has nothing to add: ``add_value`` makes no
    difference, and nothing raises."""
    m = repr_model
    for node, display in [
            (m.P[1][5].h.node(4), "Syn.P[1][5].h(x=4)"),
            (m.P[1].node(9), "Syn.P[1](i=9)"),
            (m.Q[1, 2].c.node(), "Syn.Q[1, 2].c()")]:
        assert not node.has_value()
        assert node._get_repr() == display
        assert node._get_repr(add_value=True) == display
        assert repr(node) == display


def test_node_multiline_value(repr_model):
    """A value whose ``repr()`` spans lines starts on a line of its own,
    as in ``repr()``."""
    m = repr_model
    m.P[1][5].h[7] = MultiLine()
    node = m.P[1][5].h.node(7)
    assert node._get_repr() == "Syn.P[1][5].h(x=7)"
    assert node._get_repr(add_value=True) == (
        "Syn.P[1][5].h(x=7)=\nfirst\nsecond")
    assert repr(node) == node._get_repr(add_value=True)


def test_node_lists(repr_model):
    """Lists of nodes print with the same strings, as in the
    ``precedents`` docstring."""
    m = repr_model
    calculate(m)
    assert repr(m.P[1][5].h.precedents(3)) == "[Syn.P[1][5].i=5]"
    assert repr(m.P[1].Child[2].w.precedents(4)) == (
        "[Syn.P[1].Child[2].j=2]")


def test_node_attrdict(repr_model):
    """The node dicts of an item of an item show its parent's
    arguments, not its ``__SpaceN`` name, in ``'repr_parent'``."""
    m = repr_model
    calculate(m)
    record = m.P[1][5].h.node(3)._get_attrdict()
    assert record["repr_parent"] == "Syn.P[1][5]"
    assert record["repr"] == "h(x)"
    record = m.P[1][5].h.precedents(3)[0]._get_attrdict()
    assert record["repr_parent"] == "Syn.P[1][5]"
    assert record["repr"] == "i"
    record = m.P[1].node(5)._get_attrdict()
    assert record["repr_parent"] == "Syn"
    assert record["repr"] == "P[1]"
