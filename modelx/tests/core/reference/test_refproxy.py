"""ReferenceProxy as a tool object.

devnotes/ToolAPIDesign.md, section 6, PR 3: T5's members and F2.

* Equality and hash go by the Reference a proxy stands for, whichever
  call made the proxy and of either class.  A proxy is never equal to
  anything that is not a proxy, and comparing one never evaluates the
  model: before 0.34 ``proxy == cells`` asked the Cells, which raised
  TypeError for a Cells with parameters and ran the formula of a scalar
  Cells.
* ``_is_valid()`` is True while the Space or the Model that holds the
  Reference still holds it under its name, and that Space has not been
  deleted or made again.  It turns False after a rebind or a
  delete of the Reference, of the base Reference of a derived copy, of
  the Space, and of the ItemSpace that holds an argument, a formula ref
  or a system binding, and stays False when an ItemSpace with the same
  arguments is made again.  A closed Model's References stay valid.
* ``_refmodes`` is the tuple of modes, and ``refmode`` is one of them or
  None, as documented, apart from the known limitations it lists, which
  no test pins.
* F2: ``UserSpace.set_ref`` raises ValueError for any other mode, and
  changes nothing then.  Models whose files hold another mode still read:
  modelx/tests/serialize/refmode/test_refmode.py.

The system bindings ``_self``, ``_space`` and ``_model`` are in no
``refs`` view, so their proxies are taken as the ``obj`` of the
ReferenceNodes among a Cells' precedents.  The tests read only the tool
API and the public API.  Each model is torn down by
``_impl._check_sanity()`` and then ``close()``.
"""

import copy
import itertools

import pytest

import modelx as mx

SYSTEM = ("_self", "_space", "_model")
SYS_FORMULA = "lambda: (_self, _space, _model)"


def build():
    """
        RefProxy--B----k=2, ka=3 (absolute), kr=4 (relative),
          |  g=1  |    readk(), f(x), sys()
          |       Sub(B)
          |       S0---z=4, sys()
          |       NS---nr=5 (new_space(refs=))
          |       P(i)----k=3, sys(), Child----sys()
          |               Space formula returns ref fr
    """
    m = mx.new_model("RefProxy")
    m.g = 1
    b = m.new_space("B")
    b.k = 2
    b.absref(ka=3)
    b.relref(kr=4)
    b.new_cells("readk", formula="lambda: k")
    b.new_cells("f", formula="lambda x: x")
    b.new_cells("sys", formula=SYS_FORMULA)
    m.new_space("Sub", bases=b)
    s0 = m.new_space("S0")
    s0.z = 4
    s0.new_cells("sys", formula=SYS_FORMULA)
    m.new_space("NS", refs={"nr": 5})
    p = m.new_space("P", formula="lambda i: {'refs': {'fr': i}}")
    p.k = 3
    p.new_cells("sys", formula=SYS_FORMULA)
    p.new_space("Child").new_cells("sys", formula=SYS_FORMULA)
    return m


@pytest.fixture
def refmodel():
    m = build()
    yield m
    m._impl._check_sanity()
    m.close()


def system(cells):
    """{name: proxy} of the system bindings that ``cells`` reads."""
    cells()
    return {n.obj.name: n.obj for n in cells.precedents()
            if n.obj.name in SYSTEM}


def item_bindings(item):
    """Fresh proxies of the References an ItemSpace makes."""
    got = {"argument": item._get_object("i", as_proxy=True),
           "formula ref": item._get_object("fr", as_proxy=True)}
    for where, cells in (("item", item.sys), ("item.Child", item.Child.sys)):
        for name, proxy in system(cells).items():
            got["system %s.%s" % (where, name)] = proxy
    return got


def bindings(m):
    """{label: proxy}, fresh proxies to one binding of each kind."""
    got = {
        "global": m._get_object("g", as_proxy=True),
        "global through a Space": m.B._get_object("g", as_proxy=True),
        "Space": m.B._get_object("k", as_proxy=True),
        "derived": m.Sub._get_object("k", as_proxy=True),
        "S0": m.S0._get_object("z", as_proxy=True),
        "shared through an ItemSpace": m.P[1]._get_object(
            "k", as_proxy=True),
    }
    for where, cells in (("B", m.B.sys), ("S0", m.S0.sys)):
        for name, proxy in system(cells).items():
            got["system %s.%s" % (where, name)] = proxy
    got.update(item_bindings(m.P[1]))
    return got


