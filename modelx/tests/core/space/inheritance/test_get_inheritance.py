"""``BaseSpace._get_inheritance()``: one read per Space of where each Cells
and each Reference is defined.

devnotes/ToolAPIDesign.md, T4, and section 6, PR 3.

For each Cells, and each name in ``refs``, the dict gives the state,
'defined', 'overriding' or 'derived' (None for a name that is not a
Reference of a Space), and the Space whose definition is in use; for a
name in ``refs`` also the scope: 'space', 'base', 'argument', 'formula',
'global' or 'builtins'.  An ItemSpace or a DynamicSpace reports the states
of the UserSpace it was made from.  The expectations of the design's
prototype probes are pinned here: inheritance/i05 (UserSpaces with single,
multiple and two-level inheritance, an ItemSpace of a sub Space) and i12
(an ItemSpace, its DynamicSpace, and an ItemSpace whose base the Space
formula chose), and the i08 regression (an ItemSpace's idstr is not a node
of the inheritance graph, and its characters name other Spaces).

The ``defined_in`` columns, which the prototypes did not compute, agree
with PR 1's 0.33 fallback recipes in test_tool_contracts.py
(``cells_recipe`` and ``refs_recipe``) on every Space of these fixtures,
which ``test_agrees_with_033_recipes`` checks.

The tests read only the tool API and the public API.  Each model is torn
down by ``_impl._check_sanity()`` and then ``close()``.  Formulas are
source text: from a lambda, modelx parses the whole of this file for each
one.
"""

import pytest

import modelx as mx
from modelx.core.errors import DeletedObjectError
from modelx.tests.core.api.test_tool_contracts import (
    cells_recipe, refs_recipe)
from modelx.tests.core.base.test_kind import kind

KEYS = ["bases", "direct_bases", "cells", "refs"]
SYSTEM_NAMES = ("_self", "_space", "_model")


def label(obj):
    """'Model' for the Model, the ``_idstr`` of a Space, None for None."""
    if obj is None:
        return None
    return "Model" if kind(obj) == "Model" else obj._idstr


def cells_table(space):
    """[(name, state, defined_in label)] in the order of the result."""
    return [(n, v["state"], label(v["defined_in"]))
            for n, v in space._get_inheritance()["cells"].items()]


def refs_table(space):
    """[(name, scope, state, defined_in label)] in the order of the result."""
    return [(n, v["scope"], v["state"], label(v["defined_in"]))
            for n, v in space._get_inheritance()["refs"].items()]


def walk(space):
    yield space
    for child in space.spaces.values():
        yield from walk(child)
    for item in space._named_itemspaces.values():
        yield from walk(item)


def all_spaces(m):
    return [s for top in m.spaces.values() for s in walk(top)]


def make_items(m):
    """Make the ItemSpace ``[1]`` of every UserSpace that has a formula,
    and return every Space of the model, ItemSpaces included."""
    for space in all_spaces(m):
        if kind(space) == "UserSpace" and space.formula is not None:
            space[1]
    return all_spaces(m)


def finish(m):
    m._impl._check_sanity()
    m.close()


B = ("__builtins__", "builtins", None, None)


def G(name):
    return (name, "global", None, "Model")


# --------------------------------------------------------------------------
# inheritance/i05: the synthetic inheritance model

