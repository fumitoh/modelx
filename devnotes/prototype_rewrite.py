
import networkx as nx


class SpaceGraph(nx.DiGraph):

    def get_subgraph(self, node):
        """"""
        # Get top nodes and explicit edges
        nodes = set().union(self.get_inherited(node, "sub"),
                            self.get_inherited(node, "base"))

        explg = self.subgraph(nodes).copy()
        implg = explg.copy()

        # Bring child nodes in and add implicit edges
        for base, sub in explg.edges:
            self.derive_children(implg, base, sub)

        return implg

    def derive_children(self, g: nx.DiGraph, base, sub):
        g.add_edge(base, sub)
        for node in self.get_child_nodes(base):
            name = node.split(".")[-1]
            derived = ".".join([sub, name])
            self.derive_children(g, node, derived)

    def get_inherited(self, origin, direction="sub"):
        """Get base and sub nodes from name"""
        if direction == "sub":
            edge = self.out_edges
            method = self.successors
        elif direction == "base":
            edge = self.in_edges
            method = self.predecessors
        else:
            raise ValueError

        trees = self.get_lineage(origin, edge)
        result = trees.copy()
        for top in trees:
            next_tops = set(node for node in method(top))
            result.update(next_tops)
            for node in next_tops:
                result.update(self.get_inherited(node, direction))
        return result

    def get_lineage(self, node, edge):
        return set().union(self.get_parents(node, edge),
                           self.get_children(node, edge))

    def get_children(self, node, edge):
        result = set()
        if edge(node):
            result.add(node)
        for child in self.get_child_nodes(node):
            result.update(self.get_children(child, edge))
        return result

    def get_parents(self, node, edge):
        return set(parent for parent in
                   self.get_parent_nodes(node) if edge(parent))

    def get_parent_nodes(self, node: str):
        split = node.split(".")
        return [".".join(split[:i+1]) for i in range(len(split))]

    def get_child_nodes(self, node: str):
        space = self.nodes[node]["space"]
        return [child.get_fullname(omit_model=True)
                for child in space.spaces.values()]

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


if __name__ == "__main__":
    import modelx as mx
    from modelx.core.base import get_impls
    g = SpaceGraph()

    """
    A---B---C
        |
    +---+
    |
    D
    
    """

    m = mx.new_model()
    m.new_space("A").new_space("B") # .new_space("C")
    g.add_spaces(*get_impls([m.A, m.A.B])) #, m.A.B.C]))
    # g.get_compos("A.B")
    m.new_space("D")
    g.add_spaces(m.D._impl)
    g.add_bases(m.D._impl, m.A.B._impl)
    result = g.get_inherited("A.B")
    sg = g.get_subgraph("A")
    # m.new_space("AA")
    # m.A.add_bases(m.AA)
    m.new_space("AA").new_space("B").new_space("C")
    g.add_bases(m.A._impl, m.AA._impl)
    g.add_spaces(m.AA.B._impl, m.AA.B.C._impl)
    sg = g.get_subgraph("A")