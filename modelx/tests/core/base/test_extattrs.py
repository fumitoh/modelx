"""Extattrs resolve on the class only (F11, decision 13), and the other
snapshot-wire defects that 0.34 fixes.

``_get_attrdict(extattrs)`` adds each requested name that the dict does
not have, through ``_get_attrdict_extra``. On 0.33 that method read the
name from the object, with ``hasattr`` and ``getattr``, and called a
callable value. On a Model or a Space a name that the class does not
define falls through to ``__getattr__``, which returns a member of that
name: a user's Reference, Cells or Space. From 0.34 the name is looked up
on the class only: a property is read, a function is bound and called,
any other class attribute is added as it is, and a ReferenceProxy also
looks on Interface, for properties and functions only, as its
``__getattr__`` forwards them. A name the class does not define is
skipped, and so is a property whose getter raises AttributeError.

The ``hostile`` model has members named like spyder-modelx's requests:
global References ``__len__``, ``_is_derived``, ``formula`` and
``parameters``, a Space Reference and a Cells named ``argvalues``, and a
Space formula that returns a ref named ``_is_derived``, each a function
that records its calls. Measured with the 0.33 rule (``extra_033`` below,
copied from 10188ae): spyder's tree list called them 20 times in one
whole-model walk, the same list with ``argvalues`` and ``_is_dynamic`` 21
times and put the Cells named ``argvalues`` into a Space's record, and
the Properties list called the globals ``formula`` and ``parameters`` on
the Model, 2 times. With the class-only rule: 0 calls, and the only keys
that go are the 44 whose values came from those members
(``test_only_member_keys_go``).

``extra_033`` is kept as an oracle. On models with no member named like a
request, the spyder fixture and lifelib's BasicTerm_S and simplelife, the
class-only rule gives the same dicts as the 0.33 rule, key order included
(``test_same_as_033``). Measured in separate processes, ids normalised, on
lifelib's BasicTerm_S, BasicTerm_SE with 1,000 ItemSpaces, BasicTerm_ME,
CashValue_ME and simplelife: the tree list (59,322 records), the tree list
with ``_is_dynamic`` and ``argvalues`` (59,322), the Properties list on
every object (55,016), ``_baseattrs`` (122,430) and the node records of
every stored value (128,886) were identical to those of the code before
this change (f1f63ed). Against 0.33 (10188ae) they differed only in keys
that T2 and T3 change: ``'_is_derived'`` added to Reference records,
``'_is_dynamic'`` gone from Space records, and a ``'value_type'`` of
``'DynamicCells'``.

Also tested here:

* The ``refs`` view skips a key that is not a str. A Space formula can
  return one, ``{'refs': {1: 'one'}}``, which no formula can read. On 0.33
  it made the dict of the ItemSpace's ``refs`` view raise ``KeyError: 1``,
  and so the whole-model walk, and ``_baseattrs`` raised RuntimeError.
* ``RefView._baseattrs_private`` works. On 0.33 it was BaseView's, which
  asks the value of each Reference for its ``_baseattrs``, and raised
  RuntimeError (from ``AttributeError: module 'builtins' has no attribute
  '_baseattrs'``).
* The dicts of an ItemNode with no stored value give None for the
  lengths of its lists, as for ``'value'``. On 0.33 they raised
  ValueError ("... has no cached value for the given arguments", or
  "... is not cached").

The tests read only the tool API and the public API to check a result.
To make the oracle and to count calls they replace class attributes with
``monkeypatch``, and ``test_object_node_lists`` makes its node through an
internal route, as it says.
"""

import collections

import pytest

import modelx as mx
from modelx.core.base import Interface
from modelx.core.model import Model
from modelx.core.space import BaseSpace
from modelx.tests.core.base.test_spyder_requests import (
    TREE_ATTRS, PROPERTY_ATTRS, build_model)
from modelx.tests.core.space.inheritance.test_tool_flags import walk_records

# ['_is_derived', '__len__', '_evalrepr']
TREE = TREE_ATTRS
# ['formula', '_evalrepr', 'allow_none', 'parameters']
PROPS = PROPERTY_ATTRS
TREE_EXT = TREE + ["argvalues", "_is_dynamic"]