@pytest.fixture
def inh_model():
    """i05's model (introspect/inheritance/synth.py):

        GetInh--Base0-----------zed()                r0
          glob  Base1(Base0)----foo(), bar(x)       k, tbl, sref -> Child
                 +--Child--y()                      cref -> foo, aref (abs)
                Base2-----------foo(), qux()        k2
                Sub(Base1)------bar overridden      k rebound; parameter i
                Multi(Base1, Base2)
                Plain-----------own()               p
                Deep(Multi)
    """
    m = mx.new_model("GetInh")
    m.glob = 7
    b0 = m.new_space("Base0")
    b0.new_cells("zed", formula="lambda: 0")
    b0.r0 = "r0"
    b1 = m.new_space("Base1", bases=b0)
    b1.new_cells("foo", formula="lambda: 1")
    b1.new_cells("bar", formula="lambda x: x + foo()")
    b1.k = 1
    b1.tbl = {"a": 1}
    child = b1.new_space("Child")
    child.new_cells("y", formula="lambda: 5")
    b1.sref = child
    b1.cref = b1.foo
    b1.absref(aref=child)
    b2 = m.new_space("Base2")
    b2.new_cells("foo", formula="lambda: 2")
    b2.new_cells("qux", formula="lambda: 3")
    b2.k2 = 2
    sub = m.new_space("Sub", bases=b1)
    sub.bar.formula = "lambda x: 100 * x"
    sub.k = 20
    sub.parameters = ("i",)
    m.new_space("Multi", bases=[b1, b2])
    plain = m.new_space("Plain")
    plain.new_cells("own", formula="lambda: 9")
    plain.p = 3
    m.new_space("Deep", bases=m.Multi)
    yield m
    finish(m)


_B1_REFS = ("tbl", "sref", "cref", "aref")

I05_CELLS = {
    "Base0": [("zed", "defined", "Base0")],
    "Base1": [("zed", "derived", "Base0"), ("foo", "defined", "Base1"),
              ("bar", "defined", "Base1")],
    "Base1.Child": [("y", "defined", "Base1.Child")],
    "Base2": [("foo", "defined", "Base2"), ("qux", "defined", "Base2")],
    "Sub": [("zed", "derived", "Base0"), ("foo", "derived", "Base1"),
            ("bar", "overriding", "Sub")],
    "Multi": [("foo", "derived", "Base1"), ("qux", "derived", "Base2"),
              ("zed", "derived", "Base0"), ("bar", "derived", "Base1")],
    "Deep": [("foo", "derived", "Base1"), ("qux", "derived", "Base2"),
             ("zed", "derived", "Base0"), ("bar", "derived", "Base1")],
    "Plain": [("own", "defined", "Plain")],
}
I05_CELLS["Sub[1]"] = I05_CELLS["Sub"]

I05_REFS = {
    "Base0": [B, G("glob"), ("r0", "space", "defined", "Base0")],
    "Base1": [B, G("glob"), ("r0", "space", "derived", "Base0"),
              ("k", "space", "defined", "Base1")]
             + [(n, "space", "defined", "Base1") for n in _B1_REFS],
    "Base1.Child": [B, G("glob")],
    "Base2": [B, G("glob"), ("k2", "space", "defined", "Base2")],
    "Sub": [B, G("glob"), ("r0", "space", "derived", "Base0")]
           + [(n, "space", "derived", "Base1") for n in _B1_REFS]
           + [("k", "space", "overriding", "Sub")],
    "Multi": [B, G("glob"), ("k2", "space", "derived", "Base2"),
              ("r0", "space", "derived", "Base0"),
              ("k", "space", "derived", "Base1")]
             + [(n, "space", "derived", "Base1") for n in _B1_REFS],
    "Plain": [B, G("glob"), ("p", "space", "defined", "Plain")],
    "Sub[1]": [B, G("glob"), ("r0", "base", "derived", "Base0")]
              + [(n, "base", "derived", "Base1") for n in _B1_REFS]
              + [("k", "base", "overriding", "Sub"),
                 ("i", "argument", None, None)],
}
I05_REFS["Deep"] = I05_REFS["Multi"]

I05_BASES = {
    # label: (bases, direct_bases)
    "Base0": ([], []),
    "Base1": (["Base0"], ["Base0"]),
    "Base1.Child": ([], []),
    "Base2": ([], []),
    "Sub": (["Base1", "Base0"], ["Base1"]),
    "Multi": (["Base1", "Base0", "Base2"], ["Base1", "Base2"]),
    "Deep": (["Multi", "Base1", "Base0", "Base2"], ["Multi"]),
    "Plain": ([], []),
    "Sub[1]": (["Sub"], ["Sub"]),
}


