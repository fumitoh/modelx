"""Resolved slots: a Reference seen through an ItemSpace that refers to the
ItemSpace's own copy of its value.

devnotes/ToolAPIDesign.md, section 6, PR 3: T5's resolved slot (decision 7)
and the fixes to ``DynamicSpaceImpl.wrap_impl``.

Take ``P.rel = P.Child`` with a formula on ``P``.  In ``P[1]``, ``rel``
refers to ``P[1].Child``.  From 0.34 the ItemSpace holds a Reference of
its own for it, its copy of ``P.rel``:

* its proxy is a ``DynamicReferenceProxy`` (decision 15) named ``'rel'``,
  with ``P[1]`` as parent, ``_idstr`` ``'P.__Space1.rel'``, ``_evalrepr``
  ``'<Model>.P(1).rel'``, ``_is_derived()`` True and the mode of
  ``P.rel``, and its ``value`` is ``P[1].Child``, what a formula in
  ``P[1]`` sees;
* it equals neither ``P[2].rel`` nor ``P.rel``, and the binding it copies
  is ``r.parent.bases[0]._get_object(r.name, as_proxy=True)``;
* it turns invalid with its ItemSpace (test_refproxy.py covers the
  edits, and an ItemSpace made again);
* ``_space.rel`` in a formula of ``P[1]`` works: before 0.34 it failed
  the assert in ``Namespace.__getattr__``, and so did ``rel.up`` for a
  slot ``up`` of ``P[1].Child``;
* formulas see the same objects as before, so values and
  ``len(tracegraph)`` are as on 1d92c67 (measured there, pinned here on
  lifelib's simplelife, whose Projection items have 7 such slots each).

Before 0.34 the slot held ``P[1].Child`` itself, so its proxy had the
copy's name and ``_idstr`` (``'Child'``, ``'P.__Space1.Child'``), its
``refmode`` raised AttributeError and it never went invalid.

Every other Reference seen through an ItemSpace is the binding of its
Space, as before.  Three cases were broken before 0.34 and are fixed by
``wrap_impl``:

* the prefix case, ``P.r = PX`` for a sibling whose name begins with
  ``P``: the slot held None, every formula of ``P[1]`` raised
  AttributeError, and so did the dicts of ``P[1]``, of its ``refs`` view
  and of the Model (fix-reference-identity/g06);
* a derived Reference whose value its Space re-pointed to a Space outside
  the item's tree: making the ItemSpace raised AttributeError, because
  ``wrap_impl`` called ``direct_bases`` on a ReferenceImpl;
* a value whose name is inside the tree but which the tree has no copy
  of, an ItemSpace such as ``P.Child[3]``: the slot held None, as in the
  prefix case.

The id round trips through ``_idstr`` and ``_address`` are PR 4's.  The
tests read only the tool API and the public API, and give formulas as
source text.  Each model is torn down by ``_impl._check_sanity()`` and then
``close()``.
"""

import warnings

import pytest

import modelx as mx
from modelx.core.errors import FormulaError
from modelx.tests.core.api.test_tool_contracts import model_digest
from modelx.tests.core.base.test_kind import kind


@pytest.fixture
def slots_model():
    """
        Slots---P(i)----k=2, rel -> P.Child, relc -> P.h, me -> P,
          |     |       rr -> P.Child (relative), out -> Other,
          |     |       ab -> P.Child (absolute), px -> PX, pxc -> PX.c,
          |     |       h(), viaspace(), viacells(), relupk(), seen(),
          |     |       seenc(), hx(), isrel(), seenout()
          |     +--Child---w(), up -> P, sib -> P.Child.w, upk()
          +-----Other
          +-----PX---c()
    """
    m = mx.new_model("Slots")
    p = m.new_space("P", formula="lambda i: None")
    p.k = 2
    child = p.new_space("Child")
    child.new_cells("w", formula="lambda: i * 10")
    child.up = p
    child.sib = child.w
    child.new_cells("upk", formula="lambda: up.k")
    p.rel = child
    p.relref(rr=child)
    p.new_cells("h", formula="lambda: rel.w() + k")
    p.relc = p.h
    p.me = p
    p.new_cells("viaspace", formula="lambda: _space.rel.w()")
    p.new_cells("viacells", formula="lambda: _space.relc()")
    p.new_cells("relupk", formula="lambda: rel.up.k")
    p.new_cells("seen", formula="lambda: _space.rel")
    p.new_cells("seenc", formula="lambda: relc")
    p.out = m.new_space("Other")
    p.absref(ab=child)
    px = m.new_space("PX")
    px.new_cells("c", formula="lambda: 5")
    p.px = px
    p.pxc = px.c
    p.new_cells("hx", formula="lambda: px.c() + pxc()")
    p.new_cells("isrel", formula="lambda: rel is _space.Child")
    p.new_cells("seenout", formula="lambda: out")
    yield m
    m._impl._check_sanity()
    m.close()


