import pickle
import pathlib
from modelx.core.system import mxsys
from modelx.core.base import NullImpl, null_impl
from modelx.io.baseio import BaseSharedIO, IOManager, BaseIOSpec
from modelx.core.node import BaseNode, ObjectNode, get_node, ItemNode, OBJ, KEY
from . import ziputil


class IOSpecPickler(pickle.Pickler):

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


class IOSpecUnpickler(pickle.Unpickler):

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model
        # Rollback point for load_pickle_tolerantly if this strict
        # attempt aborts after registering ios/specs
        reader.io_journal_mark = self.manager.journal_mark()

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

    def spec_id(self, obj):
        # The id emitted for a BaseIOSpec must match a key of the
        # iospecs dict written to iospecs.pickle, which serializer 4/5
        # writers key by memory address.
        return id(obj)

    def persistent_id(self, obj):

        if id(obj) in self.writer.value_id_map:
            return "DataValue", self.writer.value_id_map[id(obj)]
        elif isinstance(obj, BaseIOSpec):
            return "BaseIOSpec", self.spec_id(obj)
        elif isinstance(obj, BaseSharedIO):
            return "BaseSharedIO", obj.path.as_posix(), obj.__class__, obj.persistent_args
        elif isinstance(obj, BaseNode):

            model = self.writer.model
            if model is obj.obj.model:
                # Replace model name with empty string
                idtuple = ("",) + obj.obj._idtuple[1:]
            else:
                idtuple = obj.obj._idtuple

            if isinstance(obj, ItemNode):
                return "Node", idtuple, obj._impl[KEY]
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


class DeterministicModelPickler(ModelPickler):
    """ModelPickler for writers with an ``assign_id`` allocator (v6+).

    Emits the writer-assigned process-independent id for BaseIOSpec
    objects instead of their memory address, matching the keys of the
    iospecs dict those writers save to iospecs.pickle.
    """

    def spec_id(self, obj):
        return self.writer.assign_id(obj)


class ModelUnpickler(pickle.Unpickler):

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model
        if reader.version >= 5:
            self.iospecs = reader.iospecs
        # Rollback point for load_pickle_tolerantly if this strict
        # attempt aborts after registering ios/specs
        reader.io_journal_mark = self.manager.journal_mark()

    def _find_iospec(self, sp_id):
        # In the fast strict pass the error aborts the load and triggers
        # the tolerant retry (tolerant_pickle), which catches this in its
        # persistent_load and substitutes a placeholder.
        iospecs = getattr(self, "iospecs", None)
        if isinstance(iospecs, dict) and iospecs.get(sp_id) is not None:
            return iospecs[sp_id]
        raise KeyError(
            "IO spec not found for pickled value (id: %s)" % sp_id)

    def persistent_load(self, pid):

        if pid[0] == "DataValue":
            _, sp_id = pid
            return self._find_iospec(sp_id).value

        elif pid[0] in ("BaseIOSpec", "BaseDataSpec"):  # renamed in v0.20
            _, sp_id = pid
            return self._find_iospec(sp_id)

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
            _, idtuple, key = pid
            return mxsys._get_object_from_idtuple_reduce(idtuple).node(*key)

        elif pid[0] == "IOManager":
            return self.manager

        elif pid[0] == "NullImpl":
            return null_impl

        elif pid[0] == "System":
            return mxsys

        else:
            raise pickle.UnpicklingError("unsupported persistent object")