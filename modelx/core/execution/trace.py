# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

from collections import deque
from typing import Any, Tuple, Dict, Union
import networkx as nx


TraceKey = Tuple[Any, ...]


class TraceObject:

    __slots__ = ()
    # __mixin_slots = ("is_cached", "tracemgr")   # and "data"

    model: 'TraceManager'
    is_cached: bool
    data: Dict[TraceKey, Any]

    # def __init__(self, tracemgr):
    #     self.tracemgr = tracemgr

    def has_node(self, key: TraceKey) -> bool:
        raise NotImplementedError

    def on_eval_formula(self) -> Any:
        raise NotImplementedError

    def on_clear_trace(self, key: TraceKey) -> None:
        raise NotImplementedError


class ParentTraceObject(TraceObject):

    __slots__ = ()
    __mixin_slots = ()

    def get_nodes_for(self, key: TraceKey):
        raise NotImplementedError


TraceNode = Tuple[TraceObject, TraceKey]

OBJ = 0
KEY = 1


def key_to_node(obj: TraceObject, key: TraceKey) -> TraceNode:
    """Return node form object ane ky"""
    return obj, key


def get_node(obj: TraceObject, args, kwargs) -> TraceNode:
    """Create a node from arguments and return it"""

    if args is None and kwargs is None:
        return (obj,)

    if kwargs is None:
        kwargs = {}
    return obj, _bind_args(obj, args, kwargs)


def node_get_args(node: TraceNode) -> TraceKey:
    """Return an ordered mapping from params to args"""
    obj = node[OBJ]
    key = node[KEY]
    boundargs = obj.formula.signature.bind(*key)
    boundargs.apply_defaults()
    return boundargs.arguments


def tuplize_key(obj, key, remove_extra=False):
    """Args"""

    if key.__class__ is tuple:  # Not isinstance(key, tuple) for speed
        pass
    else:
        key = (key,)

    if not remove_extra:
        return key
    else:
        paramlen = len(obj.formula.parameters)
        arglen = len(key)
        if arglen:
            return key[: min(arglen, paramlen)]
        else:
            return key


def _bind_args(obj: TraceObject, args, kwargs) -> TraceKey:
    boundargs = obj.formula.signature.bind(*args, **kwargs)
    boundargs.apply_defaults()
    return tuple(boundargs.arguments.values())


def get_node_repr(node: TraceNode) -> str:

    obj = node[OBJ]
    key = node[KEY]

    name = obj.get_repr(fullname=True, add_params=False)
    params = obj.formula.parameters

    arglist = ", ".join(
        "%s=%s" % (param, arg) for param, arg in zip(params, key)
    )

    if key in obj.data:
        return name + "(" + arglist + ")" + "=" + str(obj.data[key])
    else:
        return name + "(" + arglist + ")"


class TraceGraph(nx.DiGraph):
    """Directed Graph of ObjectArgs"""

    NODE = 1
    EDGE = 2

    def _dfs_edges_and_postorder(self, source):
        """Single-pass stream of DFS tree-edges and postorder nodes."""
        for u, v, lbl in nx.dfs_labeled_edges(self, source=source):
            if lbl == "forward" and u != v:  # skip the (root, root) pseudo-edge
                yield self.EDGE, (u, v)  # matches what dfs_edges() would yield
            elif lbl == "reverse":  # v just finished => postorder event
                yield self.NODE, v  # includes the root as the last 'post'

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

    def get_startnodes_from(self, node):
        if node in self:
            return [n for n in nx.descendants(self, node)
                    if self.out_degree(n) == 0]
        else:
            return []

    def fresh_copy(self):
        """Overriding Graph.fresh_copy"""
        return TraceGraph()


class ReferenceGraph(nx.DiGraph):

    def remove_with_descs(self, ref):
        if ref not in self:
            return deque()

        descs = deque(nx.dfs_postorder_nodes(self, ref)) # includes ref
        self.remove_nodes_from(descs)
        descs.pop()     # remove ref

        return descs

    def remove_with_referred(self, node):
        """Remove nodes that refer to ref nodes.

        If the referred ref nodes become isolated, also remove them.
        """
        if not self.has_node(node):
            return

        refs = list(self.predecessors(node))
        self.remove_node(node)

        for n in refs:
            if self.degree(n) == 0:
                self.remove_node(n)


