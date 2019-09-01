# Copyright (c) 2017-2019 Fumito Hamamura <fumito.ham@gmail.com>

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

import builtins
import itertools
from textwrap import dedent
import pickle
from collections import ChainMap
import copy

import networkx as nx

from modelx.core.base import (
    Interface,
    Impl,
    get_interfaces,
    ImplDict,
    ImplChainMap,
    BaseView,
    ReferenceImpl,
)
from modelx.core.node import OBJ, KEY, get_node, node_has_key
from modelx.core.spacecontainer import (
    BaseSpaceContainerImpl,
    EditableSpaceContainerImpl,
    EditableSpaceContainer,
)
from modelx.core.space import (
    UserSpaceImpl,
    DynamicSpaceImpl,
    SpaceView,
    RefDict
)
from modelx.core.util import is_valid_name, AutoNamer


class DependencyGraph(nx.DiGraph):
    """Directed Graph of ObjectArgs"""

    def clear_descendants(self, source, clear_source=True):
        """Remove all descendants of(reachable from) `source`.

        Args:
            source: Node descendants
            clear_source(bool): Remove origin too if True.
        Returns:
            set: The removed nodes.
        """
        desc = nx.descendants(self, source)
        if clear_source:
            desc.add(source)
        self.remove_nodes_from(desc)
        return desc

    def clear_obj(self, obj):
        """"Remove all nodes with `obj` and their descendants."""
        obj_nodes = self.get_nodes_with(obj)
        removed = set()
        for node in obj_nodes:
            if self.has_node(node):
                removed.update(self.clear_descendants(node))
        return removed

    def get_nodes_with(self, obj):
        """Return nodes with `obj`."""
        result = set()

        if nx.__version__[0] == "1":
            nodes = self.nodes_iter()
        else:
            nodes = self.nodes

        for node in nodes:
            if node[OBJ] == obj:
                result.add(node)
        return result

    def fresh_copy(self):
        """Overriding Graph.fresh_copy"""
        return DependencyGraph()

    def add_path(self, nodes, **attr):
        """In replacement for Deprecated add_path method"""
        if nx.__version__[0] == "1":
            return super().add_path(nodes, **attr)
        else:
            return nx.add_path(self, nodes, **attr)


class Model(EditableSpaceContainer):
    """Top-level container in modelx object hierarchy.

    Model instances are the top-level objects and directly contain
    :py:class:`UserSpace <modelx.core.space.UserSpace>` objects, which in turn
    contain other spaces or
    :py:class:`Cells <modelx.core.cells.Cells>` objects.

    A model can be created by
    :py:func:`new_model <modelx.core.model.Model>` API function.
    """

    __slots__ = ()

    def rename(self, name, rename_old=False):
        """Rename the model itself"""
        self._impl.system.rename_model(
            new_name=name, old_name=self.name, rename_old=rename_old)

    def save(self, filepath):
        """Save the model to a file."""
        self._impl.save(filepath)

    def close(self):
        """Close the model."""
        self._impl.close()

    @Interface.doc.setter
    def doc(self, value):
        self._impl.doc = value

    def write(self, model_path):
        """Write model to files.

        This method performs the :py:func:`~modelx.write_model`
        on self. See :py:func:`~modelx.write_model` section for the details.

        Args:
            model_path(str): Folder(directory) path where the model is saved.
        """
        from modelx.core.project import write_model
        write_model(self, model_path)

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __getattr__(self, name):
        return self._impl.get_attr(name)

    def __setattr__(self, name, value):
        if name in self.properties:
            object.__setattr__(self, name, value)
        else:
            self._impl.set_attr(name, value)

    def __delattr__(self, name):
        self._impl.del_attr(name)

    def __dir__(self):
        return self._impl.namespace.interfaces

    @property
    def cellgraph(self):
        """A directed graph of cells."""
        return self._impl.cellgraph

    @property
    def refs(self):
        """Return a mapping of global references."""
        return self._impl.global_refs.interfaces


