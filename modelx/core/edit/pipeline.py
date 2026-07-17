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

"""Unified mutation pipeline (CoreRefactorDesign §5.4, Phases 4-5).

One ``ModelEditor`` entry point runs each ``Edit`` through
validate -> apply -> derive inside a :class:`Transaction`, rolls back on
any exception, and performs all side effects (trace invalidation,
deletions, batched namespace notification, ValueRegistry/IOSpec
bookkeeping, itemspace invalidation) post-commit in ``_finalize``.

Phase 4 covered the reference mutations end-to-end; Phase 5 added the
cells and non-graph space mutations; Phase 6 adds the graph-mutating
space edits (``NewSpace``, ``AddBases``, ``RemoveBases``, ``DelSpace``),
which mutate the transaction's shadow graph so that a failed edit
leaves the inheritance graph untouched. The ``derive`` stages delegate
to ``InheritanceSync`` (``inheritance/sync.py``), the single home of
derived-member creation.
"""

import itertools

import networkx as nx

from modelx.core.binding.namespace import NamespaceServer
from modelx.core.reference import ReferenceImpl
from modelx.core.cells import CellsImpl, UserCellsImpl
from modelx.core.space import UserSpaceImpl
from modelx.core.util import is_valid_name
from modelx.core.edit.transaction import Transaction, ChangeSet
from modelx.core.inheritance.sync import create_ref, replace_ref


class Edit:
    """One model mutation.

    ``validate`` performs name/cycle/relref checks without changing any
    state; ``apply`` performs the defined-member structural writes,
    journaled through the transaction; ``derive`` fans the change out to
    derived members in sub spaces (interim home, see module docstring).
    """

    result = None

    def validate(self, model, txn):
        pass

    def apply(self, model, txn):
        raise NotImplementedError

    def derive(self, model, txn):
        pass


class ModelEditor:
    """Runs Edits against a model (CoreRefactorDesign §5.4).

    Stateless: constructed per access by ``ModelImpl.editor`` so that no
    new slot enters pickled model state.
    """

    def __init__(self, model):
        self.model = model

    def execute(self, edit):
        txn = Transaction(self.model)
        try:
            edit.validate(self.model, txn)
            edit.apply(self.model, txn)
            edit.derive(self.model, txn)
        except BaseException:
            txn.rollback()
            raise
        txn.commit()
        self._finalize(txn.changes)
        return edit.result

    def _finalize(self, changes):
        """Post-commit side effects; must not fail the edit."""
        model = self.model

        # 1. Trace invalidation for removed and modified members
        for impl in changes.removed:
            if isinstance(impl, ReferenceImpl):
                model.clear_attr_referrers(impl)
            elif isinstance(impl, UserSpaceImpl):
                # Deleted spaces clear their cells' traces through
                # on_delete below (pre-pipeline behavior).
                pass
            else:
                model.clear_obj(impl)
        for impl in changes.modified:
            if isinstance(impl, ReferenceImpl):
                model.clear_attr_referrers(impl)
            else:
                model.clear_obj(impl)

        # 2. Finalize deletions
        for impl in changes.removed:
            impl.on_delete()

        # 2.5 Edit-specific post-commit operations (e.g. RenameSpace's
        #     recursive value clearing)
        for op in changes.finalize_ops:
            op()

        # 3. Batched notify: exactly one namespace invalidation per
        #    dirty container. The itemspace-deletion half of
        #    DynamicBase.on_notify is handled by ItemSpaceManager below.
        for parent, attr in changes.dirty_containers:
            container = getattr(parent, attr)
            if parent.is_model():
                for space in parent.yield_spaces():
                    NamespaceServer.on_notify(space, container)
            else:
                NamespaceServer.on_notify(parent, container)

        # 4. ValueRegistry / IOSpec bookkeeping
        for op in changes.registry_ops:
            if op[0] == "register":
                model.valreg.register(op[1])
            elif op[0] == "unregister":
                model.valreg.unregister(op[1])
            elif op[0] == "rebind":
                model.valreg.rebind(op[1], op[2])
            else:
                raise RuntimeError("must not happen")

        # 5. Itemspace invalidation (verbatim pre-pipeline policy)
        model.itemspacemgr.invalidate(changes)