class TraceManager:

    __slots__ = ()
    __mixin_slots = (
        "tracegraph",
        "refgraph"
    )

    def __init__(self):
        self.tracegraph: TraceGraph = TraceGraph()
        self.refgraph: ReferenceGraph = ReferenceGraph()

    def _extended_dfs_nodes(self, source):
        dfs = deque()
        parents = deque()
        edges = []
        for s, e_or_n in self.tracegraph._dfs_edges_and_postorder(source):
            if s == TraceGraph.EDGE:
                edges.append(e_or_n)
            elif s == TraceGraph.NODE:
                dfs.append(e_or_n)
                if isinstance(e_or_n[OBJ], ParentTraceObject):
                    parents.append(e_or_n)

        if not parents:
            return dfs
        else:
            g = nx.DiGraph(edges)
            g.add_node(source)  # in case source is isolated
            while parents:
                p = parents.popleft()
                for child in p[OBJ].get_nodes_for(p[KEY]):
                    g.add_edge(p, child)
                    for s, e_or_n in self.tracegraph._dfs_edges_and_postorder(child):
                        if s == TraceGraph.EDGE:
                            g.add_edge(*e_or_n)
                        elif s == TraceGraph.NODE:
                            if isinstance(e_or_n[OBJ], ParentTraceObject):
                                parents.append(e_or_n)
            return deque(nx.dfs_postorder_nodes(g, source))

    def clear_with_descs(self, node):
        """Clear values and nodes calculated from `source`."""
        for n in self._extended_dfs_nodes(node):
            self.tracegraph.remove_node(n)
            self.refgraph.remove_with_referred(n)
            n[OBJ].on_clear_trace(n[KEY])

    def clear_obj(self, obj: TraceObject):
        """Clear values and nodes of `obj` and their dependants."""
        if not obj.is_cached:
            self.clear_attr_referrers(obj)
            return

        keys = deque(obj.data)
        removed = set()

        while keys:
            k = keys.popleft()
            if (obj, k) not in removed:
                for n in self._extended_dfs_nodes((obj, k)):
                    self.tracegraph.remove_node(n)
                    self.refgraph.remove_with_referred(n)
                    n[OBJ].on_clear_trace(n[KEY])
                    removed.add(n)

    def clear_attr_referrers(self, ref):
        descs = self.refgraph.remove_with_descs(ref)
        while descs:
            node = descs.popleft()
            if node in self.tracegraph:
                for n in self._extended_dfs_nodes(node):
                    self.tracegraph.remove_node(n)
                    n[OBJ].on_clear_trace(n[KEY])

    def get_calcsteps(self, targets, nodes, step_size):
        """ Get calculation steps
        Calculate a new block
        Find nodes to paste in the block
        Find nodes to clear from the earlier blocks
        Push the paste node in the earlier blocks
        """
        from modelx.core.node import ItemNode
        subgraph = self.tracegraph.subgraph(nodes)

        ordered = list(nx.topological_sort(subgraph))
        node_len = len(ordered)

        pasted = []         # in reverse order
        step = 0
        result = []
        while step * step_size < node_len:

            start = step * step_size
            stop = min(node_len, (step + 1) * step_size)

            cur_block = ordered[start:stop]
            cur_paste = []
            cur_clear = []
            cur_targets = []    # also included in cur_paste
            for n in cur_block:

                paste = False
                if n in targets:
                    cur_targets.append(n)
                    paste = True
                else:
                    for suc in subgraph.successors(n):
                        if suc not in cur_block:
                            paste = True
                            break
                if paste:
                    cur_paste.append(n)
                else:
                    cur_clear.append(n)

            accum_nodes = set(ordered[:stop])
            for n in pasted.copy():

                paste = False
                for suc in subgraph.successors(n):
                    if suc not in accum_nodes:
                        paste = True
                        break

                if not paste:
                    cur_clear.append(n)
                    pasted.remove(n)

            for n in cur_paste:
                if n not in cur_targets:
                    pasted.append(n)

            result.append(['calc', [ItemNode(n) for n in cur_block]])
            result.append(['paste', [ItemNode(n) for n in reversed(cur_paste)]])
            result.append(['clear', [ItemNode(n) for n in cur_clear]])

            step += 1

        assert not pasted
        return result