def inh_space(m, name):
    if name == "Sub[1]":
        return m.Sub[1]
    space = m
    for part in name.split("."):
        space = space.spaces[part]
    return space


@pytest.mark.parametrize("name", list(I05_CELLS))
def test_i05(inh_model, name):
    """The states and scopes of i05's prototype, and where each definition
    in use is: for a derived member, the first Space in the MRO that
    defines it (Multi(Base1, Base2) takes foo from Base1, Deep(Multi)
    takes bar from Base1, because Multi's is derived)."""
    space = inh_space(inh_model, name)
    d = space._get_inheritance()
    assert set(d) == set(KEYS)
    assert cells_table(space) == I05_CELLS[name]
    assert refs_table(space) == I05_REFS[name]
    bases, direct = I05_BASES[name]
    assert [b._idstr for b in d["bases"]] == bases
    assert [b._idstr for b in d["direct_bases"]] == direct


def test_lists_match_public_members(inh_model):
    """``'bases'`` is ``bases``, ``'direct_bases'`` is ``_direct_bases``,
    and the keys of ``'cells'`` and ``'refs'`` are those of ``cells`` and
    ``refs``, in the same order, on every Space, ItemSpaces included."""
    m = inh_model
    m.Sub[1]
    m.Sub[2]
    spaces = all_spaces(m)
    assert sum(kind(s) == "ItemSpace" for s in spaces) == 2
    for space in spaces:
        d = space._get_inheritance()
        assert d["bases"] == space.bases, space
        assert d["direct_bases"] == space._direct_bases, space
        assert list(d["cells"]) == list(space.cells), space
        assert list(d["refs"]) == list(space.refs), space


def test_derived_relative_ref_to_base_child(inh_model):
    """``Base1.sref`` refers to Base1's child Space relatively.  Child Spaces
    are not inherited, so ``Sub.sref`` holds a null Space.  It is reported
    'derived', with Base1's definition in use, without being resolved."""
    m = inh_model
    proxy = m.Sub._get_object("sref", as_proxy=True)
    assert not proxy.value._is_valid()
    assert m.Sub._get_inheritance()["refs"]["sref"] == {
        "scope": "space", "state": "derived", "defined_in": m.Base1}
    assert m.Sub[1]._get_inheritance()["refs"]["sref"] == {
        "scope": "base", "state": "derived", "defined_in": m.Base1}


def test_evaluates_nothing(inh_model):
    """No formula runs and no ItemSpace is made: ``len(tracegraph)`` and
    every Cells' ``len`` are as they were.  ``cref`` holds a scalar Cells,
    which a comparison of values would have evaluated."""
    m = inh_model
    m.Sub.bar(3)
    item = m.Sub[1]
    spaces = all_spaces(m)
    nodes = len(m.tracegraph)
    lens = [len(c) for s in spaces for c in s.cells.values()]
    assert len(m.Base1.foo) == 0
    for space in spaces:
        space._get_inheritance()
    assert len(m.tracegraph) == nodes
    assert [len(c) for s in spaces for c in s.cells.values()] == lens
    assert len(m.Sub.itemspaces) == 1 and m.Sub.itemspaces[1] is item


def test_new_containers(inh_model):
    """Each call returns new containers at every level, and changing one
    changes neither a later result nor the Space."""
    m = inh_model
    for space in (m.Sub, m.Sub[1]):
        first = space._get_inheritance()
        second = space._get_inheritance()
        assert first == second
        assert first is not second
        assert first["bases"] is not first["direct_bases"]
        for key in KEYS:
            assert first[key] is not second[key]
        for key in ("cells", "refs"):
            for name in first[key]:
                assert first[key][name] is not second[key][name]

        first["bases"].clear()
        first["direct_bases"].append(None)
        first["cells"]["foo"]["state"] = "changed"
        first["refs"]["k"]["scope"] = "changed"
        del first["refs"]["r0"]
        first.clear()

        assert space._get_inheritance() == second
        assert space.bases == second["bases"]
        assert list(space.cells) == list(second["cells"])
        assert list(space.refs) == list(second["refs"])


