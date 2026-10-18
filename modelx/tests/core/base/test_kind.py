"""T1: kinds are told by class name (devnotes/ToolAPIDesign.md, decision 14).

A tool tells what a value is from its class.  It first checks that the
class is modelx's own, that ``type(v).__module__`` is a str starting with
``"modelx."``, then reads ``type(v).__name__``.  No member is read, so the
check never runs ``Model.__getattr__`` or ``BaseSpace.__getattr__``, never
evaluates, and answers on a deleted object and on an object of a closed
model.  The twelve names in ``KINDS`` are frozen tool API (decisions 14
and 15); the exact module paths are not.  ``kind`` below is the recipe as
toolapi.rst gives it, and the other tool-API tests import it from here.

The module check is not optional: a Reference can hold an instance of a
user's own class named ``Model`` or ``Cells``, and only the module tells
it from a modelx object.  Nor may the check assume ``__module__`` is a
str: wrapt's pure-Python ObjectProxy puts a ``__module__`` property into
every proxy class, so ``type(proxy).__module__.startswith`` raised
AttributeError (names14/probe_edge.py).

The name is the exact kind.  An ItemSpace is ``'ItemSpace'``, never
``'DynamicSpace'``, although its class subclasses DynamicSpace.  A Cells
of an ItemSpace or of a DynamicSpace in one is ``'DynamicCells'``, and a
proxy of a Reference whose parent is such a Space is
``'DynamicReferenceProxy'`` (decision 15); "any Cells" is
``kind(v) in {'Cells', 'DynamicCells'}``.  The attrdict ``'type'`` that
spyder-modelx reads is a separate contract and stays ``'Cells'`` and
``'Reference'`` for them.

The tests read only the tool API and the public API.  Each model is torn
down by ``_impl._check_sanity()`` and then ``close()``.
"""

import datetime
import decimal
import fractions
import math

import pytest

import modelx as mx
from modelx.tests.testdata import XL_TESTDATA
from modelx.tests.testdata.testpkg import testmod


# --------------------------------------------------------------------------
# T1's recipe, as toolapi.rst gives it

KINDS = frozenset({
    'Model', 'UserSpace', 'ItemSpace', 'DynamicSpace', 'Cells',
    'DynamicCells', 'Macro', 'ReferenceProxy', 'DynamicReferenceProxy',
    'PandasData', 'ExcelRange', 'ModuleData'})


def kind(v):
    t = type(v)
    mod = t.__module__      # not always a str: wrapt's ObjectProxy makes it a property
    if not (isinstance(mod, str) and mod.startswith('modelx.')):
        return None         # never a user's own class named Model
    return t.__name__ if t.__name__ in KINDS else None


# --------------------------------------------------------------------------
# Fixture

def macro_one():
    return 1


@pytest.fixture
def kind_model():
    """
        KindModel---S-------foo(x), gone(), ns_self(), ns_space(),
          |  glob   |       ns_model(), meth(), read_sref(), read_cref(),
          |  mac    |       read_k()
          |         |       k, sref -> P, cref -> S.foo
          |         +--Sub(S)
          |
          +---------P(i)----h(), k
          |         |       Space formula returns ref fr
          |         +--Child(j)--w()
          +---------Multi(S, Other)
          +---------Other
    """
    # Formulas are given as source text: from a lambda, modelx parses the
    # whole of this file for each one, 0.12 s each (cProfile, asttokens).
    m = mx.new_model("KindModel")
    s = m.new_space("S")
    s.new_cells("foo", formula="lambda x: 2 * x")
    s.new_cells("ns_self", formula="lambda: _self")
    s.new_cells("ns_space", formula="lambda: _space")
    s.new_cells("ns_model", formula="lambda: _model")
    s.new_cells("meth", formula="lambda: foo")
    s.new_cells("read_sref", formula="lambda: sref")
    s.new_cells("read_cref", formula="lambda: cref")
    s.new_cells("read_k", formula="lambda: k")
    s.k = 5
    m.new_space("Sub", bases=s)
    m.new_space("Other")
    m.new_space("Multi", bases=[s, m.Other])

    p = m.new_space("P", formula="lambda i: {'refs': {'fr': 2 * i}}")
    p.new_cells("h", formula="lambda: i")
    p.k = 3
    child = p.new_space("Child", formula="lambda j: None")
    child.new_cells("w", formula="lambda: 10")

    m.glob = 7
    s.sref = p
    s.cref = s.foo
    m.new_macro("mac", macro_one)

    yield m
    m._impl._check_sanity()
    m.close()


