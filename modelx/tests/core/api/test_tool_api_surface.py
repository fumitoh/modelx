"""Signature golden for the frozen tool API.

Decision 1 of devnotes/ToolAPIDesign.md writes the tool-API contract down
as a reference page, doc/source/reference/toolapi.rst ("API for tools"),
and this test.  The members it freezes are the existing tool API that
modelx-bridge, modelx-mcp and spyder-modelx call: sets S1 (identity and
addressing), S2 (inheritance and dynamic objects) and S3 (the snapshot
wire) of the design's section 3.4.  Only members that exist in this
release are listed; a later release that freezes more members adds them
here and to the page.

For each frozen member, on each class of object that a tool holds and
that has the member, the golden records its kind (``property``,
``method``, ``staticmethod``, ``classmethod`` or ``attribute``) and, if
it is callable, its ``inspect.signature``.  The member is looked up the
way the page tells tools to detect one::

    getattr(type(obj), name, None)

so the test fails when a frozen member disappears, stops being a class
attribute, changes kind or changes signature.  An answer from the
instance does not count: through ``__getattr__``, a Model or a Space
answers a name that its class does not define with a member of that
name, such as a user's Reference, if there is one.

The exception classes in ``modelx.core.errors`` that the page lists are
frozen too.  They are recorded separately, under ``"errors"``, by the
``__name__`` of each class in their ``__mro__``, looked up the way the
page tells tools to test for one::

    getattr(modelx.core.errors, name, None)

so the test fails when one disappears, changes its base classes, or
becomes an alias of another class.

A ReferenceProxy answers some frozen names by forwarding them through its
``__getattr__``, not as attributes of its class.  Those are recorded
separately, under ``"forwarded"``, and checked on a proxy instance; for
a method the signature is that of what the proxy returns, so it has no
``self``.  The test also fails when one of them becomes a class attribute
of ReferenceProxy, because the page then says something untrue.

The objects come from a small model built below, one per class, so the
golden is keyed by the class of the object a tool actually holds:
a Space's formula is a ``ParamFunc``, a Cells without a formula holds a
``NullFormula``, and so on.

A frozen member changes only through the deprecation process (decision 2,
and "Deprecation" on toolapi.rst).  If the change is additive, such as a
new optional keyword parameter, or the member has been through that
process, update toolapi.rst, and FROZEN, FORWARDED or FROZEN_ERRORS below
if the list of members changes, regenerate the golden with::

    python -m modelx.tests.core.api.test_tool_api_surface --write

and call out the diff in the commit message.
"""

import inspect
import json
import pathlib
import sys

import pytest

import modelx as mx
import modelx.core.errors
import modelx.tests.testdata
from modelx.core.base import Interface
from modelx.tests.testdata import XL_TESTDATA
from modelx.tests.testdata.testpkg import testmod

GOLDEN_PATH = (
    pathlib.Path(modelx.tests.testdata.__file__).parent
    / "tool_api_surface.json"
)

WRITE_COMMAND = "python -m modelx.tests.core.api.test_tool_api_surface --write"

RULE = (
    "A frozen tool-API member changes only through the deprecation"
    " process (devnotes/ToolAPIDesign.md, decision 2;"
    " doc/source/reference/toolapi.rst, 'Deprecation'): modelx first"
    " warns with ToolAPIDeprecationWarning, a UserWarning subclass to be"
    " added to modelx.core.errors, for at least two minor releases, and"
    " removes or changes the member only once the released modelx-bridge"
    " and modelx-mcp pass without it. If this change is additive (such as"
    " a new optional keyword parameter) or has been through that process,"
    " update toolapi.rst, and FROZEN, FORWARDED or FROZEN_ERRORS in this"
    " file if the list of members changes, regenerate the golden with"
    " '%s', and call out"
    " the diff in the commit message." % WRITE_COMMAND
)

# --------------------------------------------------------------------------
# The frozen members (design section 3.4), as rows of
# (set, class names, member names).  Class names are those of the objects
# that build_objects() returns.

INTERFACES = ("Model", "UserSpace", "ItemSpace", "DynamicSpace", "Cells",
              "Macro")
