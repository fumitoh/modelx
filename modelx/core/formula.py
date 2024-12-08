# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>
import sys
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
from types import FunctionType, CodeType
from inspect import signature, getsource, getsourcefile, findsource
from textwrap import dedent, indent
import dis
from modelx.core.base import (
    LazyEval, get_mixin_slots, Interface)

import asttokens


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


def remove_decorator(source: str, atok):
    """Remove decorators from function definition"""
    lines = source.splitlines(keepends=True)

    for node in ast.walk(atok.tree):
        if isinstance(node, ast.FunctionDef):
            break

    if node.decorator_list:
        deco_first = node.decorator_list[0]
        deco_last = node.decorator_list[-1]
        line_first = atok.tokens[deco_first.first_token.index - 1].start[0]
        line_last = atok.tokens[deco_last.last_token.index + 1].start[0]

        lines = lines[:line_first - 1] + lines[line_last:]

    return ''.join(lines)


def replace_funcname(source: str, name: str):
    """Replace function name"""

    lines = source.splitlines(keepends=True)
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

    return ''.join(lines)


def replace_docstring(source: str, docstr: str, insert_indents=False):
    """Replace docstring"""
    atok = asttokens.ASTTokens(source, parse=True)

    found = False
    for node in ast.walk(atok.tree):
        if isinstance(node, ast.FunctionDef):
            found = True
            break

    if not found:
        raise RuntimeError("FunctionDef not found")

    first_stmt = node.body[0]
    docstr = '"""' + docstr + '"""'
    prev_token = atok.tokens[first_stmt.first_token.index - 1]

    if prev_token.type == token.INDENT:     # compound statements

        # Insert indents
        lines = docstr.splitlines()
        for i, l in enumerate(tuple(lines)):
            if i == 0 or insert_indents:
                lines[i] = indent(l, prev_token.string)

        docstr = "\n".join(lines)

        if sys.version_info >= (3, 8, 0):
            has_docstring = isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str)
        else:
            has_docstring = isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Str)

        if has_docstring:     # Has docstring

            src_front = source[:prev_token.startpos]
            src_back = source[first_stmt.first_token.endpos:]
            return src_front + docstr + src_back

        else:   # No docstring
            src_front = source[:prev_token.startpos]
            src_back = source[prev_token.startpos:]
            return src_front + docstr + "\n" + src_back

    else:    # single line

        if sys.version_info >= (3, 8, 0):
            has_docstring = isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str)
        else:
            has_docstring = isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Str)

        if has_docstring:     # Has docstring

            src_front = source[:first_stmt.first_token.startpos]
            src_back = source[first_stmt.first_token.endpos:]

        else:   # No docstring
            src_front = source[:first_stmt.first_token.startpos]
            src_back = source[first_stmt.first_token.startpos:]

        return src_front + docstr + src_back


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

    __slots__ = (
        "func", "signature", "source", "module", "_is_lambda")

    def __init__(self, func, name=None, module=None, edit_source=True):

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
                self._init_from_func(func, name, edit_source)

            except OSError:
                warnings.warn(
                    "Cannot retrieve source code for function '%s'. "
                    "%s.source set to None." % (func.__name__, func.__name__)
                )
                self.func = func
                self.signature = signature(func)
                self.source = None

        elif isinstance(func, str):
            self.module = module
            self._init_from_source(func, name, edit_source)
        else:
            raise ValueError("Invalid argument func: %s" % func)

    def _init_from_func(self, func: FunctionType, name: str, edit_source: bool):

        if is_func_lambda(func):
            src = extract_lambda_from_func(func)
            self._init_from_lambda(src, name)
        else:
            self._init_from_funcdef(getsource(func), name, edit_source)

    def _init_from_source(self, src: str, name: str, edit_source: bool):

        if is_funcdef(src):
            self._init_from_funcdef(src, name, edit_source)
        elif has_lambda(src):
            src = extract_lambda_from_source(dedent(src))
            self._init_from_lambda(src, name)
        else:
            raise ValueError("invalid function or lambda definition")

    def _init_from_funcdef(self, src: str, name: str, edit_source: bool):

        self._is_lambda = False

        src = dedent(src).rstrip() + "\n"   # End src with newline
        if edit_source:
            module_node = asttokens.ASTTokens(src, parse=True)
            src = remove_decorator(src, module_node)
            if name:
                src = replace_funcname(src, name)
            else:
                name = module_node.tree.body[0].name

        namespace = {}
        code = compile(src, "<string>", mode="exec")
        exec(code, namespace)

        if edit_source:
            self.func = namespace[name]
        if not edit_source:
            # Get function name from code object
            if len(code.co_names) == 1:
                self.func = namespace[code.co_names[0]]
            else:
                for n in code.co_names:
                    # ex. def foo(x: str) -> co_names = ('str', 'foo')
                    v = namespace.get(n, None)
                    if isinstance(v, FunctionType):
                        self.func = v
                        break

        self.signature = signature(self.func)
        self.source = src

    def _init_from_lambda(self, src: str, name: str):

        self._is_lambda = True

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

    def _get_attrdict(self, extattrs=None, recursive=True):
        return {"source": self.source}


