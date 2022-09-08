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


class BaseSharedIO:

    def __init__(self, path: pathlib.Path, manager, load_from):
        self.path = path
        self.specs = {}
        self.manager = manager
        self.load_from = load_from

    def is_external(self):
        return self.path.is_absolute()

    def _on_write(self, path):
        raise NotImplementedError

    def _can_add_spec(self, spec):
        return all(c._can_add_other(spec) for c in self.specs.values())

    def _check_sanity(self):

        key, val = next(
            (k, v) for k, v in self.manager.ios.items() if v is self)

        assert self.path == key[1]
        assert self is val

        for spec in self.specs.values():
            assert spec._io is self
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

    @property
    def persistent_args(self):
        return {}


class IOManager:
    """A class to manage shared file

    * Create new spec
        - Create a new spec
        - Register a new spec
            - Create a SharedData if not exit
            - Register the spec to the file
    """

    def __init__(self):
        self.ios = {}
        self.serializing = None     # Set from external

    def _check_sanity(self):
        assert len(self.ios) == len(set(id(v) for v in self.ios.values()))
        for a_io in self.ios.values():
            a_io._check_sanity()

    def _get_io(self, io_group, path: pathlib.Path):
        return self.ios.get(self._get_io_key(io_group, path), None)

    def _get_io_key(self, io_group, path):
        if path.is_absolute():
            return None, path
        else:
            return io_group, path

    def _new_io(self, io_group, path, cls, load_from, **kwargs):
        a_io = cls(path, self, load_from, **kwargs)
        if not self._get_io(io_group, a_io.path):
            self.ios[self._get_io_key(io_group, a_io.path)] = a_io
        return a_io

    def _del_io(self, io_):
        if io_.specs:
            raise RuntimeError("specs must be deleted beforehand")

        key = next((k for k, v in self.ios.items() if v is io_), None)
        if key:
            del self.ios[key]

    def restore_io(self, io_group, io_):
        # Used only by restore_state in ModelImpl
        # To add unpickled IO in self.ios
        res = self._get_io(io_group, io_.path)
        if not res:
            self.ios[self._get_io_key(io_group, io_.path)] = io_

    def get_or_create_io(self, io_group, path, cls, load_from=None, **kwargs):
        a_io = self._get_io(io_group, path)
        if a_io:
            return a_io
        else:
            return self._new_io(io_group, path, cls, load_from, **kwargs)

    def new_spec(
            self, cls, io_group, path, spec_args=None, io_args=None):

        if spec_args is None:
            spec_args = {}
        if io_args is None:
            io_args = {}

        spec = cls(**spec_args)
        spec._manager = self
        spec._io = self.get_or_create_io(
            io_group, pathlib.Path(path), cls=cls.io_class, **io_args)
        try:
            spec._on_load_value()
            self.add_spec(spec._io, spec)
        except:
            if not spec._io.specs:
                del self.ios[self._get_io_key(io_group, spec._io.path)]
            raise

        return spec

    def add_spec(self, io_, spec):
        if id(spec) not in io_.specs:
            if io_._can_add_spec(spec):
                io_.specs[id(spec)] = spec
            else:
                raise ValueError("cannot add spec")

    def del_spec(self, spec):
        a_io = spec._io
        if id(spec) in a_io.specs:
            del a_io.specs[id(spec)]
            if not a_io.specs:
                self._del_io(a_io)

    def update_spec_value(self, spec, value, kwargs):
        if spec._can_update_value(value, kwargs):
            spec._on_update_value(value, kwargs)
        else:
            raise ValueError(
                "%s does not allow to replace its value" % repr(spec)
            )

    def write_ios(self, io_group, root):
        for a_io in self.ios.values():
            self.write_io(a_io, root)

    def write_io(self, io_, root):
        if not io_.path.is_absolute():
            path = root.joinpath(io_.path)
        else:
            path = io_.path

        path.parent.mkdir(parents=True, exist_ok=True)
        io_._on_write(path)

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
    def __init__(self):
        self._manager = None
        self._io = None

    def _check_sanity(self):
        assert self._io.specs[id(self)] is self
        assert any(self._io is d for d in self._manager.ios.values())
        assert self._manager is self._io.manager

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

    def _can_add_other(self, other):
        raise NotImplementedError

    def __hash__(self):
        return hash(id(self))

    def __getstate__(self):
        state = {
            "manager": self._manager,
            "_io": self._io
        }
        if hasattr(self, "_is_hidden"):
            state["is_hidden"] = self._is_hidden
        if self._manager.serializing is True:
            return self._on_serialize(state)
        elif self._manager.serializing is False:
            return self._on_pickle(state)
        else:
            raise RuntimeError("must not happen")

    def __setstate__(self, state):
        self._manager = state["manager"]
        self._io = state["_io"] if "_io" in state else state["_data"]  # renamed from v0.20.0
        if "is_hidden" in state:
            self._is_hidden = state["is_hidden"]
        else:
            # For backward compatibility with v0.12
            self._is_hidden = False
        if self._manager.serializing is True:
            self._on_unserialize(state)
            self._manager.add_spec(self._io, self)
        elif self._manager.serializing is False:
            self._on_unpickle(state)
        else:
            RuntimeError("must not happen")

    def _get_attrdict(self, extattrs=None, recursive=True):

        result = {
            "type": type(self).__name__,
            "path": str(self._io.path),
            "load_from": str(self._io.load_from),
            "value": self.value
        }
        return result


