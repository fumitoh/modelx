"""Snapshot gate for what spyder-modelx requests from modelx today.

``test_spyder_surface.py`` pins ``_baseattrs`` and a tree walk with
``extattrs=["get_referents"]``.  None of the classes that walk visits
(Model, the Spaces, Cells, ReferenceProxy, the views) defines
``get_referents``, and the fixture has no member of that name, so the
walk adds no extattr key.  This
module pins the calls spyder-modelx 0.15.2 (Spyder 6,
``spyder_modelx/widgets/mxshell/mxshell_6.py``) and spymx-kernels 0.3.0
(``spymx_kernels/console/kernel.py``) actually make, and records
their output in ``testdata/spyder_requests_snapshot.json``:

``tree``
    The Explorer (``update_modeltree``):
    ``model._get_attrdict(['_is_derived', '__len__', '_evalrepr'],
    recursive=True)``.  The kernel resolves the model with
    ``mx.get_object(name, as_proxy=True)``.

``properties``
    The Properties pane (``update_mxproperty``) and the Analyzer's
    object box (``update_mxanalyzer``), for the ``fullname`` of every
    object in the tree, as the Explorer passes it:
    ``mx.get_object(fullname, as_proxy=True)._get_attrdict(
    ['formula', '_evalrepr', 'allow_none', 'parameters'],
    recursive=False)``.  The Model is included, although the Explorer
    shows it as the tree's root rather than as a row.

``model_list``
    The model selector (``mx_get_modellist``):
    ``model._get_attrdict(recursive=False)``.

``codelist``
    The formula list (``mx_get_codelist``), for every Space row:
    ``mx.get_object(fullname + '.cells')._get_attrdict(['formula'])``.

``nodes``
    The Analyzer (``mx_get_node``, ``mx_eval_node``, ``mx_adj_node``):
    ``node._get_attrdict(recursive=False, extattrs=['formula'])`` for a
    root node got by ``mx.get_object(fullname, as_proxy=True)
    .node(*args)``, and for its ``'precedents'`` and its ``'succs'``,
    expanded as the Analyzer expands a row: whenever the record's
    ``'precedentslen'`` or ``'succslen'`` is not 0, by
    ``getattr(mx.get_object(fullname).node(*args), adjacency)``.
    Every root node has a value.  For a node of a Cells with no stored
    value, ``_get_attrdict`` raises ValueError on this release, which
    toolapi.rst labels a known limitation, so no such node is pinned.

``assoc_values``
    The data list (``mx_get_value_info``):
    ``model._get_assoc_values()``, and for each entry its keys, its
    ``'value'``, ``spec._get_attrdict()`` for its IOSpec and
    ``ref._get_attrdict()`` for each of its References.

The Analyzer also requests ``['_evalrepr']`` alone, non-recursively,
for a Cells (``analyze_current``).  That record is a subset of the
Properties record, so it is not pinned separately.

The model is the serializer-compat fixture (as in
``test_spyder_surface.py``) with two additions, because the fixture
has no IOSpec and the data list shows every key of an IOSpec record:
a PandasData on the Model (the global Reference ``df``) and an
ExcelRange in ``Base`` (the Reference ``xlr``, which ``Sub`` inherits).
These are the two IOSpec classes that add keys to
``BaseIOSpec._get_attrdict``.  ModuleData is left out: its
``load_from`` and the repr of its value are absolute paths of the
module's source file, and its record has only the four keys of
``BaseIOSpec._get_attrdict``, which the other two records also pin.
Before the snapshot the model computes a few values, so that the
``__len__`` keys and the node records are not empty.

Normalization is the same as ``test_spyder_surface.py``: ``id`` values
(memory addresses) are zeroed, dict keys become str, tuples become
lists and non-JSON leaf objects are reduced to their ``repr``.  Only an
``'id'`` that is an int is zeroed, so a change in what the key carries,
such as a bool or a str in place of an id, shows in the diff.  Two
volatile values are added to it:

* ``'valid'`` in node records is ``id(value)`` (``BaseNode._get_attrdict``),
  so it is zeroed like ``'id'`` when it is an int; ``None`` (no value)
  and anything else are normalized as they are;
* a str that starts with the ``modelx/tests/testdata`` directory, such
  as the ExcelRange's ``load_from``, has that directory replaced by
  ``<testdata>`` and its separators by ``/``.

A dict that modelx returns may gain keys (toolapi.rst), so a record
matches the golden when it has every key of the golden record with a
matching value; extra keys are ignored.  Names of objects, values and
lists are compared exactly; ``mismatches`` says which.

If the requests change *intentionally*, regenerate the golden with::

    python -m modelx.tests.core.base.test_spyder_requests --write

and call out the diff in the commit message.
"""

