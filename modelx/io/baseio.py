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

import pathlib


def is_in_root(path: pathlib.Path):
    """Returns False if the relative path with dots go beyond root"""
    pos = path.as_posix()
    split = pos.split("/")
    level = 0
    while split:
        item = split.pop(0)
        if item == "..":
            level -= 1
        elif item == ".":
            pass
        else:
            level += 1
        if level < 0:
            return False
    return True


class BaseSharedData:

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.clients = {}
        self.manager = None

    def save(self, root):
        raise NotImplementedError

    def can_add_client(self, client):
        return all(c._can_add_other(client) for c in self.clients.values())

    def add_client(self, client):
        if id(client) not in self.clients:
            if self.can_add_client(client):
                self.clients[id(client)] = client
            else:
                raise ValueError("cannot add client")

    def remove_client(self, client):
        if id(client) in self.clients:
            del self.clients[id(client)]
            if not self.clients:
                self.manager.remove_data(self)

    def remove_all_clients(self):
        self.clients.clear()
        self.manager.remove_data(self)

    def after_save_file(self):
        for client in self.clients.values():
            client._after_save_file()

    def _check_sanity(self):
        for client in self.clients.values():
            assert client._data is self
            assert client._manager is self.manager


class IOManager:

    def __init__(self, system):
        self.data = {}
        self.system = system

    def _check_sanity(self):
        for data in self.data.values():
            data._check_sanity()

    def get_data(self, path: pathlib.Path, model=None):
        return self.data.get(self._get_dataid(path, model), None)

    def _get_dataid(self, path, model):
        if path.is_absolute():
            return path, None
        else:
            return path, model

    def new_data(self, path, model, cls, **kwargs):
        data = cls(path, **kwargs)
        self._register_data(data, model)
        return data

    def _register_data(self, data: BaseSharedData, model):
        if not self.get_data(data.path, model):
            self.data[self._get_dataid(data.path, model)] = data
            data.manager = self

    def get_or_create_data(self, path, model, cls, **kwargs):
        data = self.get_data(path, model)
        if data:
            return data
        else:
            return self.new_data(path, model, cls, **kwargs)

    def remove_data(self, data):

        if data.clients:
            raise RuntimeError("clients must be deleted beforehand")

        key = next((k for k, v in self.data.items() if v is data), None)
        if key:
            del self.data[key]

    def register_client(self, client, model, **kwargs):
        client._on_register(self, model=model, **kwargs)
        client._data.add_client(client)

    def unpickle_client(self, client):
        client._on_unpickle()
        client._data.add_client(client)


class BaseDataClient:
    """Abstract base class for accessing data stored in files

    See Also:
        :class:`~modelx.io.excelio.ExcelRange`
        :attr:`~modelx.core.model.Model.dataclients`

    """

    def _on_register(self, manager, model, **kwargs):
        raise NotImplementedError

    def _on_delete(self, manager, **kwargs):
        raise NotImplementedError

    def _after_save_file(self):
        pass

    def _can_add_other(self, other):
        raise NotImplementedError

    def __hash__(self):
        return hash(id(self))


class DataClientReferenceManager:
    """Maintains dataclient-reference mapping"""

    def __init__(self):
        self._client_to_refs = {}

    def add_reference(self, ref, client):

        refs = self._client_to_refs.get(client, None)
        if refs:
            refs.add(ref)
        else:
            self._client_to_refs[client] = {ref}

    def del_reference(self, ref, client):

        if isinstance(client, BaseDataClient):
            refs = self._client_to_refs[client]
            refs.remove(ref)
            if not refs:
                del self._client_to_refs[client]
            client._data.remove_client(client)
        else:
            raise ValueError("client must be BaseDataClient")

    def save_data(self, root):
        for client in self._client_to_refs:
            client._data.save(root)

    def del_all(self):
        for client, refs in self._client_to_refs.copy().items():
            for ref in refs.copy():
                self.del_reference(ref, client)

    @property
    def clients(self):
        return self._client_to_refs.keys()









