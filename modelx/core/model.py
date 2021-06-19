# Copyright (c) 2017-2021 Fumito Hamamura <fumito.ham@gmail.com>

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
import zipfile

import networkx as nx

from modelx.core.base import (
    add_stateattrs,
    Interface,
    Impl,
    get_interfaces,
    ImplChainMap,
    BaseView,
    Derivable
)
from modelx.core.reference import ReferenceImpl, ReferenceProxy
from modelx.core.cells import CellsImpl, UserCellsImpl
from modelx.core.node import OBJ, KEY, get_node, node_has_key
from modelx.core.spacecontainer import (
    BaseSpaceContainerImpl,
    EditableSpaceContainerImpl,
    EditableSpaceContainer,
)
from modelx.core.space import (
    UserSpaceImpl,
    SpaceDict,
    SpaceView,
    RefDict
)
from modelx.core.formula import NULL_FORMULA
from modelx.core.util import is_valid_name, AutoNamer
from modelx.io.baseio import DataClientReferenceManager

_nxver = tuple(int(n) for n in nx.__version__.split(".")[:2])


class TraceGraph(nx.DiGraph):
    """Directed Graph of ObjectArgs"""

    def remove_with_descs(self, source):
        """Remove all descendants of(reachable from) `source`.

        Args:
            source: Node descendants
        Returns:
            set: The removed nodes.
        """
        if not self.has_node(source):
            return set()
        desc = nx.descendants(self, source)
        desc.add(source)
        self.remove_nodes_from(desc)
        return desc

    def clear_obj(self, obj):
        """"Remove all nodes with `obj` and their descendants."""
        obj_nodes = self.get_nodes_with(obj)
        removed = set()
        for node in obj_nodes:
            if self.has_node(node):
                removed.update(self.remove_with_descs(node))
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

    def get_startnodes_from(self, node):
        if node in self:
            return [n for n in nx.descendants(self, node)
                    if self.out_degree(n) == 0]
        else:
            return []

    def fresh_copy(self):
        """Overriding Graph.fresh_copy"""
        return TraceGraph()

    def add_path(self, nodes, **attr):
        """(Not used anymore) In replacement for Deprecated add_path method"""
        if nx.__version__[0] == "1":
            return super().add_path(nodes, **attr)
        else:
            return nx.add_path(self, nodes, **attr)


class ReferenceGraph(nx.DiGraph):

    def remove_with_descs(self, ref):
        if ref not in self:
            return set()
        desc = nx.descendants(self, ref)
        self.remove_nodes_from((ref, *desc))
        return desc     # Not including ref


