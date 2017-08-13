from types import MappingProxyType
from textwrap import dedent
import pickle

import networkx as nx

from modelx.core.base import Impl, get_interfaces
from modelx.core.cells import CellPointer
from modelx.core.space import SpaceContainerImpl, SpaceContainer
from modelx.core.util import is_valid_name

class ModelImpl(SpaceContainerImpl):

    def __init__(self, *, system, name):
        SpaceContainerImpl.__init__(self, system, if_class=Model, factory=None)

        self.cellgraph = nx.DiGraph()   # CellGraph(self)
        self.currentspace = None

        if not name:
            self.name = system._modelnamer.get_next(system.models)
        elif is_valid_name(name):
            self.name = name
        else:
            raise ValueError("Invalid name '%s'." % name)

        Impl.__init__(self, Model)

    @property
    def repr_(self):

        format_ = dedent("""\
        name: %s
        spaces(%s): %s""")

        return format_ % (
            self.name,
            len(self.spaces), list(self.spaces.keys()))

    @property
    def model(self):
        return self

    def close(self):
        self.system.close_model(self)

    def save(self, filename):

        with open(filename, 'wb') as file:
            pickle.dump(self, file, protocol=4)

    def get_object(self, name):
        """Retrieve an object by a dotted name relative to the model."""

        parts = name.split('.')
        space = self.spaces[parts.pop(0)]

        if parts:
            return space.get_object('.'.join(parts))
        else:
            return space

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = ['name', 'cellgraph'] + SpaceContainerImpl.state_attrs

    def __getstate__(self):

        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        mapping = {}
        for node in self.cellgraph:
            name = node.obj_.get_fullname(omit_model=True)
            mapping[node] = (name, node.argvalues)

        state['cellgraph'] = nx.relabel_nodes(self.cellgraph, mapping)

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""

        SpaceContainerImpl.restore_state(self, system)

        mapping = {}
        for node in self.cellgraph:
            name, argvalues = node
            cells = self.get_object(name)
            mapping[node] = CellPointer(cells, argvalues)

        self.cellgraph = nx.relabel_nodes(self.cellgraph, mapping)


class Model(SpaceContainer):
    """Container of spaces.

    """

    @property
    def currentspace(self):
        return self._impl.currentspace.interface

    def save(self, filename):
        self._impl.save(filename)

    def close(self):
        self._impl.close()

    def __getitem__(self, space):
        return self._impl.space[space]

    # def __repr__(self):
    #     return self._impl.repr_

    @property
    def spaces(self):
        return MappingProxyType(get_interfaces(self._impl.spaces))

    @property
    def cellgraph(self):
        return self._impl.cellgraph




