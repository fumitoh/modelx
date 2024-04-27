import itertools
from typing import List
import networkx as nx


def has_parent(node, parent):
    parent_len = len_node(parent)

    if len_node(node) <= parent_len:
        return False
    elif trim_right(node, len_node(node) - parent_len) == parent:
        return True
    else:
        return False


def len_node(node):
    return len(node.split("."))


def trim_left(node, trimmed_len):
    return ".".join(node.split(".")[trimmed_len:])


def trim_right(node, trimmed_len):
    if trimmed_len == 0:
        return node
    else:
        return ".".join(node.split(".")[:-trimmed_len])


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


class InheritanceGraph(nx.DiGraph):

    def ordered_preds(self, node: str):
        return [e[0] for e in self.in_edges(node)]

    def ordered_subs(self, node: str, incdlue_node=False, leaves_only=False):
        nodes = nx.descendants(self, node)
        nodes.add(node)
        subg = self.subgraph(nodes)
        subs = nx.topological_sort(subg)
        
        if not incdlue_node:
            subs = itertools.islice(subs, 1, None)
        
        if leaves_only:
            return iter(s for s in subs if subg.out_degree(s) == 0)
        else:
            return subs

    def get_mro(self, node: str) -> List[str]:
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

    # def to_space(self, node):
    #     return self.nodes[node]["space"]

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
