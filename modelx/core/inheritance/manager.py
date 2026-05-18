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

"""Step C3: the inheritance/composition engine, relocated from model.py.

This module holds, verbatim, the node-path helpers and the seven engine
classes that previously lived at the tail of model.py:

  split_node / len_node / trim_left / trim_right / _get_shared_part /
  get_shared_asc / get_shared_desc / has_parent
  SpaceGraph, Instruction, InstructionList, SharedSpaceOperations,
  SpaceManager, SpaceUpdater, ReferenceManager

Only the location changes -- the logic is untouched. The model class is
referenced lazily via ``_model.ModelImpl`` (runtime attribute access on the
partially-initialized model module) to break the model<->engine import
cycle: model.py imports these classes at module load, and they only need
the model class inside method bodies, by which time model.py is fully
loaded. model.py re-exports these names for backward compatibility.
"""

import itertools

import networkx as nx

import modelx.core.model as _model
from modelx.core.base import Interface, Impl, Derivable, null_impl
from modelx.core.reference import ReferenceImpl
from modelx.core.cells import CellsImpl, UserCellsImpl
from modelx.core.parent import EditableParentImpl
from modelx.core.space import UserSpaceImpl
from modelx.core.binding.namespace import NamespaceServer
from modelx.core.formula import NULL_FORMULA
from modelx.core.util import is_valid_name


def split_node(node):
    parent = ".".join(node.split(".")[:-1])
    name = node.split(".")[-1]
    return parent, name


def len_node(node):
    return len(node.split("."))


def trim_left(node, trimed_len):
    return ".".join(node.split(".")[trimed_len:])


def trim_right(node, trimed_len):
    if trimed_len == 0:
        return node
    else:
        return ".".join(node.split(".")[:-trimed_len])


def _get_shared_part(a_node, b_node, from_left=True):

    a_node = a_node.split(".")
    b_node = b_node.split(".")

    length = min(len(a_node), len(b_node))

    while length:

        if from_left:
            a_node, b_node = a_node[:length], b_node[:length]
        else:
            a_node, b_node = a_node[-length:], b_node[-length:]

        if a_node == b_node:
            return ".".join(a_node)

        length -= 1


def get_shared_asc(a_node, b_node):
    return _get_shared_part(a_node, b_node, from_left=True)


def get_shared_desc(a_node, b_node):
    return _get_shared_part(a_node, b_node, from_left=False)


def has_parent(node, parent):
    parent_len = len_node(parent)

    if len_node(node) <= parent_len:
        return False
    elif trim_right(node, len_node(node) - parent_len) == parent:
        return True
    else:
        return False