# --------------------------------------------------------------------------
# Every kind

OBJECTS = {
    # label: (getter, kind)
    "Model": (lambda m: m, "Model"),
    "UserSpace": (lambda m: m.S, "UserSpace"),
    "UserSpace, derived": (lambda m: m.Sub, "UserSpace"),
    "UserSpace, multiple inheritance": (lambda m: m.Multi, "UserSpace"),
    "UserSpace, child": (lambda m: m.P.Child, "UserSpace"),
    "ItemSpace": (lambda m: m.P[1], "ItemSpace"),
    "ItemSpace, nested P[1][5]": (lambda m: m.P[1][5], "ItemSpace"),
    "ItemSpace of a DynamicSpace": (lambda m: m.P[1].Child[2], "ItemSpace"),
    "DynamicSpace": (lambda m: m.P[1].Child, "DynamicSpace"),
    "DynamicSpace in a nested item": (lambda m: m.P[1][5].Child,
                                      "DynamicSpace"),
    "Cells": (lambda m: m.S.foo, "Cells"),
    "Cells, derived": (lambda m: m.Sub.foo, "Cells"),
    "Cells, multiple inheritance": (lambda m: m.Multi.foo, "Cells"),
    "Cells of an ItemSpace": (lambda m: m.P[1].h, "DynamicCells"),
    "Cells of a nested item": (lambda m: m.P[1][5].h, "DynamicCells"),
    "Cells of a DynamicSpace": (lambda m: m.P[1].Child.w, "DynamicCells"),
    "Macro": (lambda m: m.mac, "Macro"),
    "Macro, from macros": (lambda m: m.macros["mac"], "Macro"),
    "proxy, scalar": (lambda m: m.S._get_object("k", as_proxy=True),
                      "ReferenceProxy"),
    "proxy, global from the Model": (
        lambda m: m._get_object("glob", as_proxy=True), "ReferenceProxy"),
    "proxy, global from a Space": (
        lambda m: m.S._get_object("glob", as_proxy=True), "ReferenceProxy"),
    "proxy, global from an ItemSpace": (
        lambda m: m.P[1]._get_object("glob", as_proxy=True),
        "ReferenceProxy"),
    "proxy, Space-valued": (lambda m: m.S._get_object("sref", as_proxy=True),
                            "ReferenceProxy"),
    "proxy, Cells-valued": (lambda m: m.S._get_object("cref", as_proxy=True),
                            "ReferenceProxy"),
    "proxy, derived": (lambda m: m.Sub._get_object("k", as_proxy=True),
                       "ReferenceProxy"),
    "proxy, Space's seen through its item": (
        lambda m: m.P[1]._get_object("k", as_proxy=True), "ReferenceProxy"),
    "proxy, argument": (lambda m: m.P[1]._get_object("i", as_proxy=True),
                        "DynamicReferenceProxy"),
    "proxy, argument of a nested item": (
        lambda m: m.P[1][5]._get_object("i", as_proxy=True),
        "DynamicReferenceProxy"),
    "proxy, formula ref": (lambda m: m.P[1]._get_object("fr", as_proxy=True),
                           "DynamicReferenceProxy"),
    "proxy, from a node": (lambda m: read_k_node(m).obj, "ReferenceProxy"),
}


def read_k_node(m):
    """The ReferenceNode of ``S.k`` among ``S.read_k``'s precedents."""
    m.S.read_k()
    nodes = m.S.read_k.precedents()
    assert len(nodes) == 1
    return nodes[0]


@pytest.mark.parametrize("label", list(OBJECTS))
def test_kind_of_each_object(kind_model, label):
    get, expected = OBJECTS[label]
    obj = get(kind_model)
    assert kind(obj) == expected
    assert kind(obj) in KINDS