def extra_033(self, attrdict, extattrs=None, recursive=True):
    """``Interface._get_attrdict_extra`` of modelx 0.33 (10188ae), verbatim."""
    for name in extattrs:
        if name not in attrdict and hasattr(self, name):
            attr = getattr(self, name)
            if hasattr(attr, "_get_attrdict"):
                attrdict[name] = attr._get_attrdict(extattrs, recursive)
            elif callable(attr):
                attrdict[name] = attr()
            else:
                attrdict[name] = attr


CALLS = []


def member(tag):
    """A user's function that records each call."""
    def func(*args, **kwargs):
        CALLS.append(tag)
        return "called " + tag
    return func


def build_hostile(name):
    m = mx.new_model(name)
    for ref in ("__len__", "_is_derived", "formula", "parameters"):
        setattr(m, ref, member("global " + ref))

    s = m.new_space("S")
    s.new_cells("foo", formula="lambda x: 2 * x + k")
    s.k = 1
    s.f = member("Space Reference f")

    m.new_space("A").argvalues = member("Space Reference argvalues")
    m.new_space("C").new_cells("argvalues", formula="lambda: 1")

    p = m.new_space("P", formula="lambda i: {'refs': {'_is_derived': fr}}")
    p.fr = member("formula ref _is_derived")
    p.new_cells("h", formula="lambda x: i * x")
    p.new_space("Child").new_cells("g", formula="lambda: 1")

    s.foo(1)
    p[1].h(2)
    p[1].Child.g()
    CALLS.clear()
    return m


@pytest.fixture
def hostile():
    m = build_hostile("ExtAttrsHostile")
    yield m
    m._impl._check_sanity()
    m.close()


def tree_objects(m):
    """The Model and every object in its tree, as spyder's Explorer lists
    them: Spaces, ItemSpaces and DynamicSpaces, Cells, and the References
    that the ``refs`` views list."""
    tree = m._get_attrdict(recursive=True)
    return [obj for _, obj in walk_records(tree, m)]


# spyder's tree list, the tree list with ``argvalues`` and ``_is_dynamic``,
# and the Properties list on every object of the tree.
OUTPUTS = {
    "tree": lambda m: m._get_attrdict(TREE, recursive=True),
    "tree_ext": lambda m: m._get_attrdict(TREE_EXT, recursive=True),
    "props": lambda m: [obj._get_attrdict(PROPS, recursive=False)
                        for obj in tree_objects(m)],
}


def outputs(m):
    return {key: make(m) for key, make in OUTPUTS.items()}


def outputs_033(m, monkeypatch):
    """The outputs with the 0.33 rule, and the user calls each made."""
    old, calls = {}, {}
    with monkeypatch.context() as mp:
        mp.setattr(Interface, "_get_attrdict_extra", extra_033)
        for key, make in OUTPUTS.items():
            CALLS.clear()
            old[key] = make(m)
            calls[key] = dict(collections.Counter(CALLS))
    CALLS.clear()
    return old, calls


# The names of TREE that each kind of record has, by its 'type'.
TREE_KEYS = {
    "Model": {"_evalrepr"},
    "UserSpace": {"_evalrepr"},
    "ItemSpace": {"_evalrepr"},
    "DynamicSpace": {"_evalrepr"},
    "Cells": {"_is_derived", "__len__", "_evalrepr"},
    "Reference": {"_is_derived", "_evalrepr"},
}

# The names of PROPS that each kind of record has. 'parameters' is a key
# of every Space and Cells dict without extattrs.
PROPS_KEYS = {
    "Model": {"_evalrepr", "allow_none"},
    "UserSpace": set(PROPS),
    "ItemSpace": set(PROPS),
    "DynamicSpace": set(PROPS),
    "Cells": set(PROPS),
    "Reference": {"_evalrepr", "allow_none"},
}


# --------------------------------------------------------------------------
# spyder's lists call nothing and add no key from a member

def test_tree_list(hostile):
    """spyder's tree list on the whole model: no user function is called,
    and each record has the names its class defines, with modelx's
    answers. The Model record has no ``_is_derived`` or ``__len__``,
    though globals of those names exist."""
    m = hostile
    tree = m._get_attrdict(TREE, recursive=True)
    assert CALLS == []

    kinds = collections.Counter()
    for record, obj in walk_records(tree, m):
        kinds[record["type"]] += 1
        assert set(record) & set(TREE) == TREE_KEYS[record["type"]], (
            record["fullname"])
        assert record["_evalrepr"] == obj._evalrepr
        if record["type"] in ("Cells", "Reference"):
            assert record["_is_derived"] is obj._is_derived()
        if record["type"] == "Cells":
            assert record["__len__"] == len(obj)

    assert kinds == {"Model": 1, "UserSpace": 5, "ItemSpace": 1,
                     "DynamicSpace": 1, "Cells": 6, "Reference": 23}
    assert {"__len__", "_is_derived"} <= set(m.refs)
    assert CALLS == []


