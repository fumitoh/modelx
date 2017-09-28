"""modelx API functions.

Functions listed here are directly available in ``modelx`` package,
either by::

    import modelx as mx

or by::

    from modelx import *

"""

from types import FunctionType as _FunctionType

from modelx.core import system as _system
from modelx.core.cells import CellsMaker as _CellsMaker
from modelx.core.base import get_interfaces as _get_interfaces


def create_model(name=None):
    """Create a new model.

    Args:
        name (:obj:`str`, optional): The name of the model to create.
            If omitted, the model is named ``ModelN``, with ``N``
            being an automatically assigned integer.

    Returns:
        A new model.
    """
    return _system.create_model(name).interface


def defcells(space=None, name=None):
    """Decorator to define a new cells.

    Args:
        space: The space to create the cells in. If omitted, the cells is
            created in the current space of the current model.
        name: The name of the cells. If omitted, the model is named
            automatically ``ModelN``, where ``N`` is an available number.

    """
    if isinstance(space, _FunctionType) and name is None:
        # called as a function decorator
        func = space
        return _system.currentspace.create_cells(func=func).interface

    else:
        # return decorator itself
        if not space:
            space = _system.currentspace.interface

        return _CellsMaker(space=space._impl, name=name)


def get_models():
    """Return a dict that maps model names to models."""
    return _get_interfaces(_system.models)


def get_currentmodel():
    """Returns the current model."""
    return _system.currentmodel.interface


def get_currentspace():
    """Returns the current space of the current model."""
    return _system.currentmodel.currentspace.interface


def get_self():
    """Return self space during its dynamic creation in factory."""
    return _system.self.interface


def open_model(path):
    """Load a model saved in a file and return it.

    Args:
        path (:obj:`str`): Path to the file to load the model from.

    Returns:
        A new model created from the file.
    """
    return _system.open_model(path)



