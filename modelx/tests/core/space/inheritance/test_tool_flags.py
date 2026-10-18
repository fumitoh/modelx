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
on this release, is the proxy of a slot of an ItemSpace that holds the
ItemSpace's copy of a Space or a Cells (``P[1].rel`` for ``P.rel =
P.Child``): the slot holds the copy itself, not a Reference, until T5
(PR 3) gives it one.

Proxies are made at six sites, and each is checked: a ReferenceNode's
``obj``, ``Model._get_object`` and ``BaseSpace._get_object`` with
``as_proxy=True``, ``Model._get_refs``, and the ``_baseattrs`` and
``_get_attrdict`` of a ``refs`` view.  The views return no proxy, so the
class each makes is recorded by wrapping ``ReferenceProxy.__init__``,
which every proxy of either class runs.

T3, ``_is_derived()`` on Cells and References, has its own section at
the end of this module.

The tests read only the tool API and the public API.  They import the
classes Cells and ReferenceProxy only to check ``isinstance``, which code
outside the tool API relies on, and to wrap ``__init__`` as above.  Each
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
        FlagsModel--Base----foo(), bar(), k=1
          |  glob   Base2---baz()
          |  mac    Sub(Base)----foo() overridden
          |         MI(Base, Base2)
          |
          +---------P(i)----h(), sys(), k=5, rel -> P.Child
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
    base2 = m.new_space("Base2")
    base2.new_cells("baz", formula="lambda: 2")
    sub = m.new_space("Sub", bases=base)
    sub.foo.formula = "lambda: 10"
    m.new_space("MI", bases=[base, base2])

    p = m.new_space("P", formula="lambda i: {'refs': {'fr': 10 * i}}")
    p.new_cells("h", formula="lambda: i + fr + k + glob")
    p.new_cells("sys", formula="lambda: (_self, _space, _model)")
    p.k = 5
    child = p.new_space("Child", formula="lambda j: None")
    child.new_cells("w", formula="lambda: _self.n + _space.n + _model.glob")
    child.n = 1
    p.rel = child
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
             # The ItemSpace's copy of P.Child, in a slot that is not a
             # Reference until T5 (PR 3): see the module docstring.
             "rel": "ReferenceProxy"},
    "P[1][5]": {"i": "DynamicReferenceProxy", "fr": "DynamicReferenceProxy",
                "k": "ReferenceProxy", "glob": "ReferenceProxy",
                "rel": "ReferenceProxy"},
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


def test_isinstance_unchanged(flags_model):
    m = flags_model
    assert isinstance(m.P[1].h, Cells)
    assert isinstance(m.P[1].Child.w, Cells)
    assert isinstance(m.P[1]._get_object("i", as_proxy=True), ReferenceProxy)
    assert isinstance(m.P[1]._get_object("fr", as_proxy=True), ReferenceProxy)
    assert type(m.P.h) is Cells
    assert type(m.P[1].h) is not Cells
    assert type(m.P._get_object("k", as_proxy=True)) is ReferenceProxy


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
    rows = {"cells": set(), "refs": set()}

    def walk(attrdict):
        for key in ("cells", "refs"):
            for row in attrdict.get(key, {}).get("items", {}).values():
                rows[key].add(row["type"])
        for key in ("spaces", "named_itemspaces"):
            for row in attrdict.get(key, {}).get("items", {}).values():
                walk(row)

    walk(m._get_attrdict(recursive=True))
    assert rows == {"cells": {"Cells"}, "refs": {"Reference"}}


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
# T3: the _is_derived table (design section 6, PR 2)
#
# Comes with ReferenceProxy._is_derived() (T3): the _is_derived() table on
# static, derived, overriding and dynamic Cells and References; that
# Spaces and Models have no _is_derived class attribute (decision 4); and
# a whole-model _get_attrdict(['_is_derived', '_is_dynamic', '__len__',
# '_evalrepr']) that does not raise.
