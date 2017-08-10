from types import FunctionType

from modelx.core import system
from modelx.core.cells import CellsMaker


def create_model(name=None):
    return system.create_model(name).interface


def defcells(space=None, name=None):

    if isinstance(space, FunctionType) and name is None:
        # called as a function decorator
        func = space
        return system.currentspace.create_cells(func=func).interface

    else:
        # return decorator itself
        if not space:
            space = system.currentspace.interface

        return CellsMaker(space=space._impl, name=name)


def create_cells_from_module(module, space=None):
    return system.create_cells_from_module(module, space=None)


def get_models():
    return system.models


def get_currentmodel():
    return system.currentmodel.interface


def get_currentspace():
    return system.currentmodel.currentspace.interface


def get_self():
    """Return self space during its dynamic creation in factory."""

    return system.self.interface


def open_model(path):
    return system.open_model(path)



