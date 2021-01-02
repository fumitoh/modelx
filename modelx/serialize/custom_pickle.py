import pickle
import pathlib
from modelx.core.system import mxsys
from modelx.core.base import NullImpl, null_impl
from modelx.io.baseio import BaseSharedData, IOManager
from . import ziputil


class ModelPickler(pickle.Pickler):

    def persistent_id(self, obj):

        if isinstance(obj, BaseSharedData):
            return "BaseSharedData", pathlib.PurePath(obj.path), obj.__class__
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

    def persistent_load(self, pid):

        if pid[0] == "BaseSharedData":

            _, path, cls = pid
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

            return self.manager.get_or_create_data(
                path, model=self.model, cls=cls, load_from=loadpath)

        elif pid[0] == "IOManager":
            return self.manager

        elif pid[0] == "NullImpl":
            return null_impl

        elif pid[0] == "System":
            return mxsys

        else:
            raise pickle.UnpicklingError("unsupported persistent object")