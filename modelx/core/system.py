import pickle
from collections import deque
from modelx.core.model import ModelImpl
from modelx.core.util import AutoNamer


class Executive:
    pass


class CallStack(deque):

    def __init__(self, system):
        self._succ = None
        self._system = system
        deque.__init__(self)

    def last(self):
        return self[-1]

    def is_empty(self):
        return len(self) == 0


class System:

    def __init__(self):
        self.callstack = CallStack(self)
        self._modelnamer = AutoNamer("Model")
        self._currentmodel = None
        self._models = {}
        self.self = None

    def create_model(self, name=None):
        self._currentmodel = ModelImpl(system=self, name=name)
        self.models[self._currentmodel.name] = self._currentmodel
        return self._currentmodel

    @property
    def models(self):
        return self._models

    @property
    def currentmodel(self):
        return self._currentmodel

    @currentmodel.setter
    def currentmodel(self, model):
        self._currentmodel = model

    @property
    def currentspace(self):
        return self.currentmodel.currentspace

    def create_cells_from_module(self, module, *, space=None):

        if space is None:
            space = self.currentspace.interface

        return space.create_cells_from_module(module)

    def open_model(self, path):
        with open(path, 'rb') as file:
            self._currentmodel = pickle.load(file)

        self._currentmodel.restore_state(self)

        return self._currentmodel

    def close_model(self, model):
        del self.models[model.name]
        if self._currentmodel is model:
            self._currentmodel = None

    def get_object(self, name):
        """Retrieve an object by its absolute name."""

        parts = name.split('.')

        model_name = parts.pop(0)
        return self.models[model_name].get_object('.'.join(parts))



