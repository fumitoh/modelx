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
named_spaces) for one space/model. It replaces the raw dicts currently held
directly on ``BaseSpaceImpl``/``ModelImpl`` so that composition (parent.py),
inheritance (``UserSpaceImpl.on_inherit``) and namespace assembly
(``BaseSpaceImpl.on_update_ns``) eventually mutate/observe through one
surface instead of poking dicts and faking notifications via
``self.on_notify(self.cells)``.

It subclasses ``dict`` so step A is byte-for-byte behavior-preserving:
every existing call site (``d[name]``, ``del d[name]``, ``d.pop``,
``dict.__setitem__`` in ``_rename_item``, ``sort_dict``, use as a
``CustomChainMap`` layer, the file serializers, pickling) keeps working
unchanged. The notifying mutation API (``set``/``remove``/``move_to_end``/
``sort``/``rename``/``flush``) and the ``Subject`` nature are *additive* and
are adopted by step C; in step A the existing explicit
``self.on_notify(...)`` calls remain the notification path.
"""

from typing import Optional, Sequence

from modelx.core.base import (
    Subject,
    get_mixin_slots,
    _rename_item,
    _sort_partial,
    _sort_all,
)


class MemberContainer(dict, Subject):
    """Ordered, defined/derived-aware, observable map of one member category.

    Members are ``Derivable`` impls (CellsImpl / ReferenceImpl / SpaceImpl).
    Iteration order is significant and is whatever the caller arranges, via
    ``move_to_end``/``sort`` (step C drives these exactly as ``on_inherit``
    does today).
    """

    __slots__ = ("_owner", "_category") + get_mixin_slots(Subject)

    def __init__(self, owner, category: str):
        dict.__init__(self)
        Subject.__init__(self)
        self._owner = owner          # owning SpaceImpl/ModelImpl
        self._category = category    # "cells" | "own_refs" | "named_spaces"

    # -- defined / derived views -----------------------------------------
    # Replaces inline ``bm[name].is_defined()`` filtering in on_inherit and
    # the ``name in self.is_derived()``-style checks in del_ref/del_cells.

    def is_derived(self, name: str) -> bool:
        return self[name].is_derived()

    def defined_names(self) -> list:
        return [k for k, v in self.items() if v.is_defined()]

    def derived_names(self) -> list:
        return [k for k, v in self.items() if v.is_derived()]

    # -- notifying mutation surface (adopted by step C) ------------------
    # Bare dict ops (``d[x]=``, ``del d[x]``, ``d.pop``) keep plain dict
    # semantics so step A changes no behavior. These methods add the single
    # notify seam. ``silent=True`` batches; call ``flush()`` once at the end.

    def set(self, name: str, member, *, silent: bool = False) -> None:
        dict.__setitem__(self, name, member)
        self._touched(silent)

    def remove(self, name: str, *, silent: bool = False):
        member = dict.pop(self, name)
        self._touched(silent)
        return member

    def rename(self, old: str, new: str, *, silent: bool = False) -> None:
        _rename_item(self, old, new)
        self._touched(silent)

    def move_to_end(self, name: str, *, silent: bool = False) -> None:
        dict.__setitem__(self, name, dict.pop(self, name))
        self._touched(silent)

    def sort(self, names: Optional[Sequence[str]] = None,
             *, silent: bool = False) -> None:
        if names is None:
            _sort_all(self)
        else:
            _sort_partial(self, list(names))
        self._touched(silent)

    def flush(self) -> None:
        """Emit one notification after a ``silent=True`` batch."""
        self.notify()

    def _touched(self, silent: bool) -> None:
        if not silent:
            self.notify()

    # -- pickling --------------------------------------------------------
    # dict subclass + __slots__: rely on the protocol-2 two-phase reduce
    # (__new__ -> memoize -> set items -> __setstate__) so the space<->
    # container reference cycle resolves. Slots go through __getstate__;
    # dict items are pickled by the default reduce. Observers are
    # re-attached by the owner on rebuild, not pickled.

    def __getstate__(self):
        return {"_owner": self._owner, "_category": self._category}

    def __setstate__(self, state):
        self._owner = state["_owner"]
        self._category = state["_category"]
        self.observers = []
