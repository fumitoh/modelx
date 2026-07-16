# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

from modelx.core.base import _rename_item, sort_dict


class Instruction:

    def __init__(self, func, args=(), arghook=None, kwargs=None):

        self.func = func
        self.args = args
        self.arghook = arghook
        self.kwargs = kwargs if kwargs else {}

    def execute(self):
        if self.arghook:
            args, kwargs = self.arghook(self)
        else:
            args, kwargs = self.args, self.kwargs

        return self.func(*args, **kwargs)

    @property
    def funcname(self):
        return self.func.__name__

    def __repr__(self):
        return "<Instruction: %s>" % self.funcname


class InstructionList(list):

    def execute(self, clear=True):
        result = None
        for inst in self:
            result = inst.execute()
        if clear:
            self.clear()
        return result


class ChangeSet:
    """What one committed edit did to the model (CoreRefactorDesign §5.4).

    Collected by :class:`Transaction` while an Edit runs and consumed by
    ``ModelEditor._finalize`` after commit. ``dirty_containers`` and
    ``dirty_spaces`` are dicts used as insertion-ordered sets so that
    post-commit notification order is deterministic.
    """

    __slots__ = (
        "created",
        "removed",
        "modified",
        "dirty_containers",
        "dirty_spaces",
        "cleared_subs",
        "finalize_ops",
        "registry_ops"
    )

    def __init__(self):
        self.created = []           # new impls, including derived ones
        self.removed = []           # impls taken out of containers
        self.modified = []          # impls rebound/changed in place
        self.dirty_containers = {}  # (parent_impl, attr) -> None
        self.dirty_spaces = {}      # idstr -> None
        self.cleared_subs = {}      # space_impl -> None: spaces whose
                                    # dynamic subs' root itemspaces are
                                    # cleared selectively in finalize
                                    # (clear_subs_rootitems), as opposed
                                    # to the nuke-all policy applied to
                                    # dirty_containers
        self.finalize_ops = []      # edit-specific zero-arg callables run
                                    # post-commit, between deletions and
                                    # the batched notify
        self.registry_ops = []      # ValueRegistry ops run in finalize:
                                    # ("register", ref) / ("unregister", ref)
                                    # / ("rebind", old_ref, new_ref)


def _insert_at(container, key, value, index):
    """Insert ``key: value`` into ``container`` at position ``index``."""
    tail = [k for k in list(container) if k != key][index:]
    container[key] = value
    for k in tail:
        container[k] = container.pop(k)


class Transaction:
    """Undo journal over container writes (CoreRefactorDesign §5.4).

    Edits route every structural write through this object so that
    ``rollback`` can restore the model bit-identically — including dict
    ordering, which is observable through namespaces and serialization.
    The shadow-graph half arrives with the graph-mutating edits
    (Phase 6); the reference edits of Phase 4 do not touch the
    inheritance graph.
    """

    def __init__(self, model):
        self.model = model
        self.changes = ChangeSet()
        self._journal = []      # undo records, replayed in reverse

    # ----------------------------------------------------------------------
    # Journaled writes

    def set_item(self, container, key, value):
        if key in container:
            self._journal.append(("replace", container, key, container[key]))
        else:
            self._journal.append(("add", container, key))
        container[key] = value

    def del_item(self, container, key):
        index = list(container).index(key)
        self._journal.append(("del", container, key, container[key], index))
        del container[key]

    def move_to_end(self, container, key):
        index = list(container).index(key)
        self._journal.append(("move", container, key, index))
        container[key] = container.pop(key)

    def rename_item(self, container, old_key, new_key):
        """Rename ``old_key`` to ``new_key`` keeping its position."""
        self._journal.append(("rename", container, old_key, new_key))
        _rename_item(container, old_key, new_key)

    def sort_items(self, container, sorted_keys=None):
        """Sort ``container`` keys (all, or the ``sorted_keys`` part)."""
        self._journal.append(("order", container, list(container)))
        sort_dict(container, sorted_keys)

    def set_attr(self, obj, attr, value):
        self._journal.append(("attr", obj, attr, getattr(obj, attr)))
        setattr(obj, attr, value)

    def add_undo(self, func, *args):
        """Journal an undo callback for a side effect the caller performed
        outside the journaled writes (e.g. observer registration done by
        a constructor)."""
        self._journal.append(("undo", func, args))

    # ----------------------------------------------------------------------
    # ChangeSet bookkeeping

    def add_created(self, impl):
        self.changes.created.append(impl)

    def add_removed(self, impl):
        self.changes.removed.append(impl)

    def add_modified(self, impl):
        self.changes.modified.append(impl)

    def mark_dirty(self, parent, attr):
        self.changes.dirty_containers[(parent, attr)] = None
        if not parent.is_model():
            self.changes.dirty_spaces[parent.idstr] = None

    def add_cleared_subs(self, space):
        self.changes.cleared_subs[space] = None
        self.changes.dirty_spaces[space.idstr] = None

    # ----------------------------------------------------------------------
    # Outcome

    def rollback(self):
        """Reverse-replay the journal; the model is bit-identical to the
        state before the edit. No notify/trace/registry actions have run
        (they are all post-commit)."""
        while self._journal:
            record = self._journal.pop()
            kind = record[0]
            if kind == "add":
                _, container, key = record
                del container[key]
            elif kind == "replace":
                _, container, key, old = record
                container[key] = old
            elif kind == "del":
                _, container, key, old, index = record
                _insert_at(container, key, old, index)
            elif kind == "move":
                _, container, key, index = record
                value = container.pop(key)
                _insert_at(container, key, value, index)
            elif kind == "rename":
                _, container, old_key, new_key = record
                _rename_item(container, new_key, old_key)
            elif kind == "order":
                _, container, keys = record
                for k in keys:
                    container[k] = container.pop(k)
            elif kind == "attr":
                _, obj, attr, old = record
                setattr(obj, attr, old)
            elif kind == "undo":
                _, func, args = record
                func(*args)
            else:
                raise RuntimeError("must not happen")
        self.changes = ChangeSet()

    def commit(self):
        self._journal.clear()
