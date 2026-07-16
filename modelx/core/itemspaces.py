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


class ItemSpaceManager:
    """Per-model itemspace invalidation policy (CoreRefactorDesign §5.8).

    Phase 4 carries the pre-pipeline nuke-all policy verbatim from
    ``DynamicBase.on_notify``: a namespace change on a space deletes all
    of the space's own itemspaces, plus all itemspaces of the parent of
    each of its dynamic subs' root spaces. A model-global change applies
    this to every space, matching the previous per-space ``on_notify``
    fan-out. Phase 7 replaces this with closure-based selective
    invalidation.

    Edits that do not change namespaces (cells formula changes and
    renames) instead record spaces in ``ChangeSet.cleared_subs``, which
    applies the selective pre-pipeline ``clear_subs_rootitems`` policy:
    only the root itemspaces of the space's dynamic subs are cleared.

    Stateless: constructed per access by ``ModelImpl.itemspacemgr`` so
    that no new slot enters pickled model state.
    """

    def __init__(self, model):
        self.model = model

    def invalidate(self, changes):
        for space in changes.cleared_subs:
            space.clear_subs_rootitems()

        spaces = {}     # dict as insertion-ordered set
        for parent, attr in changes.dirty_containers:
            if parent.is_model():
                for space in parent.yield_spaces():
                    spaces[space] = None
            else:
                spaces[parent] = None

        for space in spaces:
            self._invalidate_space(space)

    def _invalidate_space(self, space):
        space.del_all_itemspaces()
        # Use dict instead of list to avoid duplicates
        for r in {s.rootspace: True for s in space._dynamic_subs}:
            r.parent.del_all_itemspaces()