import json
import os
import pathlib
import sys

import modelx as mx
import modelx.tests.testdata
from modelx.tests.testdata import XL_TESTDATA
from modelx.tests.testdata.serializer_compat import fixturemodel

SNAPSHOT_PATH = (
    pathlib.Path(modelx.tests.testdata.__file__).parent
    / "spyder_requests_snapshot.json"
)

TESTDATA_DIR = str(pathlib.Path(modelx.tests.testdata.__file__).parent)

# spyder_modelx/widgets/mxshell/mxshell_6.py, update_modeltree
TREE_ATTRS = ['_is_derived', '__len__', '_evalrepr']

# spyder_modelx/widgets/mxshell/mxshell_6.py, update_mxproperty and
# update_mxanalyzer
PROPERTY_ATTRS = ['formula', '_evalrepr', 'allow_none', 'parameters']

# spymx_kernels/console/kernel.py, mx_get_codelist
CODELIST_ATTRS = ['formula']

# spymx_kernels/console/kernel.py, mx_get_node, mx_eval_node and
# mx_adj_node
NODE_ATTRS = ['formula']

# The Analyzer's two tabs (mxanalyzer_6.py, MxAnalyzerWidget)
ADJACENCIES = ['precedents', 'succs']

# Root nodes for the Analyzer: (fullname, args).  The fullnames are
# those the Properties pane holds, so an item of Params is reached by
# its __Space1 name.
NODE_ROOTS = [
    ("SerializerCompat.Base.foo", (2,)),    # computed; preds foo(1), m
    ("SerializerCompat.Base.foo", (0,)),    # input value
    ("SerializerCompat.Base.bar", (5,)),
    ("SerializerCompat.Sub.foo", (2,)),     # derived Cells
    ("SerializerCompat.Base.Child.baz", (1,)),
    ("SerializerCompat.Params", (3,)),      # Space node; value is Params[3]
    ("SerializerCompat.Params.__Space1.qux", (2,)),  # item's Cells
]