def proxy(space, name):
    return space._get_object(name, as_proxy=True)


# (Space, name, value, binding's Space, _idstr, _evalrepr, display, mode)
SLOTS = {
    "P[1].rel": (
        lambda m: m.P[1], "rel", lambda m: m.P[1].Child, lambda m: m.P,
        "P.__Space1.rel", "Slots.P(1).rel", "Slots.P[1].rel", "auto"),
    "P[1].rr, relative": (
        lambda m: m.P[1], "rr", lambda m: m.P[1].Child, lambda m: m.P,
        "P.__Space1.rr", "Slots.P(1).rr", "Slots.P[1].rr", "relative"),
    "P[1].relc, a Cells": (
        lambda m: m.P[1], "relc", lambda m: m.P[1].h, lambda m: m.P,
        "P.__Space1.relc", "Slots.P(1).relc", "Slots.P[1].relc", "auto"),
    "P[1].me, the ItemSpace": (
        lambda m: m.P[1], "me", lambda m: m.P[1], lambda m: m.P,
        "P.__Space1.me", "Slots.P(1).me", "Slots.P[1].me", "auto"),
    "P[1][5].rel, nested": (
        lambda m: m.P[1][5], "rel", lambda m: m.P[1][5].Child,
        lambda m: m.P, "P.__Space1.__Space2.rel", "Slots.P(1)(5).rel",
        "Slots.P[1][5].rel", "auto"),
    "P[1].Child.up, through a DynamicSpace": (
        lambda m: m.P[1].Child, "up", lambda m: m.P[1],
        lambda m: m.P.Child, "P.__Space1.Child.up", "Slots.P(1).Child.up",
        "Slots.P[1].Child.up", "auto"),
    "P[1].Child.sib": (
        lambda m: m.P[1].Child, "sib", lambda m: m.P[1].Child.w,
        lambda m: m.P.Child, "P.__Space1.Child.sib",
        "Slots.P(1).Child.sib", "Slots.P[1].Child.sib", "auto"),
    "P[1][5].Child.up": (
        lambda m: m.P[1][5].Child, "up", lambda m: m.P[1][5],
        lambda m: m.P.Child, "P.__Space1.__Space2.Child.up",
        "Slots.P(1)(5).Child.up", "Slots.P[1][5].Child.up", "auto"),
}


@pytest.mark.parametrize("label", list(SLOTS))
def test_slot_is_a_reference_of_its_own(slots_model, label):
    m = slots_model
    m.P[1][5]       # make the nested item first, so its name is __Space2
    get, name, value, static, idstr, evalrepr, display, mode = SLOTS[label]
    space = get(m)
    r = proxy(space, name)
    assert kind(r) == "DynamicReferenceProxy"
    assert (r.name, r.parent, r.model) == (name, space, m)
    assert r.fullname == "Slots." + idstr
    assert r._idstr == idstr
    assert r._evalrepr == evalrepr
    assert r._get_repr() == name
    assert r._get_repr(fullname=True, add_params=False) == display
    assert repr(r) == "<DynamicReferenceProxy %s>" % display
    assert r.value is value(m)
    assert getattr(space, name) is value(m)
    assert r._is_derived() is True
    assert r.is_derived() is True
    assert r.refmode == mode
    assert r.refmode == proxy(static(m), name).refmode
    assert r._is_valid() is True
    # the binding the slot copies
    binding = r.parent.bases[0]._get_object(r.name, as_proxy=True)
    assert binding == proxy(static(m), name)
    assert kind(binding) == "ReferenceProxy"
    assert binding != r


