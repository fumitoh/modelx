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

"""Step A keystone: the mediated membership container.

A ``MemberContainer`` owns the members of ONE category (cells, own_refs,
named_spaces, ...) for one space. It replaces the raw dicts currently held
directly on ``BaseSpaceImpl`` (``self.cells``, ``self.own_refs``,
``self.named_spaces``) so that composition (parent.py), inheritance
(``UserSpaceImpl.on_inherit``) and namespace assembly
(``BaseSpaceImpl.on_update_ns``) all mutate/observe through one surface
instead of poking dicts and faking notifications via
``self.on_notify(self.cells)``.

It is a real ``Subject``: mutations call ``notify()``, and the
``NamespaceServer`` / ``AlteredFunction`` become ordinary ``Observer``s of
the relevant containers. This removes the namespace content rule from
space.py (step B) and gives the inheritance updater a call-based API
instead of in-place dict surgery (step C).
"""

from typing import Iterator, Optional, Sequence

from modelx.core.base import (
    Subject,
    get_mixin_slots,
    _rename_item,
    _sort_partial,
    _sort_all,
)


class MemberContainer(Subject):
    """Ordered, defined/derived-aware, observable map of one member category.

    Members are ``Derivable`` impls (CellsImpl / ReferenceImpl / SpaceImpl).
    Iteration order is significant and mirrors today's dict ordering rules:
    derived members are introduced in base order, defined members are kept
    after them (see ``move_to_end`` / ``sort``).
    """

    __slots__ = ("_data", "_owner", "_category") + get_mixin_slots(Subject)

    def __init__(self, owner, category: str):
        Subject.__init__(self)
        self._owner = owner          # the SpaceImpl that owns this category
        self._category = category    # "cells" | "own_refs" | "named_spaces"
        self._data = {}

    # -- read surface (drop-in for the current dict reads) ----------------

    def __getitem__(self, name: str):
        return self._data[name]

    def __contains__(self, name: str) -> bool:
        return name in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, name: str, default=None):
        return self._data.get(name, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    # -- defined / derived views -----------------------------------------
    # Replaces inline ``bm[name].is_defined()`` filtering in on_inherit and
    # the ``name in self.is_derived()`` checks in del_ref/del_cells.

    def is_derived(self, name: str) -> bool:
        return self._data[name].is_derived()

    def defined_names(self) -> list:
        return [k for k, v in self._data.items() if v.is_defined()]

    def derived_names(self) -> list:
        return [k for k, v in self._data.items() if v.is_derived()]

    # -- mutation surface (the single seam) ------------------------------
    # Every mutation notifies. ``silent=True`` batches a sequence of
    # changes (the inheritance updater applies many at once) and the caller
    # calls ``flush()`` once at the end.

    def set(self, name: str, member, *, silent: bool = False) -> None:
        """Insert or replace ``name``. Replaces ``selfdict[name] = member``."""
        self._data[name] = member
        self._touched(silent)

    def remove(self, name: str, *, silent: bool = False):
        """Delete and return ``name``. Replaces ``del self.cells[name]``."""
        member = self._data.pop(name)
        self._touched(silent)
        return member

    def rename(self, old: str, new: str, *, silent: bool = False) -> None:
        """Position-preserving rename. Wraps base._rename_item."""
        _rename_item(self._data, old, new)
        self._touched(silent)

    def move_to_end(self, name: str, *, silent: bool = False) -> None:
        """Reassert ordering. Replaces ``d[name] = d.pop(name)`` in
        on_inherit (used to keep defined members after derived ones)."""
        self._data[name] = self._data.pop(name)
        self._touched(silent)

    def sort(self, names: Optional[Sequence[str]] = None,
             *, silent: bool = False) -> None:
        """Sort all (``names is None``) or a consecutive run. Replaces
        ``sort_dict(self.cells, keys)`` driven by on_sort_cells."""
        if names is None:
            _sort_all(self._data)
        else:
            _sort_partial(self._data, list(names))
        self._touched(silent)

    def flush(self) -> None:
        """Emit one notification after a ``silent=True`` batch."""
        self.notify()

    # -- internal --------------------------------------------------------

    def _touched(self, silent: bool) -> None:
        if not silent:
            self.notify()

    # Slot-walking serialization (mirrors BaseSpaceImpl.__getstate__);
    # observers are re-attached by the owner on rebuild, not pickled.
    def __getstate__(self):
        return {"_owner": self._owner,
                "_category": self._category,
                "_data": self._data}

    def __setstate__(self, state):
        self._owner = state["_owner"]
        self._category = state["_category"]
        self._data = state["_data"]
        self.observers = []
