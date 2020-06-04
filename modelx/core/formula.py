# Copyright (c) 2017-2020 Fumito Hamamura <fumito.ham@gmail.com>

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

import token
import ast
import warnings
from types import FunctionType
from inspect import signature, getsource, getsourcefile, findsource
from textwrap import dedent
import tokenize
import io

import asttokens


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
    lambda_pos = [(t.type, t.string) for t in tkns].index(
        (tokenize.NAME, "lambda")
    )

    # Ignore tokes before 'lambda'
    tkns = tkns[lambda_pos:]

    # Find the position of th las OP
    lastop_pos = (
        len(tkns) - 1 - [t.type for t in tkns[::-1]].index(tokenize.OP)
    )
    lastop = tkns[lastop_pos]

    # Remove OP from the line
    fiedlineno = lastop.start[0]
    fixedline = lastop.line[: lastop.start[1]] + lastop.line[lastop.end[1] :]

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
        module_node = compile(
            source, "<string>", mode="exec", flags=ast.PyCF_ONLY_AST
        )
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

    def __init__(self, module):

        self.name = module.__name__
        file = module.__file__
        with open(file, "r") as srcfile:
            self.source = srcfile.read()

        codeobj = compile(self.source, file, mode="exec")
        namespace = {}
        eval(codeobj, namespace)

        srcfuncs = {}
        for name in namespace:
            obj = namespace[name]
            if isinstance(obj, FunctionType) and getsourcefile(obj) == file:
                srcfuncs[name] = obj

        self.funcs = {}
        for name in module.__dict__:
            obj = getattr(module, name)
            if (
                isinstance(obj, FunctionType)
                and obj.__module__ == self.name
                and name in srcfuncs
                and getsource(obj) == getsource(srcfuncs[name])
            ):

                self.funcs[name] = obj


def is_funcdef(src: str):
    """True if src is a function definition

    ``src`` must be a valid Python statement
    """

    module_node = ast.parse(dedent(src))

    if len(module_node.body) == 1 and isinstance(
            module_node.body[0], ast.FunctionDef
    ):
        return True
    else:
        return False


def is_lambda(src: str):
    """True if src is a function definition

    ``src`` must be a valid Python expression
    """
    module_node = ast.parse(dedent(src))
    if len(module_node.body) == 1:
        expr_node = module_node.body[0]
        if isinstance(expr_node, ast.Expr) and isinstance(
                expr_node.value, ast.Lambda):
            return True

    return False


def remove_decorator(source: str):
    """Remove decorators from function definition"""
    lines = source.splitlines()
    atok = asttokens.ASTTokens(source, parse=True)

    for node in ast.walk(atok.tree):
        if isinstance(node, ast.FunctionDef):
            break

    if node.decorator_list:
        deco_first = node.decorator_list[0]
        deco_last = node.decorator_list[-1]
        line_first = atok.tokens[deco_first.first_token.index - 1].start[0]
        line_last = atok.tokens[deco_last.last_token.index + 1].start[0]

        lines = lines[:line_first - 1] + lines[line_last:]

    return "\n".join(lines) + "\n"


def replace_funcname(source: str, name: str):
    """Replace function name"""

    lines = source.splitlines()
    atok = asttokens.ASTTokens(source, parse=True)

    for node in ast.walk(atok.tree):
        if isinstance(node, ast.FunctionDef):
            break

    i = node.first_token.index
    for i in range(node.first_token.index, node.last_token.index):
        if (atok.tokens[i].type == token.NAME
                and atok.tokens[i].string == "def"):
            break

    lineno, col_begin = atok.tokens[i + 1].start
    lineno_end, col_end = atok.tokens[i + 1].end

    assert lineno == lineno_end

    lines[lineno-1] = (
            lines[lineno-1][:col_begin] + name + lines[lineno-1][col_end:]
    )

    return "\n".join(lines) + "\n"


def has_lambda(src):
    """True if only one lambda expression is included"""

    module_node = ast.parse(dedent(src))
    lambdaexp = [node for node in ast.walk(module_node)
                 if isinstance(node, ast.Lambda)]

    return bool(lambdaexp)


def is_func_lambda(func: FunctionType):
    return func.__code__.co_name == "<lambda>"


