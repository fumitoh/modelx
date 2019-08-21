import itertools
import networkx as nx


class SpaceGraph(nx.DiGraph):

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

    def derive_edges(self):
        for e in self.visit_edges():
            self.derive_tree(e)

    def get_absbases(self):
        """Get absolute base nodes"""
        result = set(self.edges)
        for e in self.edges:
            tail, head = e
            if self.get_endpoints(
                    self.get_treenodes(
                        self.get_topnode(tail)), edge="in"):
                result.remove(e)

        return result

    def visit_edges(self):
        """Generator yielding edges in breadth-first order"""
        que = list(self.get_absbases())
        visited = set()
        while que:
            e = que.pop(0)
            yield e

            visited.add(e)
            _, head = e
            edges = self.out_edges(
                self.get_endpoints(
                    self.get_treenodes(
                        self.get_topnode(head)
                    ), edge="out"))

            que.extend(e for e in edges if e not in visited)

    def derive_tree(self, edge):
        """Create derived node under the head of edge from the tail of edge"""
        tail, head = edge

        tail_len = len(tail.split("."))
        head_len = len(head.split("."))

        # Remove parent
        bases = set(".".join(n.split(".")[tail_len:])
                    for n in self.get_treenodes(tail, include_self=False))
        subs = set(".".join(n.split(".")[head_len:])
                   for n in self.get_treenodes(head, include_self=False))

        # missing = bases - subs
        derived = set((tail + "." + n, head + "." + n) for n in bases)

        for e in derived:
            if e not in self.edges:
                t, h = e
                if h not in self.nodes:
                    self.add_node(h, type="derived")
                self.add_edge(t, h, type="derived")

    def get_subgraph(self, *nodes):
        """Get sub graph with nodes reachable form ``node``"""
        result = set()
        for node in nodes:
            nodeset, _ = self.get_nodeset(node, set())
            result.update(nodeset)
        return type(self).copy(self.subgraph(result))

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
        tree = self.get_treenodes(top)
        ends = self.get_endpoints(tree)

        neighbors = self.get_otherends(ends) - processed
        processed.update(ends)
        result = tree.copy()
        for n in neighbors:
            ret_res, _ = self.get_nodeset(n, processed)
            result.update(ret_res)

        return result, processed

    def get_parent_nodes(self, node: str, include_self=True):
        split = node.split(".")
        size = len(split) if include_self else len(split) - 1
        return [".".join(split[:i + 1]) for i in range(len(split))][:size]

    def get_topnode(self, node):
        parents = self.get_parent_nodes(node)
        return next((n for n in parents if self.is_endpoint(n)), node)

    def get_treenodes(self, node, include_self=True):
        """Get the child nodes of ``node``.

        All child nodes must be included in ``self``.
        """
        result = {node} if include_self else set()
        return result.union(
            n for n in self.nodes if n[:len(node) + 1] == (node + "."))

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

    def add_bases(self, space, *bases):
        space_name = space.get_fullname(omit_model=True)
        if space_name not in self:
            self.add_node(space_name, space=space)
        for base in bases:
            base_name = base.get_fullname(omit_model=True)
            if base_name not in self:
                self.add_node(base_name, space=base)
            self.add_edge(base_name, space_name)

    def add_spaces(self, *spaces):
        for s in spaces:
            name = s.get_fullname(omit_model=True)
            self.add_node(name, space=s)


class SpaceManager:

    def __init__(self):
        self._inherit_graph = SpaceGraph()
        self._derived_graph = SpaceGraph()

    def new_space(self, space,):
        """Create a new space."""
        name = space.get_fullname(omit_model=True)
        self._inherit_graph.add_node(name, space=space)

        self._inherit_graph = nx.compose(
            self._inherit_graph, self._derived_graph)

    def add_bases(self, space, *bases):
        space_name = space.get_fullname(omit_model=True)
        if space_name not in self._inherit_graph:
            raise ValueError("Space '%s' not found" % space_name)

        base_names = [base.get_fullname(omit_model=True) for base in bases]

        for base in base_names:
            if base not in self._inherit_graph:
                raise ValueError("Space '%s' not found" % base)

        sub_inhg = self._inherit_graph.get_subgraph(base_names)
        sub_inhg_last = sub_inhg.copy()
        sub_derg_last = sub_inhg_last.copy()

        for base in base_names:
            sub_inhg.add_edge(base, space_name)

        sub_derg = sub_inhg.derive_edges()
        self._inherit_graph.remove_nodes_from(sub_inhg_last.nodes)
        self._inherit_graph = nx.compose(self._inherit_graph,
                                         sub_inhg)

        self._derived_graph.remove_nodes_from(sub_derg_last.nodes)
        self._derived_graph = nx.compose(self._derived_graph,
                                         sub_derg)


if __name__ == "__main__":
    import modelx as mx
    from modelx.core.base import get_impls

    g = SpaceGraph()

    """
            2
         C<---------F
         |          |
       1 |          |
    A<---B          B
         |  3       |
         D<---E     D
              |
              G
    """

    m = mx.new_model()
    m.new_space("A")
    m.new_space("C").new_space("B").new_space("D")
    m.new_space("E").new_space("G")
    m.new_space("F").new_space("B").new_space("D")

    g.add_spaces(
        *get_impls(
            [m.A, m.C, m.C.B, m.C.B.D, m.F, m.F.B, m.F.B.D, m.E, m.E.G]))
    g.add_bases(m.A._impl, m.C.B._impl)
    g.add_bases(m.C._impl, m.F._impl)
    g.add_bases(m.C.B.D._impl, m.E._impl)
    retult, _ = g.get_nodeset("A", set())

    nodes = ["A", "C", "C.B", "C.B.D", "E", "E.G", "F", "F.B", "F.B.D"]
    for n in nodes:
        print(g.get_nodeset(n, set())[0])

    print(g.get_nodeset("C.B", set())[0])
    sg = g.get_subgraph("C.B")

    g.get_nodeset("F.B", set())[0]
    sg.derive_edges()

    for e in sg.edges:
        print(e, sg.edges[e])

    print(sg.get_mro('C.B.D'))