def test_value_reports_its_own_kind(kind_model):
    """A Reference whose value is a modelx object: only the proxy is a
    proxy, the value reports its own kind, read outside or inside a
    formula."""
    m = kind_model
    for name, value_kind in [("sref", "UserSpace"), ("cref", "Cells")]:
        proxy = m.S._get_object(name, as_proxy=True)
        assert kind(proxy) == "ReferenceProxy"
        assert kind(proxy.value) == value_kind
        assert kind(getattr(m.S, name)) == value_kind
    assert kind(m.S.read_sref()) == "UserSpace"
    assert kind(m.S.read_cref()) == "Cells"


def test_iospec_kinds(kind_model):
    """PandasData, ExcelRange and ModuleData by name. An ExcelRange is
    also a Reference value: the value and its entry in ``iospecs`` are
    the same object and report ``'ExcelRange'``, inside a formula too,
    and the proxy ``'ReferenceProxy'``."""
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    m = kind_model
    df = m.new_pandas("df", "files/df.csv", pd.DataFrame({"a": [1]}),
                      file_type="csv")
    xl = m.new_excel_range("xl", "files/xl.xlsx", "C9:E25", "TestTables",
                           ["r0", "c0"], XL_TESTDATA)
    mod = m.new_module("mod", "files/mod", testmod)
    m.S.xl = xl
    m.S.new_cells("read_xl", formula="lambda: xl")

    assert kind(m.get_spec(df)) == "PandasData"
    assert kind(m.get_spec(mod)) == "ModuleData"
    assert kind(xl) == "ExcelRange"
    assert sorted(kind(spec) for spec in m.iospecs) == [
        "ExcelRange", "ModuleData", "PandasData"]
    assert [spec for spec in m.iospecs if kind(spec) == "ExcelRange"] == [xl]

    assert kind(m.S._get_object("xl", as_proxy=True)) == "ReferenceProxy"
    assert kind(m.S._get_object("xl", as_proxy=True).value) == "ExcelRange"
    assert kind(m.S.read_xl()) == "ExcelRange"

    # The values a spec holds are not modelx objects.
    assert kind(df) is None
    assert kind(mod) is None

    # The attrdict 'type' of a spec is its class name.
    for spec in m.iospecs:
        assert spec._get_attrdict()["type"] == kind(spec)


# --------------------------------------------------------------------------
# None for everything else

def _generator():
    yield 1


# Values a Reference commonly holds: 29 from the standard library here and
# five from numpy and pandas below, 34 in all.  None of them is a modelx
# object.
STDLIB_VALUES = [
    None, True, 0, 1.5, 1j, "str", b"bytes", bytearray(b"ba"),
    [1], (1,), {"a": 1}, {1}, frozenset({1}), range(3), slice(1, 2),
    Ellipsis, NotImplemented, object(), int, lambda: 1, len, _generator(),
    math, decimal.Decimal("1.5"), fractions.Fraction(1, 3),
    datetime.date(2026, 1, 1), datetime.datetime(2026, 1, 1, 12, 0),
    datetime.timedelta(days=1), ValueError("x"),
]


@pytest.mark.parametrize("value", STDLIB_VALUES,
                         ids=[type(v).__name__ for v in STDLIB_VALUES])
def test_none_for_stdlib_values(value):
    assert kind(value) is None


def test_none_for_numpy_and_pandas_values():
    np = pytest.importorskip("numpy")
    pd = pytest.importorskip("pandas")
    values = [np.int64(7), np.float64(1.5), np.array([1, 2]),
              pd.DataFrame({"a": [1]}), pd.Series([1, 2])]
    assert len(STDLIB_VALUES) + len(values) == 34
    for value in values:
        assert kind(value) is None, type(value)


