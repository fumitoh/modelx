"""Signature golden for the frozen tool API.

Decision 1 of devnotes/ToolAPIDesign.md writes the tool-API contract down
as a reference page, doc/source/reference/toolapi.rst ("API for tools"),
and this test.  The members it freezes are the existing tool API that
modelx-bridge, modelx-mcp and spyder-modelx call: sets S1 (identity and
addressing), S2 (inheritance and dynamic objects) and S3 (the snapshot
wire) of the design's section 3.4.  Only members that exist in this
release are listed; a later release that freezes more members adds them
here and to the page.  The members that 0.34 adds (the design's section
3.1) are listed under their own ID as they land: T3's
``ReferenceProxy._is_derived()``, on both proxy classes, and T7's
``BaseNode._get_repr()``, on both node classes.

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
frozen too.  They are recorded separately, under ``"errors"``, looked up
the way the page tells tools to test for one::

    getattr(modelx.core.errors, name, None)

For each, the golden records that it is a class, its ``__name__``, and
its base classes, ``__bases__``, by module and qualified name, so the
test fails when one disappears, stops being a class, becomes an alias
of another class, or changes its base classes.

The names of the twelve classes that T1 lists (decisions 14 and 15) are
frozen too, and so is the promise that each is defined in a module of
the ``modelx`` package; the exact module paths are not.  A tool tells
what a value is from them::

    mod = type(v).__module__
    if isinstance(mod, str) and mod.startswith('modelx.'):
        name = type(v).__name__

They are recorded under ``"kinds"``, from the object built for each
name: its class's ``__name__`` and whether that module check passes.
A listed class name cannot be deprecated with a warning, because
reading ``type(v).__name__`` runs no modelx code.  So it follows the
deprecation process without the warning (decision 14): it is marked
deprecated on toolapi.rst and in the release notes' "Deprecations"
section at least two minor releases before a rename or split, which
then lands only when the downstream job is green, under "Backward
Incompatible Changes".

A ReferenceProxy, of either class, answers some frozen names by
forwarding them through its ``__getattr__``.  Those are recorded separately, under ``"forwarded"``,
and checked on a proxy instance; for a method the signature is that of
what the proxy returns, so it has no ``self``.  Whether the class of the
proxy defines such a name or forwards it is not recorded: toolapi.rst
labels that a known limitation, which a later release may change, and
the proxy answers the name with the same kind and signature either way.

The objects come from a small model built below, one per class, so the
golden is keyed by the class of the object a tool actually holds:
a Space's formula is a ``ParamFunc``, a Cells without a formula holds a
``NullFormula``, and so on.  So ``Formula._get_attrdict`` is pinned on
``Formula``, ``NullFormula`` and ``ParamFunc``, and
``BaseIOSpec._get_attrdict`` on ``ModuleData``, ``PandasData`` and
``ExcelRange``, as no object a tool holds is a ``BaseIOSpec`` itself.
toolapi.rst ("Frozen members and other members") says so.  Likewise a
Cells of an ItemSpace is a ``DynamicCells`` and the proxy of an
ItemSpace's argument a ``DynamicReferenceProxy`` (decision 15), and
their members, forwarded ones included, are pinned as on ``Cells`` and
``ReferenceProxy``.

The test pins the surface only, never behaviour.  The behaviour that
toolapi.rst labels a known limitation is not part of the frozen
contract, and no test pins it.

A frozen member changes only through the deprecation process (decision 2,
and "Deprecation" on toolapi.rst).  If the change is additive, such as a
new optional keyword parameter or a new class name in KINDS, or the
member has been through that process, update toolapi.rst, and FROZEN,
FORWARDED, FROZEN_ERRORS or KINDS below if the list changes, regenerate
the golden with::

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
from modelx.tests.core.base import test_kind
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
    " update toolapi.rst, and FROZEN, FORWARDED, FROZEN_ERRORS or KINDS in"
    " this file if the list changes, regenerate the golden with"
    " '%s', and call out"
    " the diff in the commit message." % WRITE_COMMAND
)

KINDS_RULE = (
    "A class name that T1 lists is frozen tool API (devnotes/"
    "ToolAPIDesign.md, decisions 14 and 15; doc/source/reference/"
    "toolapi.rst, 'Deprecation'), and so is its definition in a module of"
    " the modelx package. It cannot warn, because a tool reads"
    " type(v).__name__ without running modelx code: a rename or split is"
    " marked deprecated on toolapi.rst and in the release notes'"
    " 'Deprecations' section at least two minor releases before it lands,"
    " and lands only when the downstream job is green, under 'Backward"
    " Incompatible Changes'. A new name is an addition: add it to KINDS in"
    " this file and in modelx/tests/core/base/test_kind.py, and to"
    " toolapi.rst, regenerate the golden with '%s', and call out the diff"
    " in the commit message." % WRITE_COMMAND
)

# --------------------------------------------------------------------------
# The frozen members (design section 3.4), as rows of
# (set, class names, member names).  Class names are those of the objects
# that build_objects() returns.

CELLS = ("Cells", "DynamicCells")
PROXIES = ("ReferenceProxy", "DynamicReferenceProxy")
INTERFACES = ("Model", "UserSpace", "ItemSpace", "DynamicSpace") + CELLS + (
    "Macro",)
SPACES = ("UserSpace", "ItemSpace", "DynamicSpace")
VIEWS = ("SpaceView", "CellsView", "RefView", "MacroView")
NODES = ("ItemNode", "ReferenceNode")
FORMULAS = ("Formula", "NullFormula", "ParamFunc")
IOSPECS = ("ModuleData", "PandasData", "ExcelRange")

FROZEN = [
    # S1 identity and addressing
    ("S1", INTERFACES, ("_idstr", "_idtuple", "_evalrepr", "_get_repr",
                        "_name", "_parent", "_get_object", "_is_valid")),
    ("S1", PROXIES, ("_evalrepr",)),
    ("S1", ("Model",), ("_get_from_name",)),
    ("S1", SPACES, ("_named_itemspaces",)),
    # New in 0.34 (T7): the display string of a node, defined on BaseNode.
    ("T7", NODES, ("_get_repr",)),

    # S2 inheritance and dynamic objects
    ("S2", CELLS, ("_is_derived", "_is_defined")),
    # No underscore, but frozen: modelx-bridge 0.10 calls it. From 0.34 it
    # is an alias of _is_derived(), kept for good (decision 11).
    ("S2", PROXIES, ("is_derived",)),
    # New in 0.34 (T3). Spaces and Models have none (decision 4).
    ("T3", PROXIES, ("_is_derived",)),
    # _is_dynamic, _is_static and _is_root were removed in 0.34 (decision
    # 16): the class tells the kind of a Space (KINDS below).
    ("S2", SPACES, ("_is_base", "_is_sub", "_own_refs", "_direct_bases")),
    ("S2", ("ItemSpace",), ("argvalues",)),

    # S3 snapshot wire
    ("S3", INTERFACES + PROXIES + VIEWS + NODES,
     ("_get_attrdict", "_baseattrs")),
    ("S3", FORMULAS + IOSPECS, ("_get_attrdict",)),
    ("S3", ("Model",), ("_get_assoc_values", "_get_refs")),
]

# Names a ReferenceProxy, of either class, answers by forwarding them to
# the base class of Model, Spaces and Cells (reference.py,
# ReferenceProxy.__getattr__), not as class attributes.
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

# T1 (decisions 14 and 15): the class names a tool tells kinds by, once
# the class's module is in the modelx package.  Recorded under "kinds",
# from the object build_objects() returns for each name.
KINDS_SET = "T1"
KINDS = ("Model", "UserSpace", "ItemSpace", "DynamicSpace", "Cells",
         "DynamicCells", "Macro", "ReferenceProxy", "DynamicReferenceProxy",
         "PandasData", "ExcelRange", "ModuleData")

SECTIONS = ("members", "forwarded", "errors", "kinds")

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
        for cls_name in PROXIES:
            for name in names:
                key = ("forwarded", cls_name, name)
                assert key not in table, "listed twice: %s.%s" % key[1:]
                table[key] = set_
    for set_, names in FROZEN_ERRORS:
        for name in names:
            key = ("errors", ERRORS_MODULE, name)
            assert key not in table, "listed twice: %s.%s" % key[1:]
            table[key] = set_
    for name in KINDS:
        key = ("kinds", KINDS_SET, name)
        assert key not in table, "listed twice: %s.%s" % key[1:]
        table[key] = KINDS_SET
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
    proj.new_cells("bar", formula=lambda: i)

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
    proj[1].bar()

    getters.update({
        "Model": lambda: m,
        "UserSpace": lambda: base,
        "ItemSpace": lambda: proj[1],
        "DynamicSpace": lambda: proj[1].Child,
        "Cells": lambda: foo,
        "DynamicCells": lambda: proj[1].bar,
        "Macro": lambda: mac,
        "ReferenceProxy": lambda: baz.precedents()[0].obj,
        # The proxy of the argument i, which proj[1].bar reads.
        "DynamicReferenceProxy": lambda: proj[1].bar.precedents()[0].obj,
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


def forwarding_class(objs):
    """The class that a ReferenceProxy forwards names to.

    toolapi.rst says a proxy answers the forwarded names "as the base
    class of Model, Spaces and Cells answers them".  That class is found
    here from the classes of the objects a tool holds, so the test
    imports nothing from ``modelx.core`` but ``modelx.core.errors``: it is
    the first class in the method resolution order of a Cells that the
    classes of a Model and a UserSpace also have, other than ``object``.
    ``None`` if one of the three objects could not be built, or the three
    classes have no such base.
    """
    try:
        cells, others = type(objs["Cells"]), [
            type(objs[name]) for name in ("Model", "UserSpace")]
    except KeyError:
        return None
    for cls in cells.__mro__:
        if cls is not object and all(cls in c.__mro__ for c in others):
            return cls
    return None


def record_forwarded(proxy, name, source):
    """Kind and signature of what a proxy answers for ``name``.

    The kind is that of the class attribute the answer comes from: the
    proxy's own, if its class has one, else that of ``source``, the
    class that ``ReferenceProxy.__getattr__`` forwards to (see
    ``forwarding_class``).  A method comes back bound to the proxy, so
    its signature has no ``self``.  Which of the two classes the answer
    comes from is not recorded (see the module docstring).
    """
    try:
        attr = getattr(proxy, name)
    except Exception as e:
        return {"kind": None, "error": repr(e)}
    static = inspect.getattr_static(type(proxy), name, None)
    if static is None:
        if source is None:
            return {"kind": None,
                    "error": "no base class of Model, Spaces and Cells"
                             " found to look %r up on" % name}
        static = inspect.getattr_static(source, name, None)
    return describe(attr, static)


def qualified_name(cls):
    """``module.qualname`` of a class, such as ``'builtins.Exception'``."""
    return "%s.%s" % (cls.__module__, cls.__qualname__)


def record_error(name):
    """Kind of ``getattr(modelx.core.errors, name, None)`` and, if it is
    a class, its ``__name__`` and the qualified names of its
    ``__bases__``, in order."""
    obj = getattr(modelx.core.errors, name, None)
    if obj is None:
        return {"kind": None}
    if not isinstance(obj, type):
        return {"kind": "attribute"}
    return {"kind": "class", "name": obj.__name__,
            "bases": [qualified_name(c) for c in obj.__bases__]}


def record_kind(obj):
    """The ``__name__`` of the class of ``obj``, and whether T1's module
    check passes for it: the class's ``__module__`` is a str that starts
    with ``'modelx.'``."""
    cls = type(obj)
    mod = cls.__module__
    return {"kind": "class", "name": cls.__name__,
            "modelx_module": isinstance(mod, str) and mod.startswith(
                "modelx.")}


def build_surface():
    """Record the frozen members on objects of a fresh model.

    Returns a dict:

    ``surface``
        the golden's layout: {section: {class name: {member: entry}}},
        with the module's name in place of a class name under
        ``"errors"`` and ``"T1"`` under ``"kinds"``, whose entries are
        keyed by class name;
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

        source = forwarding_class(objs)
        for section, cls_name, name in sorted(frozen_table()):
            if section == "kinds":
                if name in objs:
                    surface["kinds"].setdefault(cls_name, {})[name] = (
                        record_kind(objs[name]))
                continue
            if section == "errors" or cls_name not in objs:
                continue
            if section == "members":
                entry = record_member(objs[cls_name], name)
            else:
                entry = record_forwarded(objs[cls_name], name, source)
            surface[section].setdefault(cls_name, {})[name] = entry
        m._impl._check_sanity()
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
            continue
        if g.get("name") != w.get("name"):
            problems.append(
                "%s is now another class: its __name__ changed: %s -> %s"
                % (label, w.get("name"), g.get("name")))
        if g.get("bases") != w.get("bases"):
            problems.append(
                "%s changed its base classes (__bases__): %s -> %s"
                % (label, w.get("bases"), g.get("bases")))
    return problems