def test_slot_equality(slots_model):
    """Each ItemSpace has its own slot, with its own value; one slot's
    proxies are equal however they are made: by ``_get_object``, by
    :func:`~modelx.get_object`, as the ``obj`` of the ReferenceNode that
    reading ``_space.rel`` records, and by the ``refs`` view, whose row
    describes the slot."""
    m = slots_model
    a, b, s = proxy(m.P[1], "rel"), proxy(m.P[2], "rel"), proxy(m.P, "rel")
    assert a != b and a != s and b != s
    assert len({a, b, s, proxy(m.P[1], "rel")}) == 3
    assert a == proxy(m.P[1], "rel")
    assert hash(a) == hash(proxy(m.P[1], "rel"))
    assert a.value is m.P[1].Child and b.value is m.P[2].Child
    assert a.value is not b.value
    assert mx.get_object("Slots.P.__Space1.rel", as_proxy=True) == a

    m.P[1].viaspace()
    nodes = [n.obj for n in m.P[1].viaspace.precedents()
             if n.obj.name == "rel"]
    assert nodes == [a]
    assert kind(nodes[0]) == "DynamicReferenceProxy"

    rows = m.P[1].refs._get_attrdict()["items"]
    assert (rows["rel"]["name"], rows["rel"]["fullname"],
            rows["rel"]["type"], rows["rel"]["value_type"]) == (
        "rel", "Slots.P.__Space1.rel", "Reference", "DynamicSpace")
    assert rows["relc"]["value_type"] == "DynamicCells"
    assert m.P[1].refs._baseattrs["items"]["rel"]["name"] == "rel"


def test_what_formulas_see(slots_model):
    """A formula in ``P[1]`` sees the ItemSpace's copies through the
    slots, by name and through ``_space``.  Four of these failed the
    assert in ``Namespace.__getattr__`` on 1d92c67, which reads a slot as
    an attribute of a namespace: ``P[1].viaspace()``, which reads
    ``_space.rel.w()`` (fix-reference-identity/g01), ``P[1].seen()`` and
    ``P[1].viacells()``, which read ``_space.rel`` and ``_space.relc()``,
    and ``P[1].relupk()``, which reads ``rel.up.k``, where ``up`` is a
    slot of ``P[1].Child``.  The others gave these values there too, in
    this model without ``px`` and ``pxc``, whose None slots made every
    formula of ``P[1]`` fail there.

    ``rel`` by name is the object ``_space.Child`` is, in ``P[1]`` as on
    1d92c67, so a formula sees the same object as before; with
    ``DynamicSpaceImpl.on_update_ns`` reduced to the base class's it was
    ``P[1].Child`` and ``P[1].isrel()`` was False.  ``out``, a binding
    that is not a slot, is ``Other`` itself."""
    m = slots_model
    assert m.P[1].h() == 12
    assert m.P[2].h() == 22
    assert m.P[1][5].h() == 52
    assert m.P[1].Child.sib() == 10
    assert m.P[1].viaspace() == 10
    assert m.P[1].viacells() == 12
    assert m.P[1].relupk() == 2
    assert m.P[1].Child.upk() == 2
    assert m.P[1].seen() is m.P[1].Child
    assert m.P[1].seenc() is m.P[1].h
    assert m.P[1].rel is m.P[1].Child
    assert m.P[1].relc is m.P[1].h
    assert m.P[1].Child.up is m.P[1]
    assert m.P[1].isrel() is True
    assert m.P[1][5].isrel() is True
    assert m.P[1].seenout() is m.Other