class ModelImpl(EditableSpaceContainerImpl, Impl):
    if_cls = Model

    def __init__(self, *, system, name):
        Impl.__init__(self, system=system)
        EditableSpaceContainerImpl.__init__(self)

        self.cellgraph = DependencyGraph()
        self.lexdep = DependencyGraph()  # Lexical dependency
        self.spacemgr = SpaceManager(self)
        self.currentspace = None

        if not name:
            self.name = system._modelnamer.get_next(system.models)
        elif is_valid_name(name):
            self.name = name
        else:
            raise ValueError("Invalid name '%s'." % name)

        data = {"__builtins__": builtins}
        self._global_refs = RefDict(self, data=data)
        self._spaces = ImplDict(self, SpaceView)
        self._dynamic_bases = {}
        self._dynamic_bases_inverse = {}
        self._dynamic_base_namer = AutoNamer("__Space")
        self._namespace = ImplChainMap(
            self, BaseView, [self._spaces, self._global_refs]
        )
        self.allow_none = False
        self.lazy_evals = self._namespace

    def rename(self, name):
        """Rename self. Must be called only by its system."""
        if is_valid_name(name):
            if name not in self.system.models:
                self.name = name
                return True  # Rename success
            else:  # Model name already exists
                return False
        else:
            raise ValueError("Invalid name '%s'." % name)

    def clear_descendants(self, source, clear_source=True):
        """Clear values and nodes calculated from `source`."""
        removed = self.cellgraph.clear_descendants(source, clear_source)
        for node in removed:
            del node[OBJ].data[node[KEY]]

    # TODO
    # def clear_lexdescendants(self, refnode):
    #     """Clear values of cells that refer to `ref`."""

    def clear_obj(self, obj):
        """Clear values and nodes of `obj` and their dependants."""
        removed = self.cellgraph.clear_obj(obj)
        for node in removed:
            del node[OBJ].data[node[KEY]]

    def repr_self(self, add_params=True):
        return self.name

    def repr_parent(self):
        return ""

    @property
    def model(self):
        return self

    @Impl.doc.setter
    def doc(self, value):
        self._doc = value

    @property
    def global_refs(self):
        return self._global_refs.get_updated()

    @property
    def namespace(self):
        return self._namespace.get_updated()

    def close(self):
        self.system.close_model(self)

    def save(self, filepath):
        self.update_lazyevals()
        with open(filepath, "wb") as file:
            pickle.dump(self.interface, file, protocol=4)

    def get_object(self, name):
        """Retrieve an object by a dotted name relative to the model."""
        parts = name.split(".")
        space = self.spaces[parts.pop(0)]
        if parts:
            return space.get_object(".".join(parts))
        else:
            return space

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = (
        [
            "name",
            "cellgraph",
            "lexdep",
            "_namespace",
            "_global_refs",
            "_dynamic_bases",
            "_dynamic_bases_inverse",
            "_dynamic_base_namer",
            "spacemgr",
        ]
        + BaseSpaceContainerImpl.state_attrs
        + Impl.state_attrs
    )

    assert len(state_attrs) == len(set(state_attrs))

    def __getstate__(self):

        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.state_attrs
        }

        graphs = {
            name: graph
            for name, graph in state.items()
            if isinstance(graph, DependencyGraph)
        }

        for gname, graph in graphs.items():
            mapping = {}
            for node in graph:
                name = node[OBJ].get_fullname(omit_model=True)
                if node_has_key(node):
                    mapping[node] = (name, node[KEY])
                else:
                    mapping[node] = name
            state[gname] = nx.relabel_nodes(graph, mapping)

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""
        Impl.restore_state(self, system)
        BaseSpaceContainerImpl.restore_state(self, system)
        mapping = {}
        for node in self.cellgraph:
            if isinstance(node, tuple):
                name, key = node
            else:
                name, key = node, None
            cells = self.get_object(name)
            mapping[node] = get_node(cells, key, None)

        self.cellgraph = nx.relabel_nodes(self.cellgraph, mapping)

    def del_space(self, name):
        space = self.spaces[name]
        self.spaces.del_item(name)

    def _set_space(self, space):

        if space.name in self.spaces:
            self.del_space(space.name)
        elif space.name in self.global_refs:
            raise KeyError("Name '%s' already already assigned" % self.name)

        self.spaces.set_item(space.name, space)

    def del_ref(self, name):
        self.global_refs.del_item(name)

    def get_attr(self, name):
        if name in self.spaces:
            return self.spaces[name].interface
        elif name in self.global_refs:
            return get_interfaces(self.global_refs[name])
        else:
            raise AttributeError(
                "Model '{0}' does not have '{1}'".format(self.name, name)
            )

    def set_attr(self, name, value):
        if name in self.spaces:
            raise KeyError("Space named '%s' already exist" % self.name)

        self.global_refs.set_item(name, ReferenceImpl(self, name, value))

    def del_attr(self, name):

        if name in self.spaces:
            self.del_space(name)
        elif name in self.global_refs:
            self.del_ref(name)
        else:
            raise KeyError("Name '%s' not defined" % name)

    def get_dynamic_base(self, bases: tuple):
        """Create of get a base space for a tuple of bases"""

        try:
            return self._dynamic_bases_inverse[bases]
        except KeyError:
            name = self._dynamic_base_namer.get_next(self._dynamic_bases)
            base = self._new_space(name=name)
            self.spacemgr.graph.add_space(base)
            self._dynamic_bases[name] = base
            self._dynamic_bases_inverse[bases] = base
            base.add_bases(bases)
            return base


