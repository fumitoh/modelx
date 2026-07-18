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

"""Inheritance synchronization (CoreRefactorDesign §5.6, Phase 5).

:class:`InheritanceSync` is the only place derived members are created,
updated or removed. It absorbs what used to be three duplicated code
paths:

(a) ``UserSpaceImpl.on_inherit``'s member reconciliation loop
    (:meth:`InheritanceSync.reconcile`),
(b) the derived-cells fan-out of ``SpaceManager.new_cells`` including
    the ``cells_after`` reorder (:meth:`InheritanceSync.derive_new_cells`),
(c) the derived-ref fan-outs of ``new_ref``/``change_ref``
    (:meth:`derive_new_ref`/:meth:`derive_change_ref`).

Member-level ``CellsImpl.on_inherit``/``ReferenceImpl.on_inherit``
remain as callbacks invoked from here, with all container writes routed
through the transaction. Since the graph mutations moved into the
pipeline (Phase 6), every derive path runs under a transaction.
"""

from modelx.core.base import Interface
from modelx.core.chainmap import CustomChainMap
from modelx.core.cells import UserCellsImpl
from modelx.core.reference import ReferenceImpl


def create_ref(txn, space, name, value, is_derived, refmode):
    """Create a reference in ``space`` through the transaction."""
    ref = ReferenceImpl(space, name, value, container=space.own_refs,
                        is_derived=is_derived, refmode=refmode)
    txn.set_item(space.own_refs, name, ref)
    txn.add_created(ref)
    txn.mark_dirty(space, "own_refs")
    return ref


def replace_ref(txn, space, name, value, is_derived, refmode):
    """Replace the reference bound to ``name`` through the transaction."""
    old = space.own_refs[name]
    txn.del_item(space.own_refs, name)
    txn.add_removed(old)
    new = create_ref(txn, space, name, value, is_derived, refmode)
    return old, new


class InheritanceSync:
    """The single home of derived-member creation (D-8).

    ``ops`` is a ``SpaceManager`` providing the graph queries — subs,
    space bases and relative-interface resolution — against the graph
    the operation is running on (the transaction's shadow graph while a
    graph-mutating edit is in progress). Stateless: constructed per
    access by the ``sync`` property of ``SpaceManager``.
    """

    def __init__(self, ops):
        self.ops = ops

    # ----------------------------------------------------------------------
    # Full reconciliation (from UserSpaceImpl.on_inherit)

    def derive_subs(self, space, txn, skip_self=True):
        """Reconcile all subs of ``space`` against their bases."""
        self.derive_spaces(self.ops._get_subs(space, skip_self), txn)

    def derive_spaces(self, spaces, txn):
        """Reconcile the given spaces against their bases.

        Keeps the two-phase inheritance order: all ``cells`` syncs across
        the affected subgraph run before all ``own_refs`` syncs, so that
        relative references resolve against derived spaces created in the
        same edit (CoreRefactorDesign §2.1). ``spaces`` must be in
        topological order, bases before subs.
        """
        for attr in ("cells", "own_refs"):
            for s in spaces:
                bases = self.ops._get_space_bases(s)
                self.reconcile(s, bases, attr, txn)

    def reconcile(self, space, bases, attr, txn):
        """Reconcile ``attr`` ('cells' or 'own_refs') of ``space``
        against ``bases``.

        Derived members missing from ``space`` are created, members no
        longer backed by a base are removed, and surviving members are
        reordered to the bases' order and re-derived through their
        member-level ``on_inherit`` callbacks.
        """
        selfdict = getattr(space, attr)
        basedict = CustomChainMap(*[getattr(b, attr) for b in bases])
        selfkeys = list(selfdict)

        for name in basedict: # ChainMap iterates from the last map

            bs = [bm[name] for bm in basedict.maps
                  if name in bm and bm[name].is_defined()]

            if name not in selfdict:

                if attr == "cells":
                    cells = UserCellsImpl(
                        space=space, name=name, formula=None,
                        is_derived=True)
                    # The constructor registered the cells as an
                    # observer of space; undo that on rollback.
                    txn.add_undo(space.remove_observer, cells)
                    txn.set_item(selfdict, name, cells)
                    txn.add_created(cells)
                    txn.mark_dirty(space, attr)

                elif attr == "own_refs":
                    ref = ReferenceImpl(
                        space, name, None,
                        container=space.own_refs,
                        is_derived=True,
                        refmode=bs[0].refmode
                    )
                    txn.set_item(selfdict, name, ref)
                    txn.add_created(ref)
                    txn.mark_dirty(space, attr)
                else:
                    raise RuntimeError("must not happen")

            else:
                # Remove & add back for reorder
                txn.move_to_end(selfdict, name)
                selfkeys.remove(name)

            if selfdict[name].is_derived():
                selfdict[name].on_inherit(self.ops, bs, txn)

        for name in selfkeys:
            if selfdict[name].is_derived():
                member = selfdict[name]
                txn.del_item(selfdict, name)
                txn.add_removed(member)
                txn.mark_dirty(space, attr)
            else:   # defined
                txn.move_to_end(selfdict, name)

    # ----------------------------------------------------------------------
    # Member-creation fan-outs (from SpaceManager.new_cells and the
    # Phase 4 NewRef/ChangeRef derive stages)

    def derive_new_cells(self, space, cells, txn):
        """Fan a newly defined cells out to the subs of ``space``.

        Each derived cells is inserted at the position ``cells.name``
        occupies in the union of the sub's bases' cells (the
        ``cells_after`` reorder).
        """
        name = cells.name
        for subspace in self.ops._get_subs(space):
            if name in subspace.cells:
                continue
            derived = UserCellsImpl(
                space=subspace, base=cells, is_derived=True)
            txn.add_undo(subspace.remove_observer, derived)

            base_cells = {}
            for b in reversed(subspace.bases):
                base_cells.update(b.cells)

            idx = list(base_cells).index(name)
            cells_after = list(subspace.cells)[idx:]

            txn.set_item(subspace.cells, name, derived)
            txn.add_created(derived)
            txn.mark_dirty(subspace, "cells")

            for k in cells_after:
                txn.move_to_end(subspace.cells, k)

    def derive_new_ref(self, space, name, value, refmode, txn):
        """Fan a newly defined reference out to the subs of ``space``."""
        for subspace in self.ops._get_subs(space):
            is_relative = False
            if name in subspace.own_refs:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = self.ops.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = create_ref(txn, subspace, name, value,
                             is_derived=True, refmode=refmode)
            ref.is_relative = is_relative

    def derive_change_ref(self, space, name, value, refmode, txn):
        """Fan a reference rebinding out to the subs of ``space``."""
        for subspace in self.ops._get_subs(space):
            is_relative = False
            subref = subspace.own_refs[name]
            if subref.is_defined():
                break
            elif subref.defined_bases[0] is not space.own_refs[name]:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = self.ops.get_relative_interface(
                        subspace, space.own_refs[name])
            old, _ = replace_ref(txn, subspace, name, value,
                                 is_derived=True, refmode=refmode)
            # Preserved pre-pipeline behavior: SpaceManager.change_ref
            # assigned the resolved is_relative to the object returned by
            # on_change_ref, which was the replaced (old) ref; the new
            # derived ref keeps the flag its constructor derives from
            # refmode.
            txn.set_attr(old, "is_relative", is_relative)
