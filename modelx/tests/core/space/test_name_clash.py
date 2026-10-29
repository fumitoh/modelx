"""Name clashes that modelx accepted or reported wrongly before 0.34.

devnotes/ToolAPIDesign.md, section 3.3, F10 (section 6, PR 3).  Each made
a valid name do something other than what was asked:

* ``UserSpace.set_ref(name, value, mode)``, and ``absref`` and ``relref``,
  with the name of a Cells of the Space: on 0.33, for a Cells with no
  parameters, it set the Cells' input and made no Reference, against its
  docstring, which says a clash with a Cells or a Space is refused.  The
  name of a child Space raised a ValueError with no message.  From 0.34
  both raise AttributeError, the type the docstring gives, and nothing
  changes.  ``space.name = value`` still sets the Cells' input, and the
  refmode check of F2 still runs first.  Neither check runs while a model
  is read: 0.33 saves a Reference whose name a base's Cells also has, and
  reads the file back by setting the Cells' input.
* ``Model.new_space(name)`` with the name of a macro: on 0.33 the Space
  hid the macro (``m.mac`` was the Space), and so did renaming or copying
  a Space to that name, though ``new_macro`` refuses a Space's name.  Such
  a model is written, but ``read_model`` cannot read it back (``ValueError:
  Name 'mac' already used``, measured fix-integrate/i01 and on every
  format 0.33 writes that keeps macros).  From 0.34 all three routes raise
  ValueError, as for any other name the Model holds.
* Assigning to a read-only property of a UserSpace or a Model: on 0.33
  ``EditableParent.__setattr__`` called the property's ``fset``, None, and
  raised ``TypeError: 'NoneType' object is not callable``.  From 0.34 it
  raises ``AttributeError: <name> is read-only``.  The properties are
  found by code: 23 on UserSpace and 16 on Model on 0.33, underscore
  names included.

The tests read only the tool API and the public API, and give formulas as
source text.  Each model is torn down by ``_impl._check_sanity()`` and then
``close()``.
"""

import os

import pytest

import modelx as mx
from modelx.core.model import Model
from modelx.core.space import UserSpace


MACRO = "def mac(x):\n    return x + 1\n"


@pytest.fixture
def clash_model():
    """
        Clash---S(B)----a(), p(i), x=5, Child, [b() from B]
          |   +---B-----b()
          |   +---T(S)--t()
          +---glob=1, macro mac(x)
    """
    m = mx.new_model("Clash")
    m.glob = 1
    s = m.new_space("S")
    s.new_cells("a", formula="lambda: 1")
    s.new_cells("p", formula="lambda i: i")
    s.new_space("Child")
    s.x = 5
    b = m.new_space("B")
    b.new_cells("b", formula="lambda: 2")
    s.add_bases(b)
    t = m.new_space("T", bases=s)
    t.new_cells("t", formula="lambda: 3")
    m.new_macro("mac", MACRO)
    yield m
    m._impl._check_sanity()
    m.close()


# ----------------------------------------------------------------------
# set_ref, absref and relref

SET_REF_ROUTES = {
    "set_ref auto": lambda s, n, v: s.set_ref(n, v, "auto"),
    "set_ref absolute": lambda s, n, v: s.set_ref(n, v, "absolute"),
    "set_ref relative": lambda s, n, v: s.set_ref(n, v, "relative"),
    "absref": lambda s, n, v: s.absref(**{n: v}),
    "relref": lambda s, n, v: s.relref(**{n: v}),
}

# (name, what holds it in S)
MEMBERS = {
    "a, a Cells with no parameters": ("a", "Cells"),
    "p, a Cells with a parameter": ("p", "Cells"),
    "b, a Cells S inherits from B": ("b", "Cells"),
    "Child, a child Space": ("Child", "Space"),
}


def snapshot(s):
    """What the refused calls must leave unchanged."""
    return {
        "refs": sorted(s.refs),
        "cells": list(s.cells),
        "spaces": list(s.spaces),
        "a": s.a(),
        "b": s.b(),
        "inputs": [c.is_input() for c in (s.a, s.b)],
        "children": [type(s.spaces[n]).__name__ for n in s.spaces],
    }