class Model(EditableSpaceContainer):
    """Top-level container in modelx object hierarchy.

    Model instances are the top-level objects and directly contain
    :py:class:`~modelx.core.space.UserSpace` objects, which in turn
    contain other spaces or
    :py:class:`~modelx.core.cells.Cells` objects.

    A model can be created by
    :py:func:`~modelx.new_model` API function.
    """

    __slots__ = ()

    def rename(self, name, rename_old=False):
        """Rename the model itself"""
        self._impl.system.rename_model(
            new_name=name, old_name=self.name, rename_old=rename_old)

    def clear_all(self):
        """Clears :class:`~modelx.core.cells.Cells` and :class:`~modelx.core.space.ItemSpace`.

        Clears both the input values and the calculated values of
        all the :class:`~modelx.core.cells.Cells` in the model and
        delete all the :class:`~modelx.core.space.ItemSpace` objects
        in the model.

        .. seealso::

            :meth:`UserSpace.clear_all<modelx.core.space.UserSpace.clear_all>`

        .. versionadded:: 0.16.0
        """
        for space in self._impl.spaces.values():
            space.clear_all_cells(
                clear_input=True,
                recursive=True,
                del_items=True
            )

    def save(self, filepath, datapath=None):
        """Back up the model to a file.

        .. deprecated:: 0.9.0 Use :meth:`backup` instead.

        Alias for :meth:`backup`. See :meth:`backup` for details.
        """
        self._impl.system.backup_model(self, filepath, datapath)

    def backup(self, filepath, datapath=None):
        """Back up the model to a file.

        Backup the model to a single binary file. This method internally
        utilizes Python's standard library,
        `pickle <https://docs.python.org/3/library/pickle.html>`_.
        This method should only be used for saving the model temporarily,
        as the saved model may not be restored by different
        versions of modelx, or when the Python environment changes,
        for example, due to package upgrade.
        Saving the model by :meth:`write` method is more robust.

        .. versionchanged:: 0.9.0 ``datapath`` parameter is added.
        .. versionadded:: 0.7.0

        Args:
            filepath(str): file path
            datapath(optional): Path to a folder to store internal files.

        See Also:
            :meth:`write`
            :func:`~modelx.restore_model`
        """
        self._impl.system.backup_model(self, filepath, datapath)

    def close(self):
        """Close the model."""
        self._impl.close()

    @Interface.doc.setter
    def doc(self, value):
        self._impl.doc = value

    def write(self, model_path, backup=True, log_input=False):
        """Write model to files.

        This method performs the :py:func:`~modelx.write_model`
        on self. See :py:func:`~modelx.write_model` section for the details.

        .. versionchanged:: 0.8.0
        .. versionadded:: 0.0.22

        Args:
            model_path(str): Folder(directory) path where the model is saved.
            backup(bool, optional): Whether to backup an existing file with
                the same name if it already exists. Defaults to ``True``.
            log_input(bool, optional): If ``True``, input values in Cells are
                output to *_input_log.txt* under ``model_path``. Defaults
                to ``False``.
        """
        from modelx.serialize import write_model
        write_model(self._impl.system, self, model_path, is_zip=False,
                    backup=backup, log_input=log_input)

    def zip(self, model_path, backup=True, log_input=False,
            compression=zipfile.ZIP_DEFLATED, compresslevel=None):
        """Archive model to a zip file.

        This method performs the :py:func:`~modelx.zip_model`
        on self. See :py:func:`~modelx.zip_model` section for the details.

        .. versionchanged:: 0.9.0
            ``compression`` and ``compresslevel`` parameters are added.

        .. versionadded:: 0.8.0

        Args:
            model_path(str): Folder(directory) path where the model is saved.
            backup(bool, optional): Whether to backup an existing file with
                the same name if it already exists. Defaults to ``True``.
            log_input(bool, optional): If ``True``, input values in Cells are
                output to *_input_log.txt* under ``model_path``. Defaults
                to ``False``.
            compression(optional): Identifier of the ZIP compression method
                to use. This method uses `zipfile.ZipFile`_ class internally
                and ``compression`` and ``compresslevel`` arguments are
                passed to `zipfile.ZipFile`_ constructor.
                See `zipfile.ZipFile`_ manual page for available identifiers.
                Defaults to `zipfile.ZIP_DEFLATED`_.
            compresslevel(optional):
                Integer identifier to indicate the compression level to use.
                If not specified, the default compression level is used.
                See `zipfile.ZipFile`_ explanation on the Python Standard
                Library site for available integer identifiers for
                each compression method.
                For Python 3.6, this parameter is ignored.

        .. _zipfile.ZipFile:
           https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile

        .. _zipfile.ZIP_DEFLATED:
           https://docs.python.org/3/library/zipfile.html#zipfile.ZIP_DEFLATED

        """
        from modelx.serialize import write_model
        write_model(self._impl.system, self, model_path, is_zip=True,
                    backup=backup, log_input=log_input,
                    compression=compression, compresslevel=compresslevel)

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __getattr__(self, name):
        return self._impl.get_attr(name)

    def __delattr__(self, name):
        self._impl.del_attr(name)

    def __dir__(self):
        return self._impl.namespace.interfaces

    @property
    def dataclients(self):
        """List of :class:`~modelx.io.baseio.BaseDataClient` objects

        Returns a list of all objects of BaseDataClient subclasses
        defined in this Model.

        :class:`~modelx.io.excelio.ExcelRange` and
        :class:`~modelx.io.pandasio.PandasData`
        are subclasses of :class:`~modelx.io.baseio.BaseDataClient`.

        :class:`~modelx.io.excelio.ExcelRange`
        objects are created either by
        :meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>`
        or
        :meth:`UserSpace.new_excel_range<modelx.core.space.UserSpace.new_excel_range>`
        method.
        :class:`~modelx.io.pandasio.PandasData` objects are
        created either by
        :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`
        or
        :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
        method.

        See Also:
            * :class:`~modelx.io.excelio.ExcelRange`
            * :class:`~modelx.io.pandasio.PandasData`
            * :meth:`UserSpace.new_excel_range<modelx.core.space.UserSpace.new_excel_range>`
            * :meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>`
            * :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
            * :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`

        .. versionadded:: 0.9.0

        """
        return list(self._impl.datarefmgr.clients)

    @property
    def tracegraph(self):
        """A directed graph of cells."""
        return self._impl.tracegraph

    @property
    def refs(self):
        """Return a mapping of global references."""
        return self._impl.global_refs.interfaces

    def _get_from_name(self, name):
        """Get object by named id"""
        return self._impl.get_impl_from_name(name).interface

    def _get_object(self, name, as_proxy=False):
        parts = name.split(".")
        attr = parts.pop(0)

        if as_proxy and attr in self.refs:
            return ReferenceProxy(self._impl.global_refs[attr])
        else:
            return super()._get_object(name, as_proxy)