def test_properties_list(hostile):
    """spyder's Properties list on every object: nothing is called, and
    the Model record has no ``formula`` or ``parameters``, though globals
    of those names exist."""
    m = hostile
    objs = tree_objects(m)
    assert len(objs) == 1 + 7 + 6 + 23    # as test_tree_list counts them

    for obj in objs:
        record = obj._get_attrdict(PROPS, recursive=False)
        assert set(record) & set(PROPS) == PROPS_KEYS[record["type"]], (
            record["fullname"])
        assert record["_evalrepr"] == obj._evalrepr
        assert record["allow_none"] == obj.allow_none
        if "formula" in record:
            formula = obj.formula
            assert record["formula"] == (
                None if formula is None else {"source": formula.source})
            assert record["parameters"] == obj.parameters

    assert {"formula", "parameters"} <= set(m.refs)
    assert CALLS == []


def test_argvalues_reaches_no_member(hostile):
    """``argvalues`` answers on an ItemSpace only. A Space Reference and a
    Cells of that name are not read."""
    m = hostile
    tree = m._get_attrdict(TREE + ["argvalues"], recursive=True)
    items = 0
    for record, obj in walk_records(tree, m):
        if record["type"] == "ItemSpace":
            assert record["argvalues"] == obj.argvalues == (1,)
            items += 1
        else:
            assert "argvalues" not in record, record["fullname"]
    assert items == 1
    assert "argvalues" in m.A.refs and "argvalues" in m.C.cells
    assert CALLS == []


def test_formula_ref_named_is_derived(hostile):
    """A ref that a Space formula returns as ``_is_derived`` is not read:
    an ItemSpace has no ``_is_derived``."""
    item = hostile.P[1]
    assert "_is_derived" in item.refs
    for recursive in (True, False):
        assert "_is_derived" not in item._get_attrdict(TREE, recursive)
    assert CALLS == []


def test_walks_reach_no_getattr(hostile, monkeypatch):
    """No name is resolved through ``Model.__getattr__`` or
    ``BaseSpace.__getattr__`` in the walks, whatever is requested."""
    m = hostile
    objs = tree_objects(m)
    hits = []
    for cls in (Model, BaseSpace):
        def counting(self, name, orig=cls.__getattr__):
            hits.append(name)
            return orig(self, name)
        monkeypatch.setattr(cls, "__getattr__", counting)

    m._get_attrdict(TREE_EXT, recursive=True)
    for obj in objs:
        obj._get_attrdict(PROPS + TREE_EXT, recursive=False)
    assert hits == []

    m.formula, m.P[1].h     # the counters are in place
    assert hits == ["formula", "P", "h"]


def test_only_member_keys_go(hostile, monkeypatch):
    """Against the 0.33 rule, on the ``hostile`` model: every difference is
    a key that 0.34 leaves out, and its 0.33 value came from a user's
    member, either a recorded call or the dict of the Cells named
    ``argvalues``. Nothing else changes."""
    m = hostile
    new = outputs(m)
    assert CALLS == []
    old, calls = outputs_033(m, monkeypatch)
    # The 0.33 tree walk makes the Model's record and 9 Space records: the
    # Model's 4 Spaces, P[1], and P.Child and P[1].Child twice each, under
    # 'spaces' and 'named_spaces'. Each read __len__ from the global, and
    # each but P[1]'s read _is_derived from the global; P[1]'s read the
    # formula ref.
    tree = {"global __len__": 1 + 9, "global _is_derived": 1 + 8,
            "formula ref _is_derived": 1}
    assert calls == {
        "tree": tree,
        "tree_ext": dict(tree, **{"Space Reference argvalues": 1}),
        "props": {"global formula": 1, "global parameters": 1}}

    gone = []

    def diff(a, b, path):
        if isinstance(a, dict):
            assert isinstance(b, dict), path
            # b has no key that a lacks, and the same order
            assert [k for k in a if k in b] == list(b), path
            for k in a:
                if k in b:
                    diff(a[k], b[k], path + (k,))
                else:
                    gone.append((path, k, a[k]))
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, path + (i,))
        else:
            assert a == b, path

    diff(old, new, ())
    for path, key, value in gone:
        if key == "argvalues" and isinstance(value, dict):
            assert value["namedid"] == "C.argvalues", path
        else:
            assert isinstance(value, str) and value.startswith("called "), (
                path, key, value)
    # 2 keys in each of the 10 records of each tree walk, argvalues in A's
    # and C's records of the second, and formula and parameters in the
    # Model's Properties record.
    assert len(gone) == 2 * 10 + (2 * 10 + 2) + 2


