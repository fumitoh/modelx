"""Which objects are dynamic, and which are inherited, as tools tell them.

devnotes/ToolAPIDesign.md, section 6, PR 2.

T2 (decisions 15 and 16).  An object is dynamic when modelx generated it
inside an ItemSpace, and its class says so: ``ItemSpace``,
``DynamicSpace``, ``DynamicCells`` and ``DynamicReferenceProxy``, read
with T1's recipe (``kind``, from test_kind.py).  The Space flags
``_is_dynamic()``, ``_is_static()`` and ``_is_root()`` are removed in 0.34,
and no kind has ``_is_dynamic()``.  A DynamicCells is a Cells and a
DynamicReferenceProxy a ReferenceProxy, so ``isinstance`` is unaffected;
the attrdict ``'type'`` stays ``'Cells'`` and ``'Reference'``; ``repr()``
and ``.info`` print the new names.

Not dynamic: the Model, every UserSpace and its Cells, derived ones
included, Space and global References, a Reference of a Space seen
through one of its ItemSpaces (``P[1].k`` is ``P.k``), and macros.  Nor,
on this release, is the proxy of a slot of an ItemSpace, or of a
DynamicSpace in one, that holds the ItemSpace's copy of a Space or a
Cells (``P[1].rel`` for ``P.rel = P.Child``, ``P[1].Child.up`` for
``P.Child.up = P``): the slot holds the copy itself, not a Reference,
until T5 (PR 3) gives it one.

Proxies are made at six sites, and each is checked: a ReferenceNode's
``obj``, ``Model._get_object`` and ``BaseSpace._get_object`` with
``as_proxy=True``, ``Model._get_refs``, and the ``_baseattrs`` and
``_get_attrdict`` of a ``refs`` view.  The views return no proxy, so the
class each makes is recorded by wrapping ``ReferenceProxy.__init__``,
which every proxy of either class runs.

T3, ``_is_derived()`` on Cells and References, has its own section at
the end of this module.  A Cells or a Reference is derived when it has
no definition of its own where it is seen: it was copied from a base
Space, or it is a dynamic Cells.  An argument, a formula ref and the
system bindings of an item are dynamic but not derived; a Reference of
a Space seen through an item, and a global Reference seen through any
Space, give the flag of that Reference.  ``Cells._is_derived()`` is as
on 0.33.  ``ReferenceProxy._is_derived()`` is new, and returns None for
a proxy that stands for no Reference, such as the slot above, so that a
whole-model ``_get_attrdict`` asking for it never raises.
``ReferenceProxy.is_derived()`` stays for good as its alias (decision
11).  No Space class, and not Model, has ``_is_derived`` (decision 4).

The tests read only the tool API and the public API.  They import the
classes Cells and ReferenceProxy only to check ``isinstance``, which code
outside the tool API relies on, to wrap ``__init__`` as above, and once to
subclass ReferenceProxy.  Each
model is torn down by ``_impl._check_sanity()`` and then ``close()``.
"""

import copy

import pytest

import modelx as mx
from modelx.core.cells import Cells
from modelx.core.reference import ReferenceProxy
from modelx.tests.core.base.test_kind import kind

DYNAMIC = frozenset(
    {"ItemSpace", "DynamicSpace", "DynamicCells", "DynamicReferenceProxy"})

REMOVED_FLAGS = ("_is_dynamic", "_is_static", "_is_root")


def macro_one():
    return 1


