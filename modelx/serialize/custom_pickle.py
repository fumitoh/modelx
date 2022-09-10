import pickle
import pathlib
from modelx.core.system import mxsys
from modelx.core.base import NullImpl, null_impl
from modelx.io.baseio import BaseSharedIO, IOManager, BaseIOSpec
from modelx.core.node import BaseNode, ObjectNode, get_node, ItemNode, OBJ, KEY
from . import ziputil


class DataSpecPickler(pickle.Pickler):

    def persistent_id(self, obj):

        if isinstance(obj, BaseSharedIO):
            return "BaseSharedIO", obj.path.as_posix(), obj.__class__, obj.persistent_args
        elif isinstance(obj, IOManager):
            return "IOManager", None
        elif isinstance(obj, NullImpl):
            return "NullImpl", None
        elif obj is mxsys:
            # Needed by Interface._reduce_serialize
            return "System", None
        else:
            return None


class DataSpecUnpickler(pickle.Unpickler):

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model

    def persistent_load(self, pid):

        if pid[0] in ("BaseSharedIO", "BaseSharedData"):    # renamed in v0.20

            if len(pid) == 3:   # mx < v0.20
                _, path, cls = pid
                kwargs = {}
            elif len(pid) == 4:
                _, path, cls, kwargs = pid
            else:
                raise RuntimeError("must not happen")

            path = pathlib.Path(path)

            if not path.is_absolute():
                src = self.reader.path.joinpath(path)
                if self.reader.temproot:
                    dst = self.reader.temproot.joinpath(path)
                    if not dst.exists():
                        ziputil.copy_file(src, dst, None, None)
                    loadpath = dst
                else:
                    loadpath = src
            else:
                loadpath = path

            return self.manager.get_or_create_io(
                io_group=self.model, path=path, cls=cls, load_from=loadpath, **kwargs)

        elif pid[0] == "IOManager":
            return self.manager

        elif pid[0] == "NullImpl":
            return null_impl

        elif pid[0] == "System":
            return mxsys

        else:
            raise pickle.UnpicklingError("unsupported persistent object")


class ModelPickler(pickle.Pickler):

    def __init__(self, file, writer):
        super().__init__(file)
        self.writer = writer

    def persistent_id(self, obj):

        if id(obj) in self.writer.value_id_map:
            return "DataValue", self.writer.value_id_map[id(obj)]
        elif isinstance(obj, BaseIOSpec):
            return "BaseIOSpec", id(obj)
        elif isinstance(obj, BaseSharedIO):
            return "BaseSharedIO", obj.path.as_posix(), obj.__class__, obj.persistent_args
        elif isinstance(obj, BaseNode):

            model = self.writer.model
            if model is obj.obj.model:
                # Replace model name with empty string
                tupleid = ("",) + obj.obj._tupleid[1:]
            else:
                tupleid = obj.obj._tupleid

            if isinstance(obj, ItemNode):
                return "Node", tupleid, obj._impl[KEY]
            else:
                raise ValueError("invalid node" + repr(obj))

        elif isinstance(obj, IOManager):
            return "IOManager", None
        elif isinstance(obj, NullImpl):
            return "NullImpl", None
        elif obj is mxsys:
            # Needed by Interface._reduce_serialize
            return "System", None
        else:
            return None


class ModelUnpickler(pickle.Unpickler):

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model
        if reader.version >= 5:
            self.dataspecs = reader.dataspecs

    def persistent_load(self, pid):

        if pid[0] == "DataValue":
            _, dc_id = pid
            return self.dataspecs[dc_id].value

        elif pid[0] in ("BaseIOSpec", "BaseDataSpec"):  # renamed in v0.20
            _, dc_id = pid
            return self.dataspecs[dc_id]

        elif pid[0] in ("BaseSharedIO", "BaseSharedData"):  # renamed in v0.20

            if len(pid) == 3:   # mx < v0.20
                _, path, cls = pid
                kwargs = {}
            elif len(pid) == 4:
                _, path, cls, kwargs = pid
            else:
                raise RuntimeError("must not happen")

            path = pathlib.Path(path)

            if not path.is_absolute():
                src = self.reader.path.joinpath(path)
                if self.reader.temproot:
                    dst = self.reader.temproot.joinpath(path)
                    if not dst.exists():
                        ziputil.copy_file(src, dst, None, None)
                    loadpath = dst
                else:
                    loadpath = src
            else:
                loadpath = path

            return self.manager.get_or_create_io(
                io_group=self.model, path=path, cls=cls, load_from=loadpath, **kwargs)

        elif pid[0] == "Node":
            _, tupleid, key = pid
            return mxsys._get_object_from_tupleid_reduce(tupleid).node(*key)

        elif pid[0] == "IOManager":
            return self.manager

        elif pid[0] == "NullImpl":
            return null_impl

        elif pid[0] == "System":
            return mxsys

        else:
            raise pickle.UnpicklingError("unsupported persistent object")