# --------------------------------------------------------------------------
# The rule

def test_property_value_is_added_as_it_is(hostile):
    """A property's value is added as it is, so a Reference's value that is
    a user's function is not called; on 0.33 it was. A value whose class
    defines ``_get_attrdict`` is replaced by its dict."""
    s = hostile.S
    proxy = s._get_object("f", as_proxy=True)
    assert proxy._get_attrdict(["value"])["value"] is proxy.value
    assert CALLS == []

    # Whether the value has a dict of its own is asked of its class, so a
    # user's __getattr__ is not called for '_get_attrdict' either.
    class Anything:
        def __getattr__(self, name):
            CALLS.append("Anything." + name)
            return member("Anything." + name)

    s.anything = Anything()
    CALLS.clear()
    proxy = s._get_object("anything", as_proxy=True)
    assert proxy._get_attrdict(["value"])["value"] is proxy.value
    assert CALLS == []

    record = s.foo._get_attrdict(["parent", "formula"], recursive=False)
    assert record["parent"] == s._get_attrdict(["parent", "formula"],
                                               recursive=False)
    assert record["parent"]["parent"] == hostile._get_attrdict(
        ["parent", "formula"], recursive=False)
    assert record["formula"] == {"source": s.foo.formula.source}


def test_methods_called_and_attributes_added(hostile):
    """A function is bound and called with no arguments; any other class
    attribute is added as it is."""
    foo = hostile.S.foo
    record = foo._get_attrdict(
        ["_is_derived", "__len__", "_get_repr", "properties"],
        recursive=False)
    assert record["_is_derived"] is False
    assert record["__len__"] == len(foo) == 1
    assert record["_get_repr"] == foo._get_repr()
    assert record["properties"] == type(foo).properties


PROXIES = {
    "global Reference": lambda m: m._get_object("formula", as_proxy=True),
    "Space Reference": lambda m: m.S._get_object("k", as_proxy=True),
    "ItemSpace argument": lambda m: m.P[1]._get_object("i", as_proxy=True),
}


@pytest.mark.parametrize("get", PROXIES.values(), ids=list(PROXIES))
def test_proxy_looks_on_interface(hostile, get):
    """A proxy answers the properties and functions of Interface, as its
    attribute forwarding does, ``allow_none`` included, and nothing else
    of Interface: not its ``properties`` list."""
    proxy = get(hostile)
    record = proxy._get_attrdict(
        ["allow_none", "doc", "_get_repr", "properties", "__len__"],
        recursive=False)
    assert "allow_none" in record
    assert record["allow_none"] == proxy.allow_none
    assert record["doc"] == proxy.doc
    assert record["_get_repr"] == proxy._get_repr()
    assert "properties" not in record and "__len__" not in record
    assert CALLS == []


def test_getter_raising_attributeerror_is_skipped(hostile, monkeypatch):
    """A property whose getter raises AttributeError is skipped, on every
    kind, and no member of its name is read instead, though a global of
    that name exists. Any other error is raised, as on 0.33."""
    m = hostile
    m._probe = member("global _probe")

    def absent(self):
        raise AttributeError("absent")

    def broken(self):
        raise KeyError("broken")

    monkeypatch.setattr(Interface, "_probe", property(absent), raising=False)
    monkeypatch.setattr(Interface, "_broken", property(broken), raising=False)
    objs = [m, m.S, m.S.foo, m.P[1], m.P[1].h,
            *(get(m) for get in PROXIES.values())]
    for obj in objs:
        assert "_probe" not in obj._get_attrdict(["_probe"], recursive=False)
        with pytest.raises(KeyError):
            obj._get_attrdict(["_broken"], recursive=False)
    assert CALLS == []


