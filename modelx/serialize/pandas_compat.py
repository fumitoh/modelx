import pickle
import copy

from .custom_pickle import ModelUnpickler
from pandas.compat import pickle_compat as pc

# Since pickle._Unpickler is written in pure Python and
# pickle.Unpickler is written in C,
# CompatUnpickler is slower then ModelUnpickler, so
# Use CompatUpickler only when needed.

# pandas' own compat unpickler (a pickle._Unpickler subclass): its
# find_class remaps relocated pandas classes, and on pandas < 3 its
# dispatch copy binds REDUCE/NEWOBJ to pandas-compat handlers.
CompatBase = getattr(pc, "Unpickler", None)

if CompatBase is None:
    # Very old pandas exposing module-level handlers instead

    class CompatBase(pickle._Unpickler):

        def find_class(self, module, name):
            key = (module, name)
            module, name = pc._class_locations_map.get(key, key)
            return super().find_class(module, name)

    CompatBase.dispatch = copy.copy(CompatBase.dispatch)
    for _opcode, _name in (
            (pickle.REDUCE, "load_reduce"),
            (pickle.NEWOBJ, "load_newobj"),
            (pickle.NEWOBJ_EX, "load_newobj_ex")):
        _func = getattr(pc, _name, None)
        if _func is not None:
            CompatBase.dispatch[_opcode[0]] = _func


class CompatUnpickler(CompatBase):
    """Unpickler to fix Pandas incompatibility issue"""

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model
        if reader.version >= 5:
            self.iospecs = reader.iospecs

    persistent_load = ModelUnpickler.persistent_load
    _find_iospec = ModelUnpickler._find_iospec