def compare_kind(golden, live, name):
    """Return a list of problems with the frozen class name ``name``."""
    if name in live["errors"]:
        return ["could not get an object of class %s from public API: %s"
                % (name, live["errors"][name])]
    want = golden.get("kinds", {}).get(KINDS_SET, {}).get(name)
    got = live["surface"]["kinds"].get(KINDS_SET, {}).get(name)
    if got is None:
        return ["build_objects() returns no object for the kind %s" % name]
    if want is None:
        return ["the kind %s is listed but not in the golden; regenerate it"
                " with '%s'" % (name, WRITE_COMMAND)]

    problems = []
    if got["name"] != want["name"]:
        problems.append(
            "the object built for the kind %s is of a class named %s: the"
            " class was renamed, or the object is now of another class"
            % (want["name"], got["name"]))
    if got["modelx_module"] != want["modelx_module"]:
        problems.append(
            "the class of the kind %s is no longer defined in a module of"
            " the modelx package, so T1's module check fails for it" % name)
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
                      if section not in ("errors", "kinds")})


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


@pytest.mark.parametrize("name", KINDS)
def test_kind_names_unchanged(golden, live, name):
    if name in live["skipped"]:
        pytest.skip("%s needs %s: %s" % (
            name, OPTIONAL[name], live["skipped"][name]))

    problems = compare_kind(golden, live, name)
    assert not problems, (
        "Frozen class name of T1 changed:\n  %s\n%s"
        % ("\n  ".join(problems), KINDS_RULE))


def test_kinds_are_the_recipes():
    """KINDS here is the set of T1's recipe in test_kind.py."""
    assert len(set(KINDS)) == len(KINDS) == 12
    assert set(KINDS) == test_kind.KINDS


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
        if entry["kind"] != "class" or entry["name"] != name)
    if aliases:
        sys.exit("cannot write: not a class of that name in %s: %s"
                 % (ERRORS_MODULE, aliases))
    kinds = live["surface"]["kinds"].get(KINDS_SET, {})
    wrong = sorted(name for name in KINDS if name not in kinds
                   or kinds[name]["name"] != name
                   or not kinds[name]["modelx_module"])
    if wrong:
        sys.exit("cannot write: kinds not of a modelx class of that name: %s"
                 % wrong)
    with pathlib.Path(path).open("w", encoding="utf-8") as f:
        json.dump(live["surface"], f, indent=1, sort_keys=True)
        f.write("\n")
    print("written:", path)


if __name__ == "__main__":
    if "--write" in sys.argv:
        write_golden()
    else:
        print("pass --write to regenerate", GOLDEN_PATH)