class SpaceGraph(nx.DiGraph):
    """New implementation of inheritance graph"""

    def ordered_preds(self, node):
        edges = [(self.edges[e]["index"], e) for e in self.in_edges(node)]
        return [e[0] for i, e in sorted(edges, key=lambda elm: elm[0])]

    def ordered_subs(self, node):
        g = nx.descendants(self, node)
        g.add(node)
        return nx.topological_sort(self.subgraph(g))

    def max_index(self, node):
        return max(
            [self.edges[e]["index"] for e in self.in_edges(node)],
            default=0
        )

    def get_mro(self, node):
        """Calculate the Method Resolution Order of bases using the C3 algorithm.

        Code modified from
        http://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/

        Args:
            bases: sequence of direct base spaces.

        Returns:
            mro as a list of bases including node itself
        """
        seqs = [self.get_mro(base)
                for base in self.ordered_preds(node)
                ] + [self.ordered_preds(node)]
        res = []
        while True:
            non_empty = list(filter(None, seqs))

            if not non_empty:
                # Nothing left to process, we're done.
                res.insert(0, node)
                return res

            for seq in non_empty:  # Find merge candidates among seq heads.
                candidate = seq[0]
                not_head = [s for s in non_empty if candidate in s[1:]]
                if not_head:
                    # Reject the candidate.
                    candidate = None
                else:
                    break

            if not candidate:  # Better to return None instead of error?
                raise TypeError(
                    "inconsistent hierarchy, no C3 MRO is possible"
                )

            res.append(candidate)

            for seq in non_empty:
                # Remove candidate.
                if seq[0] == candidate:
                    del seq[0]

    def _visit_tree_inner(self, node, include_self=True):
        que = [node]
        level = 0
        while que:
            n = que.pop(0)
            if n != node or include_self:
                yield level, n
            childs = [ch for ch in self.nodes
                      if ch[:len(n) + 1] == (n + ".")
                      and len_node(n) + 1 == len_node(ch)]
            que += childs
            level += 1

    def visit_tree(self, node, include_self=True):
        for _, n in self._visit_tree_inner(
                node,include_self=include_self):
            yield n

    def to_space(self, node):
        return self.nodes[node]["space"]

    def get_relative(self, subspace, basespace, basevalue):

        shared_parent = get_shared_asc(basespace, basevalue)
        if not shared_parent:
            return None
        shared_desc = get_shared_desc(subspace, basespace)
        if shared_desc:
            shared_desc = shared_desc.split(".")
        else:
            shared_desc = []

        subroot = trim_right(subspace, len(shared_desc))
        basroot = trim_right(basespace, len(shared_desc))

        while True:

            if basroot in self.get_mro(subroot):
                break

            if shared_desc:
                n = shared_desc.pop(0)
                subroot = ".".join(subroot.split(".") + [n])
                basroot = ".".join(basroot.split(".") + [n])
            else:
                raise RuntimeError("must not happen")

        if basroot == shared_parent or has_parent(shared_parent, basroot):
            relative_part = trim_left(basevalue, len_node(basroot))
            if relative_part:
                return subroot + "." + relative_part
            else:
                return subroot
        else:
            return None


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


