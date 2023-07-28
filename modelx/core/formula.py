# Copyright (c) 2017-2023 Fumito Hamamura <fumito.ham@gmail.com>

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
import tokenize
import io
import dis
from modelx.core.base import (
    LazyEval, get_mixin_slots, add_statemethod, null_impl, Interface)

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


def replace_docstring(source: str, docstr: str, insert_indents=False):
    """Replace docstring"""
    # lines = source.splitlines()
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

        if isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Str):     # Has docstring

            src_front = source[:prev_token.startpos]
            src_back = source[first_stmt.first_token.endpos:]
            return src_front + docstr + src_back

        else:   # No docstring
            src_front = source[:prev_token.startpos]
            src_back = source[prev_token.startpos:]
            return src_front + docstr + "\n" + src_back

    else:    # single line

        if isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Str):     # Has docstring

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
        "func", "signature", "source", "module", "srcnames", "_is_lambda")

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

        self._is_lambda = False

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


@add_statemethod
class BoundFunction(LazyEval):
    """Hold function with updated namespace"""

    __slots__ = ("owner", "global_names", "altfunc") + get_mixin_slots(LazyEval)
    __no_state = ("global_names", "altfunc")

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
        if base is None:
            self.global_names = None
        else:
            self.global_names = base.global_names
        self.set_refresh()

    def _init_names(self):
        return tuple(self._extract_globals(self.owner.formula.func.__code__))

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

    def _refresh_data(self):
        """Update altfunc"""
        if self.global_names is None:
            self.global_names = self._init_names()

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
        names = (self._init_names()
                 if self.global_names is None else self.global_names)

        result = {}
        for mid in ns.map_ids:
            result[mid] = {}

        result["missing"] = {}
        result["builtins"] = {}

        for n in names:
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

    def on_add_item(self, namespace, name, value):
        self.global_names = self._init_names()

    def on_delete_item(self, namespace, name):
        self.global_names = self._init_names()

    def on_update(self, operation, args=()):
        self.global_names = self._init_names()

    def __setstate(self, state):
        self.global_names = None
        self.altfunc = None


class BoundFormula:     # Not Used
    """Hold function with updated namespace"""

    __slots__ = ("owner", "_altfunc", "_referred_names",
                 "need_update_names", "need_update_altfunc")

    def __init__(self, owner):
        self.owner = owner
        self._altfunc = None
        self._referred_names = None
        self.need_update_names = True
        self.need_update_altfunc = True

    @property
    def referred_names(self):
        if self.need_update_names:
            self._referred_names = self._get_referred_names()
            self.need_update_names = False
        return self._referred_names

    @property
    def altfunc(self):
        if self.need_update_altfunc:
            self._altfunc = self._update_altfunc()
            self.need_update_altfunc = False
        return self._altfunc

    def _get_referred_names(self):
        insts = list(dis.get_instructions(self.owner.formula.func.__code__))

        names = []
        for inst in insts:
            if inst.opname == "LOAD_GLOBAL" and inst.argval not in names:
                names.append(inst.argval)

        return set(names)

    def _update_altfunc(self):
        """Update altfunc"""

        func = self.owner.formula.func
        codeobj = func.__code__
        name = func.__name__  # self.cells.name   # func.__name__

        closure = func.__closure__  # None normally.
        if closure is not None:  # pytest fails without this.
            closure = create_closure(self.owner.interface)

        self._altfunc = FunctionType(
            codeobj, self.owner.namespace.interfaces, name=name, closure=closure
        )

    def __getstate__(self):
        return {"owner": self.owner}

    def __setstate__(self, state):
        self.__init__(state["owner"])


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