# ----------------------------------------------------------------------
# Space-level reference edits


class NewRef(Edit):
    """Create a reference in a space and derive it into sub spaces."""

    def __init__(self, space, name, value, refmode, register=False):
        self.space = space
        self.name = name
        self.value = value
        self.refmode = refmode
        self.register = register

    def validate(self, model, txn):
        spmgr = model.spmgr
        other = spmgr._find_name_in_subs(self.space, self.name)
        if other is not None:
            if not isinstance(other, ReferenceImpl):
                raise ValueError("Cannot create reference '%s'" % self.name)
            elif other not in model.global_refs.values():
                raise ValueError("Cannot create reference '%s'" % self.name)

        spmgr._check_subs_relrefs(
            self.space, self.name, self.value, self.refmode)

    def apply(self, model, txn):
        ref = create_ref(txn, self.space, self.name, self.value,
                         is_derived=False, refmode=self.refmode)
        if self.register:
            txn.changes.registry_ops.append(("register", ref))
        self.result = ref

    def derive(self, model, txn):
        model.spmgr.sync.derive_new_ref(
            self.space, self.name, self.value, self.refmode, txn)


class ChangeRef(Edit):
    """Assign a new value to an existing reference in a space."""

    def __init__(self, space, name, value, refmode, rebind=False):
        self.space = space
        self.name = name
        self.value = value
        self.refmode = refmode
        self.rebind = rebind

    def validate(self, model, txn):
        model.spmgr._check_subs_relrefs(
            self.space, self.name, self.value, self.refmode)

    def apply(self, model, txn):
        old, new = replace_ref(txn, self.space, self.name, self.value,
                               is_derived=False, refmode=self.refmode)
        if self.rebind:
            txn.changes.registry_ops.append(("rebind", old, new))

    def derive(self, model, txn):
        model.spmgr.sync.derive_change_ref(
            self.space, self.name, self.value, self.refmode, txn)


class DelRef(Edit):
    """Delete a reference from a space and re-derive its sub spaces."""

    def __init__(self, space, name, unregister=False):
        self.space = space
        self.name = name
        self.unregister = unregister

    def apply(self, model, txn):
        ref = self.space.own_refs[self.name]
        txn.del_item(self.space.own_refs, self.name)
        txn.add_removed(ref)
        txn.mark_dirty(self.space, "own_refs")
        if self.unregister:
            txn.changes.registry_ops.append(("unregister", ref))

    def derive(self, model, txn):
        model.spmgr.sync.derive_subs(self.space, txn, skip_self=False)


# ----------------------------------------------------------------------
# Cells edits


class NewCells(Edit):
    """Create a cells in a space and derive it into sub spaces."""

    def __init__(self, space, name=None, formula=None, data=None,
                 is_derived=False, is_cached=True, edit_source=True):
        self.space = space
        self.name = name
        self.formula = formula
        self.data = data
        self.is_derived = is_derived
        self.is_cached = is_cached
        self.edit_source = edit_source

    def validate(self, model, txn):
        # FIX: Creating a Cells of the same name in ``space``
        if not model.spmgr._can_add(self.space, self.name, CellsImpl):
            raise ValueError("Cannot create cells '%s'" % self.name)

    def apply(self, model, txn):
        space = self.space
        cells = UserCellsImpl(
            space=space, name=self.name, formula=self.formula,
            data=self.data, is_derived=self.is_derived,
            is_cached=self.is_cached, edit_source=self.edit_source)
        # The constructor registered the cells as an observer of the
        # space; undo that on rollback.
        txn.add_undo(space.remove_observer, cells)
        txn.set_item(space.cells, cells.name, cells)
        txn.add_created(cells)
        txn.mark_dirty(space, "cells")
        self.result = cells

    def derive(self, model, txn):
        model.spmgr.sync.derive_new_cells(self.space, self.result, txn)


class CopyCells(NewCells):
    """Create a copy of ``source`` in a space of the same model."""

    def __init__(self, space, source, name=None):
        if name is None:
            name = source.name
        data = {k: v for k, v in source.data.items()
                if k in source.input_keys}
        NewCells.__init__(self, space, name=name, formula=source.formula,
                          data=data, is_derived=False)


