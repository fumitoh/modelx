# Copyright (c) 2017-2025 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""modelx core API functions.

Functions listed here are available directly in ``modelx`` module,
either by::

    import modelx as mx

or by::

    from modelx import *

"""
import sys
import sys as _sys
import ast as _ast
import itertools as _itertools
import warnings
from types import FunctionType as _FunctionType
import zipfile
from contextlib import contextmanager

from modelx.core import mxsys as _system
from modelx.core.cells import CellsMaker as _CellsMaker
from modelx.core.macro import MacroMaker as _MacroMaker
from modelx.core.space import BaseSpace as _Space
from modelx.core.model import Model as _Model
from modelx.core.base import get_interface_dict as _get_interfaces
from modelx.core.util import is_valid_name as _is_valid_name
import modelx.serialize as _serialize

def configure_python():
    """Configure Python ``sys`` settings for modelx.

    This function is called implicitly when importing modelx.
    To restore the Python settings, call :py:func:`restore_python`
    """
    _system.configure_python()


def restore_python():
    """Restore Python ``sys`` settings for modelx.

    Restore ``sys`` settings to the original states before
    importing modelx.
    """
    _system.restore_python()


def setup_ipython():
    """Set up IPython shell for modelx.

    Suppress IPython's default traceback messages upon error.
    """
    _system.setup_ipython()


def restore_ipython():
    """Restore IPython' default error message.

    Bring back IPython's default traceback message upon error for debugging.
    """
    _system.restore_ipython()


def set_recursion(maxdepth=1000):
    """Set formula recursion limit.

    Args:
        maxdepth: The maximum depth of the modelx interpreter stack.
    """
    _system.callstack.maxdepth = maxdepth


def get_recursion():
    """Returns formula recursion limit"""
    return _system.callstack.maxdepth


def new_model(name=None):
    """Create and return a new model.

    The current model is set set to the created model.

    Args:
        name (:obj:`str`, optional): The name of the model to create.
            Defaults to ``ModelN``, with ``N``
            being an automatically assigned integer.

    Returns:
        :class:`~modelx.core.model.Model`: The new model.
    """
    return _system.new_model(name).interface


def new_space(name=None, bases=None, formula=None):
    """Create and return a new space in the current model.

    The ``currentspace`` of the current model is set to the created model.

    Args:
        name (:obj:`str`, optional): The name of the space to create.
            Defaults to ``SpaceN``, with ``N``
            being an automatically assigned integer.

    Returns:
        The new space.
    """
    if cur_model() is None:
        new_model()
    return cur_model().new_space(name, bases, formula)


def defcells(space=None, name=None, is_cached=None, *funcs):
    """Decorator to create or update a cells from a Python function.

    Note:
        :func:`cached` is an alies for :func:`defcells`.

    This convenience function serves as a decorator to create a new cells or
    update the formula of an existing cells directly from a Python function definition.
    It replaces the need to manually call :py:meth:`~modelx.core.space.UserSpace.new_cells`
    or :py:meth:`~modelx.core.space.UserSpace.set_formula`
    on the parent space, or to set the :py:attr:`~modelx.core.space.UserSpace.formula` property.

    Examples:

        **1. As a decorator without arguments**

        The code below creates a cells named ``foo`` in the current space.
        If ``foo`` already exists in the current space, updates its formula.

        If the current space does not exist, a new space is created.
        If the current model does not exist, a new model is also created::

            >>> import modelx as mx

            >>> @mx.defcells
            ... def foo(x):
            ...     return x

            >>> foo
            <Cells Model1.Space1.foo(x)>

        If a cells with the same name already exists in the current space,
        its formula is updated based on the decorated function::

            >>> bar = foo

            >>> @mx.defcells
            ... def foo(x):
            ...     return 2 * x

            >>> foo is bar
            True

        **2. As a decorator with arguments**

        The code below creates an uncached cells in a specified space
        with the specified name, "bar".
        If the cells named "bar" already exists in the specified space,
        update its formula and ``is_cached`` property::

            >>> space = mx.new_space("Foo")

            >>> @mx.defcells(space=space, name='bar', is_cached=False)
            ... def foo(x):
            ...     return x

            >>> foo
            <Cells Model1.Foo.bar(x)>

            >>> foo.is_cached
            False

        **3. As a function**

        Creates multiple cells from multiple function definitions::

            def foo(x):
                return x

            def bar(y):
                return foo(y)

            foo, bar = defcells(foo, bar)

    Args:
        space (optional): For usage 2, specifies the space to create the cells in. Defaults to the current space of the current model.
        name (optional): For usage 2, specifies the name of the created cells. Defaults to the function name.
        is_cached (optional): For usage 2, a boolean indicating whether the cells should be cached. Defaults to :obj:`True` when creating a new cell and :obj:`False` when updating an existing cell.
        *funcs: For usage 3, function objects. (``space`` and ``name`` can also accept function objects for this usage.)

    Returns:
        For usage 1 and 2, the newly created single cells is returned.
        For usage 3, a list of newly created cells is returned.

    .. seealso:: :func:`uncached`

    .. versionchanged:: 0.27.0: :func:`cached` is introduced as an alies.

    .. versionchanged:: 0.27.0: The ``is_cached`` parameter is introduced.

    .. versionchanged:: 0.1.0
        If the current space does not exist, a new space is created.
        If the current model does not exist, a new model is created.

    .. versionchanged:: 0.1.0
        If a cells with the same name already exists in the current space,
        its formula is updated based on the decorated function.
    """
    if isinstance(space, _FunctionType) and name is None:
        # called as a function decorator
        func = space
        space = _system.get_curspace()
        return _CellsMaker(
            space=space, name=func.__name__, is_cached=is_cached
        ).create_or_change_cells(func)

    elif (isinstance(space, _Space) or space is None) and (
        isinstance(name, str) or name is None
    ):
        # return decorator itself
        if space is None:
            space = _system.get_curspace().interface

        return _CellsMaker(space=space._impl, name=name, is_cached=is_cached)

    elif all(
        isinstance(func, _FunctionType) for func in (space, name) + funcs
    ):
        if isinstance(is_cached, _FunctionType):
            return [defcells(func) for func in (space, name, is_cached) + funcs]
        else:
            return [defcells(func) for func in (space, name) + funcs]

    else:
        raise TypeError("invalid defcells arguments")


cached = defcells

def uncached(space=None, name=None, *funcs):
    """Decorator to create or update an uncached cells from a Python function.

    This decorator is an alies for :func:`defcells(is_cached=False)<defcells>`.

    Example:

        .. code-block:: python

            import modelx as mx

            @mx.uncached
            def foo(x):
                return x

    .. seealso:: :func:`defcells`

    .. versionadded:: 0.27.0
    """
    return defcells(space, name, is_cached=False, *funcs)


def defmacro(model=None, name=None, *funcs):
    """Decorator to create or update a macro from a Python function.
    
    This convenience function serves as a decorator to create a new macro or
    update an existing macro directly from a Python function definition.
    Macros are Python functions that can be saved within a Model and executed
    to manipulate or query the model.
    
    All macros in a model share the same dedicated global namespace.
    In the namespace, the model is defined as a global variable, ``mx_model``
    as well as by its model name.
    
    Examples:
    
        **1. As a decorator without arguments**
        
        The code below creates a macro in the current model.
        If a macro with the same name already exists, updates its formula.
        
        If the current model does not exist, a new model is created::
        
            >>> import modelx as mx
            
            >>> m = mx.new_model('MyModel')
            
            >>> @mx.defmacro
            ... def get_model_name():
            ...     return mx_model._name
            
            >>> get_model_name
            <Macro MyModel.get_model_name>
            
            >>> m.get_model_name()
            'MyModel'
        
        **2. As a decorator with arguments**
        
        The code below creates a macro in a specified model with the specified name::
        
            >>> m = mx.new_model('MyModel')
            
            >>> @mx.defmacro(model=m, name='print_name')
            ... def print_model_name(message):
            ...     print(f"{message} {get_model_name()}")
            
            >>> print_model_name
            <Macro MyModel.print_name>
            
            >>> m.print_name("This model is")
            This model is MyModel
        
        **3. As a function**
        
        Creates multiple macros from multiple function definitions::
        
            def foo():
                return mx_model._name
            
            def bar():
                return foo()
            
            foo, bar = defmacro(foo, bar)
    
    Args:
        model (optional): For usage 2, specifies the model to create the macro in.
            Defaults to the current model.
        name (optional): For usage 2, specifies the name of the created macro.
            Defaults to the function name.
        *funcs: For usage 3, function objects. (``model`` and ``name`` can also
            accept function objects for this usage.)
    
    Returns:
        For usage 1 and 2, the newly created single macro is returned.
        For usage 3, a list of newly created macros is returned.
    
    .. versionadded:: 0.30.0
    """
    if isinstance(model, _FunctionType) and name is None:
        # called as a function decorator
        func = model
        cur_model_obj = cur_model()
        if cur_model_obj is None:
            cur_model_obj = new_model()
        return _MacroMaker(
            model=cur_model_obj._impl, name=func.__name__
        ).create_or_change_macro(func)
    
    elif (isinstance(model, _Model) or model is None) and (
        isinstance(name, str) or name is None
    ):
        # return decorator itself
        if model is None:
            cur_model_obj = cur_model()
            if cur_model_obj is None:
                cur_model_obj = new_model()
            model = cur_model_obj
        
        return _MacroMaker(model=model._impl, name=name)
    
    elif all(
        isinstance(func, _FunctionType) for func in (model, name) + funcs
    ):
        return [defmacro(func) for func in (model, name) + funcs]
    
    else:
        raise TypeError("invalid defmacro arguments")


def get_models():
    """Returns a dict that maps model names to models.

    From Python 3.7, :attr:`modelx.models` attribute of :mod:`modelx` module
    is available as an alias for this function.
    """
    return _get_interfaces(_system.models)


if _sys.version_info >= (3, 7):
    def __getattr__(name: str):
        if name == "models":
            return get_models()
        elif name in get_models():
            return get_models()[name]
        raise AttributeError(f"module {__name__} has no attribute {name}")

    def __dir__():
        names = list(globals())
        names.append("models")
        names.extend(get_models())
        return names


def get_object(name: str, as_proxy=False):
    """Get a modelx object from its full name."""
    return _system.get_object(name, as_proxy)


def _get_node(name: str, args: str):
    """Get node from object name and arg string

    Not Used. Left for future reference purpose.
    """
    obj = get_object(name)
    args = _ast.literal_eval(args)
    if not isinstance(args, tuple):
        args = (args,)

    return obj.node(*args)


def cur_model(model=None):
    """Get and/or set the current model.

    If ``model`` is given, set the current model to ``model`` and return it.
    ``model`` can be the name of a model object, or a model object itself.
    If ``model`` is not given, the current model is returned.
    """
    if model is None:
        if _system.currentmodel is not None:
            return _system.currentmodel.interface
        else:
            return None
    else:
        if isinstance(model, _Model):
            _system.currentmodel = model._impl
        else:
            _system.currentmodel = _system.models[model]

        return _system.currentmodel.interface


def cur_space(space=None):
    """Get and/or set the current space of the current model.

    If ``name`` is given, the current space of the current model is
    set to ``name`` and return it.
    If ``name`` is not given, the current space of the current model
    is returned.
    """
    if space is None:
        if _system.currentmodel is not None:
            if _system.currentmodel.currentspace is not None:
                return _system.currentmodel.currentspace.interface
            else:
                return None
        else:
            return None
    else:
        if isinstance(space, _Space):
            cur_model(space.model)
            _system.currentmodel.currentspace = space._impl
        else:
            _system.currentmodel.currentspace = _system.currentmodel.spaces[
                space
            ]

        return cur_space()


def start_stacktrace(maxlen=10000):
    """Activate stack tracing.

    Start tracing the call stack of formula calculations held internally
    in modelx.

    The tracing is useful when the user wants to get the information on
    the execution of cells formulas, such as
    how much time each formula takes from start to finish, or
    what formulas are called in what order to identify performance bottlenecks.

    While the tracing is active, the history of
    loading and unloading cells and its arguments to/from the call stack
    is recorded with timestamps
    and available through calling :func:`get_stacktrace` function.
    The tracing continues until the user calls :func:`stop_stacktrace`.

    Warning:
        Activating stack tracing may slow down formula calculations.
        You should activate it only when needed for inspection purposes.

    Args:
        maxlen(:obj:`int`, optional): Max number of records to be kept. When
            exceeding, records are removed from the oldest. Defaults to 10000.

    See Also:
        :func:`stop_stacktrace`
        :func:`get_stacktrace`
        :func:`clear_stacktrace`

    .. versionchanged:: 0.1.0 `maxlen` parameter is added.
    .. versionadded:: 0.0.25
    """
    return _system.start_stacktrace(maxlen=maxlen)


def stop_stacktrace():
    """Deactivate stack tracing.

    Stop tracing the call stack of formula calculations started
    by :func:`start_stacktrace`.
    If the tracing is not active, a runtime error is raised.

    See Also:
        :func:`start_stacktrace`
        :func:`get_stacktrace`
        :func:`clear_stacktrace`

    .. versionadded:: 0.0.25
    """
    return _system.stop_stacktrace()


def clear_stacktrace():
    """Clear stack trace.

    If the tracing is not active, a runtime error is raised.

    See Also:
        :func:`start_stacktrace`
        :func:`stop_stacktrace`
        :func:`get_stacktrace`

    .. versionadded:: 0.0.25
    """
    return _system.clear_stacktrace()


def get_stacktrace(summarize=False):
    """Get stack trace.

    If ``summarize`` is set to ``False`` (default),
    returns the call stack trace. The stack trace is a list
    of tuples each of which represents one of two types of operations,
    push("ENTER") or pop("EXIT") to/from the call stack.
    The table blow shows data sored in the tuple elements.

    ===== =========================================
    Index Content
    ===== =========================================
        0 "ENTER" or "EXIT"
        1 Stack position
        2 Time (Seconds elapsed from the epoch_)
        3 String to represent Cells object
        4 A tuple of arguments to the Cells object
    ===== =========================================

    .. _epoch: https://docs.python.org/3/library/time.html#epoch

    If ``summarize`` is set to ``True``, returns a summary of the trace.
    The summary is a :obj:`dict`, whose keys are the representation
    strings of the called Cells, and whose values are dicts
    containing the following statistics of the Cells.

    ================== ======================================================
    Key                Value
    ================== ======================================================
    "calls"            Number of calls to the Cells
    "duration"         Total time in seconds elapsed in the Cells
    "first_entry_at"   Time (from the epoch_) of the first entry to the Cells
    "last_exit_at"     Time (from the epoch_) of the last exit from the Cells
    ================== ======================================================

    The call stack trace must be activated by :func:`start_stacktrace`
    before using :func:`get_stacktrace`, otherwise a runtime error is raised.
    When setting ``summarize`` to ``True``,
    make sure that :func:`start_stacktrace`
    was called with its parameter ``maxlen`` being set to ``None``,
    otherwise :func:`get_stacktrace` may raise an Error because of
    incomplete trace records.

    Returns:
        A list of tuples each of which is a record of stack history,
        or a dict containing the summary information.

    Example:
        The sample code below creates and executes a sample model,
        and stores a trace summary of the execution
        as Pandas DataFrame::

            import time
            import pandas as pd
            import modelx as mx

            m = mx.new_model()

            m.time = time

            @mx.defcells
            def foo(x):
                time.sleep(0.1)     # Waits 0.1 second
                return foo(x-1) + 1 if x > 0 else bar()

            @mx.defcells
            def bar():
                time.sleep(0.2)     # Waits 0.2 second
                return 0

            mx.start_stacktrace(maxlen=None)

            foo(5)

            df = pd.DataFrame.from_dict(
                mx.get_stacktrace(summarize=True), orient="index")

            mx.stop_stacktrace()

        The DataFrame shows how many times each formula was called,
        how much time each formula took, time at which
        the execution enters into each formula for the first time,
        and time at which the execution leaves each formula for the last.

        ====================== ======== ======================= ======================= =====================
        Cells                     calls               duration     first_entry_at         last_exit_at
        ====================== ======== ======================= ======================= =====================
        Model1.Space1.foo(x)         6   0.6097867488861084       1605873067.2099519      1605873068.0203028
        Model1.Space1.bar()          1   0.20056414604187012      1605873067.8197386      1605873068.0203028
        ====================== ======== ======================= ======================= =====================

    See Also:
        :func:`start_stacktrace`
        :func:`stop_stacktrace`
        :func:`clear_stacktrace`

    .. versionchanged:: 0.11.0 `summarize` parameter is added.
    .. versionadded:: 0.0.25
    """
    return _system.get_stacktrace(summarize)


@contextmanager
def trace_stack(maxlen=10000):
    """Context manager to activate stack trace in with statements"""
    start_stacktrace(maxlen)
    try:
        yield None
    finally:
        clear_stacktrace()
        stop_stacktrace()


def write_model(model, model_path, backup=True, log_input=False, version=None):
    """Write model to files.

    Write ``model`` to text files in a folder(directory) tree at ``model_path``.

    Model attributes, such as its name and refs, are output in the file
    named *_model.py*, directly under `model_path`.
    For each space in the model, a text file is created with the same name
    as the space with ".py" extension. The tree structure of the spaces
    is represented by the tree of folders, i.e. child spaces
    of a space is stored in a folder named the space.

    Generated text files are Python pseudo-scripts, i.e. they are
    syntactically correct but semantically not-correct Python scripts,
    that can only be interpreted through :py:func:`~read_model` function.

    Dynamic spaces and cells values are not stored.

    For spaces and cells created
    by :py:meth:`~modelx.core.space.UserSpace.new_space_from_excel` and
    :py:meth:`~modelx.core.space.UserSpace.new_cells_from_excel`,
    the source Excel files are copied into the same directory where
    the text files for the spaces the methods are associated with are located.
    Then when the model is read by :py:func:`~read_model` function,
    the methods are invoked to create the spaces or cells.

    Method :py:meth:`~modelx.core.model.Model.write` performs the same operation.

    .. versionchanged:: 0.8.0 ``log_input`` parameter is added.

    .. versionchanged:: 0.1.0 ``version`` parameter is added.

    .. versionadded:: 0.0.22

    Warning:
        The order of members of each type (Space, Cells, Ref)
        is not preserved by :func:`write_model` and :func:`read_model`.

    Args:
        model: Model object to write.
        model_path(str): Folder path where the model will be output.
        backup(bool, optional): Whether to backup the directory/folder
            if it already exists. Defaults to ``True``.
        log_input(bool, optional): If ``True``, input values in Cells are
            output to *_input_log.txt* under ``model_path``. Defaults
            to ``False``.
        version(int, optional): Format version to write model.
            Defaults to the most recent version.

    """
    return _serialize.write_model(
        _system, model, model_path, is_zip=False,
        backup=backup, log_input=log_input, version=version)


def zip_model(model, model_path, backup=True, log_input=False,
              compression=zipfile.ZIP_DEFLATED, compresslevel=None,
              version=None):
    """Archive model to a zip file

    Write ``model`` to a single zip file. The contents are the
    same as the directory tree output by the :func:`write_model` function.

    .. versionchanged:: 0.9.0
        ``compression`` and ``compresslevel`` parameters are added.

    .. versionadded:: 0.8.0

    Args:
        model: Model object to archive.
        model_path(str): Path to the zip file.
        backup(bool, optional): Whether to backup an existing file with
            the same name if it already exists. Defaults to ``True``.
        log_input(bool, optional): If ``True``, input values in Cells are
            output to *_input_log.txt* under ``model_path``. Defaults
            to ``False``.
        compression(optional): Identifier of the ZIP compression method
            to use. This method uses `zipfile.ZipFile`_ class internally
            and ``compression`` and ``compresslevel`` arguments are
            passed to `zipfile.ZipFile`_ constructor.
            See `zipfile.ZipFile`_ manual page for available identifiers.
            Defaults to `zipfile.ZIP_DEFLATED`_.
        compresslevel(optional):
            Integer identifier to indicate the compression level to use.
            If not specified, the default compression level is used.
            See `zipfile.ZipFile`_ explanation on the Python Standard
            Library site for available integer identifiers for
            each compression method.
            For Python 3.6, this parameter is ignored.

        version(int, optional): Format version to write model.
            Defaults to the most recent version.
            This parameter should be left unspecified in normal cases.

    .. _zipfile.ZipFile:
       https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile

    .. _zipfile.ZIP_DEFLATED:
       https://docs.python.org/3/library/zipfile.html#zipfile.ZIP_DEFLATED

    See Also:
        :func:`write_model`
    """
    return _serialize.write_model(
        _system, model, model_path, is_zip=True,
        backup=backup, log_input=log_input,
        compression=compression, compresslevel=compresslevel,
        version=version)


def read_model(model_path, name=None):
    """Read model from files.

    Read model form a folder(directory) tree or a zip file ``model_path``.
    The model must be saved either by :py:func:`~write_model`,
    :py:meth:`Model.write<modelx.core.model.Model.write>`,
    :py:func:`~write_model`
    or :py:meth:`Model.zip<modelx.core.model.Model.zip>`.

    .. versionadded:: 0.0.22

    Args:
        model_path(str): Path to a model folder or a zipped model file.
        name(str, optional): Model name to overwrite the saved name.

    Returns:
        A Model object constructed from the files.

    """
    return _serialize.read_model(_system, model_path, name=name)


def get_recalc():
    """Return :obj:`True` if dependent values are recalculated,
    :obj:`False` if they are cleared.

    If this option is set to :py:obj:`True`, when a value is assigned to a cell
    by the user to overwrite the cell's existing value, values of the cells
    that depend on the overwritten cell are recalculated.
    If the option is set to :obj:`False`, the dependent values are cleared.
    By default, the option is set to :obj:`True`.

    Returns:
        bool: `True` if dependents are recalculated, `False` if cleared.

    See also:
        :func:`set_recalc`
    """
    return _system._recalc_dependents


def set_recalc(recalc):
    """Set the recalculation option.

    If this option is set to :py:obj:`True`, when a value is assigned to a cell
    by the user to overwrite the cell's existing value, values of the cells
    that depend on the overwritten cell are recalculated.
    If the option is set to :obj:`False`, the dependent values are cleared.
    By default, the option is set to :obj:`False`.

    Args:
        recalc(bool):  :obj:`True` to recalculate, :obj:`False`
            to clear values.

    See also:
        :func:`get_recalc`
    """
    _system._recalc_dependents = bool(recalc)


def get_error():
    """Returns exception raised during last formula execution

    If the last formula execution is failed, returns the exception,
    otherwise returns None.
    """
    if _system.executor.excinfo:
        return _system.executor.excinfo[1]
    else:
        return None


def get_traceback(show_locals=False):
    """Traces back the last formula error.

    Returns traceback information if an error is thrown during the last formula
    execution. Otherwise, returns an empty list.
    The traceback information is a list of tuples, each of which
    has 2 or 3 elements depending on ``show_locals``.
    The first element is a *Node* object representing a call to a formula.
    The second element is the line number at which point, the formula
    either called the next formula or raised the error.
    When ``show_locals`` is :obj:`True`, there exists another elemet.
    The third element is a :obj:`dict` of the local variables
    referenced by the formula execution.

    Args:
        show_locals(:obj:`bool`, optional):
            Whether to show the local variabls of each call.
            :obj:`False` by default.

    Example:

        .. code-block:: python

            >>> import modelx as mx

            >>> @mx.defcells
            ... def foo(x):
            ...     a = 1
            ...     return bar(x) + a

            >>> @mx.defcells
            ... def bar(y):
            ...     b = 2
            ...     return 2 * y / 0  # raises ZeroDivisionError

            >>> foo(1)
            modelx.core.errors.FormulaError: Error raised during formula execution
            ZeroDivisionError: division by zero
            Formula traceback:
            0: Model1.Space1.foo(x=1), line 3
            1: Model1.Space1.bar(y=1), line 3
            Formula source:
            def bar(y):
                b = 2
                return 2 * y / 0 #  raise ZeroDivizion

            >>> mx.get_traceback(show_locals=True)
            [(Model1.Space1.foo(x=1), 3, {'x': 1, 'a': 1}),
             (Model1.Space1.bar(y=1), 3, {'y': 1, 'b': 2})]

    .. versionchanged:: 0.22.0 ``show_locals`` option is added.
    .. versionchanged:: 0.21.0 The 3rd element is added.
    .. seealso:: :func:`trace_locals`
    """
    if _system.executor.errorstack:
        return _system.executor.errorstack.get_traceback(show_locals)
    else:
        return []


def trace_locals(index=-1):
    """Retuns the local variables of a formula execution in the last traceback.

    This function is a shotcut for
    :func:`get_traceback()[index][2]<get_traceback>`, and
    returns a :obj:`dict` of the local variables referenced by
    the formula execution at ``index`` in the traceback list.
    By default, ``index`` is -1, so the local variables
    of the last formula execution in which the error is raised, are returned.

    If the last formula execution is sucessful, i.e. the traceback list is
    empty, then returns :obj:`None`.

    Args:
        index(optional): The position of the formula exectuion in the traceback list.

    Example:

        .. code-block:: python

            >>> import modelx as mx

            >>> @mx.defcells
            ... def foo(x):
            ...     a = 1
            ...     return bar(x) + a

            >>> @mx.defcells
            ... def bar(y):
            ...     b = 2
            ...     return 2 * y / 0  # raises ZeroDivisionError

            >>> foo(1)
            modelx.core.errors.FormulaError: Error raised during formula execution
            ZeroDivisionError: division by zero
            Formula traceback:
            0: Model1.Space1.foo(x=1), line 3
            1: Model1.Space1.bar(y=1), line 3
            Formula source:
            def bar(y):
                b = 2
                return 2 * y / 0 #  raise ZeroDivizion

            >>> mx.trace_locals()
            {'y': 1, 'b': 2}

            >>> mx.trace_locals(-2)
            {'x': 1, 'a': 1}

    .. versionadded: 0.21.0

    .. seealso:: :func:`get_traceback`

    """
    if _system.executor.errorstack:
        return _system.executor.errorstack.get_traceback(show_locals=True)[index][2]
    else:
        return None


def use_formula_error(use=None):
    """Specifies whether to replace error raised during formula execution

    By default, modelx traps errors raised during formula execution,
    and raise ``FormulaError`` instead. :func:`get_formula_error` can be used
    to get the original errors.
    You can change the behaviour by passing ``False`` to this function,
    so that the original errors are raised.
    If no argument is given, returns the current setting.
    """
    if use is not None:
        _system.executor.is_formula_error_used = bool(use)

    return _system.executor.is_formula_error_used


def handle_formula_error(handle=None):
    """Specifies whether to raise FormulaError

    If :obj:`True` is given to ``handle``,
    modelx does not raise FormulaError, but instead output the error message to stderr.
    If :obj:`False` is given to ``handle``,
    modelx raises FormulaError, which is the default behaviour.

    If no ``handle`` is given, i.e. ``handle`` is :obj:`None`,
    just returns, the current setting.

    Args:
        handle(:obj:`bool`, optional): Whether to handle FormulaError

    .. versionadded:: 0.22.0
    """
    if handle is not None:
        _system.executor.is_formula_error_handled = bool(handle)

    return _system.executor.is_formula_error_handled


def export_model(model, path):
    """Export a given model as a self-contained Python package.

    .. warning:: This function is currently experimental
            and subject to limitations detailed below.

    This function exports the provided ``model`` as a Python package.
    The resulting package is self-contained, meaning it does not require modelx.

    In the resulting package,
    classes are defined to represent the original model and its spaces.
    The cells from the original model are exported
    as methods within these space classes.

    Upon importing the generated package,
    an instance of the model class is created.
    This model can be accessed as ``mx_model``,
    or under the name of the original model within the package's namespace.

    Values of types :obj:`int`, :obj:`str`, and :obj:`float` that are assigned
    to references are output as literals within the package's modules.

    Values associated with PandasData objects are saved in files within the package.
    The metadata from these PandasData objects are output
    as dictionary literals in the *_mx_io.py* module of the package.

    Values not associated with any IOSpec objects
    (except for those of the types listed above) are serialized (pickled)
    and stored in the *_mx_pickled* file within the package.

    **Limitations**

    As this function is currently experimental,
    not all modelx models can be exported. Current limitations include:

    * Relative references in ItemSpaces are not supported.
      All references within an ItemSpace are bound
      to the same objects their base references point to.

    * Objects associated with IOSpec other than PandasData,
      such as ExcelRange and ModuleData, are not supported.

    * modelx coerces a Cells object without parameters to its value
      when used as an operand of arithmetic operators
      (e.g., ``+``, ``-``, ``*``, ``/``).
      This coercion does not occur in the exported models
      and will be deprecated in future modelx releases.
      Users should ensure that such Cells are called using ``()``
      in the original model's formulas.

    Args:
        model: The Model object to be exported.
        path: The path where the generated Python package will be located.

    .. seealso:: :meth:`~modelx.core.model.Model.export`
    .. versionadded:: 0.22.0
    """
    from ..export.exporter import Exporter
    Exporter(model, path).export()


def _new_cells_keep_source(space, formula):
    """Used by deserializer"""
    return space._impl.spmgr.new_cells(
        space._impl, formula=formula, edit_source=False).interface


def export_members(space: _Space, module='__main__'):
    """Export members of a space to a module's global namespace.

    This function defines global variables in the specified module
    for all static members (spaces, cells, refs) of the given ``space``.

    The global variables are named the same as the member names
    and reference the corresponding member objects.
    By default, the members are exported to the ``__main__`` module,
    making them accessible directly in the main script or interactive shell.

    Args:
        space: The space whose members are to be exported.
        module(str, optional): The name of the module to which
            the members will be exported. Defaults to ``'__main__'``.

    Example:

        .. code-block:: python

            >>> import modelx as mx

            >>> s = m.new_space()   # Create a new model and space

            >>> @mx.defcells
            ... def foo(x):
            ...     return x

            >>> del foo  # Remove foo from __main__

            >>> foo(5)  # Raises NameError: name 'foo' is not defined

            >>> mx.export_members(s) # Export members to __main__

            >>> foo(5)  # Now foo is accessible in __main__
            5
    """
    if not isinstance(space, _Space):
        raise TypeError("space must be a Space object")

    if not isinstance(module, str):
        raise TypeError("module must be a string")

    mod = sys.modules[module]
    for name, member in _itertools.chain(
            space.cells.items(), space.refs.items(), space.spaces.items()):
        setattr(mod, name, member)
