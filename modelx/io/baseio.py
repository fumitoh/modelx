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

    def __init__(self, path: pathlib.Path, load_from):
        self.path = path
        self.clients = {}
        self.manager = None
        self.load_from = load_from

    def save(self, root):
        if not self.path.is_absolute():
            path = root.joinpath(self.path)
        else:
            path = self.path

        path.parent.mkdir(parents=True, exist_ok=True)
        self._on_save(path)
        self.is_updated = False
        self.after_save_file()

    def _on_save(self, path):
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
    """A class to manage shared data files

    * Create new client
        - Create a new client
        - Register a new client
            - Create a SharedData if not exit
            - Register the client to the data
    """

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

    def new_data(self, path, model, cls, load_from, **kwargs):
        data = cls(path, load_from, **kwargs)
        if not self.get_data(data.path, model):
            self.data[self._get_dataid(data.path, model)] = data
            data.manager = self
        return data

    def get_or_create_data(self, path, model, cls, load_from=None, **kwargs):
        data = self.get_data(path, model)
        if data:
            return data
        else:
            return self.new_data(path, model, cls, load_from, **kwargs)

    def remove_data(self, data):

        if data.clients:
            raise RuntimeError("clients must be deleted beforehand")

        key = next((k for k, v in self.data.items() if v is data), None)
        if key:
            del self.data[key]

    def new_client(
            self, path, cls, model, client_args=None, data_args=None):

        if client_args is None:
            client_args = {}
        if data_args is None:
            data_args = {}

        client = cls(path, **client_args)
        client._manager = self
        client._data = self.get_or_create_data(
            client.path, model, cls=cls.data_class, **data_args)
        try:
            client._on_load_value()
            client._data.add_client(client)
        except:
            if not client._data.clients:
                del self.data[self._get_dataid(client._data.path, model)]
            raise

        return client

    def del_client(self, client):
        client._data.remove_client(client)


class BaseDataClient:
    """Abstract base class for accessing data stored in files

    See Also:
        :class:`~modelx.io.excelio.ExcelRange`
        :attr:`~modelx.core.model.Model.dataclients`

    """

    def __init__(self, path, is_hidden):
        self.path = pathlib.Path(path)
        self._manager = None
        self._data = None
        self._is_hidden = is_hidden

    def _on_load_value(self):
        raise NotImplementedError

    def _on_pickle(self, state):
        raise NotImplementedError

    def _on_unpickle(self, state):
        raise NotImplementedError

    def _on_serialize(self, state):
        raise NotImplementedError

    def _on_unserialize(self, state):
        raise NotImplementedError

    def _after_save_file(self):
        pass

    def _can_add_other(self, other):
        raise NotImplementedError

    def __hash__(self):
        return hash(id(self))

    def __getstate__(self):
        state = {
            "manager": self._manager,
            "_data": self._data,
            "path": pathlib.PurePath(self.path),
            "is_hidden": self._is_hidden
        }
        if self._manager.system.serializing:
            return self._on_serialize(state)
        else:
            return self._on_pickle(state)

    def __setstate__(self, state):
        self._manager = state["manager"]
        self._data = state["_data"]
        self.path = pathlib.Path(state["path"])
        if "is_hidden" in state:
            self._is_hidden = state["is_hidden"]
        else:
            # For backward compatibility with v0.12
            self._is_hidden = False
        if self._manager.system.serializing:
            self._on_unserialize(state)
            self._data.add_client(self)
        else:
            self._on_unpickle(state)


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
                client._manager.del_client(client)
        else:
            raise ValueError("client must be BaseDataClient")

    def save_data(self, root):
        saved = set()
        for client in self._client_to_refs:
            if not client._data in saved:
                client._data.save(root)
                saved.add(client._data)

    def del_all(self):
        for client, refs in self._client_to_refs.copy().items():
            for ref in refs.copy():
                self.del_reference(ref, client)

    @property
    def clients(self):
        return self._client_to_refs.keys()

    def get_client(self, ref):
        for client, refs in self._client_to_refs.items():
            if ref in refs:
                return client

        raise KeyError('must not happen')