SPACES = ("UserSpace", "ItemSpace", "DynamicSpace")
VIEWS = ("SpaceView", "CellsView", "RefView", "MacroView")
NODES = ("ItemNode", "ReferenceNode")
FORMULAS = ("Formula", "NullFormula", "ParamFunc")
IOSPECS = ("ModuleData", "PandasData", "ExcelRange")

FROZEN = [
    # S1 identity and addressing
    ("S1", INTERFACES, ("_idstr", "_idtuple", "_evalrepr", "_get_repr",
                        "_name", "_parent", "_get_object", "_is_valid")),
    ("S1", ("ReferenceProxy",), ("_evalrepr",)),
    ("S1", ("Model",), ("_get_from_name",)),
    ("S1", SPACES, ("_named_itemspaces",)),

    # S2 inheritance and dynamic objects
    ("S2", ("Cells",), ("_is_derived", "_is_defined")),
    # No underscore, but frozen: modelx-bridge 0.10 calls it.
    ("S2", ("ReferenceProxy",), ("is_derived",)),
    ("S2", SPACES, ("_is_dynamic", "_is_static", "_is_root", "_is_base",
                    "_is_sub", "_own_refs", "_direct_bases")),
    ("S2", ("ItemSpace",), ("argvalues",)),

    # S3 snapshot wire
    ("S3", INTERFACES + ("ReferenceProxy",) + VIEWS + NODES,
     ("_get_attrdict", "_baseattrs")),
    ("S3", FORMULAS + IOSPECS, ("_get_attrdict",)),
    ("S3", ("Model",), ("_get_assoc_values", "_get_refs")),
]

# Names a ReferenceProxy answers by forwarding them to Interface
# (reference.py, ReferenceProxy.__getattr__), not as class attributes.
FORWARDED = [
    ("S1", ("_name", "_parent")),
    ("S3", ("name", "fullname", "parent", "model", "doc", "allow_none",
            "_idtuple", "_idstr", "_get_repr", "_is_valid")),
]

# The classes of modelx.core.errors that toolapi.rst lists ("Errors and
# warnings"), as rows of (set, class names).
ERRORS_MODULE = "modelx.core.errors"
FROZEN_ERRORS = [
    ("errors", ("FormulaError", "DeepReferenceError", "NoneReturnedError",
                "DeletedObjectError")),
]

SECTIONS = ("members", "forwarded", "errors")

# Classes whose objects need a package that modelx does not require.
OPTIONAL = {"PandasData": "pandas", "ExcelRange": "openpyxl"}


def frozen_table():
    """{(section, class name, member name): set}"""
    table = {}
    for set_, classes, names in FROZEN:
        for cls_name in classes:
            for name in names:
                key = ("members", cls_name, name)
                assert key not in table, "listed twice: %s.%s" % key[1:]
                table[key] = set_
    for set_, names in FORWARDED:
        for name in names:
            key = ("forwarded", "ReferenceProxy", name)
            assert key not in table, "listed twice: %s.%s" % key[1:]
            table[key] = set_
    for set_, names in FROZEN_ERRORS:
        for name in names:
            key = ("errors", ERRORS_MODULE, name)
            assert key not in table, "listed twice: %s.%s" % key[1:]
            table[key] = set_
    return table


# --------------------------------------------------------------------------
# One object of each class