def extract_lambda_from_source(source: str):

    atok = asttokens.ASTTokens(source, parse=True)

    for node in ast.walk(atok.tree):
        if isinstance(node, ast.Lambda):
            break

    return source[node.first_token.startpos:node.last_token.endpos]


def extract_lambda_from_func(func: FunctionType):
    """Get source from function/lambda expression.

    inspect.getsource returns entire lines including tokens following
    the lambda extraction, so undocumented inspect.findsource
    is used.
    """
    lines, row = findsource(func)  # inspect.findsource is not documented.
    src = "".join(lines)
    atok = asttokens.ASTTokens(src, parse=True)

    lambdas = list(n for n in ast.walk(atok.tree)
                   if isinstance(n, ast.Lambda) and
                   n.lineno == row + 1)     # row is 0-indexed

    if len(lambdas) == 1:
        node = lambdas[0]
        return src[node.first_token.startpos:node.last_token.endpos]

    elif len(lambdas) > 0:
        raise ValueError("more than 1 lambda expressions found")
    else:
        raise ValueError("no lambda expression found")


class Formula:

    __slots__ = ("func", "signature", "source", "module", "srcnames")

    def __init__(self, func, name=None, module=None):

        if isinstance(func, NullFormula):   # TODO: Make NULL_FORMULA singleton
            self._copy_other(func)
        elif isinstance(func, Formula):
            self.__init__(func.source, name, module)
        elif isinstance(func, FunctionType):
            if module is not None:
                self.module = module
            else:
                self.module = func.__module__

            try:
                self._init_from_func(func, name)
                self.srcnames = extract_names(self.source)

            except OSError:
                warnings.warn(
                    "Cannot retrieve source code for function '%s'. "
                    "%s.source set to None." % (func.__name__, func.__name__)
                )
                self.func = func
                self.signature = signature(func)
                self.source = None
                self.srcnames = []

        elif isinstance(func, str):
            self.module = module
            self._init_from_source(func, name)
            self.srcnames = extract_names(self.source)
        else:
            raise ValueError("Invalid argument func: %s" % func)

    def _init_from_func(self, func: FunctionType, name: str):

        if is_func_lambda(func):
            src = extract_lambda_from_func(func)
            self._init_from_lambda(src, name)
        else:
            self._init_from_funcdef(getsource(func), name)

    def _init_from_source(self, src: str, name: str):

        if is_funcdef(src):
            self._init_from_funcdef(src, name)
        elif has_lambda(src):
            src = extract_lambda_from_source(dedent(src))
            self._init_from_lambda(src, name)
        else:
            raise ValueError("invalid function or lambda definition")

    def _init_from_funcdef(self, src: str, name: str):

        module_node = ast.parse(dedent(src))
        funcname = name or module_node.body[0].name
        src = remove_decorator(dedent(src))
        if name:
            src = replace_funcname(src, name)

        namespace = {}
        code = compile(src, "<string>", mode="exec")
        exec(code, namespace)

        self.func = namespace[funcname]
        self.signature = signature(self.func)
        self.source = src

    def _init_from_lambda(self, src: str, name: str):

        namespace = {}
        # Assign the lambda to a temporary name to extract its object.
        lambda_assignment = "_lambdafunc = " + src

        exec(lambda_assignment, namespace)
        self.func = namespace["_lambdafunc"]

        if name:
            self.func.__name__ = name

        self.signature = signature(self.func)
        self.source = src

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
        return {"source": self.source, "module": self.module}

    def __setstate__(self, state):
        self.__init__(func=state["source"], module=state["module"])

    def __repr__(self):
        return self.source

    def _reload(self, module=None):
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
        if self.module is None:
            raise RuntimeError
        elif module is None:
            import importlib

            module = ModuleSource(importlib.reload(module))
        elif module.name != self.module:
            raise RuntimeError

        if self.name in module.funcs:
            func = module.funcs[self.name]
            self.__init__(func=func)
        else:
            self.__init__(func=NULL_FORMULA)

        return self

    def _to_attrdict(self, attrs=None):
        return {"source": self.source}


class NullFormula(Formula):
    """Formula sub class for NULL_FORMULA"""


NULL_FORMULA = NullFormula("lambda: None")