@pytest.fixture
def flags_model():
    """
        FlagsModel--Base----foo(), bar(), k=1, q=2
          |  glob   Base2---baz()
          |  mac    Sub(Base)----foo() overridden, q=20 overriding
          |         MI(Base, Base2)
          |         Q(i)(Base)
          |
          +---------P(i)----h(), sys(), k=5, rel -> P.Child, relc -> P.h
                    |       Space formula returns ref fr
                    +--Child(j)--w()

    Formulas are source text: from a lambda, modelx parses the whole of
    this file for each one.
    """
    m = mx.new_model("FlagsModel")
    base = m.new_space("Base")
    base.new_cells("foo", formula="lambda: 1")
    base.new_cells("bar", formula="lambda: k")
    base.k = 1
    base.q = 2
    base2 = m.new_space("Base2")
    base2.new_cells("baz", formula="lambda: 2")
    sub = m.new_space("Sub", bases=base)
    sub.foo.formula = "lambda: 10"
    sub.q = 20
    m.new_space("MI", bases=[base, base2])
    m.new_space("Q", bases=base, formula="lambda i: None")

    p = m.new_space("P", formula="lambda i: {'refs': {'fr': 10 * i}}")
    p.new_cells("h", formula="lambda: i + fr + k + glob")
    p.new_cells("sys", formula="lambda: (_self, _space, _model)")
    p.k = 5
    child = p.new_space("Child", formula="lambda j: None")
    child.new_cells("w", formula="lambda: _self.n + _space.n + _model.glob")
    child.n = 1
    p.rel = child
    p.relc = p.h
    m.glob = 7
    m.new_macro("mac", macro_one)

    yield m
    m._impl._check_sanity()
    m.close()


# --------------------------------------------------------------------------
# T2: the dynamic table (decisions 15 and 16)

SPACES = {
    # label: (getter, kind)
    "Base": (lambda m: m.Base, "UserSpace"),
    "Sub(Base)": (lambda m: m.Sub, "UserSpace"),
    "MI(Base, Base2)": (lambda m: m.MI, "UserSpace"),
    "P": (lambda m: m.P, "UserSpace"),
    "P.Child": (lambda m: m.P.Child, "UserSpace"),
    "P[1]": (lambda m: m.P[1], "ItemSpace"),
    "P[1][5]": (lambda m: m.P[1][5], "ItemSpace"),
    "P[1].Child": (lambda m: m.P[1].Child, "DynamicSpace"),
    "P[1][5].Child": (lambda m: m.P[1][5].Child, "DynamicSpace"),
    "P[1].Child[2]": (lambda m: m.P[1].Child[2], "ItemSpace"),
}


@pytest.mark.parametrize("label", list(SPACES))
def test_space_class(flags_model, label):
    """The class tells a Space's kind, where 0.33 had the flags: a
    UserSpace is what ``_is_static()`` was True for, an ItemSpace what
    ``_is_root()`` was True for, and both dynamic kinds what
    ``_is_dynamic()`` was True for (decision 16)."""
    get, expected = SPACES[label]
    space = get(flags_model)
    assert kind(space) == expected
    assert (kind(space) in DYNAMIC) is (expected != "UserSpace")


CELLS = {
    # label: (getter, kind)
    "Base.foo": (lambda m: m.Base.foo, "Cells"),
    "Sub.foo, overriding": (lambda m: m.Sub.foo, "Cells"),
    "Sub.bar, derived": (lambda m: m.Sub.bar, "Cells"),
    "MI.baz, derived from the second base": (lambda m: m.MI.baz, "Cells"),
    "P.h": (lambda m: m.P.h, "Cells"),
    "P.Child.w": (lambda m: m.P.Child.w, "Cells"),
    "P[1].h": (lambda m: m.P[1].h, "DynamicCells"),
    "P[1][5].h": (lambda m: m.P[1][5].h, "DynamicCells"),
    "P[1].Child.w": (lambda m: m.P[1].Child.w, "DynamicCells"),
    "P[1][5].Child.w": (lambda m: m.P[1][5].Child.w, "DynamicCells"),
    "P[1].Child[2].w": (lambda m: m.P[1].Child[2].w, "DynamicCells"),
}


@pytest.mark.parametrize("label", list(CELLS))
def test_cells_class(flags_model, label):
    get, expected = CELLS[label]
    cells = get(flags_model)
    assert kind(cells) == expected
    assert isinstance(cells, Cells)
    assert (type(cells) is Cells) is (expected == "Cells")


