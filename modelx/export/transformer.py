# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

import builtins
import sys
import textwrap
from collections import namedtuple
import symtable
from typing import Optional, Set

import libcst
# from symtable import symtable, SymbolTable
import libcst as cst
from libcst import FunctionDef, Module
from libcst.metadata import (
    GlobalScope, ClassScope, FunctionScope, ComprehensionScope, ParentNodeProvider)
import libcst.matchers as m


def list_symtable(source) -> list:
    table = symtable.symtable(source, "<string>", compile_type="exec")
    return _list_symtable_inner(table, [])


def _list_symtable_inner(table: symtable.SymbolTable, result: list):
    result.append(table)
    if table.has_children():
        for child in table.get_children():
            _list_symtable_inner(child, result)

    return result


def adjust_scope_table_mapping(scope, table):

    # symtable in Python 3.12+ will not produce child symbol tables for comprehensions due to PEP709
    # libCST continues to produce ComprehensionScope.
    # To maintain the correct order mapping between scope and table, None is inserted in table
    # where ComprehensionScope exists.
    # https://docs.python.org/3/whatsnew/3.12.html#pep-709-comprehension-inlining

    if sys.version_info >= (3, 12):
        for i in range(len(scope)):
            if isinstance(scope[i], ComprehensionScope) and not isinstance(scope[i].node, libcst.GeneratorExp):
                table.insert(i, None)

    assert len(scope) == len(table)

    # Global namespace
    s, t = scope[0], table[0]
    assert isinstance(s, cst.metadata.GlobalScope)
    assert t.get_type() == 'module'

    for s, t in zip(scope[1:], table[1:]):

        if isinstance(s, ClassScope):
            assert t.get_type() == 'class'
            assert s.name == t.get_name()

        elif isinstance(s, FunctionScope):
            assert t.get_type() == 'function'
            if s.name:
                assert s.name == t.get_name()
            else:
                assert t.get_name() == 'lambda'

        elif isinstance(s, ComprehensionScope):
            if sys.version_info >= (3, 12):
                if t is not None:
                    assert t.get_type() == 'function'
                    # genexpr
                    name = t.get_name()
                    assert name == 'genexpr'
            else:
                assert t.get_type() == 'function'
                # listcomp, dictcomp, setcomp, genexpr
                name = t.get_name()
                assert name[-4:] == 'comp' or name == 'genexpr'

        else:
            raise RuntimeError("must not happen")


FuncAttrs = namedtuple("FuncAttrs",
                       ["name", "params", "param_str",
                        "required_params", "arg_str",
                        "tuplized_arg_str", "key_str"])

# Example:
#
# def foo(x, y=1):
#     pass
#
#     name: 'foo'
#     params: ['x', 'y']
#     param_str: 'x, y=1'
#     required_params: ['x']
#     arg_str: x, y
#     tuplized_arg_str: '(x, y)'
#     key_str: '(x, y)'  in case of a single parameter, no parenthesis (such as 'x')


def funcdef_to_attrs(func: FunctionDef, module: Module) -> FuncAttrs:

    params = [p.name.value for p in func.params.params]
    required_params = [p.name.value for p in func.params.params if p.default is None]
    argstr = ", ".join(params)
    t_args = "(" + params[0] + ",)" if len(params) == 1 else "(" + ", ".join(params) + ")"

    return FuncAttrs(
        name=func.name.value,
        params=params,
        param_str=module.code_for_node(func.params),
        required_params=required_params,
        arg_str=argstr,
        tuplized_arg_str=t_args,
        key_str=argstr if len(params) == 1 else t_args
    )


def get_func_attrs(source: str) -> FuncAttrs:
    """source must be a function definition statement"""
    module = cst.parse_module(source)
    func = module.body[0]
    return funcdef_to_attrs(func, module)


