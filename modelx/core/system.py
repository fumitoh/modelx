# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

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

import sys
import warnings
import pickle
from collections import deque, namedtuple
from modelx.core.model import ModelImpl
from modelx.core.util import AutoNamer
from modelx.core.errors import DeepReferenceError


class Executive:
    pass


class CallStack(deque):

    def __init__(self, system, max_depth):
        self._succ = None
        self._system = system
        self.max_depth = max_depth
        deque.__init__(self)

    def last(self):
        return self[-1]

    def is_empty(self):
        return len(self) == 0

    def append(self, item):
        if len(self) > self.max_depth:
            raise DeepReferenceError(self.max_depth, self.tracemessage())
        deque.append(self, item)

    def tracemessage(self):
        result = ''
        for i, value in enumerate(self):
            result += "{0}: {1}\n".format(i, value)
        return result


class System:

    def __init__(self, max_depth=1000):
        self.orig_settings = {}
        self.configure_python()
        self.callstack = CallStack(self, max_depth)
        self._modelnamer = AutoNamer("Model")
        self._backupnamer = AutoNamer("_BAK")
        self._currentmodel = None
        self._models = {}
        self.self = None

    def configure_python(self):
        """Configure Python settings for modelx"""
        orig = self.orig_settings

        orig['sys.recursionlimit'] = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)

        if hasattr(sys, 'tracebacklimit'):
            orig['sys.tracebacklimit'] = sys.tracebacklimit
        if False:   # Print traceback for the time being
            sys.tracebacklimit = 0

    def restore_python(self):
        """Restore Python settings to the original states"""
        orig = self.orig_settings
        sys.setrecursionlimit(orig['sys.recursionlimit'])

        if 'sys.tracebacklimit' in orig:
            sys.tracebacklimit = orig['sys.tracebacklimit']
        else:
            if hasattr(sys, 'tracebacklimit'):
                del sys.tracebacklimit
        orig.clear()


    def new_model(self, name=None):

        if name in self.models:
            backupname = self._backupnamer.get_next(self.models, prefix=name)
            if self.rename_model(backupname, name):
                warnings.warn(
                    "Existing model '%s' renamed to '%s'" % (
                        name, backupname))
            else:
                raise ValueError("Failed to create %s", name)

        self._currentmodel = ModelImpl(system=self, name=name)
        self.models[self._currentmodel.name] = self._currentmodel
        return self._currentmodel

    def rename_model(self, new_name, old_name):
        result = self.models[old_name].rename(new_name)
        if result:
            self.models[new_name] = self.models.pop(old_name)
            return True
        else:
            return False

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

    def open_model(self, path):
        with open(path, 'rb') as file:
            model = pickle.load(file)

        if model.name not in self.models:
            model._impl.restore_state(self)
            self.models[model.name] = model._impl
            self._currentmodel = model._impl
        else:
            raise RuntimeError("Model '%s' already exists" % model.name)

        return model

    def close_model(self, model):
        del self.models[model.name]
        if self._currentmodel is model:
            self._currentmodel = None

    def get_object(self, name):
        """Retrieve an object by its absolute name."""

        parts = name.split('.')

        model_name = parts.pop(0)
        return self.models[model_name].get_object('.'.join(parts))



