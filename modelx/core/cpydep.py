# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

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

"""CPython Implementation alteration

This module is not used at the moment but included for future enhancements.

func::`alter_freevars` does not work.
It intended to replace local variables in a compiled function with
free variables, but it turned out to be impossible without changing
the byte code of the function due to difference at instruction level.

Reference:
    http://stackoverflow.com/questions/37665862/how-to-create-new-closure-cell-objects
    https://docs.python.org/3.7/c-api/concrete.html
    https://docs.python.org/3/library/inspect.html
    https://github.com/python/cpython/blob/master/Include/code.h
    https://github.com/python/cpython/blob/master/Objects/funcobject.c
    https://github.com/python/cpython/blob/master/Objects/codeobject.c
    https://code.activestate.com/recipes/580716-unit-testing-nested-functions/
"""


import ctypes
import inspect
from types import FunctionType

def _alter_code(code, **attrs):
    """Create a new code object by altering some of ``code`` attributes

    Args:
        code: code objcect
        attrs: a mapping of names of code object attrs to their values
    """

    PyCode_New = ctypes.pythonapi.PyCode_New

    PyCode_New.argtypes = (
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.py_object,
        ctypes.c_int,
        ctypes.py_object)

    PyCode_New.restype = ctypes.py_object

    args = [
        [code.co_argcount, 'co_argcount'],
        [code.co_kwonlyargcount, 'co_kwonlyargcount'],
        [code.co_nlocals, 'co_nlocals'],
        [code.co_stacksize, 'co_stacksize'],
        [code.co_flags, 'co_flags'],
        [code.co_code, 'co_code'],
        [code.co_consts, 'co_consts'],
        [code.co_names, 'co_names'],
        [code.co_varnames, 'co_varnames'],
        [code.co_freevars, 'co_freevars'],
        [code.co_cellvars, 'co_cellvars'],
        [code.co_filename, 'co_filename'],
        [code.co_name, 'co_name'],
        [code.co_firstlineno, 'co_firstlineno'],
        [code.co_lnotab, 'co_lnotab']]

    for arg in args:
        if arg[1] in attrs:
            arg[0] = attrs[arg[1]]

    return PyCode_New(
        args[0][0],  # code.co_argcount,
        args[1][0],  # code.co_kwonlyargcount,
        args[2][0],  # code.co_nlocals,
        args[3][0],  # code.co_stacksize,
        args[4][0],  # code.co_flags,
        args[5][0],  # code.co_code,
        args[6][0],  # code.co_consts,
        args[7][0],  # code.co_names,
        args[8][0],  # code.co_varnames,
        args[9][0],  # code.co_freevars,
        args[10][0],  # code.co_cellvars,
        args[11][0],  # code.co_filename,
        args[12][0],  # code.co_name,
        args[13][0],  # code.co_firstlineno,
        args[14][0])  # code.co_lnotab)


def _create_cell(value):

    PyCell_New = ctypes.pythonapi.PyCell_New
    PyCell_New.argtypes = (ctypes.py_object,)
    PyCell_New.restype = ctypes.py_object

    return PyCell_New(value)


def _create_closure(*values):
    return tuple(_create_cell(val) for val in values)


def alter_freevars(func, globals_=None, **vars):
    """Replace local variables with free variables

    Warnings:
        This function does not work.
    """

    if globals_ is None:
        globals_ = func.__globals__

    frees = tuple(vars.keys())
    oldlocs = func.__code__.co_names
    newlocs = tuple(name for name in oldlocs if name not in frees)

    code = _alter_code(func.__code__,
                       co_freevars=frees,
                       co_names=newlocs,
                       co_flags=func.__code__.co_flags | inspect.CO_NESTED)
    closure = _create_closure(*vars.values())

    return FunctionType(code, globals_, closure=closure)

