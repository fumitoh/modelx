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


def new_model(name=None):
    """Create and return a new model.

    The current model is set set to the created model.

    Args:
        name (:obj:`str`, optional): The name of the model to create.
            Defaults to ``ModelN``, with ``N``
            being an automatically assigned integer.

    Returns:
        The new model.
    """
    return _system.new_model(name).interface


def new_space(name=None):
    """Create and return a new space in the current model.

    The ``currentspace`` of the current model is set to the created model.

    Args:
        name (:obj:`str`, optional): The name of the space to create.
            Defaults to ``SpaceN``, with ``N``
            being an automatically assigned integer.

    Returns:
        The new space.
    """

    return get_model().new_space(name)


def defcells(space=None, name=None, *funcs):
    """Decorator/function to create cells from Python functions.

    Convenience decorator/function to create new cells directly from function
    definitions or function objects substituting for calling
    ``new_cells`` method of the parent space.

    There are 3 ways to use ``defcells`` to define cells from functions.

    **#1. As a decorator without arguments**

    To create a cells from a function definition in the current space of the
    current model with the same name as the function's::

        @defcells
        def foo(x):
            return x

    **#2. As a decorator with arguments**

    To create a cells from a function definition in a given space and/or with
    a given name::

        @defcells(space=space, name=name)
        def foo(x):
            return x

    **#3. As a function**

    To create a multiple cells from a multiple function definitions::

        def foo(x):
            return x

        def bar(y):
            return foo(y)

        foo, bar = defcells(foo, bar)

    Args:
        space(optional): For the 2nd usage, a space to create the cells in.
            Defaults to the current space of the current model.
        name(optional): For the 2nd usage, a name of the created cells.
            Defaults to the function name.
        *funcs: For the 3rd usage, function objects. (``space`` and ``name``
            also take function objects for the 3rd usage.)

    Returns:
        For the 1st and 2nd usage, the newly created single cells is returned.
        For the 3rd usage, a list of newly created cells are returned.

    """
    if isinstance(space, _FunctionType) and name is None:
        # called as a function decorator
        func = space
        return _system.currentspace.new_cells(func=func).interface

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
    """Returns a dict that maps model names to models."""
    return _get_interfaces(_system.models)


def get_model(name=None):
    """Returns a model.

    If ``name`` is not given, the current model is returned.
    """
    if name is None:
        return _system.currentmodel.interface
    else:
        return get_models()[name]


def get_space(name=None):
    """Returns a space of the current model.

    If ``name`` is not given, the current space of the current model
    is returned.
    """
    if name is None:
        return _system.currentmodel.currentspace.interface
    else:
        return _system.currentmodel.spaces[name].interface


def get_self():
    """Return self space during its dynamic creation in paramfunc."""
    return _system.self.interface


def open_model(path):
    """Load a model saved from a file and return it.

    Args:
        path (:obj:`str`): Path to the file to load the model from.

    Returns:
        A new model created from the file.
    """
    return _system.open_model(path)



