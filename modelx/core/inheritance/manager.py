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

import networkx as nx

from modelx.core.base import (
    Interface,
    Impl,
    Derivable,
    null_impl
)
from modelx.core.cells import UserCellsImpl
from modelx.core.parent import EditableParentImpl
from modelx.core.space import UserSpaceImpl
from modelx.core.binding.namespace import NamespaceServer
from modelx.core.formula import NULL_FORMULA
from modelx.core.util import is_valid_name
from modelx.core.inheritance.graph import SpaceGraph, split_node
from modelx.core.inheritance.sync import InheritanceSync
from modelx.core.edit.transaction import Instruction, InstructionList
from modelx.core.edit.pipeline import (
    NewRef,
    ChangeRef,
    DelRef,
    NewCells,
    CopyCells,
    DelCells,
    RenameCells,
    SetCellsProperty,
    SortCells,
    RenameSpace,
)


class SharedSpaceOperations:

    def __init__(self, model):
        self.model = model
        self._graph = SpaceGraph()

    @property
    def sync(self):
        """Derived-member synchronization over this operation's graph
        (CoreRefactorDesign §5.6). Stateless, so it is constructed per
        access instead of adding a slot to pickled model state."""
        return InheritanceSync(self)

    def _can_add(self, parent, name, klass):
        """Check name conflict for a given name.

        :obj:`False` if ``name`` is already defined not
        as an instance of ``klass``
        in ``parent`` or in any of ``parent`` descendants.
        :obj:`False` if ``name`` is already defined
        as an instance of ``klass`` and ``overwirte`` is :obj:`True`,
        otherwise :obj:`True`.
        """
        # TODO: Reflect the overwriting order of names
        if parent is self.model:
            return name not in parent.namespace
        else:   # parent is a Space
            child = parent.get_attr(name)
            if child is not None:
                return not isinstance(child, Impl)

        sub = self._find_name_in_subs(parent, name, skip_self=True)   # start from parent
        if sub is None:
            return True
        elif isinstance(sub, klass):
            return True
        else:
            return False

    def _find_name_in_subs(self, parent, name, skip_self=False):
        for subspace in self._get_subs(parent, skip_self=skip_self):
            child = subspace.get_attr(name)
            if child is not None:
                return child
        return None

    def _get_space_bases(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        nodes = self._graph.get_mro(space.idstr)[idx:]
        return [self._graph.to_space(n) for n in nodes]

    def get_deriv_bases(self, deriv: Derivable, defined_only=False,
                        graph: SpaceGraph=None):
        if graph is None:
            graph = self._graph

        if isinstance(deriv, UserSpaceImpl):    # Not Dynamic spaces
            return self._get_space_bases(deriv, graph)

        pnode = deriv.parent.idstr

        bases = []
        for bspace in graph.get_mro(pnode)[1:]:
            base_members = deriv._get_members(graph.to_space(bspace))
            if deriv.name in base_members:
                b = base_members[deriv.name]
                if not defined_only or b.is_defined():
                    bases.append(b)

        return bases

    def get_direct_bases(self, space):
        node = space.idstr
        preds = self._graph.ordered_preds(node)
        return [self._graph.to_space(n) for n in preds]

    def _get_subs(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        return [
            self._graph.to_space(desc) for desc in list(
                self._graph.ordered_subs(space.idstr))[idx:]
        ]

    def get_relative_interface(self, parent, base):

        basespace = base.parent.idstr
        basevalue = base.interface._impl.idstr

        subimpl = self._graph.get_relative(
            parent.idstr, basespace, basevalue)

        if subimpl:
            impl = self.model.get_impl_from_name(subimpl)
            if impl:
                return True, impl.interface
            else:
                return True, base.interface._impl.interface_cls(null_impl)
        else:
            return False, base.interface


class SpaceManager(SharedSpaceOperations):

    def rename_space(self, space, name):
        self.model.editor.execute(RenameSpace(space, name))

    def del_cells(self, space, name):
        self.model.editor.execute(DelCells(space, name))

    def del_ref(self, space, name, unregister=False):
        self.model.editor.execute(
            DelRef(space, name, unregister=unregister))

    def new_cells(self, space, name=None, formula=None, data=None,
                  is_derived=False, is_cached=True, edit_source=True):
        return self.model.editor.execute(NewCells(
            space, name=name, formula=formula, data=data,
            is_derived=is_derived, is_cached=is_cached,
            edit_source=edit_source))

    def copy_cells(self, space: UserSpaceImpl,
                   source: UserCellsImpl, name=None):
        """``space`` can be of another Model"""

        if space.model is not self.model:
            return space.spmgr.copy_cells(space, source, name)

        return self.model.editor.execute(CopyCells(space, source, name))

    def rename_cells(self, cells, name):
        """Renames the Cells name"""
        self.model.editor.execute(RenameCells(cells, name))

    def sort_cells(self, space):
        """Sort cells in a space

        - Applies only to defined UserSpaces
        - Only cells defined in the space (neither derived/overridden)
          are sorted and placed before the derived/overridden cells.
        - Derived/overridden cells in the sub spaces are also sorted.
        """
        self.model.editor.execute(SortCells(space))

    def set_cells_property(self, cells, flags, func, enable_cache):
        """Set formula and/or is_enabled"""
        self.model.editor.execute(
            SetCellsProperty(cells, flags, func, enable_cache))

    def set_cells_formula(self, cells, func):
        self.set_cells_property(cells, UserCellsImpl.PROP_FORMULA, func, True)

    def set_cache(self, cells, enable_cache):
        self.set_cells_property(cells, UserCellsImpl.PROP_CACHE, None, enable_cache)

    def del_cells_formula(self, cells):
        self.set_cells_formula(cells, NULL_FORMULA)

    def _check_subs_relrefs(self, space, name, value, refmode):

        # Check if relative ref is possible when refmode is 'relative'
        if isinstance(value, Interface) and refmode == "relative":
            basevalue = value._impl.idstr
            for subspace in self._get_subs(space):
                if name in subspace.own_refs:
                    break
                else:
                    subvalue = self._graph.get_relative(
                        subspace.idstr, space.idstr,
                        basevalue)
                    if not subvalue:
                        raise ValueError(
                            "Cannot create relative reference for '%s' in '%s'"
                            % (basevalue, subspace.idstr)
                        )

    def new_ref(self, space, name, value, refmode, register=False):
        return self.model.editor.execute(
            NewRef(space, name, value, refmode, register=register))

    def change_ref(self, space, name, value, refmode, rebind=False):
        """Assigns a new value to an existing name."""
        self.model.editor.execute(
            ChangeRef(space, name, value, refmode, rebind=rebind))

    def _check_sanity(self):

        nodes = set(self._graph.nodes)
        spaces = dict(self.model.named_spaces)

        # consistency between spaces and nodes
        while spaces:
            k, v = spaces.popitem()
            assert k == v.name
            assert v.idstr in nodes
            assert v is self._graph.nodes[v.idstr]["space"]
            nodes.remove(v.idstr)
            spaces.update(v.named_spaces)

        assert not nodes # Check all nodes are reached


class SpaceUpdater(SharedSpaceOperations):

    def __init__(self, manager):
        self.manager = manager
        super().__init__(manager.model)

        self._instructions = InstructionList()
        self._graph = self.manager._graph.copy()

    def _update_manager(self):

        self.manager._graph = self._graph

    def _update_derived_space(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        self.sync.reconcile(space, bases, 'cells')
        self._instructions.append(
            Instruction(self._update_derived_refs, (node,))
        )

    def _update_derived_refs(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        self.sync.reconcile(space, bases, 'own_refs')

    def _remove_hook(self, graph, node):

        parent_node, name = split_node(node)

        if parent_node in self.manager._graph:
            parent = self.manager._graph.to_space(parent_node)
        elif parent_node:
            parent = graph.to_space(parent_node)
        else:
            parent = self.model

        method = parent.on_del_space

        self._instructions.append(
            Instruction(method, (name,))
        )

    def new_space(
            self,
            parent,
            name=None,
            bases=None,
            formula=None,
            refs=None,
            source=None,
            prefix="",
            doc=None
    ):
        """Create a new child space.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            formula: Function whose parameters used to set space parameters.
            refs: a mapping of refs to be added.
            source: A source module from which cell definitions are read.
            prefix: Prefix to the autogenerated name when name is None.
        """
        if name is None:
            while True:
                name = parent.spacenamer.get_next(parent.namespace, prefix)
                if self.manager._can_add(parent, name, UserSpaceImpl):
                    break

        elif not self.manager._can_add(parent, name, UserSpaceImpl):
            raise ValueError("Cannot create space '%s'" % name)

        if not prefix and not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        if bases is None:
            bases = []
        elif isinstance(bases, UserSpaceImpl):
            bases = [bases]

        node = name if parent.is_model() else parent.idstr + "." + name

        spaces = [s for s in bases]
        if not parent.is_model():
            spaces.insert(0, parent)

        self._graph.add_node(node)

        for b in bases:
            base = b.idstr
            self._graph.add_edge(
                base,
                node,
                level=0,
                index=self._graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

        self._graph.get_mro(node)  # Check if MRO is possible

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(self._graph, node):
            self._graph.get_mro(n)

        space = UserSpaceImpl(
            parent,
            name,
            container=parent.named_spaces,
            formula=formula,
            refs=refs,
            source=source,
            doc=doc
        )

        if isinstance(parent, NamespaceServer):
            parent.on_notify(parent.named_spaces)   # Fix: bug GH203

        self._graph.nodes[node]["space"] = space
        self._graph.nodes[node]["state"] = "created"

        self._instructions.append(
            Instruction(self._update_derived_space, (node,)))
        for _,  v in nx.edge_dfs(self._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,)))

        try:
            self._instructions.execute()
        except BaseException:
            del parent.named_spaces[name]
            raise

        self._update_manager()

        return space

    def add_bases(self, space, bases):
        """Add bases to space in graph
        """
        node = space.idstr
        basenodes = [base.idstr for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            self._graph.add_edge(
                b,
                node,
                level=0,
                index=self._graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(
                self._graph, node)):
            self._graph.get_mro(n)

        for desc in itertools.chain(
                {node},
                nx.descendants(self._graph, node)):

            mro = self._graph.get_mro(desc)

            # Check name conflict between spaces, cells, refs
            members = {}
            for attr in ["spaces", "cells", "refs"]:
                namechain = []
                for sname in mro:
                    space = self._graph.to_space(sname)
                    namechain.append(set(getattr(space, attr).keys()))
                members[attr] = set().union(*namechain)

            conflict = set().intersection(*[n for n in members.values()])
            if conflict:
                raise NameError("name conflict: %s" % conflict)

        self._instructions.append(
            Instruction(self._update_derived_space, (node,)))
        for _,  v in nx.edge_dfs(self._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,)))

        self._instructions.execute()
        self._update_manager()

    def remove_bases(self, space, bases):

        node = space.idstr
        basenodes = [base.idstr for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            self._graph.remove_edge(b, node)

        self._instructions.append(
            Instruction(self._update_derived_space, (node,))
        )
        for _, v in nx.edge_bfs(self.manager._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,))
            )

        self._instructions.execute()
        self._update_manager()

    def del_defined_space(self, space):

        node = space.idstr

        if node not in self.manager._graph:
            raise ValueError("Space '%s' not found" % node)

        # Remove node and its child tree
        nodes_removed = list()
        for child in self._graph.visit_tree(node):
            nodes_removed.append(child)
            self._remove_hook(self._graph, child)

        for _, v in nx.edge_bfs(self.manager._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,))
            )

        self._graph.remove_nodes_from(nodes_removed)

        self._instructions.execute()
        self._update_manager()

        if space is self.model.currentspace:
            self.model.currentspace = None

    def copy_space(
            self,
            parent: EditableParentImpl,
            source: UserSpaceImpl,
            name=None,
            defined_only=False
    ):
        if parent.has_ascendant(source):
            raise ValueError("Cannot copy to child")

        if parent.model is not self.model:
            return parent.model.updater.copy_space(
                parent, source, name, defined_only)

        if name is None:
            name = source.name

        if self.manager._can_add(
            parent, name, EditableParentImpl):
            return self._copy_space_recursively(
                parent, source, name, defined_only
            )
        else:
            raise ValueError("Cannot create space '%s'" % name)

    def _copy_space_recursively(
            self, parent, source, name, defined_only):

        space = self.new_space(
            parent,
            name=name,
            bases=None,
            formula=source.formula,
            refs={k: v.interface for k, v in source.own_refs.items()},
            source=source.source,
            prefix="",
            doc=source.doc
        )

        for cells in source.cells.values():
            if cells.is_defined():
                self.manager.copy_cells(space, cells)

        for child in source.named_spaces.values():
            self._copy_space_recursively(
                space, child, child.name, defined_only)

        return space