def normalize(obj):
    if isinstance(obj, dict):
        return {
            str(k): (_zero_id(v) if k in ("id", "valid")
                     else normalize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [normalize(x) for x in obj]
    if isinstance(obj, str):
        return _portable(obj)
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def _zero_id(value):
    # Zero only a real id, so that a bool, a str or None in its place
    # is kept and shows in the diff.
    if type(value) is int:
        return 0
    return normalize(value)


def _portable(s):
    if s.startswith(TESTDATA_DIR):
        return "<testdata>" + s[len(TESTDATA_DIR):].replace(os.sep, "/")
    return s


def build_model():
    import pandas as pd

    m = fixturemodel.build_fixture_model()
    m.new_pandas(name="df", path="df.xlsx",
                 data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
                 file_type="excel", sheet="df")
    m.Base.new_excel_range(name="xlr", path="xlr.xlsx", range_="C9:E25",
                           sheet="TestTables", keyids=["r0", "c0"],
                           loadpath=XL_TESTDATA)

    m.Base.foo(2)
    m.Base.bar(5)
    m.Sub.foo(2)
    m.Base.Child.baz(1)
    m.Params[3].qux(2)
    return m


def _rows(attrdict, rows):
    """Map the fullname of every object in a tree attrdict to its type

    The views (``'type'`` ending in ``'View'``) are left out, as the
    Explorer requests no properties for them.
    """
    if isinstance(attrdict, dict):
        if ("fullname" in attrdict
                and not attrdict["type"].endswith("View")):
            rows.setdefault(attrdict["fullname"], attrdict["type"])
        for value in attrdict.values():
            _rows(value, rows)
    elif isinstance(attrdict, (list, tuple)):
        for value in attrdict:
            _rows(value, rows)
    return rows


def _node_record(node):
    return node._get_attrdict(recursive=False, extattrs=NODE_ATTRS)


def _expand(record, adjacency):
    """Expand a row of an Analyzer tab, as NodeItem does"""
    children = []
    if record[adjacency + "len"]:
        node = mx.get_object(record["obj"]["fullname"]).node(
            *record["args"])
        for child in getattr(node, adjacency):
            child_record = _node_record(child)
            children.append({
                "node": normalize(child_record),
                adjacency: _expand(child_record, adjacency)
            })
    return children


def _node_tree(fullname, args):
    node = mx.get_object(fullname, as_proxy=True).node(*args)
    record = _node_record(node)
    result = {"node": normalize(record)}
    for adjacency in ADJACENCIES:
        result[adjacency] = _expand(record, adjacency)
    return result


def _assoc_value(entry):
    spec = entry["spec"]
    return {
        "keys": sorted(entry),
        "value": normalize(entry["value"]),
        "spec": None if spec is None else normalize(spec._get_attrdict()),
        "refs": [normalize(ref._get_attrdict()) for ref in entry["refs"]],
    }


def build_snapshot():
    m = build_model()
    try:
        tree = m._get_attrdict(TREE_ATTRS, recursive=True)
        rows = _rows(tree, {})
        spaces = [name for name, type_ in rows.items()
                  if type_.endswith("Space")]
        return {
            "tree": normalize(tree),
            "properties": {
                name: normalize(mx.get_object(
                    name, as_proxy=True)._get_attrdict(
                    PROPERTY_ATTRS, recursive=False))
                for name in rows
            },
            "model_list": normalize(m._get_attrdict(recursive=False)),
            "codelist": {
                name: normalize(mx.get_object(
                    name + ".cells")._get_attrdict(CODELIST_ATTRS))
                for name in spaces
            },
            "nodes": {
                "%s%r" % (name, args): _node_tree(name, args)
                for name, args in NODE_ROOTS
            },
            "assoc_values": [
                _assoc_value(entry) for entry in m._get_assoc_values()
            ],
        }
    finally:
        m.close()


# The maps that this module builds from names: fullnames of objects and
# names of the Analyzer's root nodes.
NAME_MAPS = ("properties", "codelist", "nodes")


def mismatches(golden, live, path=()):
    """Yield a description of each place where ``live`` does not match
    ``golden``.

    toolapi.rst ("Frozen members and other members") lets a dict that a
    frozen member returns gain keys, and tells tools to ignore the keys
    they do not know.  So a dict that modelx returns matches when it has
    every key of the golden dict, with a matching value, whatever other
    keys it has.  For example, design T3 (PR 2) adds
    ``ReferenceProxy._is_derived``, and the Reference records of the
    ``tree`` request then gain the ``'_is_derived'`` key that spyder asks
    for.

    Three things are compared exactly, because they are not keys of a
    record:

    * the keys of a dict of names: the ``'items'`` of a view, which maps
      the names of its members to their dicts, and the maps in
      ``NAME_MAPS``.  A name added there is a new object, not a new key;
    * a ``'value'``, which is the value of an object, not a record;
    * a list, such as a view's ``'keys'``, item by item, except the
      ``'keys'`` of a data-list entry, which lists the keys of a dict
      that ``Model._get_assoc_values()`` returns, so the golden ones must
      be among the live ones.
    """
    if path and path[-1] == "value":
        if golden != live:
            yield "%r: %r -> %r" % (path, golden, live)
    elif isinstance(golden, dict) and isinstance(live, dict):
        missing = sorted(set(golden) - set(live))
        if missing:
            yield "%r: keys missing %r" % (path, missing)
        names = ((len(path) == 1 and path[0] in NAME_MAPS)
                 or (path and path[-1] == "items"))
        if names:
            added = sorted(set(live) - set(golden))
            if added:
                yield "%r: names added %r" % (path, added)
        for key in golden:
            if key in live:
                yield from mismatches(golden[key], live[key],
                                      path + (key,))
    elif (len(path) == 3 and path[0] == "assoc_values"
            and path[2] == "keys"):
        missing = sorted(set(golden) - set(live))
        if missing:
            yield "%r: keys missing %r" % (path, missing)
    elif isinstance(golden, list) and isinstance(live, list):
        if len(golden) != len(live):
            yield "%r: length %d -> %d" % (path, len(golden), len(live))
        else:
            for i, (g, v) in enumerate(zip(golden, live)):
                yield from mismatches(g, v, path + (i,))
    elif golden != live:
        yield "%r: %r -> %r" % (path, golden, live)


def test_spyder_requests_snapshot():
    with SNAPSHOT_PATH.open(encoding="utf-8") as f:
        golden = json.load(f)

    snapshot = build_snapshot()

    assert snapshot.keys() == golden.keys()
    for key in golden:
        problems = list(mismatches(golden[key], snapshot[key], (key,)))
        assert not problems, (
            "spyder-modelx request %r changed; if intentional,"
            " regenerate with"
            " 'python -m modelx.tests.core.base.test_spyder_requests"
            " --write':\n%s" % (key, "\n".join(problems[:20]))
        )


if __name__ == "__main__":
    if "--write" in sys.argv:
        with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
            json.dump(build_snapshot(), f, indent=1, sort_keys=True)
        print("written:", SNAPSHOT_PATH)
    else:
        print("pass --write to regenerate", SNAPSHOT_PATH)
