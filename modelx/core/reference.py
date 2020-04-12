# Copyright (c) 2017-2020 Fumito Hamamura <fumito.ham@gmail.com>

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
from types import ModuleType, FunctionType
import functools

from modelx.core.base import add_stateattrs, Derivable, Impl, Interface


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


@add_stateattrs
class ReferenceImpl(Derivable, Impl):

    picklers = []    # List of _BasePickler sub classes

    __cls_stateattrs = [
        "container"
    ]

    def __init__(self, parent, name, value, container, is_derived=False):
        Impl.__init__(
            self,
            system=parent.system,
            parent=parent,
            name=name,
            interface=value)
        Derivable.__init__(self, is_derived)

        self.container = container
        container.set_item(name, self)

    def change_value(self, value, is_derived):
        if not is_derived:
            self.set_defined()
        self.interface = value
        self.container.set_update()
        for sc in self.container.scopes:
            sc.clear_referrers(self.name)

    def __getstate__(self):
        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.stateattrs
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

    def inherit(self, bases):

            self.model.clear_obj(self)
            self.interface = bases[0].interface
            self.container.set_update()
            for sc in self.container.scopes:
                sc.clear_referrers(self.name)


ReferenceImpl.picklers.append(_ModulePickler)


class ReferenceProxy:

    __slots__ = ("_impl",)

    def __init__(self, impl):
        self._impl = impl

    def __getattr__(self, item):
        item = getattr(Interface, item)
        if isinstance(item, property):
            return item.fget(self)
        elif isinstance(item, FunctionType):
            return functools.partial(item, self)

    @property
    def value(self):
        return self._impl.interface

    @property
    def _baseattrs(self):
        return Interface._baseattrs.fget(self)
