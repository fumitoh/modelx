from types import FunctionType as _FunctionType

from modelx.core import system as _system
from modelx.core.cells import CellsMaker as _CellsMaker


def create_model(name=None):
    return _system.create_model(name).interface


def defcells(space=None, name=None):

    if isinstance(space, _FunctionType) and name is None:
        # called as a function decorator
        func = space
        return _system.currentspace.create_cells(func=func).interface

    else:
        # return decorator itself
        if not space:
            space = _system.currentspace.interface

        return _CellsMaker(space=space._impl, name=name)


def create_cells_from_module(module, space=None):
    return _system.create_cells_from_module(module, space=None)


def get_models():
    return _system.models


def get_currentmodel():
    return _system.currentmodel.interface


def get_currentspace():
    return _system.currentmodel.currentspace.interface


def get_self():
    """Return self space during its dynamic creation in factory."""

    return _system.self.interface


def open_model(path):
    return _system.open_model(path)



