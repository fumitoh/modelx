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

import itertools


class ItemSpaceManager:
    """Per-model itemspace invalidation policy (CoreRefactorDesign §5.8).

    Selective, closure-based invalidation (Phase 7). The closure of a
    live itemspace is the set of UserSpace idstrs its dynamic tree can
    observe change:

    - the ``_dynbase`` of each node of the itemspace's dynamic tree,
      recorded on the itemspace at creation
      (:meth:`ItemSpaceImpl.get_tree_dynbases`) — the tree's cells,
      refs and ``_dynbase_refs`` are all built from these spaces;
    - each such dynbase's MRO bases — derived members change when a
      base does, whether or not the sync stage writes to the sub;
    - the itemspace parent's own parent chain up to the nearest
      UserSpace — the parent's param formula evaluates in that
      namespace.

    On finalize an itemspace is cleared iff:

    - ``ChangeSet.dirty_spaces`` (spaces whose namespace bindings
      changed) intersects the full closure, or
    - ``ChangeSet.dirty_bases`` (formula changes and renames, which
      alter no bindings) intersects the recorded dynbases only —
      preserving the per-dynbase selectivity these edits always had.

    This refines §5.8's parent-granularity formula per itemspace, so an
    edit to one dynbase spares sibling itemspaces built on other
    dynbases (pinned granularity of the Phase 0 characterization
    tests). The closure over-approximates — clearing goes through the
    untouched trace-graph deletion path and can only ever clear too
    much, not too little.

    Itemspaces of *other* models built on this model's dirty spaces are
    cleared through the dirty spaces' ``_dynamic_subs`` back-pointers:
    idstrs are model-relative, so the closure intersection is only
    meaningful within one model.

    Model-global ref edits (a dirty model-level container) keep the
    nuke-all policy: ``global_names`` refinement is a later
    optimization.

    Stateless: constructed per access by ``ModelImpl.itemspacemgr`` so
    that no new slot enters pickled model state.
    """

    def __init__(self, model):
        self.model = model

    def invalidate(self, changes):
        for parent, attr in changes.dirty_containers:
            if parent.is_model():
                self._invalidate_all()
                return

        dirty = set(changes.dirty_spaces)
        dirty_bases = set(changes.dirty_bases)
        if not dirty and not dirty_bases:
            return

        # Decide before clearing: clearing one itemspace can cascade
        # through the trace graph into others.
        mro_cache = {}
        targets = []
        for parent, key, item in self._iter_itemspaces():
            bases, mros, chain = self._closure_parts(parent, item, mro_cache)
            if dirty & (bases | mros | chain) or dirty_bases & bases:
                targets.append((parent, key))
        targets.extend(self._iter_foreign_targets(
            itertools.chain(changes.dirty_spaces.values(),
                            changes.dirty_bases.values())))

        for parent, key in targets:
            parent.clear_itemspace_at(key)  # no-op if a cascade or an
                                            # earlier clear removed it

    def _invalidate_all(self):
        targets = list(self._iter_foreign_targets(self.model.yield_spaces()))
        for space in self.model.yield_spaces():
            space.del_all_itemspaces()
        for parent, key in targets:
            parent.clear_itemspace_at(key)

    def _iter_foreign_targets(self, spaces):
        """``(parent, key)`` of root itemspaces in *other* models whose
        trees contain a dynamic sub of one of ``spaces``."""
        for space in spaces:
            for sub in space._dynamic_subs:
                root = sub.rootspace
                if root.parent.model is not self.model:
                    yield root.parent, root.argvalues_if

    def _iter_itemspaces(self, parent=None):
        """Yield ``(parent, key, itemspace)`` for every live itemspace,
        including those of ItemSpaceParents nested in dynamic trees."""
        if parent is None:
            for space in self.model.yield_spaces():
                yield from self._iter_itemspaces(space)
            return

        for key, item in parent.param_spaces.items():
            yield parent, key, item
            for node in self._iter_tree_nodes(item):
                yield from self._iter_itemspaces(node)

    @classmethod
    def _iter_tree_nodes(cls, item):
        yield item
        for child in item.named_spaces.values():
            yield from cls._iter_tree_nodes(child)

    def _closure_parts(self, parent, item, mro_cache):
        """The closure of ``item`` (see the class docstring) as three
        idstr sets: recorded dynbases, their MRO bases, and the
        parent-chain UserSpace."""
        graph = self.model.spmgr._graph

        chain = parent
        while chain.is_dynamic():
            chain = chain.parent

        bases = set()
        mros = set()
        for base in item.get_tree_dynbases():
            idstr = base.idstr
            bases.add(idstr)
            if idstr not in mro_cache:
                # A deleted dynbase's node is gone from the graph; its
                # (still computable) idstr alone marks the tree stale.
                mro_cache[idstr] = (
                    graph.get_mro(idstr)[1:] if idstr in graph.nodes
                    else []
                )
            mros.update(mro_cache[idstr])
        return bases, mros, {chain.idstr}