class FormulaTransformer(m.MatcherDecoratableTransformer):
    """Transform formulas to methods"""

    METADATA_DEPENDENCIES = (ParentNodeProvider,)
    matchers_compstats = m.If() | m.Try() | m.With() | m.For() | m.While()

    def __init__(self, source: str, cells: Set[str]):
        super().__init__()
        self.source = source
        self.cells = cells
        self.prefix = "_f_"
        self.wrapper = cst.metadata.MetadataWrapper(cst.parse_module(source))
        self.module = self.wrapper.module
        self.node_to_scope = n_to_s = self.wrapper.resolve(cst.metadata.ScopeProvider)
        self.scopes = list(dict.fromkeys(n_to_s.values()))
        self.symtables = list_symtable(source)
        adjust_scope_table_mapping(self.scopes, self.symtables)     # See comment in the function

        # A list each of whose element is a name-to-symbol map
        self.name_to_symbol = [
            {s.get_name(): s for s in table.get_symbols()} if table else None for table in self.symtables
        ]
        self.global_names = set()

        self.builtins = set(n for n in builtins.__dict__.keys()
                            if n[:2] != '__' or n[-2:] != '__')

        # state variables
        self.func_level = 0
        self.attr_stack = []
        self.topfunc_name = None

        self.func_attrs = {}
        self.transformed = self.wrapper.visit(self)

    def should_replace(self, node: cst.Name):

        # Name nodes in import statements are not in the keys of self.node_to_scope
        # For such names, their parents' scopes are looked for
        n = node
        scope = self.node_to_scope.get(n, None)
        while not scope:
            prev = n
            n = self.get_metadata(ParentNodeProvider, n)
            if n == prev:
                raise RuntimeError(f"scope not found for {n.value}")
            scope = self.node_to_scope.get(n, None)

        i = next(i for i, v in enumerate(self.scopes) if scope == v)

        n_to_s = self.name_to_symbol[i]
        while n_to_s is None:
            i -= 1
            n_to_s = self.name_to_symbol[i]

        symbol = n_to_s.get(node.value, None)
        if symbol:
            if symbol.is_global():
                symbol_top = self.name_to_symbol[0].get(node.value, None)
                if symbol_top:
                    # Due to a bug in old versions,
                    # for globals at the top level, is_global and is_local are both checked.
                    # https://github.com/python/cpython/issues/86006 fixes
                    # from Python 3.10+, 3.9.1+, 3.8.7+
                    return ((symbol_top.is_global() or symbol_top.is_local())
                            and symbol_top.is_assigned())
                elif node.value in self.builtins:
                    return False
                else:
                    return True
            else:
                return False
        else:   # names between from and import, True, False, None
            return False

    def should_redirect(self, node: cst.BaseExpression):
        if m.matches(node, m.Name()):
            if self.should_replace(node) and node.value in self.cells:
                return True
            else:
                return False
        else:
            return False

    @m.call_if_not_inside(m.FunctionDef())
    @m.leave(m.SimpleStatementLine() | matchers_compstats | m.Comment() | m.EmptyLine())
    def remove_statements(self, original_node, updated_node):
        """Remove all other than function defs at module level """
        if self.get_metadata(ParentNodeProvider, original_node) == self.module:
            return cst.RemoveFromParent()
        else:
            return updated_node

    def visit_FunctionDef(self, node: "FunctionDef") -> Optional[bool]:
        if self.func_level == 0:
            self.topfunc_name = node.name
        self.func_level += 1

    def leave_FunctionDef(
        self, original_node: "FunctionDef", updated_node: "FunctionDef"
    ):
        if self.func_level > 1:
            self.func_level -= 1
            return updated_node

        self.func_attrs[original_node.name.value] = get_func_attrs(
            self.module.code_for_node(original_node)
        )

        name = updated_node.name.with_changes(
            value=self.prefix + updated_node.name.value
        )

        self_param = cst.Param(name=cst.Name(value='self'))
        new_params = updated_node.params.with_changes(
            params=(self_param,) + tuple(updated_node.params.params)
        )

        self.topfunc_name = None
        self.func_level -= 1
        return updated_node.with_changes(
            name=name,
            params=new_params
        )

    def visit_Attribute(self, node: "Attribute") -> Optional[bool]:
        self.attr_stack.append(node.attr)

    def leave_Attribute(
        self, original_node: "Attribute", updated_node: "Attribute"
    ) -> "BaseExpression":
        self.attr_stack.pop()
        return updated_node

    def leave_Name(
        self, original_node: "Name", updated_node: "Name"
    ) -> "BaseExpression":

        if original_node == self.topfunc_name:
            return updated_node
        elif self.attr_stack and self.attr_stack[-1] == original_node:
            # Do nothing if node is an attribute of another name
            return updated_node
        elif self.should_replace(original_node):
            return cst.Attribute(value=cst.Name('self'), attr=updated_node)
        else:
            return updated_node

    def leave_Subscript(
        self, original_node: "Subscript", updated_node: "Subscript"
    ) -> "BaseExpression":

        if self.should_redirect(original_node.value):
            name = self.module.code_for_node(updated_node.value)
            args = []
            for elm in updated_node.slice:
                args.append(self.module.code_for_node(elm))

            return cst.parse_expression(
                name + '(' + ''.join(args) + ')',
                config=self.module.config_for_parsing)
        else:
            return updated_node


def is_lambda_expr(source):
    return source.strip()[:6] == "lambda"


def lambda_to_func(source, name):
    template = textwrap.dedent("""\
    def {name}({params}):
        return {value}
    """)
    m = cst.parse_module(source)
    lmd = m.body[0].body[0].value
    params = m.code_for_node(lmd.params)
    value = m.code_for_node(lmd.body)
    return template.format(
        name=name,
        params=params,
        value=value
    )