class SharedSpaceOperations:

    def __init__(self, model):
        self.model = model
        self._graph = SpaceGraph()

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

    def update_subs(self, space, skip_self=True):

        for attr in ("cells", "own_refs"):
            for s in self._get_subs(space, skip_self):
                b = self._get_space_bases(s, self._graph)
                s.on_inherit(self, b, attr)

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

        # Check name does not exit already
        parent = space.parent
        if not self._can_add(
                parent, name, UserSpaceImpl):
            raise ValueError("Cannot rename '%s' to '%s'" % (space.name, name))

        # Create name mapping
        mapping = {}
        old_id = tuple(space.idstr.split("."))
        new_id = old_id[:-1] + (name,)
        for node in self._graph.visit_tree(
                space.idstr, include_self=True):

            old_child = tuple(node.split("."))
            assert old_id == old_child[:len(old_id)]
            mapping[node] = ".".join(new_id + old_child[len(new_id):])

        if not space.parent.is_model():
            # Clear parent's dynsub, not s's
            space.parent.clear_subs_rootitems()

        # Call on_rename callbacks
        space.on_rename(name)

        # Rename nodes
        nx.relabel_nodes(self._graph, mapping, copy=False)

    def del_cells(self, space, name):
        cells = space.cells[name]
        if cells.is_derived():
            raise ValueError("cannot delete derived")
        space.on_del_cells(name)
        self.update_subs(space, skip_self=False)

    def del_ref(self, space, name):
        space.on_del_ref(name)
        self.update_subs(space, skip_self=False)

    def new_cells(self, space, name=None, formula=None, data=None,
                  is_derived=False, is_cached=True, edit_source=True):

        # FIX: Creating a Cells of the same name in ``space``

        if not self._can_add(space, name, CellsImpl):
            raise ValueError("Cannot create cells '%s'" % name)

        cells = UserCellsImpl(
            space=space, name=name, formula=formula,
            data=data, is_derived=is_derived, is_cached=is_cached, edit_source=edit_source)
        space.clear_subs_rootitems()

        name = cells.name   # If name is none, auto-named in __init__

        for subspace in self._get_subs(space):
            if name in subspace.cells:
                continue
            else:
                subspace.clear_subs_rootitems()
                derived = UserCellsImpl(
                    space=subspace,
                    base=cells, is_derived=True, add_to_space=False,
                    is_cached=is_cached
                )
                base_cells = {}
                for b in reversed(subspace.bases):
                    base_cells.update(b.cells)

                idx = list(base_cells).index(name)
                cells_after = list(subspace.cells)[idx:]
                subspace.cells[name] = derived
                subspace.on_notify(subspace.cells)

                for k in cells_after:
                    subspace.cells[k] = subspace.cells.pop(k)

        return cells

    def copy_cells(self, space: UserSpaceImpl,
                   source: UserCellsImpl, name=None):
        """``space`` can be of another Model"""

        if space.model is not self.model:
            return space.spmgr.copy_cells(space, source, name)

        if name is None:
            name = source.name

        data = {k: v for k, v in source.data.items() if k in source.input_keys}
        return self.new_cells(space, name=name, formula=source.formula,
                       data=data, is_derived=False)

    def rename_cells(self, cells, name):
        """Renames the Cells name"""
        if not is_valid_name(name):
            raise ValueError("name '%s' is invalid" % name)

        if not self._can_add(cells.parent, name, CellsImpl):
            raise ValueError("cannot create cells '%s'" % name)

        if cells.bases:
            raise ValueError("'%s' is a sub Cells of '%s'" % (
                cells.get_repr(fullname=True, add_params=False),
                cells.bases[0].get_repr(fullname=True, add_params=False)))

        old_name = cells.name

        for space in self._get_subs(cells.parent, skip_self=False):
            space.clear_subs_rootitems()
            space.cells[old_name].on_rename(name)

    def sort_cells(self, space):
        """Sort cells in a space

        - Applies only to defined UserSpaces
        - Only cells defined in the space (neither derived/overridden)
          are sorted and placed before the derived/overridden cells.
        - Derived/overridden cells in the sub spaces are also sorted.
        """
        for subspace in self._get_subs(space, skip_self=False):
            subspace.on_sort_cells(space=space)

    def set_cells_property(self, cells, flags, func, enable_cache):
        """Set formula and/or is_enabled"""
        define = True
        for space in self._get_subs(cells.parent, skip_self=False):
            c = space.cells[cells.name]
            if (c is not cells and c.is_defined() and
                    self.get_deriv_bases(c, defined_only=True)[0] is cells):
                continue   # Skip when c's base is not cells
            space.clear_subs_rootitems()
            space.cells[cells.name].on_set_property(
                flags, define, func, enable_cache
            )
            define = False  # Do not define derived cells

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

    def new_ref(self, space, name, value, refmode):

        other = self._find_name_in_subs(space, name)
        if other is not None:
            if not isinstance(other, ReferenceImpl):
                raise ValueError("Cannot create reference '%s'" % name)
            elif other not in self.model.global_refs.values():
                raise ValueError("Cannot create reference '%s'" % name)

        self._check_subs_relrefs(space, name, value, refmode)
        result = space.on_create_ref(name, value, is_derived=False,
                            refmode=refmode)

        for subspace in self._get_subs(space):
            is_relative = False
            if name in subspace.own_refs:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = self.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = subspace.on_create_ref(name, value, is_derived=True,
                                   refmode=refmode)
            ref.is_relative = is_relative

        return result

    def change_ref(self, space, name, value, refmode):
        """Assigns a new value to an existing name."""

        self._check_subs_relrefs(space, name, value, refmode)
        # self._set_defined(space.idstr)
        # space.set_defined()

        is_relative = False if refmode == "absolute" else True

        space.on_change_ref(name, value, is_derived=False, refmode=refmode,
                            is_relative=is_relative)

        for subspace in self._get_subs(space):
            is_relative = False
            subref = subspace.own_refs[name]
            if subref.is_defined():
                break
            elif subref.defined_bases[0] is not space.own_refs[name]:
                break
            if isinstance(value, Interface) and value._is_valid():
                if (refmode == "auto"
                        or refmode == "relative"):
                    is_relative, value = self.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = subspace.on_change_ref(name, value,
                                         is_derived=True, refmode=refmode,
                                         is_relative=is_relative)
            ref.is_relative = is_relative

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
        space.on_inherit(self, bases, 'cells')
        self._instructions.append(
            Instruction(self._update_derived_refs, (node,))
        )

    def _update_derived_refs(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        space.on_inherit(self, bases, 'own_refs')

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


class ReferenceManager:

    def __init__(self, model, iomanager):
        self._model = model
        self._manager = iomanager
        self._valid_to_refs = {}         # id(value) -> [refs]

    def _check_sanity(self):

        for refs in self._valid_to_refs.values():
            for r in refs:
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=r.interface)
                if spec is not None:
                    assert r.interface is spec.value
                    spec._check_sanity()

    def has_spec(self, value):
        spec = self._manager.get_spec_from_value(self._model.interface, value)
        return spec is not None

    def get_spec(self, value):
        return self._manager.get_spec_from_value(self._model.interface, value)

    @property
    def values(self):
        return list(ref[0].interface for ref in self._valid_to_refs.values())

    @property
    def specs(self):
        result = []
        for r in self._valid_to_refs.values():
            spec = self.get_spec(r[0].interface)
            if spec is not None:
                result.append(spec)
        return result

    def new_ref(self, impl, name, value, refmode):

        if isinstance(impl, _model.ModelImpl):
            ref = impl.new_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            ref = impl.model.spmgr.new_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(value, Interface):
            refs = self._valid_to_refs.setdefault(id(value), [])
            assert all(ref is not r for r in refs)
            refs.append(ref)

    def del_ref(self, impl, name):

        refdict = impl.own_refs
        ref = refdict[name]
        valid = id(ref.interface)
        val = ref.interface

        if isinstance(impl, _model.ModelImpl):
            impl.del_ref(name)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.del_ref(impl, name)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(val, Interface):
            refs = self._valid_to_refs.get(valid)
            assert refs
            refs.remove(ref)
            if not refs:
                del self._valid_to_refs[valid]
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=val
                )
                if spec:
                    self._manager.del_spec(spec)

    def change_ref(self, impl, name, value, refmode=None):

        refdict = impl.own_refs
        prev_ref = refdict[name]
        prev_valid = id(prev_ref.interface)
        prev_val = prev_ref.interface

        if isinstance(impl, _model.ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        refs = self._valid_to_refs.get(prev_valid, None)
        if refs is not None:        # None in case prev_ref is derived
            if prev_ref in refs:
                refs.remove(prev_ref)
            if not refs:    # ref is empty
                del self._valid_to_refs[prev_valid]
                spec = self._manager.get_spec_from_value(self._model.interface, prev_val)
                if spec:
                    self._manager.del_spec(spec)

        if not isinstance(value, Interface):
            self._valid_to_refs.setdefault(id(value), []).append(refdict[name])

    def del_all_spec(self):
        specs = self.specs.copy()
        while specs:
            self._manager.del_spec(specs.pop())

    def update_value(self, old_value, new_value=None, **kwargs):

        prev_id = id(old_value)
        refs = self._valid_to_refs.get(prev_id, None)
        spec = self._manager.get_spec_from_value(self._model.interface, old_value)

        if refs is None:
            raise ValueError("value not referenced")

        if new_value is None:
            new_value = old_value

        if spec is not None:
            self._manager.update_spec_value(spec, new_value, kwargs)
            new_value = spec.value

        newrefs = []
        while refs:
            ref = refs.pop()
            impl = ref.parent
            name = ref.name
            refmode = ref.refmode
            value = new_value
            self._impl_change_ref(impl, name, value, refmode)
            newrefs.append(impl.own_refs[name])

        self._valid_to_refs.pop(prev_id)
        self._valid_to_refs[id(new_value)] = newrefs

    @staticmethod
    def _impl_change_ref(impl, name, value, *refmode):

        if isinstance(impl, _model.ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")