def test_no_kind_has_the_flags(flags_model):
    """No class defines ``_is_dynamic``, ``_is_static`` or ``_is_root``:
    the Spaces' were removed (decision 16), and Cells, proxies, the Model
    and macros never had them (decision 15). Looked up on the class, as
    a tool detects a member."""
    m = flags_model
    objs = [m, m.mac, m.P._get_object("k", as_proxy=True),
            m.P[1]._get_object("i", as_proxy=True)]
    objs += [get(m) for get, _ in SPACES.values()]
    objs += [get(m) for get, _ in CELLS.values()]
    assert {kind(o) for o in objs} == {
        "Model", "Macro", "ReferenceProxy", "DynamicReferenceProxy",
        "UserSpace", "ItemSpace", "DynamicSpace", "Cells", "DynamicCells"}
    for obj in objs:
        for name in REMOVED_FLAGS:
            assert getattr(type(obj), name, None) is None, (obj, name)


# The class of the proxy of each name, seen through each Space.
PROXIES = {
    "P": {"k": "ReferenceProxy", "rel": "ReferenceProxy",
          "glob": "ReferenceProxy"},
    "P[1]": {"i": "DynamicReferenceProxy", "fr": "DynamicReferenceProxy",
             "k": "ReferenceProxy", "glob": "ReferenceProxy",
             # The ItemSpace's copies of P.Child and P.h, in slots that
             # are not References until T5 (PR 3): see the module
             # docstring.
             "rel": "ReferenceProxy", "relc": "ReferenceProxy"},
    "P[1][5]": {"i": "DynamicReferenceProxy", "fr": "DynamicReferenceProxy",
                "k": "ReferenceProxy", "glob": "ReferenceProxy",
                "rel": "ReferenceProxy", "relc": "ReferenceProxy"},
    "P[1].Child": {"i": "DynamicReferenceProxy", "n": "ReferenceProxy",
                   "glob": "ReferenceProxy"},
    "P[1].Child[2]": {"i": "DynamicReferenceProxy",
                      "j": "DynamicReferenceProxy", "n": "ReferenceProxy",
                      "glob": "ReferenceProxy"},
}


@pytest.mark.parametrize("label", list(PROXIES))
def test_proxy_class_from_space_get_object(flags_model, label):
    """``BaseSpace._get_object(name, as_proxy=True)``."""
    space = SPACES[label][0](flags_model)
    got = {name: kind(space._get_object(name, as_proxy=True))
           for name in PROXIES[label]}
    assert got == PROXIES[label]


@pytest.fixture
def made_proxies(monkeypatch):
    """The kind of every proxy made while the fixture is in use."""
    made = []
    init = ReferenceProxy.__init__

    def record(self, impl):
        init(self, impl)
        made.append(kind(self))

    monkeypatch.setattr(ReferenceProxy, "__init__", record)
    return made


@pytest.mark.parametrize("label", list(PROXIES))
@pytest.mark.parametrize("call", ["_baseattrs", "_get_attrdict"])
def test_proxy_class_from_refs_view(flags_model, made_proxies, label, call):
    """The ``refs`` view's ``_baseattrs`` and ``_get_attrdict`` make a
    proxy for each name that does not start with ``_``, in order, of the
    class ``_get_object`` gives, and each row's ``'type'`` is
    ``'Reference'``."""
    space = SPACES[label][0](flags_model)
    want = {name: kind(space._get_object(name, as_proxy=True))
            for name in space.refs if not name.startswith("_")}
    assert set(PROXIES[label]) <= set(want)

    del made_proxies[:]
    view = space.refs
    rows = (view._baseattrs if call == "_baseattrs"
            else view._get_attrdict())["items"]
    assert list(rows) == list(want)
    assert dict(zip(rows, made_proxies)) == want
    assert len(made_proxies) == len(want)
    assert {row["type"] for row in rows.values()} == {"Reference"}


