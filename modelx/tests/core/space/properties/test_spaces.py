from collections import ChainMap
import modelx as mx
import pytest


@pytest.fixture(scope="module")
def testspaces():
    m = mx.new_model()
    parent = m.new_space("Parent", formula=lambda i: None)
    child = parent.new_space("Child")
    item = parent[1]

    yield parent, child, item
    m._impl._check_sanity()
    m.close()


def test_spaces(testspaces):
    parent, child, item = testspaces
    assert list(parent.spaces.keys()) == ["Child"]
    assert list(parent.spaces.values()) == [child]


def test_named_spaces(testspaces):
    parent, child, item = testspaces
    assert list(parent.named_spaces.keys()) == ["Child"]
    assert list(parent.named_spaces.values()) == [child]


def test_all_spaces(testspaces):
    parent, child, item = testspaces
    all_spaces = ChainMap(parent.named_spaces, parent._named_itemspaces)
    assert len(all_spaces) == 2
    assert child in all_spaces.values()
    assert item in all_spaces.values()


