import modelx as mx
from types import MappingProxyType
import pytest


def test_itemspaces(itemspacetest):

    _, s = itemspacetest
    items = s.itemspaces

    assert isinstance(items, MappingProxyType)
    assert len(items) == 10
    for k, v in items.items():
        assert s[k] is v


def test_delitem(itemspacetest):

    paramlen, s = itemspacetest

    assert s.itemspaces

    for i in range(10):
        del s[(i,) * paramlen]

    for i in range(10):
        with pytest.raises(KeyError):
            del s[(i,) * paramlen]

    assert not s.itemspaces


def test_clear_all(itemspacetest):

    paramlen, s = itemspacetest

    assert s.itemspaces
    s.clear_all()
    assert not s.itemspaces


def test_clear_at(itemspacetest):

    paramlen, s = itemspacetest

    assert s.itemspaces
    for i in range(10):
        s.clear_at(*((i,) * paramlen))

    assert not s.itemspaces