def test_proxy_class_from_nodes(flags_model):
    """A ReferenceNode's ``obj``: arguments, formula refs and the system
    bindings of an ItemSpace and of a DynamicSpace in it are dynamic; a
    UserSpace's system bindings, Space References seen through an item
    and global References are not."""
    m = flags_model

    def obj_kinds(cells):
        cells()
        return {n.obj.name: kind(n.obj) for n in cells.precedents()}

    D, R = "DynamicReferenceProxy", "ReferenceProxy"
    assert obj_kinds(m.P[1].h) == {"i": D, "fr": D, "k": R, "glob": R}
    assert obj_kinds(m.P[1].sys) == {"_self": D, "_space": D, "_model": D}
    assert obj_kinds(m.P[1].Child.w) == {
        "_self": D, "_space": D, "_model": D, "n": R, "glob": R}
    assert obj_kinds(m.P.sys) == {"_self": R, "_space": R, "_model": R}
    assert obj_kinds(m.P.Child.w) == {
        "_self": R, "_space": R, "_model": R, "n": R, "glob": R}


def test_proxy_class_from_model(flags_model):
    """``Model._get_object(name, as_proxy=True)`` and ``Model._get_refs``
    give global and Space References, which are never dynamic."""
    m = flags_model
    assert kind(m._get_object("glob", as_proxy=True)) == "ReferenceProxy"

    value = object()
    m.held = value
    m.P.held = value
    m.P[1]      # the edits above deleted the ItemSpaces
    refs = m._get_refs(value)
    assert sorted((r.fullname, kind(r)) for r in refs) == [
        ("FlagsModel.P.held", "ReferenceProxy"),
        ("FlagsModel.held", "ReferenceProxy")]


def test_copy_keeps_class_and_binding(flags_model):
    """``copy.copy`` calls ``cls.__new__(cls)`` with no argument. It makes
    a proxy of the same class over the same Reference, and a Cells of the
    same class over the same Cells."""
    m = flags_model
    m.P[1].h()
    originals = [
        m.P._get_object("k", as_proxy=True),
        m._get_object("glob", as_proxy=True),
        m.P[1]._get_object("i", as_proxy=True),
        m.P[1]._get_object("fr", as_proxy=True),
        m.P[1]._get_object("k", as_proxy=True),
    ]
    assert [kind(o) for o in originals] == [
        "ReferenceProxy", "ReferenceProxy", "DynamicReferenceProxy",
        "DynamicReferenceProxy", "ReferenceProxy"]
    for orig in originals:
        dup = copy.copy(orig)
        assert dup is not orig
        assert type(dup) is type(orig)
        assert dup.value is orig.value
        assert (dup.name, dup.fullname, dup._idstr, dup._evalrepr) == (
            orig.name, orig.fullname, orig._idstr, orig._evalrepr)
        assert repr(dup) == repr(orig)

    for cells in (m.Base.foo, m.P[1].h):
        dup = copy.copy(cells)
        assert type(dup) is type(cells)
        assert dup._idstr == cells._idstr
        assert dup() == cells()


def test_named_proxy_class_is_kept(flags_model):
    """``ReferenceProxy.__new__`` picks DynamicReferenceProxy only when the
    class asked for is ReferenceProxy itself, so a subclass stays itself.
    Without that test, a subclass made over an argument of an ItemSpace
    came back a DynamicReferenceProxy, and the copy test above still
    passed, because a copy passes no Reference to ``__new__``.
    The Reference is the proxy's own state, which copy and pickle use."""

    class Mine(ReferenceProxy):
        __slots__ = ()

    m = flags_model
    for proxy in (m.P[1]._get_object("i", as_proxy=True),
                  m.P._get_object("k", as_proxy=True)):
        mine = Mine(proxy.__getstate__())
        assert type(mine) is Mine
        assert (mine.value, mine.fullname) == (proxy.value, proxy.fullname)