def build_objects(m):
    """Return ({class name: getter}, {class name: why it is skipped}).

    Each getter returns one object of that class from the model ``m``.
    The getters use only public members, never a frozen one, so that a
    broken frozen member is reported as such and not as a broken fixture.
    """
    base = m.new_space("Base")
    foo = base.new_cells("foo", formula=lambda x: 2 * x)
    nof = base.new_cells("nof")
    baz = base.new_cells("baz", formula=lambda: rate)
    base.rate = 0.05

    proj = m.new_space("Proj", formula=lambda i: None)
    proj.new_space("Child")

    mac = m.new_macro("mac", lambda: 1)
    mod = m.new_module("mod", "files/mod", testmod)
    getters, skipped = {}, {}

    try:
        import pandas as pd
    except ImportError as e:
        skipped["PandasData"] = repr(e)
    else:
        df = m.new_pandas("df", "files/df.csv", pd.DataFrame({"a": [1]}),
                          file_type="csv")
        getters["PandasData"] = lambda: m.get_spec(df)

    try:
        import openpyxl     # noqa: F401
    except ImportError as e:
        skipped["ExcelRange"] = repr(e)
    else:
        xl = m.new_excel_range("xl", "files/xl.xlsx", "C9:E25", "TestTables",
                               ["r0", "c0"], XL_TESTDATA)
        getters["ExcelRange"] = lambda: xl

    # Calculate last: an edit, such as a new global Reference, can clear
    # the values, and with them the nodes the getters below read.
    foo(3)
    baz()

    getters.update({
        "Model": lambda: m,
        "UserSpace": lambda: base,
        "ItemSpace": lambda: proj[1],
        "DynamicSpace": lambda: proj[1].Child,
        "Cells": lambda: foo,
        "Macro": lambda: mac,
        "ReferenceProxy": lambda: baz.precedents()[0].obj,
        "SpaceView": lambda: m.spaces,
        "CellsView": lambda: base.cells,
        "RefView": lambda: base.refs,
        "MacroView": lambda: m.macros,
        "ItemNode": lambda: foo.node(3),
        "ReferenceNode": lambda: baz.precedents()[0],
        "Formula": lambda: foo.formula,
        "NullFormula": lambda: nof.formula,
        "ParamFunc": lambda: proj.formula,
        "ModuleData": lambda: m.get_spec(mod),
    })
    return getters, skipped


# --------------------------------------------------------------------------
# Recording

def describe(attr, static):
    """Kind of a class attribute and, if callable, its signature."""
    if isinstance(static, property):
        return {"kind": "property"}
    elif isinstance(static, staticmethod):
        kind = "staticmethod"
    elif isinstance(static, classmethod):
        kind = "classmethod"
    elif inspect.isfunction(static):
        kind = "method"
    else:
        kind = "attribute"

    result = {"kind": kind}
    if callable(attr):
        try:
            result["signature"] = str(inspect.signature(attr))
        except (TypeError, ValueError):
            result["signature"] = None
    return result


def record_member(obj, name):
    """Kind and signature of ``getattr(type(obj), name)``."""
    cls = type(obj)
    attr = getattr(cls, name, None)
    if attr is None:
        return {"kind": None}
    return describe(attr, inspect.getattr_static(cls, name))


def record_forwarded(proxy, name):
    """Kind and signature of what a proxy answers for ``name``.

    The kind is that of the class attribute the answer comes from: the
    proxy's own, if its class has one, else Interface's, which is where
    ``ReferenceProxy.__getattr__`` forwards to.  A method comes back bound
    to the proxy, so its signature has no ``self``.
    """
    try:
        attr = getattr(proxy, name)
    except Exception as e:
        return {"kind": None, "error": repr(e)}
    static = inspect.getattr_static(type(proxy), name, None)
    if static is None:
        static = inspect.getattr_static(Interface, name, None)
    result = describe(attr, static)
    result["class_attribute"] = getattr(type(proxy), name, None) is not None
    return result


def record_error(name):
    """Kind of ``getattr(modelx.core.errors, name, None)`` and, if it is
    a class, the ``__name__`` of each class in its ``__mro__``."""
    obj = getattr(modelx.core.errors, name, None)
    if obj is None:
        return {"kind": None}
    if not isinstance(obj, type):
        return {"kind": "attribute"}
    return {"kind": "class", "mro": [c.__name__ for c in obj.__mro__]}


