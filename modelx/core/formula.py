import ast
import os
from types import FunctionType
from inspect import signature, getsource


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


class Formula:

    __slots__ = ('func', 'signature', 'source')

    def __init__(self, func):

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

            module_ = compile(func, '<string>', mode='exec',
                              flags=ast.PyCF_ONLY_AST)

            if len(module_.body) == 1 and \
                    isinstance(module_.body[0], ast.FunctionDef):

                funcdef = module_.body[0]
                funcname = funcdef.name
                namespace = {}

                if 'decorator_list' in funcdef._fields:
                    namespace['defcells'] = _dummy_defcells

                exec(func, namespace)

                self.func = namespace[funcname]
                self.signature = signature(self.func)

            elif len(module_.body) == 1 and \
                    isinstance(module_.body[0].value, ast.Lambda):

                funcdef = module_.body[0].value
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

    def _copy_other(self, other):
        for attr in self.__slots__:
            setattr(self, attr, getattr(other, attr))

    @property
    def name(self):
        return self.func.__name__

    def __getstate__(self):
        """Specify members to pickle."""
        return {'source': self.source}

    def __setstate__(self, state):
        self.__init__(state['source'])

NULL_FORMULA = Formula('lambda: None')