# --------------------------------------------------------------------------
# Same output as 0.33 where no member is named like a request

def lifelib_model(library, name, calc):
    def load(tmp_path):
        lifelib = pytest.importorskip("lifelib")
        lifelib.create(library, tmp_path / library)
        m = mx.read_model(tmp_path / library / name,
                          name="ExtAttrs" + library.capitalize())
        calc(m)
        return m
    return load


def calc_basicterm_s(m):
    m.Projection[1].pv_net_cf()
    m.Projection[2].pv_net_cf()


def calc_simplelife(m):
    m.Projection[1].PV_NetCashflow(0)
    m.Projection[2].PV_NetCashflow(0)


MODELS = {
    "spyder fixture": lambda tmp_path: build_model(),
    "BasicTerm_S": lifelib_model("basiclife", "BasicTerm_S", calc_basicterm_s),
    "simplelife": lifelib_model("simplelife", "model", calc_simplelife),
}


@pytest.mark.parametrize("load", MODELS.values(), ids=list(MODELS))
def test_same_as_033(load, tmp_path, monkeypatch):
    """The tree list, the tree list with ``argvalues`` and ``_is_dynamic``,
    and the Properties list on every object give the same dicts as the
    0.33 rule, key order included, on models with no member named like a
    request."""
    m = load(tmp_path)
    try:
        new = outputs(m)
        old, calls = outputs_033(m, monkeypatch)
        assert calls == {"tree": {}, "tree_ext": {}, "props": {}}
        assert new == old
        assert repr(new) == repr(old)
        assert len(new["props"]) > 20
    finally:
        m._impl._check_sanity()
        m.close()


# --------------------------------------------------------------------------
# The refs view

@pytest.fixture
def refs_model():
    m = mx.new_model("ExtAttrsRefs")
    m.g = 3
    m._ug = 4
    s = m.new_space("S", refs={"_u": 2})
    s.k = 1
    q = m.new_space(
        "Q", formula="lambda i: {'refs': {1: 'one', '': 0, 'two': 2}}")
    q[1]
    yield m
    m._impl._check_sanity()
    m.close()


def test_non_str_ref_key(refs_model):
    """A ref that a Space formula returns under a key that is not a str is
    left out of the ``refs`` view's dicts, and the whole-model walk
    passes. The item's row lists its str refs, the empty name included,
    which does not start with an underscore."""
    m = refs_model
    item = m.Q[1]
    assert 1 in list(item.refs) and item.two == 2
    str_refs = {"i", "two", "", "g"}     # g is a global
    assert str_refs == {n for n in item.refs
                        if isinstance(n, str) and n[:1] != "_"}

    assert set(item.refs._get_attrdict()["items"]) == str_refs
    assert set(item.refs._baseattrs["items"]) == str_refs

    tree = m._get_attrdict(TREE, recursive=True)
    row = tree["spaces"]["items"]["Q"]["_named_itemspaces"]["items"][
        item.name]
    assert set(row["refs"]["items"]) == str_refs
    assert row["refs"]["items"]["two"]["_evalrepr"] == item._evalrepr + ".two"

    base = m._baseattrs
    row = base["spaces"]["items"]["Q"]["named_itemspaces"]["items"][
        item.name]
    assert set(row["refs"]["items"]) == str_refs


VIEWS = {
    "Model": lambda m: m.refs,
    "UserSpace": lambda m: m.S.refs,
    "ItemSpace": lambda m: m.Q[1].refs,
}


@pytest.mark.parametrize("get", VIEWS.values(), ids=list(VIEWS))
def test_refview_baseattrs_private(refs_model, get):
    """``_baseattrs_private`` of a ``refs`` view lists every str name,
    ``__builtins__`` and the other names that start with an underscore
    included, each with the Reference's ``_baseattrs``; for the other
    names, the same as ``_baseattrs``."""
    view = get(refs_model)
    private = view._baseattrs_private
    public = view._baseattrs
    assert private["type"] == public["type"] == "RefView"

    names = {n for n in view if isinstance(n, str)}
    assert "__builtins__" in names and any(
        n.startswith("_") and n != "__builtins__" for n in names)
    assert set(private["items"]) == names
    for name, record in private["items"].items():
        assert record["type"] == "Reference"
        assert record["name"] == name
        assert record["value_type"] == type(view[name]).__name__
        if not name.startswith("_"):
            assert record == public["items"][name]
    assert set(public["items"]) == {n for n in names if n[:1] != "_"}