class SpaceGraph(nx.DiGraph):
    def add_space(self, space):
        self.add_node(space)
        self.update_subspaces(space)

    def add_edge(self, basespace, subspace, **attr):

        if basespace.has_linealrel(subspace):
            if not isinstance(subspace, DynamicSpaceImpl):
                raise ValueError(
                    "%s and %s have parent-child relationship"
                    % (basespace, subspace)
                )

        nx.DiGraph.add_edge(self, basespace, subspace)

        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(basespace, subspace)
            raise ValueError("Loop detected in inheritance")

        try:
            self._start_space = subspace
            self.update_subspaces(subspace, check_only=True)
        finally:
            self._start_space = None

        # Flag update MRO cache
        for desc in nx.descendants(self, basespace):
            desc.update_mro = True

    def remove_edge(self, basespace, subspace):
        nx.DiGraph.remove_edge(self, basespace, subspace)

        basespace.update_mro = True
        subspace.update_mro = True

        for desc in nx.descendants(self, subspace):
            desc.update_mro = True

    def get_bases(self, node):
        """Direct Bases iterator"""
        return self.predecessors(node)

    def check_mro(self, bases):
        """Check if C3 MRO is possible with given bases"""

        try:
            self.add_node("temp")
            for base in bases:
                nx.DiGraph.add_edge(self, base, "temp")
            result = self.get_mro("temp")[1:]

        finally:
            self.remove_node("temp")

        return result

    def get_mro(self, space):
        """Calculate the Method Resolution Order of bases using the C3 algorithm.

        Code modified from
        http://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/

        Args:
            bases: sequence of direct base spaces.

        Returns:
            mro as a list of bases including node itself
        """
        seqs = [self.get_mro(base) for base in self.get_bases(space)] + [
            list(self.get_bases(space))
        ]
        res = []
        while True:
            non_empty = list(filter(None, seqs))

            if not non_empty:
                # Nothing left to process, we're done.
                res.insert(0, space)
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

    def update_subspaces(self, space, skip=True, check_only=False, **kwargs):
        self.update_subspaces_downward(space, skip, check_only, **kwargs)
        self.update_subspaces_upward(space, **kwargs)

    def update_subspaces_upward(self, space, from_parent=True, **kwargs):

        if from_parent:
            target = space.parent
        else:
            target = space

        if target.is_model():
            return
        else:
            succ = self.successors(target)
            for subspace in succ:
                if subspace is self._start_space:
                    raise ValueError("Cyclic inheritance")
                self.update_subspaces(subspace, False, **kwargs)
            self.update_subspaces_upward(
                space.parent, from_parent=from_parent, **kwargs
            )

    def update_subspaces_downward(
        self, space, skip=True, check_only=False, **kwargs
    ):
        for child in space.static_spaces.values():
            self.update_subspaces_downward(child, False, check_only, **kwargs)
        if not skip and not check_only:
            space.inherit(**kwargs)
        succ = self.successors(space)
        for subspace in succ:
            if subspace is self._start_space:
                raise ValueError("Cyclic inheritance")
            self.update_subspaces(subspace, False, **kwargs)


