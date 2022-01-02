# Copyright (c) 2017-2022 Fumito Hamamura <fumito.ham@gmail.com>

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
    add_stateattrs, Derivable, Impl, Interface, get_mixin_slots)
from modelx.io.baseio import BaseDataSpec
from modelx.core.node import ObjectNode, get_node, OBJ


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

    picklers = [_ModulePickler]    # List of _BasePickler sub classes

    __slots__ = (
        "container",
        "refmode",
        "is_relative"
    ) + get_mixin_slots(Derivable, Impl)

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

        self.container = container
        if set_item:
            container.set_item(name, self)

        self.refmode = refmode
        if refmode == "absolute":
            self.is_relative = False
        else:   # 'auto' or 'relative'
            self.is_relative = True

    def on_delete(self):
        pass

    def __getstate__(self):

        state = {key: getattr(self, key) for key in self.stateattrs}
        value = state["interface"]

        if self.model.refmgr.has_spec(value):
            state["interface"] = self.model.refmgr.get_spec(value)
        else:
            for pickler in self.picklers:
                if pickler.condition(value):
                    state["interface"] = pickler(value)
                    break

        return state

    def __setstate__(self, state):

        if isinstance(state["interface"], _DummyBuiltins):
            # For backward compatibility with -v0.0.23
            state["interface"] = builtins
        elif isinstance(state["interface"], BaseDataSpec):
            state["interface"] = state["interface"].value
        else:
            if isinstance(state["interface"], _BasePickler):
                state["interface"] = state["interface"].restore()

        for attr in state:
            setattr(self, attr, state[attr])

    def to_node(self):
        return ReferenceNode(get_node(self, None, None))

    def repr_parent(self):
        if self.parent.repr_parent():
            return self.parent.repr_parent() + "." + self.parent.repr_self()
        else:
            return self.parent.repr_self()

    def repr_self(self, add_params=True):
        return self.name

    @staticmethod
    def _get_members(other):
        return other.self_refs

    def has_interface(self):
        return (isinstance(self.interface, Interface)
                and self.interface._is_valid())

    def on_inherit(self, updater, bases):

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
        self.container.set_refresh()


class ReferenceProxy:
    """Proxy to interface to References

    *Reference* objects are not exposed to the user,
    thus ReferenceProxy objects are used to interface to References.
    A proxy object to a Reference can be created and returned by
    the :func:`~modelx.get_object` function, by passing
    the full dotted name of the Reference to ``name``,
    and :obj:`True` to ``as_proxy``::

    >>> mx.get_object("Model1.Space1.foo", as_proxy=True)

    Reference shares its ultimate base class with Model, Space and
    Cells classes, and below are attributes common among those
    classes.

    Attributes:

        name (str): The name of the Reference.

        fullname (str): The dotted name of the object.

        parent: The parent of the Reference.

        model: The Model that the Reference belongs to.

    .. seealso::

        :func:`~modelx.get_object`, :class:`~ReferenceNode`

    """

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
        """Returns referenced object"""
        return self._impl.interface

    @property
    def refmode(self):
        """Returns reference mode

        Returns a string representing the reference mode

        Returns:
            str: "auto", "absolute" or "relative"

        .. seealso::

            :meth:`~modelx.core.space.UserSpace.set_ref`,
            :meth:`~modelx.core.space.UserSpace.absref`,
            :meth:`~modelx.core.space.UserSpace.relref`

        """
        return self._impl.refmode

    @property
    def is_derived(self):   # TODO: Rename this to _is_derived
        return self._impl.is_derived

    @property
    def _baseattrs(self):
        result = Interface._baseattrs.fget(self)
        result["type"] = "Reference"
        result["value_type"] = type(self.value).__name__
        return result

    def _get_attrdict(self, extattrs=None, recursive=True):
        result = Interface._get_attrdict(self, extattrs, recursive)
        result["type"] = "Reference"
        result["value_type"] = type(self.value).__name__
        if extattrs:
            Interface._get_attrdict_extra(self, result, extattrs, recursive)

        return result

    @property
    def _evalrepr(self):
        return Interface._evalrepr.fget(self)

    def __repr__(self):
        return Interface.__repr__(self)


class ReferenceNode(ObjectNode):

    @property
    def obj(self):
        """Return the ReferenceProxy object"""
        return ReferenceProxy(self._impl[OBJ])

    def has_value(self):
        """Always returns :obj:`True` as Reference has value"""
        return True

    @property
    def value(self):
        return self._impl[OBJ].interface
