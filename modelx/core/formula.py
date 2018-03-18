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

import ast
import os
from types import FunctionType
from inspect import signature, getsource, getsourcefile

from modelx.core.util import get_module

def create_closure(new_value):
    # Used to prevent pytest from failing.
    # Code modified from:
    # http://stackoverflow.com/questions/37665862/how-to-create-new-closure-cell-objects

    import ctypes

    dummy = None
    def temp_func():
        return dummy

    closure = temp_func.__closure__

    PyCell_Set = ctypes.pythonapi.PyCell_Set

    # ctypes.pythonapi functions need to have argtypes and restype set manually
    PyCell_Set.argtypes = (ctypes.py_object, ctypes.py_object)

    # restype actually defaults to c_int here, but we might as well be explicit
    PyCell_Set.restype = ctypes.c_int

    PyCell_Set(closure[0], new_value)

    return closure


def _dummy_defcells(space=None, name=None):

    if isinstance(space, FunctionType) and name is None:
        # called as a function decorator
        return space

    else:   # called as a deco-maker
        def _dummy_decorator(func):
            return func
        return _dummy_decorator


class ModuleSource:
    """A class to hold function objects defined in a module.

    In Python, when a module is reloaded by ``importlib.reload`` function,
    formula objects created from function definitions in that module
    before reloading still remain accessible through their names in
    the module's global namespace, unless the names are rebound
    to renewed formula objects.

    This class checks function objects in the global namespace of a module
    against function definitions in the module by looking at the module's
    source code, and filter out old functions and only hold new functions
    in its ``funcs`` attribute.
    """

    def __init__(self, module_):
        import types

        self.name = module_.__name__
        file = module_.__file__
        with open(file, 'r') as srcfile:
            self.source = srcfile.read()

        codeobj = compile(self.source, file, mode='exec')
        namespace = {}
        eval(codeobj, namespace)

        srcfuncs = {}
        for name in namespace:
            obj = namespace[name]
            if isinstance(obj, types.FunctionType) \
                    and getsourcefile(obj) == file:
                srcfuncs[name] = obj

        self.funcs = {}
        for name in dir(module_):
            obj = getattr(module_, name)
            if isinstance(obj, types.FunctionType) \
                    and obj.__module__ == self.name \
                    and name in srcfuncs \
                    and getsource(obj) == getsource(srcfuncs[name]):

                self.funcs[name] = obj


class Formula:

    __slots__ = ('func', 'signature', 'source', 'module_')

    def __init__(self, func, module_=None):

        if isinstance(func, Formula):
            self._copy_other(func)

        elif callable(func):
            self.func = func
            self.signature = signature(func)
            try:
                self.source = getsource(func)
            except:
                print("Cannot retrieve source code for %s", func.__name__)

        elif isinstance(func, str):

            module_node = compile(func, '<string>', mode='exec',
                                  flags=ast.PyCF_ONLY_AST)

            if len(module_node.body) == 1 and \
                    isinstance(module_node.body[0], ast.FunctionDef):

                funcdef = module_node.body[0]
                funcname = funcdef.name
                namespace = {}

                if 'decorator_list' in funcdef._fields:
                    namespace['defcells'] = _dummy_defcells

                exec(func, namespace)

                self.func = namespace[funcname]
                self.signature = signature(self.func)

            elif len(module_node.body) == 1 and \
                    isinstance(module_node.body[0].value, ast.Lambda):

                funcdef = module_node.body[0].value
                namespace = {}

                # Assign the lambda to a temporary name to extract its object.
                lambda_assignment = "_lambdafunc = " + \
                    os.linesep.join([s for s in func.splitlines() if s])
                # Remove blank lines.

                exec(lambda_assignment, namespace)
                self.func = namespace['_lambdafunc']
                self.signature = signature(self.func)

            else:
                raise ValueError("func must be a function definition")

            self.source = func

        else:
            raise ValueError("Invalid argument func: %s" % func)

        if module_ is not None:
            self.module_ = module_
        else:
            self.module_ = self.func.__module__

    def _copy_other(self, other):
        for attr in self.__slots__:
            setattr(self, attr, getattr(other, attr))

    @property
    def name(self):
        return self.func.__name__

    @property
    def parameters(self):
        return self.signature.parameters

    def __getstate__(self):
        """Specify members to pickle."""
        return {'source': self.source,
                'module_': self.module_}

    def __setstate__(self, state):
        self.__init__(func=state['source'],
                      module_=state['module_'])

    def _reload(self, module_=None):
        """Reload the source function from the source module.

        **Internal use only**
        Update the source function of the formula.
        This method is used to updated the underlying formula
        when the source code of the module in which the source function
        is read from is modified.

        If the formula was not created from a module, an error is raised.
        If ``module_`` is not given, the source module of the formula is
        reloaded. If ``module_`` is given and matches the source module,
        then the module_ is used without being reloaded.
        If ``module_`` is given and does not match the source module of
        the formula, an error is raised.

        Args:
            module_: A ``ModuleSource`` object

        Returns:
            self
        """
        if self.module_ is None:
            raise RuntimeError
        elif module_ is None:
            import importlib
            module_ = ModuleSource(importlib.reload(module_))
        elif module_.name != self.module_:
            raise RuntimeError

        if self.name in module_.funcs:
            func = module_.funcs[self.name]
            self.__init__(func=func)
        else:
            self.__init__(func=NULL_FORMULA)

        return self


NULL_FORMULA = Formula('lambda: None')


