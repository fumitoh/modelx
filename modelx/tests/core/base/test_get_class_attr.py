"""``get_class_attr``, the class-only lookup behind extattrs (F11).

It walks the namespaces of ``cls.__mro__`` and keeps them for modelx's
classes and the built-in types, so that a request does not call
``vars()`` on every class of the MRO each time: a Cells' Properties
request took 4.89 us against 0.33's 3.55 us without that.  The kept
namespaces are the classes' live mappingproxies, and are used only while
``cls.__mro__`` is the same tuple, so the lookup answers as an uncached
walk does after an attribute is set or deleted, as ``monkeypatch`` does,
and after ``__bases__`` is replaced.  A class of any other module is not
kept.

These tests check a function of ``modelx.core.base``, which is not tool
API; the last one checks the same through ``_get_attrdict``.
"""

import gc
import weakref

import pytest

import modelx as mx
from modelx.core.base import get_class_attr, _MISSING
from modelx.core.cells import Cells


def test_modelx_class_sees_later_changes(monkeypatch):
    """This module is in ``modelx.``, so its classes are kept too."""

    class A:
        x = 1

    class B(A):
        pass

    class C:
        z = 3

    assert B.__module__.startswith("modelx.")
    assert get_class_attr(B, "x") == 1
    assert get_class_attr(B, "y") is _MISSING
    B.y = 2
    assert get_class_attr(B, "y") == 2
    del A.x
    assert get_class_attr(B, "x") is _MISSING
    B.__bases__ = (C,)
    assert get_class_attr(B, "z") == 3
    monkeypatch.setattr(C, "z", 30)
    assert get_class_attr(B, "z") == 30
    monkeypatch.undo()
    assert get_class_attr(B, "z") == 3


def test_builtin_types():
    for cls in (str, int, type(None), tuple, dict):
        assert get_class_attr(cls, "_get_attrdict") is _MISSING
    assert get_class_attr(str, "upper") is vars(str)["upper"]
    assert get_class_attr(bool, "__repr__") is vars(bool)["__repr__"]


def test_other_classes_are_not_kept():
    """A class of a user's module is walked each time, and not held."""
    User = type("User", (), {"__module__": "usermod", "a": 1})
    Sub = type("Sub", (User,), {"__module__": "usermod"})
    assert get_class_attr(Sub, "a") == 1
    Sub.b = 2
    assert get_class_attr(Sub, "b") == 2
    ref = weakref.ref(Sub)
    del Sub
    gc.collect()
    assert ref() is None


def test_module_not_a_str():
    """wrapt's proxy classes, for one, make ``__module__`` a property."""

    class Proxy:
        @property
        def __module__(self):
            return "x"

        a = 1

    assert get_class_attr(Proxy, "a") == 1
    assert get_class_attr(Proxy, "b") is _MISSING


@pytest.fixture
def one_cells():
    m = mx.new_model("ClassAttr")
    c = m.new_space("S").new_cells("c", formula="lambda: 1")
    yield c
    m._impl._check_sanity()
    m.close()


def test_extattrs_see_a_patched_class(one_cells, monkeypatch):
    """A name the class gains after a request is answered by the next
    request, and a name it loses is left out again."""
    c = one_cells
    assert "_probe_attr" not in c._get_attrdict(["_probe_attr"], False)
    monkeypatch.setattr(Cells, "_probe_attr", property(lambda self: 5),
                        raising=False)
    assert c._get_attrdict(["_probe_attr"], False)["_probe_attr"] == 5
    monkeypatch.undo()
    assert "_probe_attr" not in c._get_attrdict(["_probe_attr"], False)
