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

from modelx.core.base import Interface


class _ValueEntry:
    """Registry entry for one referenced value.

    Holds the value itself strongly, so its id cannot be reused by
    another object while the entry exists (D-4).
    """

    __slots__ = ("value", "refs")

    def __init__(self, value, refs):
        self.value = value
        self.refs = refs        # [ReferenceImpl]


class ValueRegistry:
    """Tracks non-Interface values assigned to References (Phase 3).

    Successor to ``ReferenceManager``. The ``register``/``unregister``/
    ``rebind`` hooks below are pure bookkeeping: the callers
    (``ModelImpl.set_attr``/``del_attr``, ``UserSpaceImpl.set_attr``/
    ``del_ref``) invoke the spmgr/ModelImpl mutators directly and then
    the hooks. The one remaining mutation path is ``update_value``,
    which rebinds refs through ``parent.on_update_ref``; it is slated
    to become an Edit in Phase 4.

    Only refs assigned through those attribute-access paths are
    registered; derived refs and refs created by
    ``new_space(refs=...)`` are not, matching ReferenceManager.
    The IOSpec associated with a value is garbage-collected exactly
    when the value's last registered ref disappears.
    """

    def __init__(self, model, iomanager):
        self._model = model
        self._manager = iomanager
        self._entries = {}          # id(value) -> _ValueEntry

    # ----------------------------------------------------------------------
    # Registry hooks called after model mutation

    def register(self, ref):
        """Add ``ref`` to the entry of its value."""
        value = ref.interface
        if isinstance(value, Interface):
            return
        entry = self._entries.get(id(value))
        if entry is None:
            self._entries[id(value)] = _ValueEntry(value, [ref])
        else:
            assert all(ref is not r for r in entry.refs)
            entry.refs.append(ref)

    def unregister(self, ref):
        """Remove ``ref``; GC the value's spec when its last ref goes."""
        value = ref.interface
        if isinstance(value, Interface):
            return
        entry = self._entries.get(id(value))
        assert entry
        entry.refs.remove(ref)
        if not entry.refs:
            del self._entries[id(value)]
            self._del_spec_if_any(value)

    def rebind(self, old_ref, new_ref):
        """Move registration from ``old_ref`` to ``new_ref``.

        Tolerates ``old_ref`` not being registered (e.g. it is derived,
        or was created by ``new_space(refs=...)``), unlike
        ``unregister``.
        """
        old_value = old_ref.interface
        entry = self._entries.get(id(old_value))
        if entry is not None:
            if old_ref in entry.refs:
                entry.refs.remove(old_ref)
            if not entry.refs:
                del self._entries[id(old_value)]
                self._del_spec_if_any(old_value)

        new_value = new_ref.interface
        if not isinstance(new_value, Interface):
            entry = self._entries.get(id(new_value))
            if entry is None:
                self._entries[id(new_value)] = _ValueEntry(
                    new_value, [new_ref])
            else:
                entry.refs.append(new_ref)

    # ----------------------------------------------------------------------
    # Queries

    def has_value(self, value):
        return id(value) in self._entries

    def get_refs(self, value):
        """Return a list of the refs registered for ``value``."""
        return list(self._entries[id(value)].refs)

    @property
    def values(self):
        return list(entry.value for entry in self._entries.values())

    @property
    def _valid_to_refs(self):
        """Backward-compat view: id(value) -> [refs].

        The lists are the live entry lists; the dict itself is built on
        each access.
        """
        return {valid: entry.refs
                for valid, entry in self._entries.items()}

    # ----------------------------------------------------------------------
    # IOSpec bookkeeping

    def has_spec(self, value):
        return self.get_spec(value) is not None

    def get_spec(self, value):
        return self._manager.get_spec_from_value(self._model.interface, value)

    @property
    def specs(self):
        result = []
        for entry in self._entries.values():
            spec = self.get_spec(entry.value)
            if spec is not None:
                result.append(spec)
        return result

    def del_all_spec(self):
        specs = self.specs.copy()
        while specs:
            self._manager.del_spec(specs.pop())

    def _del_spec_if_any(self, value):
        spec = self._manager.get_spec_from_value(
            io_group=self._model.interface,
            value=value
        )
        if spec:
            self._manager.del_spec(spec)

    # ----------------------------------------------------------------------
    # Value update

    def update_value(self, old_value, new_value=None, **kwargs):

        entry = self._entries.get(id(old_value))
        spec = self._manager.get_spec_from_value(
            self._model.interface, old_value)

        if entry is None:
            raise ValueError("value not referenced")

        if new_value is None:
            new_value = old_value

        if spec is not None:
            self._manager.update_spec_value(spec, new_value, kwargs)
            new_value = spec.value

        refs = entry.refs
        newrefs = []
        while refs:
            ref = refs.pop()
            newrefs.append(
                ref.parent.on_update_ref(ref.name, new_value, ref.refmode))

        del self._entries[id(old_value)]
        self._entries[id(new_value)] = _ValueEntry(new_value, newrefs)

    # ----------------------------------------------------------------------
    # Sanity check

    def _check_sanity(self):

        for valid, entry in self._entries.items():
            assert valid == id(entry.value)
            assert entry.refs
            for r in entry.refs:
                assert r.interface is entry.value
            spec = self._manager.get_spec_from_value(
                io_group=self._model.interface,
                value=entry.value)
            if spec is not None:
                assert entry.value is spec.value
                spec._check_sanity()


# Import alias: ReferenceManager was replaced by ValueRegistry in
# Phase 3 of the core refactoring. Kept for compatibility with code
# importing the old name.
ReferenceManager = ValueRegistry
