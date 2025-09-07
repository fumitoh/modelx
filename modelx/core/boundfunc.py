# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>
import sys
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

from types import FunctionType, CodeType
import dis
from modelx.core.base import Subject
from modelx.core.namespace import BaseNamespaceReferrer


def create_closure(new_value):
    # Used to prevent pytest from failing.
    # Code modified from:
    # http://stackoverflow.com/questions/37665862/how-to-create-new-closure-cell-objects

    import ctypes

    dummy = None

    def temp_func():
        return dummy

    closure = temp_func.__closure__

    PyCell_Set = ctypes.pythonapi.PyCell_Set

    # ctypes.pythonapi functions need to have argtypes and restype set manually
    PyCell_Set.argtypes = (ctypes.py_object, ctypes.py_object)

    # restype actually defaults to c_int here, but we might as well be explicit
    PyCell_Set.restype = ctypes.c_int

    PyCell_Set(closure[0], new_value)

    return closure


class AlteredFunction(BaseNamespaceReferrer):
    """Hold function with updated namespace"""

    __slots__ = ()
    __mixin_slots = (
        "_global_names",
        "is_altfunc_updated",
        "_is_global_updated",
        "_altfunc")

    is_altfunc_updated: bool
    _is_global_updated: bool
    _global_names: tuple
    _altfunc: FunctionType

    def __init__(self, server):
        """Create altered function from owner's formula.

        owner is a UserSpaceImpl or CellsImpl, which has formula, and
        namespace_impl as its members.
        """
        BaseNamespaceReferrer.__init__(self, server)
        self.is_altfunc_updated = False
        self._is_global_updated = False

    def on_notify(self, subject: Subject):
        self.is_altfunc_updated = False
        self._is_global_updated = False

    @property
    def global_names(self):
        if self._is_global_updated:
            return self._global_names
        else:
            self._global_names = tuple(self._extract_globals(self.altfunc.__code__))
            return self._global_names

    @property
    def altfunc(self):
        if self.is_altfunc_updated:
            return self._altfunc
        else:
            self._update_altfunc()
            return self._altfunc

    def _extract_globals(self, codeobj):

        insts = list(dis.get_instructions(codeobj))

        names = []
        for inst in insts:
            if inst.opname == "LOAD_GLOBAL" and inst.argval not in names:
                names.append(inst.argval)

        # Extract globals in generators and nested functions
        for co in codeobj.co_consts:
            if isinstance(co, CodeType):
                names.extend(self._extract_globals(co))

        return names

    def _update_altfunc(self):
        """Update altfunc"""

        func = self.formula.func    # TODO: Refactor.
        codeobj = func.__code__
        name = func.__name__  # self.cells.name   # func.__name__

        closure = func.__closure__  # None normally.
        if closure is not None:  # pytest fails without this.
            closure = create_closure(self.interface)

        self._altfunc = FunctionType(
            codeobj, self.ns_server.ns_dict, name=name, closure=closure
        )
        self._is_global_updated = False
        self.is_altfunc_updated = True