ITEM_LABELS = ("argument", "formula ref") + tuple(
    "system %s.%s" % (where, name)
    for where in ("item", "item.Child") for name in SYSTEM)


# --------------------------------------------------------------------------
# Equality and hash

def test_equal_by_binding(refmodel):
    """Two proxies to one Reference are equal and hash equally, and make a
    set of 1; a copy is equal to its original."""
    m = refmodel
    first, second = bindings(m), bindings(m)
    assert len(first) == 6 + 6 + len(ITEM_LABELS)
    for label, proxy in first.items():
        other = second[label]
        assert proxy is not other
        assert proxy == other, label
        assert not proxy != other, label
        assert hash(proxy) == hash(other), label
        assert len({proxy, other}) == 1, label
        assert {proxy: label}[other] == label
        dup = copy.copy(proxy)
        assert dup == proxy and hash(dup) == hash(proxy), label


def test_equal_whichever_call_made_it(refmodel):
    """A proxy from get_object, from _get_object and from a ReferenceNode
    are equal; so are a Reference of a Space seen through its ItemSpace
    and through the Space, and a global seen through the Model and a
    Space."""
    m = refmodel
    k = m.B._get_object("k", as_proxy=True)
    m.B.readk()
    node_k = m.B.readk.precedents()[0].obj
    assert node_k.name == "k"
    assert mx.get_object("RefProxy.B.k", as_proxy=True) == k == node_k
    assert (m.P[1]._get_object("k", as_proxy=True)
            == m.P._get_object("k", as_proxy=True))
    assert (m._get_object("g", as_proxy=True)
            == m.B._get_object("g", as_proxy=True)
            == m.P[1]._get_object("g", as_proxy=True))


def test_unequal_bindings(refmodel):
    """Proxies to different References are unequal: each pair of the
    bindings above, B.k and its copy Sub.k among them, whose values are
    equal, and the argument i, or the formula ref fr, of P[1] and of
    P[2]."""
    m = refmodel
    proxies = bindings(m)
    distinct = dict(proxies)
    del distinct["global through a Space"]      # the global itself
    for (la, a), (lb, b) in itertools.combinations(distinct.items(), 2):
        assert a != b, (la, lb)
        assert not a == b, (la, lb)
    assert len(set(distinct.values())) == len(distinct)
    assert (m.P[1]._get_object("i", as_proxy=True)
            != m.P[2]._get_object("i", as_proxy=True))
    assert (m.P[1]._get_object("fr", as_proxy=True)
            != m.P[2]._get_object("fr", as_proxy=True))


def test_never_equal_to_other_objects(refmodel):
    """A proxy equals nothing that is not a proxy, its value included,
    and comparing it asks no other object: no TypeError from a Cells with
    parameters, and a scalar Cells is not evaluated."""
    m = refmodel
    k = m.B._get_object("k", as_proxy=True)
    nodes = len(m.tracegraph)
    for other in (k.value, 2, None, "k", k._idstr, m.B, m.B.f, m.B.readk,
                  m.B.readk.node()):
        assert (k == other) is False, other
        assert (k != other) is True, other
    assert len(m.tracegraph) == nodes
    assert not m.B.readk.node().has_value()


# --------------------------------------------------------------------------
# _is_valid()

def test_valid_while_bound(refmodel):
    for label, proxy in bindings(refmodel).items():
        assert proxy._is_valid() is True, label


def del_attr(name):
    def edit(m):
        obj, _, attr = name.rpartition(".")
        delattr(m if not obj else m._get_object(obj), attr)
    return edit


def set_attr(name, value):
    def edit(m):
        obj, _, attr = name.rpartition(".")
        setattr(m if not obj else m._get_object(obj), attr, value)
    return edit


def del_item(m):
    del m.P[1]


ALL = ("global", "global through a Space", "Space", "derived", "S0",
       "shared through an ItemSpace", "system B._self", "system B._space",
       "system B._model", "system S0._self", "system S0._space",
       "system S0._model") + ITEM_LABELS