@pytest.mark.parametrize("route", list(SET_REF_ROUTES))
@pytest.mark.parametrize("member", list(MEMBERS))
def test_set_ref_refuses_a_member_name(clash_model, route, member):
    s = clash_model.S
    name, kind = MEMBERS[member]
    before = snapshot(s)
    with pytest.raises(AttributeError,
                       match="'%s' is already defined as a %s" % (name, kind)):
        SET_REF_ROUTES[route](s, name, 3)
    assert snapshot(s) == before
    assert name not in s.refs
    assert not s.a.is_input()


def test_set_ref_refuses_a_modelx_value(clash_model):
    # 0.33 set S.a's input to the Space.
    s = clash_model.S
    with pytest.raises(AttributeError, match="'a' is already defined"):
        s.set_ref("a", s.Child, "auto")
    assert s.a() == 1
    assert not s.a.is_input()


def test_refmode_check_runs_first(clash_model):
    with pytest.raises(ValueError, match="refmode must be one of"):
        clash_model.S.set_ref("a", 3, "sideways")


def test_attribute_assignment_is_unchanged(clash_model):
    s = clash_model.S
    s.a = 3
    assert s.a() == 3
    assert s.a.is_input()
    assert "a" not in s.refs
    with pytest.raises(AttributeError, match="Cells 'p' is not a scalar"):
        s.p = 3
    with pytest.raises(ValueError):
        s.Child = 3
    assert type(s.Child).__name__ == "UserSpace"


def test_set_ref_on_other_names_is_unchanged(clash_model):
    m, s = clash_model, clash_model.S
    s.set_ref("x", 6, "auto")       # its own Reference: rebound
    assert s.x == 6
    s.set_ref("glob", 7, "auto")    # a global: a Reference of S hides it
    assert s.glob == 7
    assert m.glob == 1
    s.set_ref("new", 8, "absolute")
    assert s.new == 8
    assert s._get_object("new", as_proxy=True).refmode == "absolute"
    # A Cells of a sub Space only: refused by the sub Space's check.
    with pytest.raises(ValueError, match="Cannot create reference 't'"):
        s.set_ref("t", 3, "auto")
    assert "t" not in s.refs


def test_read_keeps_a_reference_named_like_a_base_cells(tmp_path):
    """0.33 saves a Reference of S and a Cells S inherits under one name.

    The reader restores a Reference whose value is a modelx object with
    set_ref, so the check does not run while a model is read.  The file
    reads as on 0.33, which sets the Cells' input to the value.
    """
    m = mx.new_model("ClashRead")
    s = m.new_space("S")
    s.c = m.new_space("Other")
    b = m.new_space("B")
    b.new_cells("c", formula="lambda: 1")
    s.add_bases(b)
    assert "c" in s.refs and "c" in s.cells
    path = str(tmp_path / "ClashRead")
    mx.write_model(m, path)
    m._impl._check_sanity()
    m.close()

    m2 = mx.read_model(path)
    try:
        assert "c" in m2.S.cells
        assert m2.S.c.is_input()
        assert m2.S.c() is m2.Other
        m2._impl._check_sanity()
    finally:
        m2.close()


# ----------------------------------------------------------------------
# Model-level Space names and macros

def model_state(m):
    return {"spaces": list(m.spaces), "macros": list(m.macros),
            "mac": m.mac(1)}


@pytest.mark.parametrize("route, message", [
    (lambda m: m.new_space("mac"), "Cannot create space 'mac'"),
    (lambda m: m.S.rename("mac"), "Cannot rename 'S' to 'mac'"),
    (lambda m: m.S.copy(m, "mac"), "Cannot create space 'mac'"),
], ids=["new_space", "rename", "copy"])
def test_space_refuses_a_macro_name(clash_model, route, message):
    m = clash_model
    before = model_state(m)
    with pytest.raises(ValueError, match=message):
        route(m)
    assert model_state(m) == before
    assert m.mac is m.macros["mac"]


