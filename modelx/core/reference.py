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

import sys
import builtins
import importlib
from types import ModuleType, FunctionType
import functools

from modelx.core.base import (
    add_stateattrs, Derivable, Impl, Interface)
from modelx.io.excelio import BaseDataClient


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
        "container",
        "refmode",
        "is_relative"
    ]

    def __init__(self, parent, name, value, container, is_derived=False,
                 refmode=None, set_item=True):
        Impl.__init__(
            self,
            system=parent.system,
            parent=parent,
            name=name,
            interface=value)
        self.spacemgr = parent.spacemgr
        Derivable.__init__(self, is_derived)

        if isinstance(value, BaseDataClient):
            self.model.datarefmgr.add_reference(self, value)

        self.container = container
        if set_item:
            container.set_item(name, self)

        self.refmode = refmode
        if refmode == "absolute":
            self.is_relative = False
        else:   # 'auto' or 'relative'
            self.is_relative = True

    def change_value(self, value, is_derived, refmode, is_relative):
        if not is_derived:
            self.set_defined()
        if isinstance(self.interface, BaseDataClient):
            self.model.datarefmgr.del_reference(self, self.interface)
        if isinstance(value, BaseDataClient):
            self.model.datarefmgr.add_reference(self, value)
        self.interface = value
        self.refmode = refmode
        self.is_relative = is_relative
        self.container.change_item(self.name, self)

    def on_delete(self):
        if isinstance(self.interface, BaseDataClient):
            self.model.datarefmgr.del_reference(self, self.interface)

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

    def has_interface(self):
        return (isinstance(self.interface, Interface)
                and self.interface._is_valid())

    def inherit(self, updater, bases):

        self.model.clear_obj(self)
        if bases[0].has_interface():

            if self.refmode == "absolute":
                self.interface = bases[0].interface
                self.is_relative = False
            else:
                is_relative, interface = updater.get_relative_interface(
                    self.parent,
                    bases[0])
                if self.refmode == "auto":
                    self.is_relative = is_relative
                    self.interface = interface
                elif self.refmode == "relative":
                    if is_relative:
                        self.is_relative = is_relative
                        self.interface = interface
                    else:
                        raise ValueError(
                            "Relative reference %s out of scope" %
                            self.get_fullname()
                        )
                else:
                    raise ValueError("must not happen")
        else:
            self.interface = bases[0].interface
        self.container.set_update()


ReferenceImpl.picklers.append(_ModulePickler)


class ReferenceProxy:

    __slots__ = ("_impl",)

    def __init__(self, impl):
        self._impl = impl

    def __getattr__(self, name):
        item = getattr(Interface, name)
        if isinstance(item, property):
            return item.fget(self)
        elif isinstance(item, FunctionType):
            return functools.partial(item, self)

    @property
    def value(self):
        return self._impl.interface

    @property
    def refmode(self):
        return self._impl.refmode

    @property
    def is_derived(self):
        return self._impl.is_derived

    @property
    def _baseattrs(self):
        result = Interface._baseattrs.fget(self)
        result["type"] = "Reference"
        result["value_type"] = type(self.value).__name__
        return result
