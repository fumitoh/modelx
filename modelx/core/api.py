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
from modelx.core.space import Space as _Space
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


def defcells(space=None, name=None, *funcs):
    """Decorator to define a new cells.

    Args:
        space: The space to create the cells in. If omitted, the cells is
            created in the current space of the current model.
        name: The name of the cells. If omitted, the model is named
            automatically ``ModelN``, where ``N`` is an available number.

    """
    if isinstance(space, _FunctionType) \
            and (name is None or isinstance(name, str)):
        # called as a function decorator
        func = space
        return _system.currentspace.create_cells(func=func).interface

    elif (isinstance(space, _Space) or space is None) \
            and (isinstance(name, str) or name is None):
        # return decorator itself
        if space is None:
            space = _system.currentspace.interface

        return _CellsMaker(space=space._impl, name=name)

    elif all(isinstance(func, _FunctionType) for func \
             in (space, name) + funcs):

        return [defcells(func) for func in (space, name) + funcs]

    else:
        raise TypeError('invalid defcells arguments')


def get_models():
    """Return a dict that maps model names to models."""
    return _get_interfaces(_system.models)


def get_model(name=None):
    """Returns the current model."""
    if name is None:
        return _system.currentmodel.interface
    else:
        return get_models()[name]


def get_space(name=None):
    """Returns the current space of the current model."""
    if name is None:
        return _system.currentmodel.currentspace.interface
    else:
        return _system.currentmodel.spaces[name].interface


def get_self():
    """Return self space during its dynamic creation in paramfunc."""
    return _system.self.interface


def open_model(path):
    """Load a model saved in a file and return it.

    Args:
        path (:obj:`str`): Path to the file to load the model from.

    Returns:
        A new model created from the file.
    """
    return _system.open_model(path)