def build_surface():
    """Record the frozen members on objects of a fresh model.

    Returns a dict:

    ``surface``
        the golden's layout: {section: {class name: {member: entry}}};
    ``classes``
        {class name in the table: class name of the object built for it};
    ``skipped``
        {class name: the ImportError of the package its object needs};
    ``errors``
        {class name: the exception raised while getting its object}.
    """
    surface = {section: {} for section in SECTIONS}
    for _, names in FROZEN_ERRORS:
        for name in names:
            surface["errors"].setdefault(ERRORS_MODULE, {})[name] = (
                record_error(name))
    classes, errors = {}, {}
    m = mx.new_model()
    try:
        getters, skipped = build_objects(m)
        objs = {}
        for cls_name, get in getters.items():
            try:
                objs[cls_name] = get()
            except Exception as e:
                errors[cls_name] = repr(e)
            else:
                classes[cls_name] = type(objs[cls_name]).__name__

        for section, cls_name, name in sorted(frozen_table()):
            if section == "errors" or cls_name not in objs:
                continue
            if section == "members":
                entry = record_member(objs[cls_name], name)
            else:
                entry = record_forwarded(objs[cls_name], name)
            surface[section].setdefault(cls_name, {})[name] = entry
    finally:
        m.close()

    return {"surface": surface, "classes": classes, "skipped": skipped,
            "errors": errors}


# --------------------------------------------------------------------------
# Comparison

def compare_class(golden, live, cls_name):
    """Return a list of problems with the frozen members of ``cls_name``."""
    table = frozen_table()

    if cls_name in live["errors"]:
        return ["could not get an object of class %s from public API: %s"
                % (cls_name, live["errors"][cls_name])]
    if cls_name not in live["classes"]:
        return ["build_objects() returns no object of class %s" % cls_name]

    problems = []
    if live["classes"][cls_name] != cls_name:
        problems.append(
            "the object built for %s is now of class %s, so a tool's"
            " getattr(type(obj), name) looks its members up on another"
            " class" % (cls_name, live["classes"][cls_name]))

    for section in ("members", "forwarded"):
        want = golden.get(section, {}).get(cls_name, {})
        got = live["surface"][section].get(cls_name, {})

        for name in sorted(set(want) | set(got)):
            qual = "%s.%s" % (cls_name, name)
            set_ = table.get((section, cls_name, name), "-")
            label = "%s %s" % (set_, qual)

            if name not in got:
                problems.append(
                    "%s is in the golden but no longer listed in %s"
                    % (qual, "FROZEN" if section == "members"
                       else "FORWARDED"))
                continue
            if name not in want:
                problems.append(
                    "%s is listed but not in the golden; regenerate it"
                    " with '%s'" % (label, WRITE_COMMAND))
                continue

            w, g = want[name], got[name]
            if g["kind"] is None:
                if section == "members":
                    problems.append(
                        "%s is gone or no longer a class attribute:"
                        " getattr(type(obj), %r, None) is None (it was a"
                        " %s)" % (label, name, w["kind"]))
                else:
                    problems.append(
                        "%s: a ReferenceProxy no longer answers it (%s;"
                        " it was a forwarded %s)"
                        % (label, g["error"], w["kind"]))
                continue
            if g["kind"] != w["kind"]:
                problems.append(
                    "%s changed kind: %s -> %s"
                    % (label, w["kind"], g["kind"]))
            if g.get("signature") != w.get("signature"):
                problems.append(
                    "%s changed signature: %s -> %s"
                    % (label, w.get("signature"), g.get("signature")))
            if (section == "forwarded"
                    and g["class_attribute"] != w["class_attribute"]):
                problems.append(
                    "%s is now %s of ReferenceProxy: move it between"
                    " FORWARDED and FROZEN, update toolapi.rst, which says"
                    " which names a ReferenceProxy forwards, and"
                    " regenerate the golden"
                    % (label, "a class attribute" if g["class_attribute"]
                       else "no longer a class attribute"))

    return problems


def compare_errors(golden, live):
    """Return a list of problems with the frozen classes of
    modelx.core.errors."""
    table = frozen_table()
    want = golden.get("errors", {}).get(ERRORS_MODULE, {})
    got = live["surface"]["errors"].get(ERRORS_MODULE, {})

    problems = []
    for name in sorted(set(want) | set(got)):
        qual = "%s.%s" % (ERRORS_MODULE, name)
        label = "%s %s" % (table.get(("errors", ERRORS_MODULE, name), "-"),
                           qual)
        if name not in got:
            problems.append("%s is in the golden but no longer listed in"
                            " FROZEN_ERRORS" % qual)
            continue
        if name not in want:
            problems.append("%s is listed but not in the golden; regenerate"
                            " it with '%s'" % (label, WRITE_COMMAND))
            continue

        w, g = want[name], got[name]
        if g["kind"] is None:
            problems.append(
                "%s is gone: getattr(modelx.core.errors, %r, None) is None"
                % (label, name))
            continue
        if g["kind"] != w["kind"]:
            problems.append("%s changed kind: %s -> %s"
                            % (label, w["kind"], g["kind"]))
        if g.get("mro") != w.get("mro"):
            problems.append(
                "%s changed its classes (__mro__): %s -> %s%s"
                % (label, w.get("mro"), g.get("mro"),
                   "; it is now another class" if g.get("mro")
                   and g["mro"][0] != name else ""))
    return problems