# (edit, the bindings it ends, the bindings it must leave valid)
EDITS = {
    "rebind a Space Reference and so its copy": (
        set_attr("B.k", 20), ("Space", "derived"),
        ("global", "S0", "system B._self", "system B._space",
         "system B._model", "shared through an ItemSpace")),
    "delete a Space Reference and so its copy": (
        del_attr("B.k"), ("Space", "derived"),
        ("global", "S0", "system B._space", "shared through an ItemSpace")),
    "rebind a global": (
        set_attr("g", 5), ("global", "global through a Space"),
        ("Space", "derived", "S0", "system B._space")),
    "delete a global": (
        del_attr("g"), ("global", "global through a Space"),
        ("Space", "derived", "S0", "system S0._model")),
    "delete a Space": (
        del_attr("S0"), ("S0", "system S0._self", "system S0._space",
                         "system S0._model"),
        ("global", "Space", "derived", "system B._space")),
    "delete an ItemSpace": (
        del_item, ITEM_LABELS,
        ("global", "Space", "derived", "shared through an ItemSpace")),
    "clear the ItemSpaces": (
        lambda m: m.P.clear_items(), ITEM_LABELS,
        ("global", "Space", "derived", "shared through an ItemSpace")),
    "rebind a Reference of the Space with the ItemSpaces": (
        set_attr("P.k", 30), ("shared through an ItemSpace",) + ITEM_LABELS,
        ("global", "Space", "derived", "S0")),
}


@pytest.mark.parametrize("edit", EDITS)
def test_invalid_after_edit(refmodel, edit):
    m = refmodel
    apply, ended, kept = EDITS[edit]
    proxies = bindings(m)
    apply(m)
    for label in ended:
        assert proxies[label]._is_valid() is False, label
    for label in kept:
        assert proxies[label]._is_valid() is True, label
    assert set(ended).isdisjoint(kept)
    assert set(ended) | set(kept) <= set(ALL)


def test_repr_of_an_ended_binding(refmodel):
    m = refmodel
    k = m.B._get_object("k", as_proxy=True)
    i = m.P[1]._get_object("i", as_proxy=True)
    assert repr(k) == "<ReferenceProxy RefProxy.B.k>"
    assert repr(i) == "<DynamicReferenceProxy RefProxy.P[1].i>"
    m.B.k = 20
    del m.P[1]
    assert repr(k) == "<ReferenceProxy null object>"
    assert repr(i) == "<DynamicReferenceProxy null object>"


def make_again_by_delete(m):
    del m.P[3]
    return m.P[3]


def make_again_by_clear(m):
    m.P.clear_items()
    return m.P[3]


def make_again_by_rebind(m):
    m.P.k = 30
    return m.P[3]


@pytest.mark.parametrize("make_again", [
    make_again_by_delete, make_again_by_clear, make_again_by_rebind])
def test_invalid_after_itemspace_made_again(refmodel, make_again):
    """An ItemSpace made again with the same arguments has References of
    its own.  modelx re-uses the interface of the old ItemSpace, and the
    old ItemSpace keeps its dicts, so a test that asked the parent's
    interface, or the container alone, answered True again for a kept
    argument and formula ref (refute2/r08, r08b; fix-final/e03)."""
    m = refmodel
    old = item_bindings(m.P[3])
    item = make_again(m)
    assert item.argvalues == (3,)
    new = item_bindings(item)
    assert set(new) == set(old) == set(ITEM_LABELS)
    for label in ITEM_LABELS:
        assert old[label]._is_valid() is False, label
        assert new[label]._is_valid() is True, label
        assert old[label] != new[label], label
        assert old[label].name == new[label].name


def test_is_valid_where_no_reference_is_held():
    """A proxy that stands for no Reference answers a bool and raises
    nothing: on this release, a slot of an ItemSpace that holds the
    ItemSpace's copy of a Space or a Cells (``P[1].rel`` for
    ``P.rel = P.Child``), and one that holds None (``PP[1].r`` for
    ``PP.r = PPX``).  Which bool is a known limitation, not pinned.  A
    whole-model ``_get_attrdict(['_is_valid'])`` asks every proxy."""
    m = mx.new_model("NoRef")
    p = m.new_space("P", formula="lambda i: None")
    p.rel = p.new_space("Child")
    p.relc = p.new_cells("h", formula="lambda: 1")
    pp = m.new_space("PP", formula="lambda i: None")
    pp.r = m.new_space("PPX")
    item = p[1]
    for name, copy_ in (("rel", item.Child), ("relc", item.h)):
        proxy = item._get_object(name, as_proxy=True)
        assert proxy.value is copy_
        assert isinstance(proxy._is_valid(), bool), name
    assert isinstance(pp[1]._get_object("r", as_proxy=True)._is_valid(), bool)
    del m.PP
    record = m._get_attrdict(["_is_valid"], recursive=True)
    items = record["spaces"]["items"]["P"]["_named_itemspaces"]["items"]
    refs = items["__Space1"]["refs"]["items"]
    assert isinstance(refs["rel"]["_is_valid"], bool)
    assert isinstance(refs["relc"]["_is_valid"], bool)
    m._impl._check_sanity()
    m.close()