def test_isinstance_unchanged(flags_model):
    m = flags_model
    assert isinstance(m.P[1].h, Cells)
    assert isinstance(m.P[1].Child.w, Cells)
    assert isinstance(m.P[1]._get_object("i", as_proxy=True), ReferenceProxy)
    assert isinstance(m.P[1]._get_object("fr", as_proxy=True), ReferenceProxy)
    assert type(m.P.h) is Cells
    assert type(m.P[1].h) is not Cells
    assert type(m.P._get_object("k", as_proxy=True)) is ReferenceProxy


def walk_records(attrdict, obj):
    """Yield ``(record, object)`` for ``attrdict``, the dict of ``obj``
    from a recursive ``_get_attrdict``, and for each record in it, with
    the object the record describes: a Space's through ``spaces`` and
    ``_named_itemspaces``, a Cells' through ``cells``, and a Reference's
    as ``_get_object(name, as_proxy=True)`` on the Space or the Model
    whose ``refs`` lists it.

    The key is ``'_named_itemspaces'``, not the ``'named_itemspaces'`` of
    ``_baseattrs``: a walk that read the latter here reached no
    ItemSpace, so on this fixture, with the items of
    ``test_attrdict_type_unchanged``, it saw 13 of the 22 Cells records
    and 20 of the 46 Reference records, and no dynamic one."""
    yield attrdict, obj
    for key, members in (("spaces", lambda o: o.spaces),
                         ("_named_itemspaces", lambda o: o._named_itemspaces)):
        for name, record in attrdict.get(key, {}).get("items", {}).items():
            yield from walk_records(record, members(obj)[name])
    for name, record in attrdict.get("cells", {}).get("items", {}).items():
        yield record, obj.cells[name]
    for name, record in attrdict.get("refs", {}).get("items", {}).items():
        yield record, obj._get_object(name, as_proxy=True)


def test_attrdict_type_unchanged(flags_model):
    """The attrdict ``'type'``: ``'Cells'`` for every Cells and
    ``'Reference'`` for every proxy, dynamic ones included, as spyder
    reads it; in a whole-model walk too."""
    m = flags_model
    for get, _ in CELLS.values():
        cells = get(m)
        assert cells._get_attrdict(recursive=False)["type"] == "Cells"
        assert cells._baseattrs["type"] == "Cells"
    for name in ("i", "fr", "k", "glob"):
        proxy = m.P[1]._get_object(name, as_proxy=True)
        assert proxy._get_attrdict()["type"] == "Reference"
        assert proxy._baseattrs["type"] == "Reference"

    m.P[1][5].Child[2]
    m.Q[1]
    types = {}
    for record, obj in walk_records(m._get_attrdict(recursive=True), m):
        types.setdefault(kind(obj), set()).add(record["type"])
    assert types == {
        "Model": {"Model"}, "UserSpace": {"UserSpace"},
        "ItemSpace": {"ItemSpace"}, "DynamicSpace": {"DynamicSpace"},
        "Cells": {"Cells"}, "DynamicCells": {"Cells"},
        "ReferenceProxy": {"Reference"},
        "DynamicReferenceProxy": {"Reference"}}


def test_repr_and_info_name_the_class(flags_model):
    m = flags_model
    assert repr(m.P[1].h) == "<DynamicCells FlagsModel.P[1].h()>"
    assert repr(m.P[1].Child.w) == "<DynamicCells FlagsModel.P[1].Child.w()>"
    assert repr(m.P.h) == "<Cells FlagsModel.P.h()>"
    assert repr(m.P[1]._get_object("i", as_proxy=True)) == (
        "<DynamicReferenceProxy FlagsModel.P[1].i>")
    assert repr(m.P[1]._get_object("k", as_proxy=True)) == (
        "<ReferenceProxy FlagsModel.P.k>")
    assert repr(m.P[1].h.info).splitlines()[0] == (
        "DynamicCells: FlagsModel.P[1].h()")
    assert repr(m.P.h.info).splitlines()[0] == "Cells: FlagsModel.P.h()"


# --------------------------------------------------------------------------
# T3: _is_derived() on Cells and References