def test_slot_hidden_by_argument_or_formula_ref():
    """``P.i = P.Child`` and ``P.rel = P.Child`` with the Space formula
    ``lambda i: {'refs': {'rel': 2 * i}}``: in ``P[1]`` both names are
    slots, hidden by the argument ``i`` and by the formula's ref ``rel``,
    and a formula sees those, as on 1d92c67.  Without the hide test in
    ``on_update_ns``, both gave ``P[1].Child``'s namespace."""
    m = mx.new_model("SlotsHidden")
    p = m.new_space("P", formula="lambda i: {'refs': {'rel': 2 * i}}")
    child = p.new_space("Child")
    p.i = child
    p.rel = child
    p.new_cells("geti", formula="lambda: i")
    p.new_cells("getrel", formula="lambda: rel")
    assert p.geti() is child and p.getrel() is child
    item = p[1]
    assert (item.geti(), item.getrel()) == (1, 2)
    assert (item.i, item.rel) == (1, 2)
    assert (p[3].geti(), p[3].getrel()) == (3, 6)
    m._impl._check_sanity()
    m.close()


def test_cells_and_slot_of_one_name():
    """``S.c = S.Child``, then ``S.add_bases(B)`` for a Cells ``B.c``:
    ``add_bases`` does not check names, so ``S`` has a Reference and a
    Cells named ``c``.  A formula of ``S`` calls the Cells, and so does
    one of ``S[1]``, as on 1d92c67.  With the slot put over the Cells,
    ``S[1].h()`` raised FormulaError, as ``c`` was ``S[1].Child``'s
    namespace."""
    m = mx.new_model("SlotsCellsClash")
    b = m.new_space("B")
    b.new_cells("c", formula="lambda: 1")
    s = m.new_space("S", formula="lambda i: None")
    s.new_space("Child")
    s.c = s.Child
    s.add_bases(b)
    s.new_cells("h", formula="lambda: c() + 1")
    assert ("c" in s.cells, "c" in s.refs) == (True, True)
    assert s.h() == 2
    assert s[1].h() == 2
    assert s[2].h() == s.h()
    m._impl._check_sanity()
    m.close()


def test_bindings_that_are_not_slots(slots_model):
    """A Reference whose value is not in the tree, an absolute one, a
    global, and one whose value is a sibling whose name begins with
    ``P`` are the bindings of ``P`` and the Model, seen through the
    item."""
    m = slots_model
    item = m.P[1]
    for name, value in (("k", 2), ("out", m.Other), ("ab", m.P.Child),
                        ("px", m.PX), ("pxc", m.PX.c)):
        r = proxy(item, name)
        assert r == proxy(m.P, name), name
        assert kind(r) == "ReferenceProxy", name
        assert r._idstr == "P." + name
        assert r.parent is m.P
        assert r.value is value or r.value == value, name
        assert r._is_derived() is False, name
        assert getattr(item, name) is r.value


def test_slot_invalid_with_its_itemspace(slots_model):
    """A kept slot proxy turns invalid when its ItemSpace goes, also for a
    nested item and through a DynamicSpace, and stays invalid when the
    ItemSpace is made again; the new slot is another Reference."""
    m = slots_model
    kept = [proxy(m.P[1], "rel"), proxy(m.P[1][5], "rel"),
            proxy(m.P[1].Child, "up")]
    nested = proxy(m.P[2][5], "relc")
    assert all(r._is_valid() for r in kept + [nested])
    del m.P[1]
    assert [r._is_valid() for r in kept] == [False, False, False]
    assert nested._is_valid() is True
    again = [proxy(m.P[1], "rel"), proxy(m.P[1][5], "rel"),
             proxy(m.P[1].Child, "up")]
    assert [r._is_valid() for r in kept] == [False, False, False]
    assert all(r._is_valid() for r in again)
    assert all(old != new for old, new in zip(kept, again))
    assert repr(kept[0]) == "<DynamicReferenceProxy null object>"
    m.P.rel = m.P.Child         # a rebind deletes every ItemSpace of P
    assert nested._is_valid() is False
    assert all(not r._is_valid() for r in again)
    assert len(m.P.itemspaces) == 0
    assert m.P[1].h() == 12


WALK_ATTRS = ["_is_derived", "__len__", "_evalrepr"]


