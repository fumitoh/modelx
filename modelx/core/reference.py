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

import sys
import builtins
import importlib
from types import ModuleType

from modelx.core.base import Derivable, Impl


# For backward compatibility with -v0.0.23
class _DummyBuiltins:
    pass


class _BasePickler:

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = self.convert(value)

    @classmethod
    def condition(cls, value):
        raise NotImplementedError

    def convert(self, value):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError


class _ModulePickler(_BasePickler):

    __slots__ = ()

    @classmethod
    def condition(cls, value):
        return isinstance(value, ModuleType)

    def convert(self, value):
        for k, v in sys.modules.items():
            if value is v:
                return k
        raise ValueError("must not happen")

    def restore(self):
        return importlib.import_module(self.value)


class ReferenceImpl(Derivable, Impl):

    state_attrs = Impl.state_attrs + Derivable.state_attrs
    assert len(state_attrs) == len(set(state_attrs))
    picklers = []    # List of _BasePickler sub classes

    def __init__(self, parent, name, value, container, is_derived=False):
        Impl.__init__(self, parent.system, interface=value)
        Derivable.__init__(self)

        self.parent = parent
        self.model = parent.model
        self.name = name

        container.set_item(name, self)
        self.is_derived = is_derived

    def __getstate__(self):
        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.state_attrs
        }
        value = state["interface"]

        for pickler in ReferenceImpl.picklers:
            if pickler.condition(value):
                state["interface"] = pickler(value)

        return state

    def __setstate__(self, state):

        if isinstance(state["interface"], _DummyBuiltins):
            # For backward compatibility with -v0.0.23
            state["interface"] = builtins
        else:
            if isinstance(state["interface"], _BasePickler):
                state["interface"] = state["interface"].restore()

        self.__dict__.update(state)

    def repr_parent(self):
        return self.parent.repr_parent() + "." + self.parent.repr_self()

    def repr_self(self, add_params=True):
        return self.name

    @staticmethod
    def _get_members(other):
        return other.self_refs

    def inherit(self, bases, **kwargs):

        if "clear_value" in kwargs:
            clear_value = kwargs["clear_value"]
        else:
            clear_value = True

        if bases:
            if clear_value:
                self.model.clear_obj(self)
            self.interface = bases[0].interface


ReferenceImpl.picklers.append(_ModulePickler)

