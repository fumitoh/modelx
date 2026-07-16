"""Unit tests for the Phase 4 edit-pipeline transaction journal.

The Transaction must restore containers bit-identically on rollback,
including dict ordering, which is observable through namespaces and
serialized models (CoreRefactorDesign.md §5.4).
"""

import pytest

from modelx.core.edit.transaction import Transaction, ChangeSet


class _FakeModel:
    def is_model(self):
        return True


@pytest.fixture
def txn():
    return Transaction(_FakeModel())


def test_rollback_restores_order_after_del(txn):
    d = {"a": 1, "b": 2, "c": 3, "d": 4}
    txn.del_item(d, "b")
    assert list(d) == ["a", "c", "d"]
    txn.rollback()
    assert d == {"a": 1, "b": 2, "c": 3, "d": 4}
    assert list(d) == ["a", "b", "c", "d"]


def test_rollback_restores_order_after_move(txn):
    d = {"a": 1, "b": 2, "c": 3}
    txn.move_to_end(d, "a")
    assert list(d) == ["b", "c", "a"]
    txn.rollback()
    assert list(d) == ["a", "b", "c"]


def test_rollback_removes_added_and_restores_replaced(txn):
    d = {"a": 1}
    txn.set_item(d, "b", 2)      # add
    txn.set_item(d, "a", 10)     # replace
    txn.rollback()
    assert d == {"a": 1}
    assert list(d) == ["a"]


def test_rollback_interleaved_ops(txn):
    d = {"a": 1, "b": 2, "c": 3}
    txn.del_item(d, "a")
    txn.set_item(d, "x", 9)
    txn.move_to_end(d, "b")
    txn.del_item(d, "c")
    txn.set_item(d, "b", 20)
    assert list(d) == ["x", "b"]
    txn.rollback()
    assert d == {"a": 1, "b": 2, "c": 3}
    assert list(d) == ["a", "b", "c"]


def test_rollback_restores_attrs_and_runs_undo_callbacks(txn):
    class Obj:
        pass

    obj = Obj()
    obj.value = 1
    calls = []

    txn.set_attr(obj, "value", 2)
    txn.add_undo(calls.append, "undone")
    txn.rollback()

    assert obj.value == 1
    assert calls == ["undone"]


def test_rollback_resets_changeset(txn):
    d = {}
    txn.set_item(d, "a", 1)
    txn.add_created("impl")
    txn.mark_dirty(_FakeModel(), "global_refs")
    txn.rollback()
    assert txn.changes.created == []
    assert txn.changes.dirty_containers == {}


def test_commit_clears_journal(txn):
    d = {"a": 1}
    txn.set_item(d, "b", 2)
    txn.commit()
    txn.rollback()      # nothing to undo after commit
    assert d == {"a": 1, "b": 2}


def test_changeset_defaults():
    ch = ChangeSet()
    assert ch.created == [] and ch.removed == [] and ch.modified == []
    assert ch.dirty_containers == {} and ch.dirty_spaces == {}
    assert ch.registry_ops == []