def test_dynamic_cells_order():
    """An ItemSpace lists its Cells in the order of its own ``cells``.
    ``sort_cells()`` reorders a Space's Cells and leaves its ItemSpaces
    alive, in their order."""
    m = mx.new_model("GetInhOrder")
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda: i")
    p.new_cells("g", formula="lambda: 2")
    item = p[1]
    p.sort_cells()
    assert item._is_valid()
    assert (list(item.cells), list(p.cells)) == (["h", "g"], ["g", "h"])
    assert list(item._get_inheritance()["cells"]) == ["h", "g"]
    assert list(p._get_inheritance()["cells"]) == ["g", "h"]
    finish(m)


def test_deleted_space(inh_model):
    """A deleted Space raises DeletedObjectError, as its ``bases`` does."""
    m = inh_model
    item = m.Sub[1]
    del m.Sub[1]
    plain = m.Plain
    del m.Plain
    for space in (item, plain):
        with pytest.raises(DeletedObjectError):
            space._get_inheritance()


# --------------------------------------------------------------------------
# inheritance/i12: ItemSpaces, a DynamicSpace, and a base the formula chose

@pytest.fixture
def scopes_model():
    """i12's model:

        GetInhScopes--P(i)----h()     k = 5
          glob = 1     +--Kid--y()    kk = 6
                      R(j)----z()     PP -> P (absolute)
                      R's formula returns {'base': PP, 'refs': {'extra': ...}}
    """
    m = mx.new_model("GetInhScopes")
    m.glob = 1
    p = m.new_space("P")
    p.new_cells("h", formula="lambda: i")
    p.k = 5
    kid = p.new_space("Kid")
    kid.new_cells("y", formula="lambda: 1")
    kid.kk = 6
    p.parameters = ("i",)
    r = m.new_space("R")
    r.new_cells("z", formula="lambda: j")
    r.absref(PP=p)
    r.formula = "lambda j: {'base': PP, 'refs': {'extra': j * 10}}"
    yield m
    finish(m)


I12 = {
    "P[1]": ("P", [("h", "defined", "P")],
             [B, G("glob"), ("k", "base", "defined", "P"),
              ("i", "argument", None, None)]),
    "P[1].Kid": ("P.Kid", [("y", "defined", "P.Kid")],
                 [B, G("glob"), ("kk", "base", "defined", "P.Kid"),
                  ("i", "argument", None, None)]),
    "R[1]": ("P", [("h", "defined", "P")],
             [B, G("glob"), ("k", "base", "defined", "P"),
              ("extra", "formula", None, None),
              ("j", "argument", None, None)]),
}


def i12_space(m, name):
    return {"P[1]": lambda: m.P[1], "P[1].Kid": lambda: m.P[1].Kid,
            "R[1]": lambda: m.R[1]}[name]()


@pytest.mark.parametrize("name", list(I12))
def test_i12(scopes_model, name):
    """A dynamic Space reports the states of the UserSpace it was made
    from, its only base, and its names in ``refs`` by scope: arguments,
    formula refs, then the UserSpace's References."""
    space = i12_space(scopes_model, name)
    base, cells, refs = I12[name]
    d = space._get_inheritance()
    assert [b._idstr for b in d["bases"]] == [base]
    assert [b._idstr for b in d["direct_bases"]] == [base]
    assert cells_table(space) == cells
    assert refs_table(space) == refs