def absent_members(surface):
    return sorted(
        "%s.%s" % (cls_name, name)
        for section in SECTIONS
        for cls_name, members in surface[section].items()
        for name, entry in members.items()
        if entry.get("kind") is None
    )


# --------------------------------------------------------------------------
# Tests

ALL_CLASSES = sorted({cls_name for section, cls_name, _ in frozen_table()
                      if section != "errors"})


@pytest.fixture(scope="module")
def golden():
    with GOLDEN_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def live():
    return build_surface()


@pytest.mark.parametrize("cls_name", ALL_CLASSES)
def test_frozen_members_unchanged(golden, live, cls_name):
    if cls_name in live["skipped"]:
        pytest.skip("%s needs %s: %s" % (
            cls_name, OPTIONAL[cls_name], live["skipped"][cls_name]))

    problems = compare_class(golden, live, cls_name)
    assert not problems, (
        "Frozen tool API of %s changed:\n  %s\n%s"
        % (cls_name, "\n  ".join(problems), RULE))


def test_frozen_errors_unchanged(golden, live):
    problems = compare_errors(golden, live)
    assert not problems, (
        "Frozen tool API of %s changed:\n  %s\n%s"
        % (ERRORS_MODULE, "\n  ".join(problems), RULE))


def test_golden_matches_table(golden):
    """The golden records every listed member as present, and no other."""
    listed = set(frozen_table())
    recorded = {
        (section, cls_name, name)
        for section in SECTIONS
        for cls_name, members in golden.get(section, {}).items()
        for name in members
    }
    assert set(golden) == set(SECTIONS)
    assert recorded == listed, (
        "The golden and FROZEN/FORWARDED/FROZEN_ERRORS disagree."
        " In the golden only: %s."
        " Listed only: %s. Regenerate with '%s'.\n%s" % (
            sorted("%s.%s" % k[1:] for k in recorded - listed),
            sorted("%s.%s" % k[1:] for k in listed - recorded),
            WRITE_COMMAND, RULE))

    absent = absent_members(golden)
    assert not absent, "the golden records these as absent: %s" % absent


def write_golden(path=GOLDEN_PATH):
    """Write the golden, refusing to record anything but a full surface."""
    live = build_surface()
    if live["skipped"] or live["errors"]:
        sys.exit("cannot write: objects not built: %s"
                 % dict(live["skipped"], **live["errors"]))
    renamed = {k: v for k, v in live["classes"].items() if k != v}
    if renamed:
        sys.exit("cannot write: objects of another class: %s" % renamed)
    absent = absent_members(live["surface"])
    if absent:
        sys.exit("cannot write: listed but absent: %s; remove them"
                 " from FROZEN, FORWARDED or FROZEN_ERRORS first" % absent)
    aliases = sorted(
        name for name, entry in live["surface"]["errors"].get(
            ERRORS_MODULE, {}).items()
        if entry["kind"] != "class" or entry["mro"][0] != name)
    if aliases:
        sys.exit("cannot write: not a class of that name in %s: %s"
                 % (ERRORS_MODULE, aliases))
    with pathlib.Path(path).open("w", encoding="utf-8") as f:
        json.dump(live["surface"], f, indent=1, sort_keys=True)
        f.write("\n")
    print("written:", path)


if __name__ == "__main__":
    if "--write" in sys.argv:
        write_golden()
    else:
        print("pass --write to regenerate", GOLDEN_PATH)