def composition(obj):
    """Design T3's compositions, from the tool API alone: ``'generated'``
    for a dynamic object (T2), ``'inherited'`` for any other derived one,
    and ``'own'`` otherwise.  Telling an overriding member from one only
    its own Space defines needs T4."""
    if kind(obj) in DYNAMIC:
        return "generated"
    return "inherited" if obj._is_derived() else "own"


DERIVED_CELLS = {
    # label: (getter, _is_derived(), composition)
    "Base.foo": (lambda m: m.Base.foo, False, "own"),
    "Sub.foo, overriding": (lambda m: m.Sub.foo, False, "own"),
    "Sub.bar, derived": (lambda m: m.Sub.bar, True, "inherited"),
    "MI.baz, derived from the second base": (
        lambda m: m.MI.baz, True, "inherited"),
    "Q.bar, derived into a Space with a formula": (
        lambda m: m.Q.bar, True, "inherited"),
    "P.h": (lambda m: m.P.h, False, "own"),
    "P.Child.w": (lambda m: m.P.Child.w, False, "own"),
    "P[1].h": (lambda m: m.P[1].h, True, "generated"),
    "P[1][5].h": (lambda m: m.P[1][5].h, True, "generated"),
    "P[1].Child.w": (lambda m: m.P[1].Child.w, True, "generated"),
    "P[1][5].Child.w": (lambda m: m.P[1][5].Child.w, True, "generated"),
    "P[1].Child[2].w": (lambda m: m.P[1].Child[2].w, True, "generated"),
    "Q[1].bar": (lambda m: m.Q[1].bar, True, "generated"),
}


def test_every_cells_of_the_dynamic_table_is_here():
    assert set(CELLS) <= set(DERIVED_CELLS)


@pytest.mark.parametrize("label", list(DERIVED_CELLS))
def test_cells_is_derived(flags_model, label):
    """``Cells._is_derived()``, which 0.34 leaves as it was, on both Cells
    classes, and ``_is_defined()``, its negation.  Every dynamic Cells is
    derived."""
    get, derived, comp = DERIVED_CELLS[label]
    cells = get(flags_model)
    assert getattr(type(cells), "_is_derived", None) is not None
    assert cells._is_derived() is derived
    assert cells._is_defined() is (not derived)
    assert composition(cells) == comp


DERIVED_REFS = {
    # label: (Space or Model, name, _is_derived(), composition)
    "Base.k": (lambda m: m.Base, "k", False, "own"),
    "P.k": (lambda m: m.P, "k", False, "own"),
    "P.rel, the binding in P": (lambda m: m.P, "rel", False, "own"),
    "Sub.k, derived": (lambda m: m.Sub, "k", True, "inherited"),
    "Sub.q, overriding": (lambda m: m.Sub, "q", False, "own"),
    "MI.k, derived": (lambda m: m.MI, "k", True, "inherited"),
    "MI.q, derived where Sub overrides it": (
        lambda m: m.MI, "q", True, "inherited"),
    "Q.k, derived into a Space with a formula": (
        lambda m: m.Q, "k", True, "inherited"),
    # A Model-level Reference, also seen through a Space (inventory probe4)
    "glob": (lambda m: m, "glob", False, "own"),
    "Base.glob": (lambda m: m.Base, "glob", False, "own"),
    "Sub.glob": (lambda m: m.Sub, "glob", False, "own"),
    "P[1].glob": (lambda m: m.P[1], "glob", False, "own"),
    "P[1].Child.glob": (lambda m: m.P[1].Child, "glob", False, "own"),
    # A Reference of a Space seen through an item is the Space's own
    # binding, so it gives that binding's flag.
    "P[1].k": (lambda m: m.P[1], "k", False, "own"),
    "P[1][5].k": (lambda m: m.P[1][5], "k", False, "own"),
    "P[1].Child.n": (lambda m: m.P[1].Child, "n", False, "own"),
    "Q[1].k, derived in Q": (lambda m: m.Q[1], "k", True, "inherited"),
    # Made by the item: dynamic, and never derived.
    "P[1].i, an argument": (lambda m: m.P[1], "i", False, "generated"),
    "P[1].fr, a formula ref": (lambda m: m.P[1], "fr", False, "generated"),
    "P[1][5].i": (lambda m: m.P[1][5], "i", False, "generated"),
    "P[1][5].fr": (lambda m: m.P[1][5], "fr", False, "generated"),
    "P[1].Child.i, an argument seen from a DynamicSpace": (
        lambda m: m.P[1].Child, "i", False, "generated"),
    "P[1].Child[2].j": (lambda m: m.P[1].Child[2], "j", False, "generated"),
    "Q[1].i": (lambda m: m.Q[1], "i", False, "generated"),
}


