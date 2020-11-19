import pickle
import copy

from .custom_pickle import ModelUnpickler
from pandas.compat import pickle_compat as pc

# Since pickle._Unpickler is written in pure Python and
# pickle.Unpickler is written in C,
# CompatUnpickler is slower then ModelUnpickler, so
# Use CompatUpickler only when needed.

class CompatUnpickler(pickle._Unpickler):
    """Unpickler to fix Pandas incompatibility issue"""

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model

    persistent_load = ModelUnpickler.persistent_load

    def find_class(self, module, name):
        # override superclass
        key = (module, name)
        module, name = pc._class_locations_map.get(key, key)
        return super().find_class(module, name)


CompatUnpickler.dispatch = copy.copy(CompatUnpickler.dispatch)
CompatUnpickler.dispatch[pickle.REDUCE[0]] = pc.load_reduce
CompatUnpickler.dispatch[pickle.NEWOBJ[0]] = pc.load_newobj

try:
    CompatUnpickler.dispatch[pickle.NEWOBJ_EX[0]] = pc.load_newobj_ex
except (AttributeError, KeyError):
    pass

