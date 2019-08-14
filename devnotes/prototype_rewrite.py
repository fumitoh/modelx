
import networkx as nx


class SpaceGraph(nx.DiGraph):

    def get_inherit_compos(self, recursive, *names):

        result = self.get_compos(*self.get_inherit(*names))
        if not recursive:
            return result
        else:
            expand = self.get_inherit_compos(False, *result)
            if result == expand:
                return result
            else:
                return self.get_inherit_compos(recursive, *expand)

    def get_inherit(self, *names):
        """Returns all ancestors and descendants of spaces"""
        anc = set().union(*[nx.ancestors(self, n) for n in names])
        desc = set().union(*[nx.descendants(self, n) for n in names])
        return set().union(names, anc, desc)

    def get_compos(self, *names):
        """Returns all lineage of spaces"""
        lineage = list(self.trace_lineage(n) for n in names)
        return set().union(*lineage)

    def trace_lineage(self, name):
        c = self.trace_children(name)
        p = self.trace_parents(name)
        return set().union(c, p)

    def trace_children(self, name):
        space = self.nodes[name]["space"]
        result = {name}
        for child in space.spaces:
            child_name = name + "." + child
            result.update(self.trace_children(child_name))
        return result

    def trace_parents(self, name):
        namesplit = name.split(".")[:-1]
        return set(".".join(namesplit[:i+1]) for i in range(len(namesplit)))

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
    m = mx.new_model()
    m.new_space("A").new_space("B").new_space("C")
    g.add_spaces(*get_impls([m.A, m.A.B, m.A.B.C]))
    g.get_compos("A.B")
    m.new_space("D")
    g.add_spaces(m.D._impl)
    g.add_bases(m.D._impl, m.A.B._impl)
    g.get_inherit_compos(True, "D")