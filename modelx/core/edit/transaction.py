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
        "removed_spaces",
        "modified",
        "dirty_containers",
        "dirty_spaces",
        "dirty_bases",
        "finalize_ops",
        "registry_ops"
    )

    def __init__(self):
        self.created = []           # new impls, including derived ones
        self.removed = []           # impls taken out of containers
        self.removed_spaces = []    # spaces deleted by this edit (also
                                    # in removed); lets ref re-derivation
                                    # treat values inside the deleted
                                    # trees as already invalid
        self.modified = []          # impls rebound/changed in place
        self.dirty_containers = {}  # (parent_impl, attr) -> None
        self.dirty_spaces = {}      # idstr -> space_impl: spaces whose
                                    # namespace bindings this edit
                                    # changed (incl. removed spaces);
                                    # intersected with the FULL closure
                                    # (dynbases + MRO bases + parent
                                    # chain) by the itemspace
                                    # invalidation (§5.8)
        self.dirty_bases = {}       # idstr -> space_impl: spaces whose
                                    # members changed only in place
                                    # (formula changes, renames);
                                    # intersected with the recorded
                                    # dynbases only, preserving the
                                    # per-dynbase selectivity these
                                    # edits always had
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

    Graph-mutating edits work on a shadow copy of the inheritance graph
    obtained from :meth:`get_shadow_graph`: the pristine pre-edit graph
    is kept aside and swapped back in on rollback, so the shadow can be
    mutated freely without journaling individual graph writes.
    """

    def __init__(self, model):
        self.model = model
        self.changes = ChangeSet()
        self._journal = []      # undo records, replayed in reverse
        self._old_graph = None  # pre-edit graph, kept for rollback

    # ----------------------------------------------------------------------
    # Shadow graph

    def get_shadow_graph(self):
        """The inheritance graph the edit reads and mutates.

        On first access the manager's graph is copied and the copy is
        installed as ``spmgr._graph``, so that all graph queries issued
        while the edit runs (``_get_subs``, MRO and relative-reference
        resolution in the derive stage) see the mutated state.
        ``commit`` keeps the copy; ``rollback`` swaps the untouched
        pre-edit graph back in.
        """
        spmgr = self.model.spmgr
        if self._old_graph is None:
            self._old_graph = spmgr._graph
            spmgr._graph = self._old_graph.copy()
        return spmgr._graph

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

    def add_removed_space(self, space):
        self.changes.removed.append(space)
        self.changes.removed_spaces.append(space)
        # Itemspace trees whose closure contains the deleted space are
        # stale and must be invalidated (§5.8).
        self.changes.dirty_spaces[space.idstr] = space

    def is_in_removed_space(self, impl):
        """True if ``impl`` is, or lives inside, a space this edit
        removes. Deletions are finalized post-commit, so during the
        derive stage such impls still look alive; refs targeting them
        must nevertheless re-derive as if the target were already
        deleted (pre-pipeline deletion order)."""
        for space in self.changes.removed_spaces:
            if impl is space or impl.has_ascendant(space):
                return True
        return False

    def add_modified(self, impl):
        self.changes.modified.append(impl)

    def mark_dirty(self, parent, attr):
        self.changes.dirty_containers[(parent, attr)] = None
        if not parent.is_model():
            self.changes.dirty_spaces[parent.idstr] = parent

    def mark_dirty_base(self, space):
        """Record ``space`` in ``dirty_bases``: for edits (formula
        changes, renames) that alter no namespace binding but stale the
        itemspace trees built on ``space``."""
        self.changes.dirty_bases[space.idstr] = space

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
        if self._old_graph is not None:
            self.model.spmgr._graph = self._old_graph
            self._old_graph = None
        self.changes = ChangeSet()

    def commit(self):
        self._journal.clear()
        self._old_graph = None