class NewSpaceGraph(nx.DiGraph):
    """New implementation of inheritance graph

    Node state:
        copied: Copied into sub graph
        defined: Node created but space yet to create
        created: Space created
        updated: Existing space updated
        unchanged: Existing space confirmed unchanged
    """

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
                for base in self.predecessors(node)
                ] + [list(self.predecessors(node))]
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

    def get_derived_graph(self, on_edge=None):
        g = type(self).copy(self)
        for e in self.visit_edges():
            g.derive_tree(e, on_edge)
        return g

    def get_absbases(self):
        """Get absolute base nodes"""
        result = set(self.edges)
        for e in self.edges:
            tail, head = e
            if self.get_endpoints(
                    self.visit_treenodes(
                        self.get_topnode(tail)), edge="in"):
                result.remove(e)

        return result

    def visit_edges(self, *start):
        """Generator yielding edges in breadth-first order"""
        if not start:
            start = self.get_absbases()

        que = list(start)
        visited = set()
        while que:
            e = que.pop(0)
            if e not in visited:
                yield e
                visited.add(e)
            _, head = e
            edges = []
            for n in self.visit_treenodes(self.get_topnode(head, edge="out")):
                if self.is_endpoint(n, edge="out"):
                    edges.extend(oe for oe in self.out_edges(n)
                                 if oe not in visited)
            que += edges

    def derive_tree(self, edge, on_edge=None):
        """Create derived node under the head of edge from the tail of edge"""
        tail, head = edge

        tail_len = len(tail.split("."))
        head_len = len(head.split("."))

        # Remove parent
        bases = list(".".join(n.split(".")[tail_len:])
                    for n in self.visit_treenodes(tail, include_self=False))
        subs = list(".".join(n.split(".")[head_len:])
                   for n in self.visit_treenodes(head, include_self=False))

        # missing = bases - subs
        derived = list((tail + "." + n, head + "." + n) for n in bases)

        for e in derived:
            if e not in self.edges:
                t, h = e
                if h not in self.nodes:
                    self.add_node(h, mode="derived", state="defined")
                self.add_edge(t, h, mode="derived")
            if on_edge:
                on_edge(self, e)

    def subgraph_from_nodes(self, nodes, on_backup=None):
        """Get sub graph with nodes reachable form ``node``"""
        result = set()
        for node in nodes:
            if node in self.nodes:
                nodeset, _ = self.get_nodeset(node, set())
                result.update(nodeset)
        subg = type(self).copy(self.subgraph(result))

        for n in subg.nodes:
            subg.nodes[n]["state"] = "copied"
            if on_backup:
                subg.nodes[n]["backup"] = on_backup(self, n)

        return subg

    def subgraph_from_state(self, state):
        nodes = set(n for n in self if self.nodes[n]["state"] == state)
        return type(self).copy(self.subgraph(nodes))

    def get_updated(self, subgraph, nodeset=None, keep_self=True,
                    on_restore=None):
        """Return a new space graph with nodeset removed and subgraph added

        subgraph's state attribute is removed.
        """
        if nodeset is None:
            nodeset = subgraph.nodes

        if keep_self:
            src = self.copy()
        else:
            src = self

        for n in subgraph.nodes:
            del subgraph.nodes[n]["state"]

        src.remove_nodes_from(nodeset)

        if on_restore:
            for n in self.nodes:
                on_restore(subgraph, n)

        return nx.compose(src, subgraph)

    def get_nodeset(self, node, processed):
        """Get a subset of self.

        Get a subset of self such that the subset contains
        nodes connected to ``node`` either through inheritance or composition.

        0. Prepare an emptly node set
        1. Get the top endopoint in the tree that ``node`` is in, or ``node``
           if none.
        2. Add to the node set all the child nodes of the top endpoint.
        3. Find node sets.
        4. For each endpoint in the child nodes, repeat from 1.
        """
        top = self.get_topnode(node)
        tree = set(self.visit_treenodes(top))
        ends = self.get_endpoints(tree)

        neighbors = self.get_otherends(ends) - processed
        processed.update(ends)
        result = tree.copy()
        for n in neighbors:
            ret_res, _ = self.get_nodeset(n, processed)
            result.update(ret_res)

        return result, processed

    def get_parent_nodes(self, node: str, include_self=True):
        """Get ancestors of ``node`` in order"""
        split = node.split(".")
        maxlen = len(split) if include_self else len(split) - 1

        result = []
        for i in range(maxlen, 0, -1):
            n = ".".join(split[:i])
            if n in self.nodes:
                result.insert(0, n)
            else:
                break
        return result

    def get_topnode(self, node, edge="any"):
        """Get the highest node that is an ancestor of the ``node``.
        If none exits, return ``node``.
        """
        parents = self.get_parent_nodes(node)
        return next((n for n in parents if self.is_endpoint(n, edge)), node)

    def visit_treenodes(self, node, include_self=True):
        que = [node]
        while que:
            n = que.pop(0)
            if n != node or include_self:
                yield n
            childs = [ch for ch in self.nodes
                      if ch[:len(n) + 1] == (n + ".")
                      and len(n.split(".")) + 1 == len(ch.split("."))]
            que += childs

    def get_endpoints(self, nodes, edge="any"):
        return set(n for n in nodes if self.is_endpoint(n, edge))

    def get_otherends(self, nodes, edge="any"):
        otherends = [set(self.get_neighbors(n, edge)) for n in nodes]
        return set().union(*otherends)

    def get_neighbors(self, node, edge):
        if edge == "in":
            return self.predecessors(node)
        elif edge == "out":
            return self.successors(node)
        else:
            return itertools.chain(
                self.predecessors(node), self.successors(node))

    def is_endpoint(self, node, edge="any"):
        if edge == "out":
            return bool(self.out_edges(node))
        elif edge == "in":
            return bool(self.in_edges(node))
        elif edge == "any":
            return bool(self.out_edges(node) or
                        self.in_edges(node))
        else:
            raise ValueError

    def dbg_add_bases(self, space, *bases):
        space_name = space.get_fullname(omit_model=True)
        if space_name not in self:
            self.add_node(space_name, space=space)
        for base in bases:
            base_name = base.get_fullname(omit_model=True)
            if base_name not in self:
                self.add_node(base_name, space=base)
            self.add_edge(base_name, space_name)

    def dbg_add_spaces(self, *spaces):
        for s in spaces:
            name = s.get_fullname(omit_model=True)
            self.add_node(name, space=s)