@pytest.mark.parametrize("label", list(DERIVED_REFS))
def test_reference_is_derived(flags_model, label):
    """``ReferenceProxy._is_derived()`` (T3) on both proxy classes, and
    ``is_derived()``, which is the same, kept for modelx-bridge 0.10
    (decision 11)."""
    get, name, derived, comp = DERIVED_REFS[label]
    proxy = get(flags_model)._get_object(name, as_proxy=True)
    assert getattr(type(proxy), "_is_derived", None) is not None
    assert proxy._is_derived() is derived
    assert proxy.is_derived() is derived
    assert composition(proxy) == comp


def test_system_bindings_are_not_derived(flags_model):
    """The ``_self``, ``_space`` and ``_model`` of a UserSpace, and of an
    ItemSpace and a DynamicSpace in it, got as a ReferenceNode's ``obj``,
    are not derived; only the item's are dynamic."""
    m = flags_model
    system = ("_self", "_space", "_model")
    for cells, comp in ((m.P.sys, "own"), (m.P.Child.w, "own"),
                        (m.P[1].sys, "generated"),
                        (m.P[1].Child.w, "generated")):
        cells()
        got = {n.obj.name: (n.obj._is_derived(), n.obj.is_derived(),
                            composition(n.obj))
               for n in cells.precedents() if n.obj.name in system}
        assert got == {name: (False, False, comp) for name in system}, cells


def test_is_derived_where_no_reference_is_held(flags_model):
    """A proxy that stands for no Reference answers None, and raises
    nothing.

    On this release a Reference of ``P`` that is not ``'absolute'`` and
    whose value is ``P.Child`` or ``P.h`` is seen in ``P[1]`` as
    ``P[1]``'s copy of the value: the slot holds the copy, not a
    Reference.  Before T3, ``is_derived()`` on its proxy raised
    AttributeError for the copy of a Space and gave the copy's own flag,
    True, for the copy of a Cells.  T5 (PR 3) gives each slot a
    Reference of its own, and its ``_is_derived()`` is then True, as
    ``P[1].h``'s is (design T3, decision 7), so these rows change
    there."""
    m = flags_model
    for space in (m.P[1], m.P[1][5]):
        for name, copy in (("rel", space.Child), ("relc", space.h)):
            proxy = space._get_object(name, as_proxy=True)
            assert proxy.value is copy
            assert proxy._is_derived() is None
            assert proxy.is_derived() is None


@pytest.fixture
def child_refs_model():
    """
        ChildRefs--P(i)----Child----w(), up -> P, side -> P.Sib,
          |          |              rw -> P.Child.w, out -> Q,
          |          |              fixed -> P (absolute)
          |          +-----Sib
          +--------Q
    """
    m = mx.new_model("ChildRefs")
    p = m.new_space("P", formula="lambda i: None")
    child = p.new_space("Child")
    child.new_cells("w", formula="lambda: 1")
    sib = p.new_space("Sib")
    q = m.new_space("Q")
    child.up = p
    child.side = sib
    child.rw = child.w
    child.out = q
    child.absref(fixed=p)
    yield m
    m._impl._check_sanity()
    m.close()


