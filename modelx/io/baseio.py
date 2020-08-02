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

    def save(self, root, **kwargs):
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


class IOManager:

    def __init__(self):
        self.data = {}
        self.dataid_to_models = {}

    def _check_sanity(self):

        assert len(self.data) == len(self.dataid_to_models)
        assert (set(id(d) for d in self.data.values())
                == set(self.dataid_to_models.keys()))

        # values of dataid_to_models  must not be empty
        assert all(models for models in self.dataid_to_models.values())

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
            if model:
                self._add_model_to_data(data, model)
            else:
                RuntimeError("must not happen")
            data.manager = self

    def _add_model_to_data(self, data, model):
        if id(data) in self.dataid_to_models:
            if model not in self.dataid_to_models[id(data)]:
                self.dataid_to_models[id(data)].append(model)
        else:
            self.dataid_to_models[id(data)] = [model]

    def get_or_create_data(self, path, model, cls, **kwargs):
        data = self.get_data(path, model)
        if data:
            self._add_model_to_data(data, model)
            return data
        else:
            return self.new_data(path, model, cls, **kwargs)

    def remove_data(self, data):
        key = next((k for k, v in self.data.items() if v is data), None)
        if key:
            del self.data[key]
            if id(data) in self.dataid_to_models:
                del self.dataid_to_models[id(data)]

    def remove_model(self, model):
        datalist = []
        for dataid, models in self.dataid_to_models.items():
            if model in models:
                data = next(
                    d for d in self.data.values() if id(d) == dataid)
                datalist.append(data)
        for data in datalist:
            data.remove_all_clients()

            assert data not in self.data.values()
            assert id(data) not in self.dataid_to_models

        for models in self.dataid_to_models.values():
            assert model not in models

    def register_client(self, client, model, **kwargs):
        client._on_register(self, model=model, **kwargs)
        client._data.add_client(client)

    def unpickle_client(self, client):
        client._on_unpickle()
        client._data.add_client(client)

    def save_file(self, model, root):
        for data in self.data.values():
            if model in self.dataid_to_models[id(data)]:
                data.save(root=root)


class BaseDataClient:

    def _on_register(self, manager, model, **kwargs):
        raise NotImplementedError

    def _on_delete(self, manager, **kwargs):
        raise NotImplementedError

    def _after_save_file(self):
        pass

    def _can_add_other(self, other):
        raise NotImplementedError