class SpaceManager:

    def __init__(self, model):
        self.model = model
        self.graph = SpaceGraph()
        self._inheritance = NewSpaceGraph()
        self._graph = NewSpaceGraph()

    def can_add(self, parent, name, klass):

        if parent is self.model:
            return name not in parent.namespace

        else:  # parent is UserSpaceImpl
            if name in parent.namespace:
                return False
            else:
                node = parent.get_fullname(omit_model=True)
                descs = nx.descendants(self._graph, node)
                for desc in descs:
                    ns = self._graph.nodes[desc]['space'].namespace
                    if desc in ns and not isinstance(ns[desc], klass):
                        return False
                return True

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
                if self.can_add(parent, name, UserSpaceImpl):
                    break

        elif not self.can_add(parent, name, UserSpaceImpl):
            raise ValueError("Cannot create space '%s'" % name)

        if not prefix and not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        if bases is None:
            bases = []
        elif isinstance(bases, UserSpaceImpl):
            bases = [bases]

        if parent.is_model():
            node = name
            pnode = []
        else:
            node = parent.get_fullname(omit_model=True) + "." + name
            pnode = [parent.get_fullname(omit_model=True)]

        nodes = pnode + [
            b.get_fullname(omit_model=True) for b in bases]

        subg_inh = self._inheritance.subgraph_from_nodes(
            nodes, self.backup_hook)
        subg = subg_inh.get_derived_graph()

        newsubg_inh = subg_inh.copy()

        space = UserSpaceImpl(
            parent,
            name,
            formula=formula,
            refs=refs,
            source=source,
            doc=doc)
        parent._set_space(space)

        newsubg_inh.add_node(
            node, mode="defined", state="defined", space=space)

        for b in bases:
            base = b.get_fullname(omit_model=True)
            newsubg_inh.add_edge(base, node, mode="defined")

        if not nx.is_directed_acyclic_graph(newsubg_inh):
            raise ValueError("cyclic inheritance")

        newsubg_inh.get_mro(node)  # Check if MRO is possible
        newsubg = newsubg_inh.get_derived_graph(on_edge=self.derive_hook)

        if not nx.is_directed_acyclic_graph(newsubg):
            raise ValueError("cyclic inheritance")

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(newsubg, node):
            newsubg.get_mro(n)

        self.apply_subgraph(newsubg_inh, newsubg, subg_inh, subg)

        return space

    def apply_subgraph(self, newsubg_inh, newsubg, subg_inh, subg):

        # Add derived spaces back to newsubg_inh
        created = newsubg.subgraph_from_state("created")
        if created:
            created.remove_edges_from(list(created.edges))
        newsubg_inh = nx.compose(newsubg_inh, created)

        self._inheritance = self._inheritance.get_updated(
            newsubg_inh, nodeset=subg_inh.nodes, keep_self=False
        )
        self._graph = self._graph.get_updated(
            newsubg, nodeset=subg.nodes, keep_self=False
        )

    def backup_hook(self, graph, node):
        space = graph.nodes[node]["space"]
        state = space.__getstate__()
        return copy.copy(state)

    def restore_hook(self, graph, node):
        space = graph.nodes[node]["space"]
        space.__setstate__(graph.nodes[node]["backup"])

    def derive_hook(self, graph, edge):
        tail, head = edge
        state = graph.nodes[head]["state"]
        # mro = graph.get_mro(head)
        parent_node = ".".join(head.split(".")[:-1])
        name = head.split(".")[-1]
        parent = graph.nodes[parent_node]["space"]

        if state == "defined":
            space = UserSpaceImpl(
                parent,
                name
                # formula=formula,
                # refs=refs,
                # source=source,
                # doc=doc
            )
            parent._set_space(space)
            space._is_derived = True
            graph.nodes[head]["space"] = space
            graph.nodes[head]["state"] = "created"

        self.inherit(head, graph)

    def inherit(self, node, subg: NewSpaceGraph, **kwargs):

        space = subg.nodes[node]["space"]
        mode = subg.nodes[node]["mode"]
        mro = subg.get_mro(node)
        space.set_formula(subg.nodes[mro[1]]["space"].formula)

        attrs = ("cells", "self_refs")

        for attr in attrs:
            selfdict = getattr(space, attr)
            basedict = ChainMap(*[getattr(subg.nodes[base]["space"], attr)
                                 for base in subg.get_mro(node)[1:]])

            missing = set(basedict) - set(selfdict)
            shared = set(selfdict) & set(basedict)
            diffs = set(selfdict) - set(basedict)

            for name in missing & shared:
                base = next(b[name] for b in basedict
                            if name in b and b[name].is_defined)

                if name in missing:
                    selfdict[name] = space._new_member(
                        attr, name, is_derived=True)

                if selfdict[name].is_derived:
                    if "clear_value" not in kwargs:
                        kwargs["clear_value"] = True
                    selfdict[name].inherit(**kwargs)

            if space.is_derived:
                for name in diffs:
                    selfdict.del_item(name)

        for dynspace in space._dynamic_subs:
            dynspace.inherit(**kwargs)

    def add_bases(self, space, *bases):
        """Add bases to space in graph
        """
        node = space.get_fullname(omit_model=True)

        if node not in self._inheritance:
            raise ValueError("Space '%s' not found" % node)

        basenodes = [base.get_fullname(omit_model=True) for base in bases]

        for base in basenodes:
            if base not in self._inheritance:
                raise ValueError("Space '%s' not found" % base)

        subg_inh = self._inheritance.subgraph_from_nodes([node] + basenodes)
        subg = subg_inh.get_derived_graph()
        newsubg_inh = subg_inh.copy()

        for b in basenodes:
            newsubg_inh.add_edge(b, node, mode="defined")

        for p in newsubg_inh.get_parent_nodes(node):
            newsubg_inh.nodes[p]["mode"] = "defined"

        if not nx.is_directed_acyclic_graph(newsubg_inh):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(newsubg_inh, node)):
            newsubg_inh.get_mro(n)

        newsubg = newsubg_inh.get_derived_graph(on_edge=self.derive_hook)

        if not nx.is_directed_acyclic_graph(newsubg):
            raise ValueError("cyclic inheritance")

        for desc in itertools.chain(
                {node},
                nx.descendants(newsubg, node)):

            mro = newsubg.get_mro(desc)

            # Check name conflict between spaces, cells, refs
            members = {}
            for attr in ["spaces", "cells", "refs"]:
                namechain = []
                for sname in mro:
                    space = newsubg.nodes[sname]["space"]
                    namechain.append(set(getattr(space, attr).keys()))
                members[attr] = set().union(*namechain)

            conflict = set().intersection(*[n for n in members.values()])
            if conflict:
                raise NameError("name conflict: %s" % conflict)

        self.apply_subgraph(newsubg_inh, newsubg, subg_inh, subg)