def test_closed_model_stays_valid():
    """A closed Model's References stay valid (fix-final/e03).  Whether
    the closed Model itself answers True is a known limitation, not
    pinned."""
    m = build()
    proxies = bindings(m)
    m._impl._check_sanity()
    m.close()
    for label, proxy in proxies.items():
        assert proxy._is_valid() is True, label


# --------------------------------------------------------------------------
# _refmodes and refmode

def test_refmodes(refmodel):
    m = refmodel
    for proxy in (m.B._get_object("k", as_proxy=True),
                  m.P[1]._get_object("i", as_proxy=True)):
        assert type(proxy).__name__ in ("ReferenceProxy",
                                        "DynamicReferenceProxy")
        assert type(proxy)._refmodes == ("auto", "absolute", "relative")
        assert proxy._refmodes is type(proxy)._refmodes


def test_refmode_by_kind(refmodel):
    """refmode is one of _refmodes for a Reference of a Space, its copies,
    the same Reference seen through an ItemSpace, and a formula ref; None
    for a global, an argument and a system binding."""
    m = refmodel
    modes = {
        "B.k": "auto", "B.ka": "absolute", "B.kr": "relative",
        "Sub.k": "auto", "Sub.ka": "absolute", "Sub.kr": "relative",
        "NS.nr": "auto",
    }
    for name, mode in modes.items():
        space, _, ref = name.partition(".")
        assert m._get_object(space)._get_object(
            ref, as_proxy=True).refmode == mode, name
    proxies = bindings(m)
    assert proxies["shared through an ItemSpace"].refmode == "auto"
    assert proxies["formula ref"].refmode == "auto"
    for label in ("global", "global through a Space", "argument") + tuple(
            label for label in proxies if label.startswith("system ")):
        assert proxies[label].refmode is None, label
    for label, proxy in proxies.items():
        assert proxy.refmode in proxy._refmodes + (None,), label


# --------------------------------------------------------------------------
# F2: set_ref validates refmode

INVALID_MODES = ["sideways", None, 42, "AUTO", "", ("auto",)]


@pytest.mark.parametrize("mode", INVALID_MODES)
def test_set_ref_refuses_a_new_reference(refmodel, mode):
    m = refmodel
    with pytest.raises(ValueError, match="refmode must be one of"):
        m.B.set_ref("new", 1, mode)
    assert "new" not in m.B.refs
    assert "new" not in m.Sub.refs


@pytest.mark.parametrize("mode", INVALID_MODES)
def test_set_ref_refuses_and_changes_nothing(refmodel, mode):
    """A refused set_ref on an existing Reference leaves its value, its
    mode, its binding and the computed values as they were."""
    m = refmodel
    k = m.B._get_object("k", as_proxy=True)
    assert m.B.readk() == 2
    nodes = len(m.tracegraph)
    with pytest.raises(ValueError, match="refmode must be one of"):
        m.B.set_ref("k", 99, mode)
    assert k._is_valid()
    assert k == m.B._get_object("k", as_proxy=True)
    assert (k.value, k.refmode) == (2, "auto")
    assert len(m.tracegraph) == nodes
    assert m.B.readk.node().has_value()


@pytest.mark.parametrize("mode", ["auto", "absolute", "relative"])
def test_set_ref_takes_each_mode(refmodel, mode):
    m = refmodel
    m.B.set_ref("new", m.B.readk, mode)
    proxy = m.B._get_object("new", as_proxy=True)
    assert proxy.refmode == mode
    assert m.Sub._get_object("new", as_proxy=True).refmode == mode
    assert proxy.value is m.B.readk


def test_absref_relref(refmodel):
    m = refmodel
    m.B.absref(a1=m.B.readk)
    m.B.relref(r1=m.B.readk)
    assert m.B._get_object("a1", as_proxy=True).refmode == "absolute"
    assert m.B._get_object("r1", as_proxy=True).refmode == "relative"
    assert m.Sub.a1 is m.B.readk
    assert m.Sub.r1 is m.Sub.readk


def test_baseattrs():

    m = mx.new_model()
    s = m.new_space()
    s.bar = 1
    attrs = mx.get_object(s.fullname + "." + "bar", as_proxy=True)._baseattrs

    assert attrs["name"] == "bar"
    assert attrs["fullname"] == s.fullname + "." + "bar"
    assert attrs["repr"] == "bar"
    assert attrs["namedid"] == s.name + ".bar"

    m._impl._check_sanity()
    m.close()