def test_whole_model_walk(slots_model):
    """spyder-modelx's tree list gives a resolved slot's row the slot's
    own name, ``_evalrepr`` and ``_is_derived``, and the prefix case no
    longer stops the walk."""
    m = slots_model
    m.P[1].h()
    record = m._get_attrdict(WALK_ATTRS, recursive=True)
    rows = record["spaces"]["items"]["P"]["_named_itemspaces"]["items"][
        "__Space1"]["refs"]["items"]
    for name in ("rel", "rr", "relc", "me"):
        assert rows[name]["name"] == name
        assert rows[name]["_evalrepr"] == "Slots.P(1)." + name
        assert rows[name]["_is_derived"] is True
    for name in ("k", "out", "ab", "px", "pxc"):
        assert rows[name]["fullname"] == "Slots.P." + name
        assert rows[name]["_is_derived"] is False


# --------------------------------------------------------------------------
# wrap_impl: the in-tree test, and bindings it now keeps

def test_prefix_sibling(slots_model):
    """``P.px = PX``, a sibling whose name begins with ``P``, is outside
    ``P``'s tree.  Before 0.34 ``wrap_impl`` tested the start of the
    name without a dot boundary, so it took ``PX`` as in the tree and the
    slot held None: ``P[1].hx()`` raised AttributeError, ``P[1].px`` was
    missing, and each of the dicts below raised AttributeError
    (fix-reference-identity/g06, g06b)."""
    m = slots_model
    item = m.P[1]
    assert item.hx() == 10
    assert item.px is m.PX and item.pxc is m.PX.c
    assert set(item._get_attrdict(recursive=True)["refs"]["items"]) >= {
        "px", "pxc"}
    assert set(item.refs._get_attrdict()["items"]) >= {"px", "pxc"}
    assert set(item.refs._baseattrs["items"]) >= {"px", "pxc"}
    assert item.refs._baseattrs_private["type"] == "RefView"
    assert {"px", "pxc"} <= set(item.refs._baseattrs_private["items"])
    assert "spaces" in m._get_attrdict(recursive=True)
    assert {"px", "pxc"} <= set(dict(item.refs))


def test_prefix_sibling_relative():
    """A ``'relative'`` Reference to a sibling whose name begins with
    ``P`` is out of ``P``'s tree, as one to any other sibling: making an
    ItemSpace raises ValueError.  Before 0.34 the ItemSpace was made with
    None in the slot, and each of its formulas raised AttributeError."""
    m = mx.new_model("SlotsRelative")
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda: 1")
    for name in ("PX", "Q"):
        p.relref(r=m.new_space(name))
        with pytest.raises(FormulaError) as e:
            p[1]
        assert "'%s' referred as 'P.r' is out of 'P'" % name in str(e.value)
        assert len(p.itemspaces) == 0
    del p.r
    assert p[1].h() == 1
    m._impl._check_sanity()
    m.close()


def test_derived_reference_out_of_the_tree():
    """``Y.P`` is a sub Space of ``X.P``, and ``Y`` of ``X``.
    ``X.P.r = X.Other`` is ``'auto'``, so ``Y.P``'s copy refers to
    ``Y.Other``, which is outside ``Y.P``'s tree.  ``Y.P[1]`` sees what
    ``Y.P`` sees.  Before 0.34 ``wrap_impl`` called ``direct_bases`` on
    the copy, which a Reference does not have, and making ``Y.P[1]``
    raised AttributeError: 'ReferenceImpl' object has no attribute
    'direct_bases'."""
    m = mx.new_model("SlotsDerived")
    x = m.new_space("X")
    xp = x.new_space("P", formula="lambda i: None")
    x.new_space("Other").new_cells("c", formula="lambda: 'X.Other'")
    xp.r = x.Other
    xp.new_cells("f", formula="lambda: r.c()")
    y = m.new_space("Y", bases=x)
    y.new_space("Other").new_cells("c", formula="lambda: 'Y.Other'")
    yp = y.new_space("P", bases=xp, formula="lambda i: None")
    binding = proxy(yp, "r")
    assert (binding.value, binding._is_derived()) == (y.Other, True)

    assert xp[1].f() == "X.Other"
    assert yp.f() == "Y.Other"
    item = yp[1]
    assert item.f() == "Y.Other"
    assert item.r is y.Other
    r = proxy(item, "r")
    assert r == binding
    assert (kind(r), r._idstr, r._is_derived()) == (
        "ReferenceProxy", "Y.P.r", True)
    m._impl._check_sanity()
    m.close()