def test_base_chosen_by_formula(scopes_model):
    """``R[1]`` is made from P, which R's formula returned as ``'base'``.
    Its formula and ``parameters`` are P's, ``('i',)``, but its argument is
    ``j``, a parameter of R's formula, its parent's ``parameters``."""
    m = scopes_model
    item = m.R[1]
    assert item.parameters == ("i",)
    assert m.R.parameters == ("j",)
    refs = item._get_inheritance()["refs"]
    args = [n for n, v in refs.items() if v["scope"] == "argument"]
    assert args == list(m.R.parameters)
    assert "i" not in refs and "PP" not in refs


# --------------------------------------------------------------------------
# inheritance/i08: an ItemSpace's idstr is not a node of the graph

@pytest.fixture
def chars_model():
    """i08's model: a one-letter Space S, with the base B, whose name
    occurs in the idstr of ``Sub[1]``, ``'Sub.__Space1'``."""
    m = mx.new_model("GetInhChars")
    b = m.new_space("B")
    b.new_cells("foo", formula="lambda: 'B.foo'")
    m.new_space("S", bases=b)
    sub = m.new_space("Sub", formula="lambda i: None")
    sub.new_cells("foo", formula="lambda: 'Sub.foo'")
    yield m
    finish(m)


def test_i08_itemspace_idstr(chars_model):
    """``Sub[1]`` has the only base Sub, and its ``foo`` is Sub's own.  Read
    through the graph with ``'Sub.__Space1'``, networkx took the idstr's
    characters as nodes, and B, the base of S, came back as a base of the
    ItemSpace; its ``foo`` would then have been 'overriding'."""
    m = chars_model
    item = m.Sub[1]
    assert item._idstr == "Sub.__Space1"
    d = item._get_inheritance()
    assert d["bases"] == [m.Sub]
    assert d["direct_bases"] == [m.Sub]
    assert cells_table(item) == [("foo", "defined", "Sub")]
    assert cells_table(m.S) == [("foo", "derived", "B")]
    assert m.S._get_inheritance()["direct_bases"] == [m.B]


# --------------------------------------------------------------------------
# Names that start with '_', builtins and system names (C2(2))

@pytest.fixture
def underscore_model():
    """``_`` names on the four routes that take them until 0.36: a global
    Reference ``_ug``, a Space Reference ``_sr`` made by
    ``new_space(refs=)``, an argument ``_a`` and a formula ref ``_fr``."""
    m = mx.new_model("GetInhUnderscore")
    setattr(m, "_ug", 1)
    m.new_space("S", refs={"_sr": 2})
    m.new_space("Q", formula="lambda _a: {'refs': {'_fr': 10 * _a}}")
    m.Q[1]
    yield m
    finish(m)


def test_underscore_names(underscore_model):
    """Each ``_`` name is reported under its scope, as ``refs`` lists it."""
    m = underscore_model
    assert refs_table(m.S) == [B, G("_ug"), ("_sr", "space", "defined", "S")]
    assert refs_table(m.Q) == [B, G("_ug")]
    assert refs_table(m.Q[1]) == [
        B, G("_ug"), ("_fr", "formula", None, None),
        ("_a", "argument", None, None)]


@pytest.mark.parametrize(
    "fixture", ["inh_model", "scopes_model", "chars_model",
                "underscore_model", "slot_model"])
def test_builtins_and_system_names(request, fixture):
    """``__builtins__`` is in every Space's ``refs`` with scope 'builtins',
    and the system names ``_self``, ``_space`` and ``_model``, which
    ``refs`` does not list, are never reported."""
    m = request.getfixturevalue(fixture)
    for space in make_items(m):
        refs = space._get_inheritance()["refs"]
        assert refs["__builtins__"] == {
            "scope": "builtins", "state": None, "defined_in": None}, space
        for name in SYSTEM_NAMES:
            assert name not in refs, (space, name)


