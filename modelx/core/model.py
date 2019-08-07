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
from modelx.core.space import DynamicSpaceImpl, SpaceView, RefDict
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
        self.spacegraph = SpaceGraph()
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
            "spacegraph",
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
            self.spacegraph.add_space(base)
            self._dynamic_bases[name] = base
            self._dynamic_bases_inverse[bases] = base
            base.add_bases(bases)
            return base


class SpaceGraph(nx.DiGraph):
    def add_space(self, space):
        self.add_node(space)
        self.update_subspaces(space)

    def add_edge(self, basespace, subspace):

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
