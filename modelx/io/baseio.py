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

    def __init__(self, path: pathlib.Path, manager, load_from):
        self.path = path
        self.specs = {}
        self.manager = manager
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

    def is_external(self):
        return self.path.is_absolute()

    def _on_save(self, path):
        raise NotImplementedError

    def can_add_spec(self, spec):
        return all(c._can_add_other(spec) for c in self.specs.values())

    def add_spec(self, spec):
        if id(spec) not in self.specs:
            if self.can_add_spec(spec):
                self.specs[id(spec)] = spec
            else:
                raise ValueError("cannot add spec")

    def remove_spec(self, spec):
        if id(spec) in self.specs:
            del self.specs[id(spec)]
            if not self.specs:
                self.manager.remove_data(self)

    def remove_all_specs(self):
        self.specs.clear()
        self.manager.remove_data(self)

    def after_save_file(self):
        for spec in self.specs.values():
            spec._after_save_file()

    def _check_sanity(self):

        key, val = next(
            (k, v) for k, v in self.manager.data.items() if v is self)

        assert self.path == key[0]
        assert self is val

        for spec in self.specs.values():
            assert spec._data is self
            spec._check_sanity()

    def __getstate__(self):
        return {
            "path": pathlib.PurePath(self.path),
            "specs": list(self.specs.values()),
            "manager": self.manager,
            "load_from": self.load_from
        }

    def __setstate__(self, state):
        self.path = pathlib.Path(state["path"])
        self.manager = state["manager"]
        self.load_from = state["load_from"]
        self.specs = {id(c): c for c in state["specs"]}


class IOManager:
    """A class to manage shared data files

    * Create new spec
        - Create a new spec
        - Register a new spec
            - Create a SharedData if not exit
            - Register the spec to the data
    """

    def __init__(self, system):
        self.data = {}
        self.system = system

    def _check_sanity(self):
        assert len(self.data) == len(set(id(v) for v in self.data.values()))
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
        data = cls(path, model._impl.system.iomanager, load_from, **kwargs)
        if not self.get_data(data.path, model):
            self.data[self._get_dataid(data.path, model)] = data
        return data

    def restore_data(self, model, data):
        # Used only by restore_state in ModelImpl
        # To add unpickled data in self.data
        res = self.get_data(data.path, model)
        if not res:
            self.data[self._get_dataid(data.path, model)] = data

    def get_or_create_data(self, path, model, cls, load_from=None, **kwargs):
        data = self.get_data(path, model)
        if data:
            return data
        else:
            return self.new_data(path, model, cls, load_from, **kwargs)

    def remove_data(self, data):

        if data.specs:
            raise RuntimeError("specs must be deleted beforehand")

        key = next((k for k, v in self.data.items() if v is data), None)
        if key:
            del self.data[key]

    def new_spec(
            self, path, cls, model, spec_args=None, data_args=None):

        if spec_args is None:
            spec_args = {}
        if data_args is None:
            data_args = {}

        spec = cls(path, **spec_args)
        spec._manager = self
        spec._data = self.get_or_create_data(
            spec.path, model, cls=cls.data_class, **data_args)
        try:
            spec._on_load_value()
            spec._data.add_spec(spec)
        except:
            if not spec._data.specs:
                del self.data[self._get_dataid(spec._data.path, model)]
            raise

        return spec

    def del_spec(self, spec):
        spec._data.remove_spec(spec)

    def update_spec_value(self, spec, value, kwargs):
        if spec._can_update_value(value, kwargs):
            spec._on_update_value(value, kwargs)
        else:
            raise ValueError(
                "%s does not allow to replace its value" % repr(spec)
            )


class BaseDataSpec:
    """Abstract base class for accessing data stored in files

    .. versionchanged:: 0.18.0 The ``is_hidden`` parameter is removed.
    .. versionchanged:: 0.18.0 the class name is changed
        from ``BaseDataClient`` to :class:`BaseDataSpec`.

    See Also:
        * :class:`~modelx.io.pandasio.PandasData`
        * :class:`~modelx.io.moduleio.ModuleData`
        * :class:`~modelx.io.excelio.ExcelRange`
        * :attr:`~modelx.core.model.Model.dataspecs`

    """
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self._manager = None
        self._data = None

    def _check_sanity(self):
        assert self._data.specs[id(self)] is self
        assert any(self._data is d for d in self._manager.data.values())
        assert self._manager is self._data.manager

    def _on_load_value(self):
        raise NotImplementedError

    def _can_update_value(self, value, kwargs):
        raise NotImplementedError

    def _on_update_value(self, value, kwargs):
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
        }
        if hasattr(self, "_is_hidden"):
            state["is_hidden"] = self._is_hidden
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
            self._data.add_spec(self)
        else:
            self._on_unpickle(state)

    def _get_attrdict(self, extattrs=None, recursive=True):

        result = {
            "type": type(self).__name__,
            "path": str(self.path),
            "load_from": str(self._data.load_from),
            "value": self.value
        }
        return result