class DelCells(Edit):
    """Delete a cells from a space and re-derive its sub spaces."""

    def __init__(self, space, name):
        self.space = space
        self.name = name

    def validate(self, model, txn):
        cells = self.space.cells[self.name]
        if cells.is_derived():
            raise ValueError("cannot delete derived")

    def apply(self, model, txn):
        cells = self.space.cells[self.name]
        txn.del_item(self.space.cells, self.name)
        txn.add_removed(cells)
        txn.mark_dirty(self.space, "cells")

    def derive(self, model, txn):
        model.spmgr.sync.derive_subs(self.space, txn, skip_self=False)


class RenameCells(Edit):
    """Rename a defined cells and its derived cells in sub spaces."""

    def __init__(self, cells, name):
        self.cells = cells
        self.name = name

    def validate(self, model, txn):
        if not is_valid_name(self.name):
            raise ValueError("name '%s' is invalid" % self.name)

        if not model.spmgr._can_add(self.cells.parent, self.name, CellsImpl):
            raise ValueError("cannot create cells '%s'" % self.name)

        if self.cells.bases:
            raise ValueError("'%s' is a sub Cells of '%s'" % (
                self.cells.get_repr(fullname=True, add_params=False),
                self.cells.bases[0].get_repr(
                    fullname=True, add_params=False)))

    def apply(self, model, txn):
        old_name = self.cells.name
        for space in model.spmgr._get_subs(self.cells.parent,
                                           skip_self=False):
            txn.add_cleared_subs(space)
            space.cells[old_name].on_rename(self.name, txn)


class SetCellsProperty(Edit):
    """Set formula and/or is_cached on a cells and its derived cells."""

    def __init__(self, cells, flags, func, enable_cache):
        self.cells = cells
        self.flags = flags
        self.func = func
        self.enable_cache = enable_cache

    def apply(self, model, txn):
        spmgr = model.spmgr
        cells = self.cells
        define = True
        for space in spmgr._get_subs(cells.parent, skip_self=False):
            c = space.cells[cells.name]
            if (c is not cells and c.is_defined() and
                    spmgr.get_deriv_bases(c, defined_only=True)[0] is cells):
                continue   # Skip when c's base is not cells
            txn.add_cleared_subs(space)
            space.cells[cells.name].on_set_property(
                self.flags, define, self.func, self.enable_cache, txn
            )
            define = False  # Do not define derived cells


class SortCells(Edit):
    """Sort cells in a space and its sub spaces.

    - Applies only to defined UserSpaces
    - Only cells defined in the space (neither derived/overridden)
      are sorted and placed before the derived/overridden cells.
    - Derived/overridden cells in the sub spaces are also sorted.
    """

    def __init__(self, space):
        self.space = space

    def apply(self, model, txn):
        space = self.space
        for c in space.cells.values():
            txn.add_modified(c)
        for subspace in model.spmgr._get_subs(space, skip_self=False):
            txn.sort_items(subspace.cells,
                           self._sorted_keys(subspace, space))

    @staticmethod
    def _sorted_keys(subspace, space):
        if subspace.bases:

            # Select names in space but not in space's bases

            bases = [subspace] + list(subspace.bases)
            while True:
                if bases.pop(0) is space:
                    break

            keys = list(space.cells)
            d = {}
            for b in bases:
                d.update(b.cells)

            for k in d:
                try:
                    keys.remove(k)
                except ValueError:
                    pass

            return sorted(keys)

        else:
            assert subspace is space
            return None


# ----------------------------------------------------------------------
# Non-graph space edits