# --------------------------------------------------------------------------
# Resolved slots (T5): a Reference whose value is the item's own copy

@pytest.fixture
def slot_model():
    """``P.rel = P.Child``, ``P.relc = P.h`` and ``P.Child.up = P``: through
    ``P[1]``, each refers to the item's own copy of its value (T5's
    resolved slots); ``P.k`` is a plain Reference."""
    m = mx.new_model("GetInhSlots")
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda: i")
    child = p.new_space("Child")
    child.new_cells("w", formula="lambda: 1")
    p.k = 5
    p.rel = child
    p.relc = p.h
    child.up = p
    yield m
    finish(m)


def test_resolved_slot_is_base(slot_model):
    """A resolved slot is a Reference of the static Space seen through the
    item: scope 'base', with the binding's state and definition."""
    m = slot_model
    item = m.P[1]
    assert item.rel is item.Child and item.relc is item.h
    assert refs_table(item) == [
        B, ("k", "base", "defined", "P"), ("rel", "base", "defined", "P"),
        ("relc", "base", "defined", "P"), ("i", "argument", None, None)]
    assert item.Child.up is item
    assert refs_table(item.Child) == [
        B, ("up", "base", "defined", "P.Child"),
        ("i", "argument", None, None)]


# --------------------------------------------------------------------------
# _own_refs against the scopes (ToolAPIDesign section 9, assigned to T4)

@pytest.mark.parametrize(
    "fixture", ["inh_model", "scopes_model", "underscore_model",
                "slot_model"])
def test_own_refs_scopes(request, fixture):
    """``_own_refs`` holds the names reported with scope 'space' in a
    UserSpace and 'formula' in an ItemSpace, and nothing in a
    DynamicSpace.  The rest of a dynamic Space's ``refs`` is reported as
    'argument', 'base', 'global' or 'builtins'."""
    m = request.getfixturevalue(fixture)
    spaces = make_items(m)
    assert any(kind(s) == "ItemSpace" for s in spaces)
    for space in spaces:
        refs = space._get_inheritance()["refs"]
        own = "space" if kind(space) == "UserSpace" else "formula"
        assert set(space._own_refs) == {
            n for n, v in refs.items() if v["scope"] == own}, space
        if kind(space) == "DynamicSpace":
            assert not space._own_refs


def test_own_refs_hidden_formula_ref():
    """A formula ref that an argument of the same name hides is in the
    ItemSpace's ``_own_refs``, and reported as the argument it is in
    ``refs``."""
    m = mx.new_model("GetInhHidden")
    q = m.new_space("Q", formula="lambda i: {'refs': {'i': 0, 'x': 1}}")
    item = q[1]
    assert dict(item._own_refs) == {"i": 0, "x": 1}
    assert item.refs["i"] == 1
    assert refs_table(item) == [B, ("i", "argument", None, None),
                                ("x", "formula", None, None)]
    finish(m)


# --------------------------------------------------------------------------
# PR 1's 0.33 fallback recipes give the same answers

@pytest.mark.parametrize(
    "fixture", ["inh_model", "scopes_model", "chars_model",
                "underscore_model", "slot_model"])
def test_agrees_with_033_recipes(request, fixture):
    """On every Space, ItemSpaces and DynamicSpaces included, the states,
    scopes and ``defined_in`` equal those of the recipes that tools use on
    0.33 (test_tool_contracts.py), in the same order."""
    m = request.getfixturevalue(fixture)
    for space in make_items(m):
        d = space._get_inheritance()
        cells = {n: (v["state"], v["defined_in"])
                 for n, v in d["cells"].items()}
        refs = {n: (v["scope"], v["state"], v["defined_in"])
                for n, v in d["refs"].items()}
        expected_cells, expected_refs = cells_recipe(space), refs_recipe(space)
        assert list(cells.items()) == list(expected_cells.items()), space
        assert list(refs.items()) == list(expected_refs.items()), space
