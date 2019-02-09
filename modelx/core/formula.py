# Copyright (c) 2017-2019 Fumito Hamamura <fumito.ham@gmail.com>

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

import os
import ast
import warnings
from types import FunctionType
from inspect import signature, getsource, getsourcefile
from textwrap import dedent
import tokenize
import io


def fix_lamdaline(source):
    """Remove the last redundant token from lambda expression

    lambda x: return x)
                      ^
    Return string without irrelevant tokens
    returned from inspect.getsource on lamda expr returns
    """

    # Using undocumented generate_tokens due to a tokenize.tokenize bug
    # See https://bugs.python.org/issue23297
    strio = io.StringIO(source)
    gen = tokenize.generate_tokens(strio.readline)

    tkns = []
    try:
        for t in gen:
            tkns.append(t)
    except tokenize.TokenError:
        pass

    # Find the position of 'lambda'
    lambda_pos = [(t.type, t.string)
                  for t in tkns].index((tokenize.NAME, 'lambda'))

    # Ignore tokes before 'lambda'
    tkns = tkns[lambda_pos:]

    # Find the position of th las OP
    lastop_pos = len(tkns) -1 - [t.type for t in tkns[::-1]].index(tokenize.OP)
    lastop = tkns[lastop_pos]

    # Remove OP from the line
    fiedlineno = lastop.start[0]
    fixedline = lastop.line[:lastop.start[1]] + lastop.line[lastop.end[1]:]

    tkns = tkns[:lastop_pos]

    fixedlines = ""
    last_lineno = 0
    for t in tkns:
        if last_lineno == t.start[0]:
            continue
        elif t.start[0] == fiedlineno:
            fixedlines += fixedline
            last_lineno = t.start[0]
        else:
            fixedlines += t.line
            last_lineno = t.start[0]

    return fixedlines


def find_funcdef(source):
    """Find the first FuncDef ast object in source"""

    try:
        module_node = compile(source, '<string>', mode='exec',
                              flags=ast.PyCF_ONLY_AST)
    except SyntaxError:
        return find_funcdef(fix_lamdaline(source))

    for node in ast.walk(module_node):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.Lambda):
            return node

    raise ValueError("function definition not found")


def extract_params(source):
    """Extract parameters from a function definition"""

    funcdef = find_funcdef(source)
    params = []
    for node in ast.walk(funcdef.args):
        if isinstance(node, ast.arg):
            if node.arg not in params:
                params.append(node.arg)

    return params


def extract_names(source):
    """Extract names from a function definition

    Looks for a function definition in the source.
    Only the first function definition is examined.

    Returns:
         a list names(identifiers) used in the body of the function
         excluding function parameters.
    """
    if source is None:
        return None

    source = dedent(source)
    funcdef = find_funcdef(source)
    params = extract_params(source)
    names = []

    if isinstance(funcdef, ast.FunctionDef):
        stmts = funcdef.body
    elif isinstance(funcdef, ast.Lambda):
        stmts = [funcdef.body]
    else:
        raise ValueError("must not happen")

    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                if node.id not in names and node.id not in params:
                    names.append(node.id)

    return names


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
            if isinstance(obj, FunctionType) \
                    and getsourcefile(obj) == file:
                srcfuncs[name] = obj

        self.funcs = {}
        for name in module_.__dict__:
            obj = getattr(module_, name)
            if isinstance(obj, FunctionType) \
                    and obj.__module__ == self.name \
                    and name in srcfuncs \
                    and getsource(obj) == getsource(srcfuncs[name]):

                self.funcs[name] = obj


class Formula:

    __slots__ = ('func', 'signature', 'source', 'module_', 'srcnames')

    def __init__(self, func, module_=None):

        if isinstance(func, Formula):
            self._copy_other(func)

        elif callable(func):
            self.func = func
            self.signature = signature(func)
            try:
                self.source = getsource(func)
            except:
                warnings.warn(
                    "Cannot retrieve source code for function '%s'. "
                    "%s.source set to None." % (func.__name__, func.__name__))
                self.source = None

        elif isinstance(func, str):

            func = dedent(func)
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

        self.srcnames = extract_names(self.source)

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
        return tuple(self.signature.parameters)

    def __getstate__(self):
        """Specify members to pickle."""
        return {'source': self.source,
                'module_': self.module_}

    def __setstate__(self, state):
        self.__init__(func=state['source'],
                      module_=state['module_'])

    def __repr__(self):
        return self.source

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

    def _to_attrdict(self, attrs=None):
        return {'source': self.source}


NULL_FORMULA = Formula('lambda: None')