class NullFormula(Formula):
    """Formula sub class for NULL_FORMULA"""


NULL_FORMULA = NullFormula("lambda: None")


class BoundFunction(LazyEval):
    """Hold function with updated namespace"""

    __slots__ = (
        "owner",
        "_global_names",
        "_is_names_updated",
        "altfunc") + get_mixin_slots(LazyEval)

    def __init__(self, owner, base=None):
        """Create altered function from owner's formula.

        owner is a UserSpaceImpl or CellsImpl, which has formula, and
        namespace_impl as its members.
        """
        LazyEval.__init__(self, [])
        self.owner = owner

        # Must not update owner's namespace to avoid circular updates.
        self.observe(owner._namespace)
        self.altfunc = None
        self.notify()

    @property
    def global_names(self):
        if self._is_names_updated:
            return self._global_names
        else:
            self._global_names = tuple(self._extract_globals(self.owner.formula.func.__code__))
            return self._global_names

    def _extract_globals(self, codeobj):

        insts = list(dis.get_instructions(codeobj))

        names = []
        for inst in insts:
            if inst.opname == "LOAD_GLOBAL" and inst.argval not in names:
                names.append(inst.argval)

        # Extract globals in generators and nested functions
        for co in codeobj.co_consts:
            if isinstance(co, CodeType):
                names.extend(self._extract_globals(co))

        return names

    def _refresh(self):
        """Update altfunc"""
        self._is_names_updated = False

        func = self.owner.formula.func
        codeobj = func.__code__
        name = func.__name__  # self.cells.name   # func.__name__

        closure = func.__closure__  # None normally.
        if closure is not None:  # pytest fails without this.
            closure = create_closure(self.owner.interface)

        self.altfunc = FunctionType(
            codeobj, self.owner.namespace.interfaces, name=name, closure=closure
        )

    def get_referents(self):
        ns = self.owner.namespace

        result = {}
        for mid in ns.map_ids:
            result[mid] = {}

        result["missing"] = {}
        result["builtins"] = {}

        for n in self.global_names:
            idx = ns.get_map_index_from_key(n)
            if idx is None:
                if '__builtins__' in ns:
                    builtins = ns['__builtins__'].interface.__dict__
                    if n in builtins:
                        result["builtins"][n] = builtins[n]
                    else:
                        result["missing"][n] = None
                else:
                    result["missing"][n] = None
            else:
                result[ns.map_ids[idx]][n] = ns[n]

        return result


class HasFormula:

    __slots__ = ()
    __mixin_slots = ()

    def get_referents(self):

        if self.formula is None:
            return None
        else:
            refs = self.altfunc.get_referents()
            result = refs.copy()

            for key, data in refs.items():
                if key != "builtins" and key != "missing":
                    result[key] = {name: obj.to_node() for
                                   name, obj in refs[key].items()}
            return result

    def get_valuerefs(self):
        refs = self.get_referents()
        if refs and "refs" in refs:
            return [v for v in refs["refs"].values()
                    if v.has_value()
                    and not isinstance(v.value, Interface)]
        else:
            return []