class RenameSpace(Edit):
    """Rename a space, relabeling its node tree in the graph."""

    def __init__(self, space, name):
        self.space = space
        self.name = name
        self._mapping = None

    def validate(self, model, txn):
        if not model.spmgr._can_add(
                self.space.parent, self.name, UserSpaceImpl):
            raise ValueError(
                "Cannot rename '%s' to '%s'" % (self.space.name, self.name))

        self._mapping = model.spmgr._graph.get_rename_mapping(
            self.space.idstr, self.name)

    def apply(self, model, txn):
        space, name = self.space, self.name
        parent = space.parent

        if not parent.is_model():
            # Clear parent's dynsub, not space's
            txn.add_cleared_subs(parent)

        txn.add_modified(space)     # clear_obj in finalize
        txn.changes.finalize_ops.append(
            lambda: space.clear_all_cells(
                clear_input=True, recursive=True, del_items=True))

        old_name = space.name
        txn.set_attr(space, "name", name)
        # Pre-pipeline behavior: pop + reassign moves the space to the
        # end of its parent's container.
        txn.del_item(parent.named_spaces, old_name)
        txn.set_item(parent.named_spaces, name, space)
        if isinstance(parent, NamespaceServer):
            txn.mark_dirty(parent, "named_spaces")

        graph = model.spmgr._graph
        inverse = {new: old for old, new in self._mapping.items()}
        txn.add_undo(graph.relabel, inverse)
        graph.relabel(self._mapping)


# ----------------------------------------------------------------------
# Graph-mutating space edits (Phase 6)