class TraceManager:

    __cls_stateattrs = [
            "tracegraph",
            "refgraph"
    ]

    def __init__(self):
        self.tracegraph = TraceGraph()
        self.refgraph = ReferenceGraph()

    def clear_with_descs(self, node):
        """Clear values and nodes calculated from `source`."""
        removed = self.tracegraph.remove_with_descs(node)
        self.refgraph.remove_nodes_from(removed)
        for node in removed:
            node[OBJ].on_clear_trace(node[KEY])

    def clear_obj(self, obj):
        """Clear values and nodes of `obj` and their dependants."""
        removed = self.tracegraph.clear_obj(obj)
        self.refgraph.remove_nodes_from(removed)
        for node in removed:
            node[OBJ].on_clear_trace(node[KEY])

    def clear_attr_referrers(self, ref):
        removed = self.refgraph.remove_with_descs(ref)
        for node in removed:
            descs = self.tracegraph.remove_with_descs(node)
            for desc in descs:
                desc[OBJ].on_clear_trace(desc[KEY])


@add_stateattrs
class ModelImpl(
    TraceManager,
    EditableSpaceContainerImpl,
    Impl):

    interface_cls = Model
    __cls_stateattrs = [
            "_namespace",
            "_global_refs",
            "_dynamic_bases",
            "_dynamic_bases_inverse",
            "_dynamic_base_namer",
            "currentspace",
            "datarefmgr"
    ]

    def __init__(self, *, system, name):

        if not name:
            name = system._modelnamer.get_next(system.models)
        elif not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        Impl.__init__(self, system=system, parent=None, name=name)
        EditableSpaceContainerImpl.__init__(self)
        TraceManager.__init__(self)

        self.spacemgr = SpaceManager(self)
        self.currentspace = None
        self._global_refs = RefDict(self)
        self._global_refs.set_item("__builtins__", builtins)
        self._named_spaces = SpaceDict(self)
        self._dynamic_bases = SpaceDict(self)
        self._all_spaces = ImplChainMap(
            self, SpaceView, [self._named_spaces, self._dynamic_bases]
        )
        self._dynamic_bases_inverse = {}
        self._dynamic_base_namer = AutoNamer("__Space")
        self._namespace = ImplChainMap(
            self, BaseView, [self._named_spaces, self._global_refs]
        )
        self.allow_none = False
        self.lazy_evals = self._namespace
        self.datarefmgr = DataClientReferenceManager()

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

    def repr_self(self, add_params=True):
        return self.name

    def repr_parent(self):
        return ""

    @Impl.doc.setter
    def doc(self, value):
        self._doc = value

    @property
    def global_refs(self):
        return self._global_refs.fresh

    @property
    def namespace(self):
        return self._namespace.fresh

    def close(self):
        self.system.close_model(self)

    def get_impl_from_name(self, name):
        """Retrieve an object by a dotted name relative to the model."""
        parts = name.split(".")
        space = self.spaces[parts.pop(0)]
        if parts:
            return space.get_impl_from_namelist(parts)
        else:
            return space

    # ----------------------------------------------------------------------
    # Serialization by pickle

    def __getstate__(self):

        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.stateattrs
        }

        graphs = {
            name: graph
            for name, graph in state.items()
            if isinstance(graph, TraceGraph)
        }

        for gname, graph in graphs.items():
            mapping = {}
            for node in graph:
                name = node[OBJ].namedid
                if node_has_key(node):
                    mapping[node] = (name, node[KEY])
                else:
                    mapping[node] = name
            state[gname] = nx.relabel_nodes(graph, mapping)

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, datapath=None):
        """Called after unpickling to restore some attributes manually."""
        BaseSpaceContainerImpl.restore_state(self)
        mapping = {}
        for node in self.tracegraph:
            if isinstance(node, tuple):
                name, key = node
            else:
                name, key = node, None
            cells = self.get_impl_from_name(name)
            mapping[node] = get_node(cells, key, None)

        self.tracegraph = nx.relabel_nodes(self.tracegraph, mapping)

    @property
    def updater(self):
        return SpaceUpdater(self.spacemgr)

    def del_ref(self, name):
        ref = self.global_refs[name]
        self.model.clear_attr_referrers(ref)
        ref.on_delete()
        self.global_refs.delete_item(name)

    def change_ref(self, name, value):
        """Not Used"""
        assert False
        ref = self.global_refs[name]
        self.model.clear_attr_referrers(ref)
        ref.change_value(value, False, refmode="absolute",
                         is_relative=False)

    def get_attr(self, name):
        if name in self.spaces:
            return self.spaces[name].interface
        elif name in self.global_refs:
            return get_interfaces(self.global_refs[name])
        else:
            raise AttributeError(
                "Model '{0}' does not have '{1}'".format(self.name, name)
            )

    def set_attr(self, name, value, refmode=None):
        if name in self.spaces:
            raise KeyError("Space named '%s' already exist" % self.name)
        elif name in self.global_refs:
            self.del_ref(name)

        ref = ReferenceImpl.get_class(value)(
            self, name, value, container=self._global_refs,
            set_item=False)
        self._global_refs.add_item(name, ref)

    def del_attr(self, name):

        if name in self.named_spaces:
            self.updater.del_defined_space(self.named_spaces[name])
        elif name in self.global_refs:
            self.del_ref(name)
        else:
            raise KeyError("Name '%s' not defined" % name)

    # ----------------------------------------------------------------------
    # Dynamic base manager

    def get_dynamic_base(self, bases: tuple):
        """Create of get a base space for a tuple of bases"""

        try:
            return self._dynamic_bases_inverse[bases]
        except KeyError:
            name = self._dynamic_base_namer.get_next(self._dynamic_bases)
            base = self.updater.new_space(
                self,
                name=name,
                bases=bases,
                prefix="__",
                container=self._dynamic_bases)
            self._dynamic_bases_inverse[bases] = base
            return base


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
    """New implementation of inheritance graph

    Node state:
        copied: Copied into sub graph
        defined: Node created but space yet to create
        created: Space created
        updated: Existing space updated -- Not Used
        unchanged: Existing space confirmed unchanged -- Not Used
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

    def get_derived_subs(self, node):
        """Get node and all subs that can be reached only by derived edges"""
        que = [node]
        accum = [node]
        while que:
            n = que.pop(0)
            for e in self.out_edges(n):
                if self.edges[e]["mode"] == "derived":
                    t, h = e
                    que.append(h)
                    accum.append(h)
        return accum

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
        for e in self._visit_edges(*start):
            g._derive_tree(e, on_edge, on_remove)
        return g

    def get_absbases(self):
        """Get edges from absolute base nodes"""
        result = list(self.edges)
        for e in self.edges:
            tail, head = e
            if self.get_endpoints(
                    self.visit_treenodes(
                        self._get_topnode(tail)), edge="in"):
                result.remove(e)

        return result

    def _visit_edges(self, *start):
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
            for n in self.visit_treenodes(self._get_topnode(head, edge="out")):
                if self._is_endpoint(n, edge="out"):
                    edges.extend(oe for oe in self.out_edges(n)
                                 if oe not in visited)
            que += edges

    def check_cyclic(self, start, node):
        """True if no cyclic"""

        succs = self._get_otherends(
            self.visit_treenodes(self._get_topnode(node, edge="out")),
            edge="out")

        for n in succs:
            if self._is_linealrel(start, n):
                return False
            else:
                if not self.check_cyclic(start, n):
                    return False

        return True

    def _derive_tree(self, edge, on_edge=None, on_remove=None):
        """Create derived node under the head of edge from the tail of edge"""
        tail, head = edge
        tlen, hlen = len_node(tail), len_node(head)

        if tail:
            bases = list(trim_left(n, tlen)
                    for n in self.visit_treenodes(tail, include_self=False))
        else:
            bases = []

        subs = list(trim_left(n, hlen)
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
                    level = len_node(t) - tlen
                    self.add_edge(
                        t, h,
                        mode="derived",
                        level=level,
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

    def subgraph_from_nodes(self, nodes):
        """Get sub graph with nodes reachable form ``node``"""
        result = set()
        for node in nodes:
            if node in self.nodes:
                nodeset, _ = self._get_nodeset(node, set())
                result.update(nodeset)

        subg = self.copy_as_spacegraph(self.subgraph(result))

        for n in subg.nodes:
            subg.nodes[n]["state"] = "copied"

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

    def _get_nodeset(self, node, processed):
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
        top = self._get_topnode(node)
        tree = set(self.visit_treenodes(top))
        ends = self.get_endpoints(tree)

        neighbors = self._get_otherends(ends) - processed
        processed.update(ends)
        result = tree.copy()
        for n in neighbors:
            ret_res, _ = self._get_nodeset(n, processed)
            result.update(ret_res)

        return result, processed

    def get_parent_nodes(self, node: str, include_self=True):
        """Get ancestors of ``node`` in order"""

        maxlen = len_node(node) if include_self else len_node(node) - 1
        result = []

        for i in range(maxlen, 0, -1):
            n = trim_right(node, len_node(node)-i)
            if n in self.nodes:
                result.insert(0, n)
            else:
                break
        return result

    def _get_topnode(self, node, edge="any"):
        """Get the highest node that is an ancestor of the ``node``.
        If none exits, return ``node``.
        """
        parents = self.get_parent_nodes(node)
        return next((n for n in parents if self._is_endpoint(n, edge)), node)

    def visit_treenodes_levels(self, node, include_self=True):
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

    def visit_treenodes(self, node, include_self=True):
        for _, n in self.visit_treenodes_levels(
                node,include_self=include_self):
            yield n

    def get_endpoints(self, nodes, edge="any"):
        return set(n for n in nodes if self._is_endpoint(n, edge))

    def _get_otherends(self, nodes, edge="any"):
        otherends = [set(self._get_neighbors(n, edge)) for n in nodes]
        return set().union(*otherends)

    def _get_neighbors(self, node, edge):
        if edge == "in":
            return self.predecessors(node)
        elif edge == "out":
            return self.successors(node)
        else:
            return itertools.chain(
                self.predecessors(node), self.successors(node))

    def _is_endpoint(self, node, edge="any"):
        if edge == "out":
            return bool(self.out_edges(node))
        elif edge == "in":
            return bool(self.in_edges(node))
        elif edge == "any":
            return bool(self.out_edges(node) or
                        self.in_edges(node))
        else:
            raise ValueError

    def _has_child(self, node, child):
        node_len = len_node(node)
        if node_len >= len_node(child):
            return False
        elif node == trim_right(child, len_node(child) - node_len):
            return True
        else:
            return False

    def _is_linealrel(self, node, other):
        return (
                node == other
                or self._has_child(node, other)
                or has_parent(node, other)
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
        self._inheritance = SpaceGraph()
        self._graph = SpaceGraph()

    def _can_add(self, parent, name, klass, overwrite=True):
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

        sub = self._find_name_in_subs(parent, name)   # start from parent
        if sub is None:
            return True
        elif isinstance(sub, klass) and overwrite:
            return True
        else:
            return False

    def _find_name_in_subs(self, parent, name):
        for subspace in self._get_subs(parent, skip_self=False):
            if name in subspace.namespace:
                return subspace._namespace.fresh[name]
        return None

    def _set_defined(self, node):

        for graph in (self._inheritance, self._graph):
            for parent in graph.get_parent_nodes(node):
                graph.nodes[parent]["mode"] = "defined"

    def _get_space_bases(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        nodes = self._graph.get_mro(space.namedid)[idx:]
        return [self._graph.to_space(n) for n in nodes]

    def get_deriv_bases(self, deriv: Derivable, defined_only=False,
                        graph: SpaceGraph=None):
        if graph is None:
            graph = self._graph

        if isinstance(deriv, UserSpaceImpl):    # Not Dynamic spaces
            return self._get_space_bases(deriv, graph)

        pnode = deriv.parent.namedid

        bases = []
        for bspace in graph.get_mro(pnode)[1:]:
            base_members = deriv._get_members(graph.to_space(bspace))
            if deriv.name in base_members:
                b = base_members[deriv.name]
                if not defined_only or b.is_defined:
                    bases.append(b)

        return bases

    def get_direct_bases(self, space):
        node = space.namedid
        preds = self._inheritance.ordered_preds(node)
        return [self._inheritance.to_space(n) for n in preds]

    def update_subs(self, space, skip_self=True):

        for attr in ("cells", "self_refs"):
            for s in self._get_subs(space, skip_self):
                b = self._get_space_bases(s, self._graph)
                s.inherit(self, b, attr)

    def _get_subs(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        return [
            self._graph.to_space(desc) for desc in list(
                self._graph.ordered_subs(space.namedid))[idx:]
        ]

    def get_relative_interface(self, parent, base):

        basespace = base.parent.namedid
        basevalue = base.interface._impl.namedid

        subimpl = self._graph.get_relative(
            parent.namedid, basespace, basevalue)

        if subimpl:
            return True, self.model.get_impl_from_name(subimpl).interface
        else:
            return False, base.interface


class SpaceManager(SharedSpaceOperations):

    def rename_space(self, space, name):

        # Check name does not exit already
        parent = space.parent
        if not self._can_add(
                parent, name, UserSpaceImpl, overwrite=False):
            raise ValueError("Cannot rename '%s' to '%s'" % (space.name, name))

        # Check space is not derived or overwritten
        for e in self._graph.in_edges(space.namedid):
            if self._graph.edges[e]["mode"] == "derived":
                t, h = e
                raise ValueError(
                    "'%s' has derived base '%s'" % (h, t))

        # Derived/Overwritten spaces are renamed
        subspaces = list(
            self._graph.to_space(n) for n in self._graph.get_derived_subs(
                space.namedid)
        )

        # Create name mapping
        mapping = {}
        for s in subspaces:
            old_id = tuple(s.namedid.split("."))
            new_id = old_id[:-1] + (name,)
            for node in self._graph.visit_treenodes(
                    s.namedid, include_self=True):

                old_child = tuple(node.split("."))
                assert old_id == old_child[:len(old_id)]
                mapping[node] = ".".join(new_id + old_child[len(new_id):])

        for s in subspaces:

            if not s.parent.is_model():
                # Clear parent's dynsub, not s's
                s.parent.clear_subs_rootitems()

            # Call on_rename callbacks
            s.on_rename(name)

        # Rename nodes
        nx.relabel_nodes(self._inheritance, mapping, copy=False)
        nx.relabel_nodes(self._graph, mapping, copy=False)

    def del_cells(self, space, name):
        cells = space.cells[name]
        if cells.is_derived:
            raise ValueError("cannot delete derived")
        space.on_del_cells(name)
        self.update_subs(space, skip_self=False)

    def del_ref(self, space, name):
        space.on_del_ref(name)
        self.update_subs(space, skip_self=False)

    def new_cells(self, space, name=None, formula=None, data=None,
                  is_derived=False, source=None, overwrite=True):

        # FIX: Creating a Cells of the same name in ``space``

        if not self._can_add(space, name, CellsImpl, overwrite=overwrite):
            raise ValueError("Cannot create cells '%s'" % name)

        self._set_defined(space.namedid)
        space.set_defined()

        cells = UserCellsImpl(
            space=space, name=name, formula=formula,
            data=data,
            source=source, is_derived=is_derived)
        space.clear_subs_rootitems()

        for subspace in self._get_subs(space):
            if name in subspace.cells:
                break
            else:
                subspace.clear_subs_rootitems()
                UserCellsImpl(
                    space=subspace,
                    base=cells, is_derived=True)

        return cells

    def copy_cells(self, space: UserSpaceImpl,
                   source: UserCellsImpl, name=None):
        """``space`` can be of another Model"""

        if space.model is not self.model:
            return space.spacemgr.copy_cells(space, source, name)

        if name is None:
            name = source.name

        data = {k: v for k, v in source.data.items() if k in source.input_keys}
        return self.new_cells(space, name=name, formula=source.formula,
                       data=data, is_derived=False, overwrite=False)

    def rename_cells(self, cells, name):
        """Renames the Cells name"""
        if not is_valid_name(name):
            raise ValueError("name '%s' is invalid" % name)

        if not self._can_add(cells.parent, name, CellsImpl, overwrite=True):
            raise ValueError("cannot create cells '%s'" % name)

        if cells.bases:
            raise ValueError("'%s' is a sub Cells of '%s'" % (
                cells.get_repr(fullname=True, add_params=False),
                cells.bases[0].get_repr(fullname=True, add_params=False)))

        old_name = cells.name

        for space in self._get_subs(cells.parent, skip_self=False):
            space.clear_subs_rootitems()
            space.cells[old_name].on_rename(name)

    def change_cells_formula(self, cells, func):
        for space in self._get_subs(cells.parent, skip_self=False):
            c = space.cells[cells.name]
            if c is not cells and c.is_defined:
                break   # Stop when sub cells is defined
            space.clear_subs_rootitems()
            space.cells[cells.name].on_change_formula(func)

    def del_cells_formula(self, cells):
        self.change_cells_formula(cells, NULL_FORMULA)

    def _check_subs_relrefs(self, space, name, value, refmode):

        # Check if relative ref is possible when refmode is 'relative'
        if isinstance(value, Interface) and refmode == "relative":
            basevalue = value._impl.namedid
            for subspace in self._get_subs(space):
                if name in subspace.self_refs:
                    break
                else:
                    subvalue = self._graph.get_relative(
                        subspace.namedid, space.namedid,
                        basevalue)
                    if not subvalue:
                        raise ValueError(
                            "Cannot create relative reference for '%s' in '%s'"
                            % (basevalue, subspace.namedid)
                        )

    def new_ref(self, space, name, value, refmode):

        other = self._find_name_in_subs(space, name)
        if other is not None:
            if not isinstance(other, ReferenceImpl):
                raise ValueError("Cannot create reference '%s'" % name)
            elif other not in self.model.global_refs.values():
                raise ValueError("Cannot create reference '%s'" % name)

        self._check_subs_relrefs(space, name, value, refmode)
        self._set_defined(space.namedid)
        space.set_defined()
        space.on_create_ref(name, value, is_derived=False,
                            refmode=refmode)

        for subspace in self._get_subs(space):
            is_relative = False
            if name in subspace.self_refs:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = self.get_relative_interface(
                        subspace, space.self_refs[name])
            ref = subspace.on_create_ref(name, value, is_derived=True,
                                   refmode=refmode)
            ref.is_relative = is_relative

    def change_ref(self, space, name, value, refmode):
        """Assigns a new value to an existing name."""

        self._check_subs_relrefs(space, name, value, refmode)
        self._set_defined(space.namedid)
        space.set_defined()

        is_relative = False if refmode == "absolute" else True

        space.on_change_ref(name, value, is_derived=False, refmode=refmode,
                            is_relative=is_relative)

        for subspace in self._get_subs(space):
            is_relative = False
            subref = subspace.self_refs[name]
            if subref.is_defined:
                break
            elif subref.defined_bases[0] is not space.self_refs[name]:
                break
            if isinstance(value, Interface) and value._is_valid():
                if (refmode == "auto"
                        or refmode == "relative"):
                    is_relative, value = self.get_relative_interface(
                        subspace, space.self_refs[name])
            ref = subspace.on_change_ref(name, value,
                                         is_derived=True, refmode=refmode,
                                         is_relative=is_relative)
            ref.is_relative = is_relative

    def _check_sanity(self):

        # both graph must have the same nodes
        assert self._inheritance.nodes == self._graph.nodes

        nodes = set(self._graph.nodes)
        spaces = dict(self.model._all_spaces)

        # consistency between spaces and nodes
        while spaces:
            k, v = spaces.popitem()
            assert k == v.name
            assert v.namedid in nodes
            assert v is self._graph.nodes[v.namedid]["space"]
            nodes.remove(v.namedid)
            spaces.update(v.named_spaces)

        assert not nodes # Check all nodes are reached


class SpaceUpdater(SharedSpaceOperations):

    def __init__(self, manager):
        self.manager = manager
        super().__init__(manager.model)

        self.oldsubg_inherit = None
        self.oldsubg = None

        self._instructions = InstructionList()

    def _init_subgraphs(self, spaces, copy_derived=False):

        nodes = [s.namedid for s in spaces]

        self.oldsubg_inherit = self.manager._inheritance.subgraph_from_nodes(
            nodes)
        self.oldsubg = self.oldsubg_inherit.get_derived_graph()
        self._inheritance = self.oldsubg_inherit.copy_as_spacegraph(
            self.oldsubg_inherit)

        if copy_derived:
            self._graph = self.oldsubg.copy_as_spacegraph(self.oldsubg)

    def _update_manager(self):

        self._inheritance.remove_nodes_from(
            set(n for n in self._inheritance if n not in self._graph))

        # Add derived spaces back to self._inheritance
        created = self._graph.subgraph_from_state("created")
        if created:
            created.remove_edges_from(list(created.edges))
        self._inheritance = nx.compose(self._inheritance, created)

        self.manager._inheritance = self.manager._inheritance.get_updated(
            self._inheritance,
            nodeset=self.oldsubg_inherit,
            keep_self=False
        )
        self.manager._graph = self.manager._graph.get_updated(
            self._graph,
            nodeset=self.oldsubg,
            keep_self=False
        )

    def _new_derived_space(self, node):

        parent_node, name = split_node(node)

        if parent_node:
            parent = self._graph.to_space(parent_node)
        else:
            parent =self.model

        space = UserSpaceImpl(
            parent,
            name,
            container=parent._named_spaces,
            is_derived=True
            # formula=formula,
            # refs=refs,
            # source=source,
            # doc=doc
        )
        self._graph.nodes[node]["space"] = space
        self._graph.nodes[node]["state"] = "created"

    def _update_derived_space(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        space.inherit(self, bases, 'cells')
        self._instructions.append(
            Instruction(self._update_derived_refs, (node,))
        )

    def _update_derived_refs(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        space.inherit(self, bases, 'self_refs')

    def _derive_hook(self, graph, edge):
        """Callback passed as on_edge parameter"""
        _, head = edge
        mode = graph.nodes[head]["mode"]
        state = graph.nodes[head]["state"]

        if mode == "derived" and state == "defined":
            self._instructions.append(
                Instruction(self._new_derived_space, (head,))
            )

        self._instructions.append(
            Instruction(self._update_derived_space, (head,))
        )

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
            is_derived=False,
            prefix="",
            doc=None,
            container=None
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

        node = name if parent.is_model() else parent.namedid + "." + name

        spaces = [s for s in bases]
        if not parent.is_model():
            spaces.insert(0, parent)

        self._init_subgraphs(spaces, copy_derived=True)

        for g in (self._inheritance, self._graph):

            g.add_node(
                node, mode="defined", state="defined")

            for b in bases:
                base = b.namedid
                g.add_edge(
                    base, node,
                    mode="defined",
                    level=0,
                    index=g.max_index(node)
                )

            for pnode in g.get_parent_nodes(node):
                g.nodes[pnode]["mode"] = "defined"

        if not nx.is_directed_acyclic_graph(self._inheritance):
            raise ValueError("cyclic inheritance")

        if not self._inheritance.check_cyclic(node, node):
            raise ValueError("cyclic inheritance through composition")

        self._inheritance.get_mro(node)  # Check if MRO is possible

        start = [
            (tail, node) for tail in self._inheritance.ordered_preds(node)]

        self._graph = self._graph.get_derived_graph(
            on_edge=self._derive_hook, start=start)

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(self._graph, node):
            self._graph.get_mro(n)

        if not parent.is_model():
            parent.set_defined()

        if container is None:
            container = parent._named_spaces

        space = UserSpaceImpl(
            parent,
            name,
            container,
            is_derived,
            formula=formula,
            refs=refs,
            source=source,
            doc=doc
        )
        self._graph.nodes[node]["space"] = space
        self._graph.nodes[node]["state"] = "created"

        self._instructions.execute()
        self._update_manager()

        return space

    def add_bases(self, space, bases):
        """Add bases to space in graph
        """
        node = space.namedid
        basenodes = [base.namedid for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._inheritance:
                raise ValueError("Space '%s' not found" % base)

        self._init_subgraphs([space] + bases)

        for b in basenodes:
            self._inheritance.add_edge(
                b,
                node,
                mode="defined",
                level=0,
                index=self._inheritance.max_index(node)
            )

        for p in self._inheritance.get_parent_nodes(node):
            self._inheritance.nodes[p]["mode"] = "defined"

        if not nx.is_directed_acyclic_graph(self._inheritance):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(
                self._inheritance, node)):
            self._inheritance.get_mro(n)

        self._graph = self._inheritance.get_derived_graph(
            on_edge=self._derive_hook)

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

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

        self._instructions.execute()
        self._update_manager()

    def remove_bases(self, space, bases):

        node = space.namedid
        basenodes = [base.namedid for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._inheritance:
                raise ValueError("Space '%s' not found" % base)

        self._init_subgraphs([space] + bases)

        for b in basenodes:
            self._inheritance.remove_edge(b, node)

        if not nx.is_directed_acyclic_graph(self._inheritance):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(
                self._inheritance, node)):
            self._inheritance.get_mro(n)

        start = self._inheritance.get_absbases()
        start.insert(0, ("", node))
        self._graph = self._inheritance.get_derived_graph(
            on_edge=self._derive_hook,
            on_remove=self._remove_hook,
            start=start
        )

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

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

        self._instructions.execute()
        self._update_manager()

    def del_defined_space(self, space):

        if space.is_derived:
            raise ValueError(
                "%s has derived spaces" % repr(space.interface)
            )

        node = space.namedid

        if node not in self.manager._inheritance:
            raise ValueError("Space '%s' not found" % node)
        elif self.manager._inheritance.nodes[node]["mode"] == "derived":
            raise ValueError("cannot delete derived space")

        self._init_subgraphs([space])
        succs = list(self._inheritance.successors(node))

        # Remove node and its child tree
        nodes_removed = list()
        for child in self._inheritance.visit_treenodes(node):
            nodes_removed.append(child)
            self._remove_hook(self._inheritance, child)

        self._inheritance.remove_nodes_from(nodes_removed)
        self._graph = self._inheritance.get_derived_graph(
            on_edge=self._derive_hook,
            on_remove=self._remove_hook,
            start=[("", node) for node in succs]
        )
        for n in set(self._inheritance.nodes):
            if n not in self._graph:
                self._inheritance.remove_node(n)

        self._instructions.execute()
        self._update_manager()

        if space is self.model.currentspace:
            self.model.currentspace = None

    def copy_space(
            self,
            parent: EditableSpaceContainerImpl,
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
            parent, name, EditableSpaceContainerImpl, overwrite=False):
            return self._copy_space_recursively(
                parent, source, name, defined_only
            )
        else:
            raise ValueError("Cannot create space '%s'" % name)

    def _copy_space_recursively(
            self, parent, source, name, defined_only):

        if source.is_derived:
            return

        space = self.new_space(
            parent,
            name=name,
            bases=None,
            formula=source.formula,
            refs={k: v.interface for k, v in source.self_refs.items()},
            source=source.source,
            is_derived=False,
            prefix="",
            doc=source.doc,
            container=None
        )

        for cells in source.cells.values():
            if cells.is_defined:
                self.manager.copy_cells(space, cells)

        for child in source.named_spaces.values():
            self._copy_space_recursively(
                space, child, child.name, defined_only)

        return space
