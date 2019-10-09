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
import pickle
import copy

import networkx as nx

from modelx.core.base import (
    Interface,
    Impl,
    get_interfaces,
    ImplDict,
    ImplChainMap,
    BaseView,
    Derivable,
    NullImpl
)
from modelx.core.reference import ReferenceImpl
from modelx.core.node import OBJ, KEY, get_node, node_has_key
from modelx.core.spacecontainer import (
    BaseSpaceContainerImpl,
    EditableSpaceContainerImpl,
    EditableSpaceContainer,
)
from modelx.core.space import (
    UserSpaceImpl,
    SpaceView,
    RefDict
)
from modelx.core.cells import CellsImpl
from modelx.core.util import is_valid_name, AutoNamer

_nxver = tuple(int(n) for n in nx.__version__.split(".")[:2])

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
        # self.lexdep = DependencyGraph()  # Lexical dependency
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
        return self._global_refs.refresh

    @property
    def namespace(self):
        return self._namespace.refresh

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
            # "lexdep",
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
            base = self.spacemgr.new_space(
                self,
                name=name, bases=bases, prefix="__", set_space=False)
            self._dynamic_bases[name] = base
            self._dynamic_bases_inverse[bases] = base
            return base


class SpaceGraph(nx.DiGraph):
    """New implementation of inheritance graph

    Node state:
        copied: Copied into sub graph
        defined: Node created but space yet to create
        created: Space created
        updated: Existing space updated
        unchanged: Existing space confirmed unchanged
    """

    def fresh_copy(self):   # Only for networkx -2.1
        """Overriding Graph.fresh_copy"""
        return SpaceGraph()

    def ordered_preds(self, node):
        edges = [(self.edges[e]["index"], e) for e in self.in_edges(node)]
        return [e[0] for i, e in sorted(edges, key=lambda elm: elm[0])]

    def ordered_subs(self, node):
        g = nx.descendants(self, node)
        g.add(node)
        return nx.topological_sort(self.subgraph(g))

    def max_index(self, node):
        return max(
            [self.edges[e]["index"] + 1 for e in self.in_edges(node)],
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

    def get_derived_graph(self, on_edge=None, on_remove=None, start=()):
        g = self.copy_as_spacegraph(self)
        for e in self.visit_edges(*start):
            g.derive_tree(e, on_edge, on_remove)
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

    def check_cyclic(self, start, node):
        """True if no cyclic"""

        succs = self.get_otherends(
            self.visit_treenodes(self.get_topnode(node, edge="out")),
            edge="out")

        for n in succs:
            if self.is_linealrel(start, n):
                return False
            else:
                if not self.check_cyclic(start, n):
                    return False

        return True

    def derive_tree(self, edge, on_edge=None, on_remove=None):
        """Create derived node under the head of edge from the tail of edge"""
        tail, head = edge

        if tail:
            tail_len = len(tail.split("."))
            bases = list(".".join(n.split(".")[tail_len:])
                    for n in self.visit_treenodes(tail, include_self=False))
        else:
            bases = []

        head_len = len(head.split("."))
        subs = list(".".join(n.split(".")[head_len:])
                   for n in self.visit_treenodes(head, include_self=False))

        # missing = bases - subs
        derived = list((tail + "." + n, head + "." + n) for n in bases)
        derived.insert(0, (tail, head))

        for e in derived:
            if e not in self.edges:
                t, h = e
                if h not in self.nodes:
                    self.add_node(h, mode="derived", state="defined")

                if t:   # t can be ""
                    self.add_edge(
                        t, h,
                        mode="derived",
                        index=self.max_index(t)
                    )
            if on_edge:
                on_edge(self, e)

        for n in reversed(subs):
            if n not in bases:
                n = head + "." + n
                if self.nodes[n]["mode"] == "derived":
                    if not list(self.predecessors(n)):
                        if on_remove:
                            on_remove(self, n)
                        self.remove_node(n)

    def subgraph_from_nodes(self, nodes, on_backup=None):
        """Get sub graph with nodes reachable form ``node``"""
        result = set()
        for node in nodes:
            if node in self.nodes:
                nodeset, _ = self.get_nodeset(node, set())
                result.update(nodeset)

        subg = self.copy_as_spacegraph(self.subgraph(result))

        for n in subg.nodes:
            subg.nodes[n]["state"] = "copied"
            if on_backup:
                subg.nodes[n]["backup"] = on_backup(self, n)

        return subg

    def subgraph_from_state(self, state):
        """Get sub graph with nodes with ``state``"""
        nodes = set(n for n in self if self.nodes[n]["state"] == state)
        return self.copy_as_spacegraph(self.subgraph(nodes))

    def get_updated(self, subgraph, nodeset=None, keep_self=True,
                    on_restore=None):
        """Return a new space graph with nodeset removed and subgraph added

        subgraph's state attribute is removed.
        """
        if nodeset is None:
            nodeset = subgraph.nodes

        if keep_self:
            src = self.copy_as_spacegraph(self)
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

    def has_child(self, node, child):
        node = node.split(".")
        node_len = len(node)

        child = child.split(".")
        child_len = len(child)

        if node_len >= child_len:
            return False
        elif node == child[:node_len]:
            return True
        else:
            return False

    def has_parent(self, node, parent):
        node = node.split(".")
        node_len = len(node)

        parent = parent.split(".")
        parent_len = len(parent)

        if node_len <= parent_len:
            return False
        elif node[:parent_len] == parent:
            return True
        else:
            return False

    def is_linealrel(self, node, other):
        return (
                node == other
                or self.has_child(node, other)
                or self.has_parent(node, other)
        )

    def to_space(self, node):
        return self.nodes[node]["space"]

    def get_mode(self, node):
        return self.nodes[node]["mode"]

    def copy_as_spacegraph(self, g):
        """Copy g as SpaceGraph.

        This method is only for compatibility with networkx 2.1 or older.
        Overriding fresh_copy method is also needed.
        G can be a sub graph view.
        """
        if _nxver < (2, 2):
            # modified from https://github.com/networkx/networkx/blob/networkx-2.1/networkx/classes/digraph.py#L1080-L1167
            # See LICENSES/NETWORKX_LICENSE.txt

            def copy(klass, graph, as_view=False):

                if as_view is True:
                    return nx.graphviews.DiGraphView(graph)
                G = klass()
                G.graph.update(graph.graph)
                G.add_nodes_from((n, d.copy()) for n, d in graph._node.items())
                G.add_edges_from((u, v, datadict.copy())
                                 for u, nbrs in graph._adj.items()
                                 for v, datadict in nbrs.items())
                return G

            return copy(type(self), g)

        else:
            return type(self).copy(g)


class SpaceManager:

    def __init__(self, model):
        self.model = model
        self._inheritance = SpaceGraph()
        self._graph = SpaceGraph()

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
                    ns = self._graph.to_space(desc).namespace
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
            is_derived=False,
            prefix="",
            doc=None,
            set_space=True
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

        newsubg_inh = subg_inh.copy_as_spacegraph(subg_inh)

        space = UserSpaceImpl(
            parent,
            name,
            formula=formula,
            refs=refs,
            source=source,
            doc=doc)
        space.is_derived = is_derived
        if set_space:
            parent._set_space(space)

        newsubg_inh.add_node(
            node, mode="defined", state="created", space=space)

        for b in bases:
            base = b.get_fullname(omit_model=True)
            newsubg_inh.add_edge(
                base, node,
                mode="defined",
                index=newsubg_inh.max_index(node)
            )

        if not nx.is_directed_acyclic_graph(newsubg_inh):
            raise ValueError("cyclic inheritance")

        if not newsubg_inh.check_cyclic(node, node):
            raise ValueError("cyclic inheritance through composition")

        newsubg_inh.get_mro(node)  # Check if MRO is possible
        newsubg = newsubg_inh.get_derived_graph(on_edge=self.derive_hook)

        if not nx.is_directed_acyclic_graph(newsubg):
            raise ValueError("cyclic inheritance")

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(newsubg, node):
            newsubg.get_mro(n)

        self.update_graphs(newsubg_inh, newsubg, subg_inh, subg)

        return space

    def update_graphs(self, newsubg_inh, newsubg, remove_inh, remove):

        newsubg_inh.remove_nodes_from(
            set(n for n in newsubg_inh if n not in newsubg))

        # Add derived spaces back to newsubg_inh
        created = newsubg.subgraph_from_state("created")
        if created:
            created.remove_edges_from(list(created.edges))
        newsubg_inh = nx.compose(newsubg_inh, created)

        self._inheritance = self._inheritance.get_updated(
            newsubg_inh, nodeset=remove_inh, keep_self=False
        )
        self._graph = self._graph.get_updated(
            newsubg, nodeset=remove, keep_self=False
        )

    def backup_hook(self, graph, node):
        state = graph.to_space(node).__getstate__()
        return copy.copy(state)

    def restore_hook(self, graph, node):
        space = graph.to_space(node)
        space.__setstate__(graph.nodes[node]["backup"])

    def derive_hook(self, graph, edge):
        """Callback passed as on_edge parameter"""
        _, head = edge
        state = graph.nodes[head]["state"]

        parent_node = ".".join(head.split(".")[:-1])
        name = head.split(".")[-1]
        if parent_node in graph:
            parent = graph.to_space(parent_node)
        elif parent_node:
            parent = self._graph.to_space(parent_node)
        else:
            parent = self.model

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

        space = graph.to_space(head)
        bases = self._get_space_bases(space, graph)
        space.inherit(
            bases)

    def remove_hook(self, graph, node):
        parent_node = ".".join(node.split(".")[:-1])
        name = node.split(".")[-1]
        if parent_node in graph:
            parent = graph.to_space(parent_node)
            parent.static_spaces.del_item(name)
        elif parent_node:
            parent = self._graph.to_space(parent_node)
            parent.static_spaces.del_item(name)
        else:
            self.model.del_space(name)

    def inherit_hook(self, graph, edge):
        """Callback passed as on_edge parameter"""
        tail, head = edge

        space = graph.to_space(head)
        bases = self._get_space_bases(space, graph)

        space.inherit(bases)


    def add_bases(self, space, bases):
        """Add bases to space in graph
        """
        node = space.get_fullname(omit_model=True)
        basenodes = [base.get_fullname(omit_model=True) for base in bases]

        for base in [node] + basenodes:
            if base not in self._inheritance:
                raise ValueError("Space '%s' not found" % base)

        subg_inh = self._inheritance.subgraph_from_nodes([node] + basenodes)
        subg = subg_inh.get_derived_graph()
        newsubg_inh = subg_inh.copy()

        for b in basenodes:
            newsubg_inh.add_edge(
                b,
                node,
                mode="defined",
                index=newsubg_inh.max_index(node)
            )

        for p in newsubg_inh.get_parent_nodes(node):
            newsubg_inh.nodes[p]["mode"] = "defined"

        if not nx.is_directed_acyclic_graph(newsubg_inh):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(newsubg_inh, node)):
            newsubg_inh.get_mro(n)

        newsubg = newsubg_inh.get_derived_graph(
            on_edge=self.derive_hook)

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
                    space = newsubg.to_space(sname)
                    namechain.append(set(getattr(space, attr).keys()))
                members[attr] = set().union(*namechain)

            conflict = set().intersection(*[n for n in members.values()])
            if conflict:
                raise NameError("name conflict: %s" % conflict)

        self.update_graphs(newsubg_inh, newsubg, subg_inh.nodes, subg.nodes)

    def remove_bases(self, space, bases):

        node = space.get_fullname(omit_model=True)
        basenodes = [base.get_fullname(omit_model=True) for base in bases]

        for base in [node] + basenodes:
            if base not in self._inheritance:
                raise ValueError("Space '%s' not found" % base)

        subg_inh = self._inheritance.subgraph_from_nodes([node] + basenodes)
        subg = subg_inh.get_derived_graph()
        newsubg_inh = subg_inh.copy()

        for b in basenodes:
            newsubg_inh.remove_edge(b, node)

        if not nx.is_directed_acyclic_graph(newsubg_inh):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(newsubg_inh, node)):
            newsubg_inh.get_mro(n)

        newsubg = newsubg_inh.get_derived_graph(
            on_edge=self.derive_hook,
            on_remove=self.remove_hook,
            start=[("", node)]
        )

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
                    space = newsubg.to_space(sname)
                    namechain.append(set(getattr(space, attr).keys()))
                members[attr] = set().union(*namechain)

            conflict = set().intersection(*[n for n in members.values()])
            if conflict:
                raise NameError("name conflict: %s" % conflict)

        self.update_graphs(newsubg_inh, newsubg, subg_inh.nodes, subg.nodes)

    def del_defined_space(self, parent, name):

        if parent.is_model():
            node =  name
        else:
            pnode = parent.get_fullname(omit_model=True)
            node = pnode + "." + name

        if node not in self._inheritance:
            raise ValueError("Space '%s' not found" % node)
        elif self._inheritance.nodes[node]["mode"] == "derived":
            raise ValueError("cannot delete derived space")

        subg_inh = self._inheritance.subgraph_from_nodes(
            [node], self.backup_hook)
        subg = subg_inh.get_derived_graph()

        newsubg_inh = subg_inh.copy()
        succs = list(newsubg_inh.successors(node))

        # Remove node and its child tree
        children = set()
        for child in newsubg_inh.visit_treenodes(node):
            children.add(child)
            self.remove_hook(newsubg_inh, child)

        newsubg_inh.remove_nodes_from(children)
        newsubg = newsubg_inh.get_derived_graph(
            on_edge=self.inherit_hook,
            on_remove=self.remove_hook,
            start=[("", node) for node in succs]
        )
        for n in set(newsubg_inh.nodes):
            if n not in newsubg:
                newsubg_inh.remove_node(n)
        self.update_graphs(newsubg_inh, newsubg, subg_inh.nodes, subg.nodes)

    def new_cells(self, space, name=None, formula=None, is_derived=False,
                  source=None):

        if not self.can_add(space, name, CellsImpl):
            raise ValueError("Cannot create cells '%s'" % name)

        node = space.get_fullname(omit_model=True)

        cells = CellsImpl(space=space, name=name, formula=formula,
                          source=source)
        space._cells.set_item(cells.name, cells)
        cells.is_derived = is_derived

        for desc in nx.descendants(self._graph, node):
            s = self._graph.to_space(desc)
            b = self._get_space_bases(s, self._graph)
            s.inherit(b)

        return cells

    def new_ref(self, space, name, value, is_derived=False):

        if not self.can_add(space, name, CellsImpl):
            raise ValueError("Cannot create cells '%s'" % name)

        node = space.get_fullname(omit_model=True)

        ref = ReferenceImpl(space, name, value)
        space.self_refs.set_item(name, ref)
        ref.is_derived = is_derived

        for desc in nx.descendants(self._graph, node):
            s = self._graph.to_space(desc)
            b = self._get_space_bases(s, self._graph)
            s.inherit(b)

        return ref

    def get_deriv_bases(self, deriv: Derivable,
                        graph: SpaceGraph=None):
        if graph is None:
            graph = self._graph

        if isinstance(deriv, UserSpaceImpl):    # Not Dynamic spaces
            return self._get_space_bases(deriv, graph)

        pnode = deriv.parent.get_fullname(omit_model=True)

        bases = []
        for b in graph.get_mro(pnode)[1:]:
            base_members = deriv._get_members(graph.to_space(b))
            if deriv.name in base_members:
                bases.append(base_members[deriv.name])

        return bases

    def _get_space_bases(self, space, graph):
        nodes = graph.get_mro(space.get_fullname(omit_model=True))[1:]
        return [graph.to_space(n) for n in nodes]

    def get_direct_bases(self, space):
        node = space.get_fullname(omit_model=True)
        return [self._inheritance.to_space(n) for n in
                self._inheritance.get_mro(node)[1:]]

    def del_cells(self, space, name):

        cells = space.cells[name]
        space.cells.del_item(name)

        self.update_subs(space)
        NullImpl(cells)

    def del_ref(self, space, name):

        space.self_refs.del_item(name)
        self.update_subs(self, space)

    def update_subs(self, space):

        for desc in list(self._graph.ordered_subs(
                space.get_fullname(omit_model=True)))[1:]:
            s = self._graph.to_space(desc)
            b = self._get_space_bases(s, self._graph)
            s.inherit(b)