class NewSpace(Edit):
    """Create a space, optionally derived from base spaces.

    ``validate`` builds the new node and its base edges on the shadow
    graph and checks acyclicity and MRO feasibility there, before any
    component-dict write.
    """

    def __init__(self, parent, name=None, bases=None, formula=None,
                 refs=None, source=None, prefix="", doc=None):
        self.parent = parent
        self.name = name
        if bases is None:
            bases = []
        elif isinstance(bases, UserSpaceImpl):
            bases = [bases]
        self.bases = bases
        self.formula = formula
        self.refs = refs
        self.source = source
        self.prefix = prefix
        self.doc = doc
        self.node = None

    def validate(self, model, txn):
        parent, spmgr = self.parent, model.spmgr

        if self.name is None:
            while True:
                name = parent.spacenamer.get_next(
                    parent.namespace, self.prefix)
                if spmgr._can_add(parent, name, UserSpaceImpl):
                    break
            self.name = name
        elif not spmgr._can_add(parent, self.name, UserSpaceImpl):
            raise ValueError("Cannot create space '%s'" % self.name)

        if not self.prefix and not is_valid_name(self.name):
            raise ValueError("Invalid name '%s'." % self.name)

        node = (self.name if parent.is_model()
                else parent.idstr + "." + self.name)
        self.node = node

        graph = txn.get_shadow_graph()
        graph.add_node(node)

        for b in self.bases:
            graph.add_edge(
                b.idstr,
                node,
                level=0,
                index=graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("cyclic inheritance")

        graph.get_mro(node)  # Check if MRO is possible

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(graph, node):
            graph.get_mro(n)

    def apply(self, model, txn):
        parent = self.parent
        space = UserSpaceImpl(
            parent,
            self.name,
            formula=self.formula,
            source=self.source,
            doc=self.doc
        )
        txn.set_item(parent.named_spaces, self.name, space)
        txn.add_created(space)
        if not parent.is_model():
            txn.mark_dirty(parent, "named_spaces")   # Fix: bug GH203

        graph = txn.get_shadow_graph()
        graph.nodes[self.node]["space"] = space
        graph.nodes[self.node]["state"] = "created"

        if self.refs is not None:
            for key, value in self.refs.items():
                create_ref(txn, space, key, value,
                           is_derived=False, refmode="auto")

        self.result = space

    def derive(self, model, txn):
        model.spmgr.sync.derive_subs(self.result, txn, skip_self=False)


class AddBases(Edit):
    """Add base spaces to a space."""

    def __init__(self, space, bases):
        self.space = space
        self.bases = bases

    def validate(self, model, txn):
        graph = txn.get_shadow_graph()
        node = self.space.idstr
        basenodes = [base.idstr for base in self.bases]

        for base in [node] + basenodes:
            if base not in graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            graph.add_edge(
                b,
                node,
                level=0,
                index=graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("cyclic inheritance")

        affected = list(itertools.chain(
            {node}, nx.descendants(graph, node)))

        for n in affected:
            graph.get_mro(n)

        for desc in affected:
            mro = graph.get_mro(desc)

            # Union of inheritable member names across the MRO
            members = set()
            for attr in ("cells", "own_refs"):
                for sname in mro:
                    members.update(getattr(graph.to_space(sname), attr))

            # Child spaces are not inherited into subs, so only a
            # space's OWN child spaces can collide with the cells and
            # refs it inherits; a base's child-space name never enters
            # the sub's namespace. Including base named_spaces here
            # would reject legitimate models — and make them unloadable,
            # because deserialization replays bases via add_bases.
            conflict = set(graph.to_space(desc).named_spaces) & members
            if conflict:
                raise NameError("name conflict: %s" % conflict)

    def apply(self, model, txn):
        pass

    def derive(self, model, txn):
        model.spmgr.sync.derive_subs(self.space, txn, skip_self=False)


class RemoveBases(Edit):
    """Remove base spaces from a space."""

    def __init__(self, space, bases):
        self.space = space
        self.bases = bases

    def validate(self, model, txn):
        graph = txn.get_shadow_graph()
        node = self.space.idstr
        basenodes = [base.idstr for base in self.bases]

        for base in [node] + basenodes:
            if base not in graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            graph.remove_edge(b, node)

    def apply(self, model, txn):
        pass

    def derive(self, model, txn):
        model.spmgr.sync.derive_subs(self.space, txn, skip_self=False)


class DelSpace(Edit):
    """Delete a defined space together with its child space tree."""

    def __init__(self, space):
        self.space = space
        self._affected = None

    def validate(self, model, txn):
        if self.space.idstr not in txn.get_shadow_graph():
            raise ValueError("Space '%s' not found" % self.space.idstr)

    def apply(self, model, txn):
        graph = txn.get_shadow_graph()
        node = self.space.idstr

        removed_nodes = list(graph.visit_tree(node))
        removed_set = set(removed_nodes)

        # Inheritance subs losing a base; re-derived in the derive
        # stage against their remaining bases.
        self._affected = [
            graph.to_space(n) for n in graph.ordered_subs(node)
            if n not in removed_set
        ]

        for n in removed_nodes:
            space = graph.to_space(n)
            txn.del_item(space.parent.named_spaces, space.name)
            txn.add_removed_space(space)

        graph.remove_nodes_from(removed_nodes)

        if self.space is model.currentspace:
            txn.set_attr(model, "currentspace", None)

    def derive(self, model, txn):
        model.spmgr.sync.derive_spaces(self._affected, txn)


# ----------------------------------------------------------------------
# Model-global reference edits


class NewGlobalRef(Edit):
    """Create a global reference on the model."""

    def __init__(self, model, name, value, register=False):
        self.name = name
        self.value = value
        self.register = register

    def apply(self, model, txn):
        ref = ReferenceImpl(model, name=self.name, value=self.value,
                            container=model._global_refs)
        txn.set_item(model._global_refs, self.name, ref)
        txn.add_created(ref)
        txn.mark_dirty(model, "global_refs")
        if self.register:
            txn.changes.registry_ops.append(("register", ref))
        self.result = ref


class DelGlobalRef(Edit):
    """Delete a global reference from the model."""

    def __init__(self, model, name, unregister=False):
        self.name = name
        self.unregister = unregister

    def apply(self, model, txn):
        ref = model.global_refs[self.name]
        txn.del_item(model._global_refs, self.name)
        txn.add_removed(ref)
        txn.mark_dirty(model, "global_refs")
        if self.unregister:
            txn.changes.registry_ops.append(("unregister", ref))


class ChangeGlobalRef(Edit):
    """Assign a new value to an existing global reference."""

    def __init__(self, model, name, value, rebind=False):
        self.name = name
        self.value = value
        self.rebind = rebind

    def apply(self, model, txn):
        old = model.global_refs[self.name]
        txn.del_item(model._global_refs, self.name)
        txn.add_removed(old)
        new = ReferenceImpl(model, name=self.name, value=self.value,
                            container=model._global_refs)
        txn.set_item(model._global_refs, self.name, new)
        txn.add_created(new)
        txn.mark_dirty(model, "global_refs")
        if self.rebind:
            txn.changes.registry_ops.append(("rebind", old, new))
        self.result = new
