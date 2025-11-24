# Copyright (c) 2017-2025 Fumito Hamamura <fumito.ham@gmail.com>

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
    Derivable, Impl, Interface, get_mixin_slots)
from modelx.io.baseio import BaseIOSpec
from modelx.core.node import ObjectNode, get_node, OBJ


class ReferenceImpl(Derivable, Impl):

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
            spmgr=parent.spmgr,
            interface=value
        )
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
        return other.own_refs

    def has_interface(self):
        return (isinstance(self.interface, Interface)
                and self.interface._is_valid())

    def on_inherit(self, updater, bases):

        self.model.clear_attr_referrers(self)
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


class NameSpaceReferenceImpl(ReferenceImpl):
    __slots__ = ()


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

    def is_derived(self):   # TODO: Rename this to _is_derived
        return self._impl.is_derived()

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
