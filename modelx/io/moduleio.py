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

import os
import inspect
import tempfile
import pathlib
from types import ModuleType
import importlib
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

from .baseio import BaseIOSpec, BaseSharedIO
from modelx.serialize.ziputil import write_str_utf8


class ModuleIO(BaseSharedIO):

    def __init__(self, path, manager, load_from, module=None):
        # module prior to load_from
        load_from = self._get_module_path(module) if module is not None else load_from
        super().__init__(path, manager, load_from=load_from)
        self.source = None  # call _load_module to set source

    @staticmethod
    def _get_module_path(module):
        if isinstance(module, ModuleType):
            return pathlib.Path(module.__file__)
        elif isinstance(module, (str, os.PathLike)):
            return pathlib.Path(module).resolve()
        else:
            raise RuntimeError("must not happen")

    def _on_write(self, path):
        write_str_utf8(self.source, path=path)

    def _on_update_value(self, value, kwargs):
        if isinstance(value, (ModuleType, str, os.PathLike)):
            self.load_from = self._get_module_path(value)
        elif value is None:     # reload current
            pass
        else:
            raise ValueError("must not happen")
        self.source = None  # call _load_module to set source

    def _load_module(self):
        loader = SourceFileLoader("<unnamed module>", path=str(self.load_from))
        spec = spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        self.source = inspect.getsource(mod)
        return mod


class ModuleData(BaseIOSpec):
    """A subclass of :class:`~modelx.io.baseio.BaseIOSpec` that
    associates a user module with its source file in the model

    A :class:`ModuleData` is created either by
    :meth:`UserSpace.new_module<modelx.core.space.UserSpace.new_module>` or
    :meth:`Model.new_module<modelx.core.model.Model.new_module>` when
    a user module is assigned to a Reference. The :class:`ModuleData`
    is assigned to the ``_mx_dataclient`` attribute of the module.

    .. versionadded:: 0.13.0

    See Also:
        * :meth:`UserSpace.new_module<modelx.core.space.UserSpace.new_module>`
        * :meth:`UserSpace.update_module<modelx.core.space.UserSpace.update_module>`
        * :meth:`Model.new_module<modelx.core.model.Model.new_module>`
        * :meth:`Model.update_module<modelx.core.model.Model.update_module>`
        * :attr:`~modelx.core.model.Model.dataspecs`

    """

    io_class = ModuleIO

    def __init__(self, module=None):
        BaseIOSpec.__init__(self)
        if isinstance(module, ModuleType):
            self._value = module
        else:
            self._value = None

    def _on_load_value(self):
        self._value = self._io._load_module()

    def _can_update_value(self, value, kwargs):
        return isinstance(value, (ModuleType, str, os.PathLike, type(None)))

    def _on_update_value(self, value, kwargs):
        self._value = self._io._load_module()

    def _on_pickle(self, state):
        return state

    def _on_unpickle(self, state):
        mod = self._io._load_module()
        self._value = mod

    def _on_serialize(self, state):
        return state

    def _on_unserialize(self, state):
        self._value = self._io._load_module()

    def _can_add_other(self, other):
        return False

    @property
    def value(self):
        """Module held in the object"""
        return self._value

    def __repr__(self):
        return "<ModuleData path=%s>" % repr(str(self._io.path.as_posix()))