def test_is_derived_none_through_a_dynamic_space(child_refs_model):
    """The same holds through a DynamicSpace, for a Reference of a Space
    inside ``P`` whose value is anywhere in ``P``'s tree: in
    ``P[1].Child``, ``up``, ``side`` and ``rw`` are ``P[1]``,
    ``P[1].Sib`` and ``P[1].Child.w``.  On 0.33 ``is_derived()`` raised
    AttributeError on the first two (``'ItemSpaceImpl' object has no
    attribute 'is_derived'``, and ``'DynamicSpaceImpl'``) and gave True
    on the third.  A Reference whose value is outside ``P``, and an
    absolute one, stand for the Reference of ``P.Child``."""
    m = child_refs_model
    dyn = m.P[1].Child
    for name, target in (("up", m.P[1]), ("side", m.P[1].Sib),
                         ("rw", dyn.w)):
        proxy = dyn._get_object(name, as_proxy=True)
        assert proxy.value is target
        assert proxy._is_derived() is None
        assert proxy.is_derived() is None
    for name, target in (("out", m.Q), ("fixed", m.P)):
        proxy = dyn._get_object(name, as_proxy=True)
        assert proxy.value is target
        assert (proxy.fullname, proxy._is_derived(), proxy.is_derived()) == (
            "ChildRefs.P.Child." + name, False, False)


def test_spaces_and_models_have_no_is_derived(flags_model):
    """Decision 4: no Space is ever inherited, so no Space class and not
    Model defines ``_is_derived``, and a dynamic Space is told by its
    class (T2).  Macro defines none either: only Cells and References
    are inherited.  Looked up on the class, as a tool detects a
    member."""
    m = flags_model
    objs = [m, m.mac, m.Q, m.Q[1]] + [get(m) for get, _ in SPACES.values()]
    assert {kind(o) for o in objs} == {
        "Model", "Macro", "UserSpace", "ItemSpace", "DynamicSpace"}
    for obj in objs:
        assert getattr(type(obj), "_is_derived", None) is None, obj


# spyder-modelx's tree request (test_spyder_requests.TREE_ATTRS) with
# '_is_dynamic', which no class answers from 0.34 (decisions 15, 16).
WALK_ATTRS = ["_is_derived", "_is_dynamic", "__len__", "_evalrepr"]


def test_whole_model_walk(flags_model):
    """``model._get_attrdict(WALK_ATTRS, recursive=True)`` does not
    raise, and every record gets what its object answers: a Cells' and a
    Reference's ``'_is_derived'`` is its ``_is_derived()``, a Cells'
    ``'__len__'`` is its ``len()``, and every record's ``'_evalrepr'`` is
    its object's.  No Space or Model record has ``'_is_derived'``
    (decision 4), and no record has ``'_is_dynamic'``.

    The walk reaches the slots of
    ``test_is_derived_where_no_reference_is_held``, whose proxies stand
    for no Reference: there a plain ``impl.is_derived()`` raised
    AttributeError, as on 0.33 (design T3, minimal/m05)."""
    m = flags_model
    m.P[1][5].Child[2].w()
    m.P[1].h()
    m.Q[1].bar()
    m.Sub.bar()
    attrdict = m._get_attrdict(WALK_ATTRS, recursive=True)

    seen = {}
    for record, obj in walk_records(attrdict, m):
        k = kind(obj)
        seen[k] = seen.get(k, 0) + 1
        assert "_is_dynamic" not in record, obj
        assert record["_evalrepr"] == obj._evalrepr, obj
        if k in ("Cells", "DynamicCells"):
            assert record["_is_derived"] is obj._is_derived(), obj
            assert record["__len__"] == len(obj), obj
        elif k in ("ReferenceProxy", "DynamicReferenceProxy"):
            assert record["_is_derived"] is obj._is_derived(), obj
        else:
            assert "_is_derived" not in record, obj
    assert set(seen) == {
        "Model", "UserSpace", "ItemSpace", "DynamicSpace", "Cells",
        "DynamicCells", "ReferenceProxy", "DynamicReferenceProxy"}, seen