def test_automatic_space_name_skips_a_macro():
    m = mx.new_model("AutoName")
    m.new_macro("Space1", "def Space1():\n    return 1\n")
    s = m.new_space()
    assert s.name == "Space2"
    assert m.Space1 is m.macros["Space1"]
    m._impl._check_sanity()
    m.close()


def test_child_space_may_have_a_macro_name(clash_model):
    m = clash_model
    child = m.S.new_space("mac")
    assert m.S.mac is child
    assert m.mac is m.macros["mac"]


def test_macro_routes_are_unchanged(clash_model):
    m = clash_model
    with pytest.raises(ValueError, match="Name 'S' already used"):
        m.new_macro("S", "def S():\n    return 1\n")
    with pytest.raises(ValueError, match="Name 'glob' already used"):
        m.new_macro("glob", "def glob():\n    return 1\n")
    with pytest.raises(KeyError, match="Macro named 'mac' already exists"):
        m.mac = 7


def test_model_with_space_and_macro_of_one_name_cannot_be_read(tmp_path):
    """Why the refusal needs no warning window: no saved model has both.

    0.33 wrote such a model, and its reader refused it, as 0.34's does:
    the reader makes the Spaces first and new_macro then refuses the name.
    The file is made here by adding the macro file 0.33 would have written.
    """
    m = mx.new_model("SpaceMacro")
    m.new_space("mac").new_cells("a", formula="lambda: 1")
    path = str(tmp_path / "SpaceMacro")
    mx.write_model(m, path)
    m._impl._check_sanity()
    m.close()
    with open(os.path.join(path, "_macros.py"), "w") as f:
        f.write(MACRO)
    with pytest.raises(ValueError, match="Name 'mac' already used"):
        mx.read_model(path)
    assert "SpaceMacro" not in mx.get_models()


# ----------------------------------------------------------------------
# Read-only properties

def readonly_properties(cls):
    return sorted(n for n in dir(cls)
                  if isinstance(getattr(cls, n, None), property)
                  and getattr(cls, n).fset is None)


# Measured on 0.33 (and found by code below, so a property added later is
# tested too).
SPACE_READONLY = [
    "_baseattrs", "_cells", "_direct_bases", "_evalrepr", "_idstr",
    "_idtuple", "_name", "_named_itemspaces", "_own_refs", "_parent",
    "bases", "cells", "frame", "fullname", "info", "itemspaces", "model",
    "name", "named_spaces", "parent", "refs", "spaces", "static_spaces"]
MODEL_READONLY = [
    "_baseattrs", "_evalrepr", "_idstr", "_idtuple", "_name", "_parent",
    "fullname", "info", "iospecs", "macros", "model", "name", "parent",
    "refs", "spaces", "tracegraph"]


def test_readonly_properties_are_found():
    assert set(SPACE_READONLY) <= set(readonly_properties(UserSpace))
    assert set(MODEL_READONLY) <= set(readonly_properties(Model))


READONLY = (
    [("UserSpace", n) for n in readonly_properties(UserSpace)]
    + [("Model", n) for n in readonly_properties(Model)])


@pytest.mark.parametrize("owner, name", READONLY,
                         ids=["%s.%s" % r for r in READONLY])
def test_readonly_property_raises_attribute_error(clash_model, owner, name):
    m = clash_model
    obj = m.S if owner == "UserSpace" else m
    refs = sorted(obj.refs)
    with pytest.raises(AttributeError, match="^%s is read-only$" % name):
        setattr(obj, name, 12345)
    assert sorted(obj.refs) == refs
    assert obj.name == ("S" if owner == "UserSpace" else "Clash")


def test_space_bases_is_read_only(clash_model):
    s = clash_model.S
    with pytest.raises(AttributeError, match="bases is read-only"):
        s.bases = 1
    assert s.bases == [clash_model.B]


@pytest.mark.parametrize("owner", ["UserSpace", "Model"])
def test_settable_properties_and_methods_are_unchanged(clash_model, owner):
    m = clash_model
    obj = m.S if owner == "UserSpace" else m
    obj.doc = "changed"
    assert obj.doc == "changed"
    obj.allow_none = True
    assert obj.allow_none is True
    with pytest.raises(AttributeError, match="new_space is not a property"):
        obj.new_space = 1
