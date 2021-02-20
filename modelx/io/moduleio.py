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

import inspect
import tempfile
import pathlib
from types import ModuleType
import importlib
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

from .baseio import BaseDataClient, BaseSharedData
from modelx.serialize.ziputil import write_str_utf8


class ModuleIO(BaseSharedData):

    def __init__(self, path, loadpath):
        super().__init__(path, load_from=loadpath)
        self._value = None
        self.is_updated = True  # Not Used

    def _on_save(self, path):
        for c in self.clients.values():     # Only one client
            write_str_utf8(inspect.getsource(c.value), path=path)



class ModuleDataClient(BaseDataClient):

    data_class = ModuleIO

    def __init__(self, path, module):
        BaseDataClient.__init__(self, path, is_hidden=True)
        self._value = module
        module._mx_dataclient = self

    def _on_load_value(self):
        pass

    def _on_pickle(self, state):
        state["value"] = inspect.getsource(self._value)
        return state

    def _on_unpickle(self, state):
        with tempfile.TemporaryDirectory() as tempdir:
            tempmod = pathlib.Path(tempdir) / "temp"
            with tempmod.open("wt") as f:
                f.write(state["value"])
            self._value = self._load_module(str(tempmod))

    def _on_serialize(self, state):
        return state

    def _on_unserialize(self, state):
        self._value = self._load_module(str(self._data.load_from))

    def _after_save_file(self):
        pass

    def _can_add_other(self, other):
        return False

    def _load_module(self, path):
        loader = SourceFileLoader("<unnamed module>", path=path)
        spec = spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        mod._mx_dataclient = self
        return mod

    @property
    def value(self):
        """Module held in the object"""
        return self._value

class UserModule(ModuleType):
    pass