def test_value_the_tree_has_no_copy_of():
    """``P.r = P.Child[3]``: the name of the value is inside ``P``'s
    tree, but an item copies no ItemSpace, so ``P[1]`` sees what ``P``
    sees, through the binding of ``P``.  Before 0.34 the slot held None,
    with the failures of the prefix case."""
    m = mx.new_model("SlotsNoCopy")
    p = m.new_space("P", formula="lambda i: None")
    child = p.new_space("Child", formula="lambda j: None")
    child.new_cells("w", formula="lambda: j")
    target = child[3]
    p.r = target
    p.new_cells("h", formula="lambda: r.w()")
    assert target._is_valid() and p.h() == 3
    item = p[1]
    assert item.h() == 3
    assert item.r is target
    r = proxy(item, "r")
    assert r == proxy(p, "r")
    assert (kind(r), r._idstr) == ("ReferenceProxy", "P.r")
    assert "r" in item.refs._get_attrdict()["items"]
    m._impl._check_sanity()
    m.close()


# --------------------------------------------------------------------------
# lifelib's simplelife

# The SHA-256 of the files of the simplelife model that lifelib 0.17.2
# creates, by test_tool_contracts.model_digest(). The values and the count
# in test_simplelife were measured on it, on 1d92c67 (before resolved
# slots) and with them, with the same results; a later change to the model
# in lifelib changes them without any change in modelx.
SIMPLELIFE_SHA256 = (
    "48e6629797e769b1a09cd23245e8f56aeaaee1ab1a0066e77d0fa89e7f99cd1b")

# The 7 slots of each Projection item: two Spaces of the item, and five
# Cells of its Policy, seen through the item's Policy and Assumptions.
SIMPLELIFE_SLOTS = {
    "": {"pol": "Policy", "asmp": "Assumptions"},
    "Policy": {"PremTerm": "Policy.PolicyTerm"},
    "Assumptions": {"gen": "Policy.Gen", "polt": "Policy.PolicyType",
                    "prod": "Policy.Product", "sex": "Policy.Sex"},
}


def test_simplelife(tmp_path):
    """simplelife's ``Projection.pol`` is ``Projection.Policy``, so each
    Projection item has resolved slots: 7 of them (g03b).  Their proxies
    stand for them, and the values of ``PV_NetCashflow(0)`` for three
    projections, and the number of nodes, are those of 1d92c67."""
    lifelib = pytest.importorskip("lifelib")
    lifelib.create("simplelife", tmp_path / "simplelife")
    path = tmp_path / "simplelife" / "model"
    measured = model_digest(path) == SIMPLELIFE_SHA256
    if not measured:
        warnings.warn(
            "lifelib's simplelife is not the copy that the values of"
            " test_simplelife were measured on (SHA-256 %s); only the"
            " slots are checked" % model_digest(path))
    m = mx.read_model(path, name="SlotsSimplelife")
    try:
        proj = m.Projection
        values = [proj[pid].PV_NetCashflow(0) for pid in (1, 2, 3)]
        for pid in (1, 2, 3):
            item = proj[pid]
            for where, slots in SIMPLELIFE_SLOTS.items():
                space = item._get_object(where) if where else item
                static = proj._get_object(where) if where else proj
                # the names the item shares with its Space, but not the
                # arguments, which hide such a name
                shared = [name for name in space.refs
                          if not name.startswith("_") and name in static.refs
                          and name not in proj.parameters]
                found = {name for name in shared
                         if proxy(space, name) != proxy(static, name)}
                assert found == set(slots), (pid, where)
                for name, target in slots.items():
                    r = proxy(space, name)
                    assert kind(r) == "DynamicReferenceProxy"
                    assert (r.name, r.parent) == (name, space)
                    assert r.value is item._get_object(target)
                    assert (r._is_derived(), r.refmode) == (True, "auto")
                    assert proxy(r.parent.bases[0], name) == proxy(
                        static, name)
        if measured:
            assert [round(float(v), 6) for v in values] == [
                8954.018303, 7511.092085, 9173.90659]
            assert len(m.tracegraph) == 5034
        m._impl._check_sanity()
    finally:
        m.close()