def test_none_for_views_nodes_and_namespaces(kind_model):
    """Views, nodes, the Namespace objects a formula sees for ``_self``,
    ``_space`` and ``_model``, and the bound method it sees for a Cells
    name, are defined in modelx modules but are not in the set."""
    m = kind_model
    m.S.foo(3)
    others = {
        "spaces": m.spaces,
        "cells": m.S.cells,
        "refs": m.S.refs,
        "Model refs": m.refs,
        "macros": m.macros,
        "_named_itemspaces": m.P._named_itemspaces,
        "ItemNode": m.S.foo.node(3),
        "ReferenceNode": read_k_node(m),
        "_self": m.S.ns_self(),
        "_space": m.S.ns_space(),
        "_model": m.S.ns_model(),
    }
    for label, obj in others.items():
        mod = type(obj).__module__
        assert isinstance(mod, str) and mod.startswith("modelx."), label
        assert kind(obj) is None, label

    meth = m.S.meth()
    assert callable(meth)
    assert kind(meth) is None


def test_none_for_classes_named_like_modelx():
    """A user's own class named ``Model`` or ``Cells``, a class whose
    ``__module__`` is None, and a class whose ``__module__`` is a
    property, as in a wrapt proxy, all give None, and the last does not
    raise."""
    user_model = type("Model", (), {"__module__": "__main__"})()
    user_cells = type("Cells", (), {"__module__": "mylib.cells"})()
    no_module = type("Cells", (), {"__module__": None})()
    wrapped = type("Model", (), {
        "__module__": property(lambda self: "modelx.core.model")})()

    assert not isinstance(type(wrapped).__module__, str)
    for value in (user_model, user_cells, no_module, wrapped):
        assert type(value).__name__ in KINDS
        assert kind(value) is None


# --------------------------------------------------------------------------
# Deleted objects and objects of a closed model

def test_kind_of_deleted_objects(kind_model):
    """A deleted object keeps its class, so the recipe still answers."""
    m = kind_model
    gone = m.S.new_cells("gone", formula="lambda: 1")
    space = m.new_space("GoneSpace")
    m.S.tmp = 1
    proxy = m.S._get_object("tmp", as_proxy=True)
    item = m.P[9]
    dynamic, cells, arg = (item.Child, item.h,
                           item._get_object("i", as_proxy=True))

    del m.S.gone
    del m.GoneSpace
    del m.S.tmp
    del m.P[9]

    assert not gone._is_valid()
    assert not space._is_valid()
    assert not item._is_valid()
    assert not dynamic._is_valid()
    assert not cells._is_valid()

    assert kind(gone) == "Cells"
    assert kind(space) == "UserSpace"
    assert kind(proxy) == "ReferenceProxy"
    assert kind(item) == "ItemSpace"
    assert kind(dynamic) == "DynamicSpace"
    assert kind(cells) == "DynamicCells"
    assert kind(arg) == "DynamicReferenceProxy"


def test_kind_on_closed_model():
    m = mx.new_model("KindClosed")
    p = m.new_space("P", formula="lambda i: None")
    p.new_cells("h", formula="lambda: i")
    p.k = 1
    m.new_macro("mac", macro_one)
    objs = {
        "Model": m,
        "UserSpace": p,
        "ItemSpace": p[1],
        "DynamicCells": p[1].h,
        "Cells": p.h,
        "Macro": m.mac,
        "ReferenceProxy": p._get_object("k", as_proxy=True),
        "DynamicReferenceProxy": p[1]._get_object("i", as_proxy=True),
    }
    m._impl._check_sanity()
    m.close()
    for expected, obj in objs.items():
        assert kind(obj) == expected


# --------------------------------------------------------------------------
# The attrdict 'type' is a separate contract, and unchanged

TYPES = {
    # label from OBJECTS: the 'type' of _get_attrdict() and _baseattrs
    "Model": "Model",
    "UserSpace": "UserSpace",
    "ItemSpace": "ItemSpace",
    "DynamicSpace": "DynamicSpace",
    "Cells": "Cells",
    "Cells of an ItemSpace": "Cells",
    "Cells of a DynamicSpace": "Cells",
    "Macro": "Macro",
    "proxy, scalar": "Reference",
    "proxy, global from the Model": "Reference",
    "proxy, argument": "Reference",
    "proxy, formula ref": "Reference",
}


@pytest.mark.parametrize("label", list(TYPES))
def test_attrdict_type_unchanged(kind_model, label):
    obj = OBJECTS[label][0](kind_model)
    assert obj._get_attrdict(recursive=False)["type"] == TYPES[label]
    assert obj._baseattrs["type"] == TYPES[label]