# --------------------------------------------------------------------------
# Nodes

@pytest.fixture
def nodes_model():
    m = mx.new_model("ExtAttrsNodes")
    s = m.new_space("S")
    s.k = 1
    s.new_cells("foo", formula="lambda x: x + k")
    s.new_cells("unc", formula="lambda x: 2 * x")
    s.unc.is_cached = False
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda x: i * x")
    s.foo(1)
    p[1].h(2)
    yield m
    m._impl._check_sanity()
    m.close()


NO_VALUE = {
    "Cells, no stored value": lambda m: m.S.foo.node(5),
    "Cells not cached": lambda m: m.S.unc.node(1),
    "Space, no ItemSpace": lambda m: m.P.node(7),
    "DynamicCells, no stored value": lambda m: m.P[1].h.node(9),
}

WITH_VALUE = {
    "Cells": lambda m: m.S.foo.node(1),
    "Space": lambda m: m.P.node(1),
    "DynamicCells": lambda m: m.P[1].h.node(2),
}

LISTS = ("predslen", "succslen", "precedentslen")


@pytest.mark.parametrize("get", NO_VALUE.values(), ids=list(NO_VALUE))
def test_itemnode_without_value(nodes_model, get):
    """An ItemNode with no stored value has the keys of one with a value,
    with None for ``'value'``, ``'valid'`` and the lengths of its lists;
    ``_baseattrs`` likewise."""
    m = nodes_model
    node = get(m)
    assert not node.has_value()
    with pytest.raises(ValueError):
        node.preds

    record = node._get_attrdict(["formula"], recursive=False)
    assert list(record) == list(
        m.S.foo.node(1)._get_attrdict(["formula"], recursive=False))
    for key in ("value", "valid") + LISTS:
        assert record[key] is None, key
    assert record["args"] == node.args
    assert record["obj"] == node.obj._get_attrdict(["formula"], False)
    assert record["repr"] == node.obj._get_repr()

    base = node._baseattrs
    assert list(base) == list(m.S.foo.node(1)._baseattrs)
    for key in ("value", "predslen", "succslen"):
        assert base[key] is None, key


@pytest.mark.parametrize("get", WITH_VALUE.values(), ids=list(WITH_VALUE))
def test_itemnode_with_value(nodes_model, get):
    """An ItemNode with a value gives the lengths of its lists."""
    node = get(nodes_model)
    assert node.has_value()
    record = node._get_attrdict()
    assert record["value"] is node.value
    assert record["valid"] == id(node.value)
    assert record["predslen"] == len(node.preds)
    assert record["succslen"] == len(node.succs)
    assert record["precedentslen"] == len(node.precedents)
    base = node._baseattrs
    assert (base["predslen"], base["succslen"]) == (
        len(node.preds), len(node.succs))


def test_reference_node_lists(nodes_model):
    """A ReferenceNode has no arguments, and its lists are empty: 0, not
    None. Its value is the Reference's."""
    nodes = [n for n in nodes_model.S.foo.precedents(1) if n.args is None]
    assert len(nodes) == 1
    record = nodes[0]._get_attrdict()
    assert record["value"] == nodes[0].value == 1
    assert [record[key] for key in LISTS] == [0, 0, 0]
    base = nodes[0]._baseattrs
    assert (base["predslen"], base["succslen"]) == (0, 0)


def test_object_node_lists(nodes_model):
    """An ObjectNode of a Cells has no value and no arguments, and its
    lists are empty: 0, not None, as on 0.33.

    No public or tool-API route gives such a node on this release, so it
    is made through the internal ``get_referents()`` of the Cells' impl,
    the route T10 is to expose; the result is read through the node's own
    dicts only."""
    nodes_model.S.new_cells("bar", formula="lambda: foo(1)")
    node = nodes_model.S.bar._impl.get_referents()["cells"]["foo"]
    assert type(node).__name__ == "ObjectNode"
    assert not node.has_value() and node.args is None
    record = node._get_attrdict()
    assert record["value"] is None
    assert [record[key] for key in LISTS] == [0, 0, 0]
    base = node._baseattrs
    assert (base["predslen"], base["succslen"]) == (0, 0)
