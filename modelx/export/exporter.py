# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

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

import collections
import pathlib
import sys
import textwrap
import types
import pprint
import inspect
import unicodedata
try:
    from functools import cached_property
except ImportError:     # - Python 3.7
    cached_property = property
import pickle

from modelx.core import mxsys
from modelx.core.base import Interface
from modelx.core.parent import BaseParent
from modelx.core.model import Model
from modelx.core.space import BaseSpace
from modelx.core.cells import Cells
from modelx.serialize.ziputil import write_str_utf8, copy_file
from modelx.core.util import abs_to_rel_tuple

from . import _mx_sys
from .transformer import (
    FormulaTransformer, lambda_to_func, is_lambda_expr, get_func_attrs)

this_dir = pathlib.Path(__file__).parent

MODEL_VAR = 'mx_model'
MODEL_MODULE = '_mx_model'
SPACE_MODULE = '_mx_classes'
DATA_MODULE = '_mx_io'  # _mx_io is hard-coded in _mx_sys
MACRO_MODULE = '_mx_macros'
SPACE_PKG_PREFIX = '_m_'
SPACE_CLS_PREFIX = '_c_'

# Members a generated Space class inherits from the _mx_sys template. A
# __slots__ entry repeating one of them silently shadows it - a slot named
# _cells would take over the property that populates _mx_cells. Every one of
# them starts with an underscore, and the only slot names that can is a Space
# parameter: modelx rejects a leading underscore in the name of a Reference or
# a Space, and a Cells name only ever reaches __slots__ behind a _v_ or _has_
# prefix.
INHERITED_ATTRS = frozenset(
    name for klass in _mx_sys.BaseSpace.__mro__ for name in vars(klass))


def normalize(name):
    """Return ``name`` as the compiler stores it.

    Python normalises every identifier in a source file to NFKC, but a
    ``__slots__`` entry is a string and is not normalised. A Reference named
    with a fullwidth letter, which :meth:`str.isidentifier` accepts and modelx
    keeps verbatim, is therefore assigned under its normalised name and has to
    be declared under that name too.
    """
    return unicodedata.normalize('NFKC', name)


def mangle(class_name, name):
    """Apply CPython's private name mangling to ``name``.

    A name of the form ``__x`` is mangled with the class whose body it
    appears in, and a ``__slots__`` entry is mangled with the class that
    declares it. ``_mx_assign_params`` and ``_mx_copy_params`` are compiled
    in the body of the Space that owns the parameter, so a descendant Space
    must declare the owner's form of the name, not its own.
    """
    name = normalize(name)
    if name.startswith('__') and not name.endswith('__'):
        return '_' + normalize(class_name).lstrip('_') + name

    return name


def get_space_formula_attrs(space: BaseSpace):
    """Return the FuncAttrs of a parameterized Space's formula.

    ``space.formula`` must not be None. The parameter assignments and the
    ``__slots__`` entries for them are both derived from the result, so that
    the two cannot disagree.
    """
    src = space.formula.source
    if is_lambda_expr(src):
        src = lambda_to_func(src, '_formula')
    return get_func_attrs(src)


class Exporter:

    def __init__(self, model: Model, path, use_slots: bool = True):
        self.model = model
        self.path = pathlib.Path(path)
        self.use_slots = use_slots

    def gen_parents(self):
        """Generator yielding model and spaces in breadth-first order"""
        que = collections.deque([self.model])
        while que:
            parent = que.popleft()
            yield parent
            for child in parent.spaces.values():
                que.append(child)

    def export(self):
        io_manager = DataManager(self.model)

        # Create self.path dir and Write Model module
        write_str_utf8(
            ModelTranslator(self.model, io_manager).code,
            self.path / (MODEL_MODULE + '.py'))

        # Write _mx_sys.py
        copy_file(this_dir / '_mx_sys.py', self.path / '_mx_sys.py')
        
        # Write _mx_macros.py if macros exist
        if self.model.macros:
            write_str_utf8(
                MacroTranslator(self.model).code,
                self.path / (MACRO_MODULE + '.py'))

        for parent in self.gen_parents():

            if parent is self.model:
                init_line = f'from .{MODEL_MODULE} import ({MODEL_VAR}, {self.model.name})'
                if self.model.macros:
                    # Add macros to __init__.py imports
                    macro_names = ', '.join(self.model.macros.keys())
                    init_line += f'\nfrom .{MACRO_MODULE} import ({macro_names})'
            else:
                init_line = f"from . import {SPACE_MODULE}"

            cur_dir = self.path / "/".join(
                SPACE_PKG_PREFIX + n for n in parent.fullname.split(".")[1:])

            if parent is self.model or parent.spaces:
                write_str_utf8(init_line, cur_dir / '__init__.py')

                # Write space modules
                write_str_utf8(
                    SpaceTranslator(parent, io_manager, self.use_slots).code,
                    cur_dir / (SPACE_MODULE + '.py'))

        # Write IO metadata
        ios = io_manager.get_literal_ios()
        specs = io_manager.get_literal_specs()

        if io_manager.ios or io_manager.iospecs:
            code = textwrap.dedent("""\
            ios = (
            {ios})

            iospecs = (
            {iospecs})
            """).format(ios=ios, iospecs=specs)
            write_str_utf8(
                code,
                self.path / (DATA_MODULE + '.py'))
            io_manager.write_ios(self.path)

        # Write pickle data
        io_manager.pickle(self.path / '_mx_pickled')


class DataManager:

    def __init__(self, model: Model):
        self.model = model
        self.iospecs = {id(spec.value): spec for spec in model.iospecs}
        self.ios = {id(v): v for v in mxsys.iomanager.get_ios(model).values()}
        self.pickle_data = {}   # id(value): value

    def get_code(self, value):
        key = id(value)
        if key in self.iospecs:
            return f"io_data[{key}]"
        else:   # pickle
            if key not in self.pickle_data:
                self.pickle_data[key] = value
            else:
                assert value is self.pickle_data[key]
            return f"pickle_data[{key}]"

    def get_literal_ios(self):
        ios = {
            pathlib.PurePath(v.path).as_posix(): {
                'type': v.__class__.__name__,
                **v.persistent_args
            }
            for v in self.ios.values()}
        if sys.version_info < (3, 8):
            return str(ios)
        else:
            return pprint.pformat(ios, sort_dicts=False)

    def get_literal_specs(self):
        specs = {k: {'type': v.__class__.__name__,
                     'io': pathlib.PurePath(v.io.path).as_posix(),
                     'kwargs': v._on_serialize({})}
                 for k, v in self.iospecs.items()}
        if sys.version_info < (3, 8):
            return str(specs)
        else:
            return pprint.pformat(specs, sort_dicts=False)

    def write_ios(self, root):
        mxsys.iomanager.write_ios(self.model, root)

    def pickle(self, path):
        if self.pickle_data:
            with open(path, 'wb') as f:
                pickle.dump(self.pickle_data, f)


class ParentTranslator:

    module_template = ''
    space_dict_template = textwrap.dedent("""\
    self._mx_spaces = {{
    {elements}
    }}
    """)

    def __init__(self, parent: BaseParent, io_manager: DataManager):
        self.parent = parent
        self.io_manager = io_manager

    @cached_property
    def code(self):
        return self.module_template.format(
            dots=self.dots,
            MODEL_VAR=MODEL_VAR,
            SPACE_MODULE=SPACE_MODULE,
            child_imports=self.child_imports,
            name=self.parent.name,
            class_defs=self.class_defs,
        )

    @cached_property
    def dots(self):
        return '.' * len(self.parent._idtuple)

    @cached_property
    def child_imports(self):
        result = []
        for k, v in self.parent.spaces.items():
            if v.spaces:
                result.append('from . import ' + SPACE_PKG_PREFIX + k)

        return '\n'.join(result)

    def class_defs(self):
        raise NotImplementedError

    def ref_names(self, parent):
        """Names of the References assigned as attributes of ``parent``.

        The single source of truth for :meth:`ref_assigns`,
        :meth:`ref_copies` and, in :class:`SpaceTranslator`, for the
        ``__slots__`` entries of the References.
        """
        return [k for k in parent.refs if k[0] != "_"]

    def space_names(self, parent):
        """Names of the child Spaces assigned as attributes of ``parent``.

        The single source of truth for :meth:`space_assigns`,
        :meth:`space_dict` and, in :class:`SpaceTranslator`, for the
        ``__slots__`` entries of the child Spaces.
        """
        return [k for k in parent.spaces if k[0] != "_"]

    def ref_assigns(self, parent, copy=False):
        result = []
        for k in self.ref_names(parent):
            if copy:
                result.append('self.' + k + ' = other.' + k)
            else:
                result.append(
                    'self.' + k + ' = '
                    + self.ref_value(parent, parent.refs[k]))

        if result:
            result.insert(0, "# Reference assignment")
        else:
            result.append('pass')

        return "\n".join(result)

    def ref_copies(self, parent):
        result = []
        for k in self.ref_names(parent):
            v = parent.refs[k]

            base_k = 'base.' + k
            self_k = 'self.' + k

            if isinstance(v, (Cells, BaseSpace)):

                proxy = parent._get_object(k, as_proxy=True)
                refmode = proxy.refmode
                if refmode == 'auto' or refmode == 'relative':
                    if_clause = 'if ' + (base_k + '.__self__' if isinstance(v, Cells) else base_k) + '._mx_is_in(base_root) else ' + base_k
                    result.append(self_k + ' = ' + self.ref_value(parent, v) + ' ' + if_clause)
                elif refmode == 'absolute' or (
                        refmode is None and isinstance(proxy.parent, Model)):
                    # refmode is None for model-level (global) references,
                    # which are inherited unchanged across spaces.
                    result.append(self_k + ' = ' + base_k)
                else:
                    raise RuntimeError('must not happen')
            else:
                result.append(self_k + ' = ' + base_k)

        if result:
            result.insert(0, "# Reference assignment")
        else:
            result.append('pass')

        return "\n".join(result)

    def ref_value(self, parent, value):

        literal_types = [bool, int, float, str, type(None)]
        if isinstance(value, Interface):
            if value._is_valid():
                ids = list(abs_to_rel_tuple(value._idtuple, parent._idtuple))
                # example of ids -> attrs:
                # ('...', 'foo', 'bar') -> ['self', '_parent', '_parent', 'foo', 'bar']
                attrs = ['self'] + ['_parent'] * (len(ids[0]) - 1) + ids[1:]
                return '.'.join(attrs)
            else:
                return 'None'
        elif any(type(value) is t for t in literal_types):
            return pprint.pformat(value)
        elif (isinstance(value, types.ModuleType)
              and value in sys.modules.values()):
            # Module
            return "_mx_sys.import_module('" + value.__name__ + "')"
        else:   # Save Data or Pickle
            return self.io_manager.get_code(value)

    def space_dict(self, parent):
        elms = []
        for k in self.space_names(parent):
            elms.append("'" + k + "'" + ': self.' + k)

        return self.space_dict_template.format(
            elements=textwrap.indent(",\n".join(elms), ' ' * 4)
        )


class ModelTranslator(ParentTranslator):
    
    module_template = textwrap.dedent("""\
    from . import _mx_sys
    from . import {SPACE_MODULE}
    
    {class_defs}
    
    {MODEL_VAR} = {name} = _c_{name}()
    """)
    
    class_template = textwrap.dedent("""\
    class _c_{name}(_mx_sys.BaseModel):
    
        def __init__(self):
        
            # modelx variables
            self._parent = None
            self._model = self
            self._name = "{name}"
                
    {space_assigns}
    {space_dict}
    
            self._mx_load_io()
    
        def _mx_assign_refs(self, io_data, pickle_data):

    {ref_assigns}
    """)

    @cached_property
    def class_defs(self):
        return self.class_template.format(
            name=self.parent.name,
            space_assigns=textwrap.indent(self.space_assigns(self.parent), ' ' * 8),
            space_dict=textwrap.indent(self.space_dict(self.parent), ' ' * 8),
            ref_assigns=textwrap.indent(self.ref_assigns(self.parent), ' ' * 8)
        )

    def space_assigns(self, parent):
        result = []
        for k in self.space_names(parent):
            result.append(
                'self.' + k + " = " + SPACE_MODULE + "." + SPACE_CLS_PREFIX + k + "(self)")
        if result:
            result.insert(0, "# Space assignments")

        return "\n".join(result)


class SpaceTranslator(ParentTranslator):

    module_template = textwrap.dedent("""\
    from {dots} import _mx_sys
    {child_imports}

    {class_defs}
    """)

    class_template = textwrap.dedent("""\

    _v_cells_names_{name} = [{cells_name_list}]
    _v_space_params_{name} = [{space_param_list}]


    class _c_{name}(_mx_sys.BaseSpace):
    {slots_decl}
        def __init__(self, parent):

            # modelx variables
            self._space = self
            self._parent = parent
            self._model = parent._model
            self._name = "{name}"

    {space_assigns}
    {space_dict}
            self._mx_cells = {{}}     # Populated on calling self._cells
            self._mx_is_cells_set = False
    {itemspace_dict}
            self._mx_roots = []     # Dynamic Space only

    {cache_vars}

        def _mx_assign_refs(self, io_data, pickle_data):

    {ref_assigns}

        def _mx_copy_refs(self, base, base_root):

    {ref_copies}

    {methods}

    {cache_methods}

    {itemspace_methods}
    
    {getitem}

    {delitem}
    """)

    # Attributes that ``class_template`` assigns in ``__init__`` on its own,
    # in the order they appear there. Everything else is contributed by one of
    # the placeholders and is collected in ``_get_class_def``.
    template_attrs = (
        '_space', '_parent', '_model', '_name',
        '_mx_cells', '_mx_is_cells_set', '_mx_roots')

    slots_template = """
    __slots__ = (
{names}
    )
"""

    cache_method_noparam = textwrap.dedent("""\
    def {name}(self):
        if self._has_{name}:
            return self._v_{name}
        else:
            val = self._v_{name} = self._f_{name}()
            self._has_{name} = True
            return val

    """)

    cache_method = textwrap.dedent("""\
    def {name}(self, {params}):
        if {idx_args} in self._v_{name}:
            return self._v_{name}[{idx_args}]
        else:
            val = self._f_{name}({args})
            self._v_{name}[{idx_args}] = val
            return val

    """)

    itemspace_methods = textwrap.dedent("""\
    def _mx_copy_params(self, other):
    {param_copies}

    @staticmethod
    def _mx_assign_params(_mx_space, {args}):
    {param_assigns}

    def __call__(self, {params}):
        _mx_key = {idx_args}
        if _mx_key in self._mx_itemspaces:
            return self._mx_itemspaces[_mx_key]
        else:
            _mx_base = self
            _mx_root = _mx_base.__class__(self)
            for _mx_s, _mx_b in zip(_mx_root._mx_walk(), _mx_base._mx_walk()):
                _mx_s._mx_copy_refs(_mx_b, _mx_base)
                for _mx_r in self._mx_roots:
                    _mx_r._mx_copy_params(_mx_s)

                self._mx_assign_params(_mx_s, {args})
                _mx_s._mx_roots.extend(self._mx_roots)
                _mx_s._mx_roots.append(_mx_root)

            self._mx_itemspaces[_mx_key] = _mx_root
            return _mx_root

    """)

    getitem_asis = textwrap.dedent("""\
    def __getitem__(self, item):
        return self.__call__(item)
    """)

    getitem_unpack = textwrap.dedent("""\
    def __getitem__(self, item):
        return self.__call__(*item)
    """)

    getitem_select = textwrap.dedent("""\
    def __getitem__(self, item):
        if item.__class__ is tuple:
            return self.__call__(*item)
        else:
            return self.__call__(item)
    """)

    delitem_asis = textwrap.dedent("""\
    def __delitem__(self, item):
        del self._mx_itemspaces[item]
    """)

    def __init__(self, parent: BaseParent, io_manager: DataManager,
                 use_slots: bool = True):
        super().__init__(parent, io_manager)
        self.use_slots = use_slots

    @cached_property
    def class_defs(self):
        defs = []
        for space in self.parent.spaces.values():
            defs.append(self._get_class_def(space))

        return '\n'.join(defs)

    def _get_class_def(self, space: BaseSpace):

        # Generate source.
        # To make sure to prefix refs with 'self.' that have builtin names,
        # Add dummy ref assignments to function definitions.
        # These assignments are removed by FormulaTransformer.
        lines = []
        for k in self.ref_names(space):
            lines.append(k + ' = None')

        for k, v in space.cells.items():
            src = v.formula.source
            if is_lambda_expr(src):
                src = lambda_to_func(src, k)
            lines.append(src)

        source = '\n'.join(lines)

        cells = set()   # Pass cells names for replacing subscription
        for d in [space.cells, space.refs]:
            for k, v in d.items():
                if isinstance(v, Cells):
                    cells.add(k)

        cacheless = set(k for k, v in space.cells.items() if v.is_cached == False)

        trans = FormulaTransformer(source, cells, cacheless)

        # Names the generated class body binds or inherits. A __slots__ entry
        # equal to one bound in the class body makes the class definition
        # raise ValueError; one equal to an inherited name shadows it.
        class_names = set(INHERITED_ATTRS)
        class_names.update(['__init__', '_mx_assign_refs', '_mx_copy_refs'])
        for name in trans.func_attrs:
            name = normalize(name)
            class_names.add(name)                   # the Cells method
            if name not in cacheless:
                class_names.add('_f_' + name)       # its underlying formula

        # __slots__ entries. Each name is collected next to the statement
        # that assigns the attribute, so that the two cannot drift apart.
        slot_names = list(self.template_attrs)
        slot_names.extend(self.space_names(space))      # space_assigns
        slot_names.append('_mx_spaces')                 # space_dict

        cache_vars = []
        cache_methods = []
        for func in trans.func_attrs.values():
            if func.name in cacheless:
                continue
            elif len(func.params) > 0:
                value_attr = "_v_" + func.name
                slot_names.append(value_attr)
                cache_vars.append(
                    "self." + value_attr + " = {}")
                cache_methods.append(self.cache_method.format(
                    name=func.name,
                    params=func.param_str,
                    args=func.arg_str,
                    idx_args=func.key_str
                ))
            else:
                value_attr = "_v_" + func.name
                has_attr = "_has_" + func.name
                slot_names.append(value_attr)
                slot_names.append(has_attr)
                cache_vars.append(
                    "self." + value_attr + " = None")
                cache_vars.append(
                    "self." + has_attr + " = False")
                cache_methods.append(
                    self.cache_method_noparam.format(name=func.name))
        if cache_vars:
            cache_vars.insert(0, "# Cache variables")

        slot_names.extend(self.ref_names(space))    # ref_assigns / ref_copies

        # ItemSpace
        if space.formula:
            itemspace_dict = "self._mx_itemspaces = {}"
            slot_names.append('_mx_itemspaces')
            attrs = get_space_formula_attrs(space)
            slot_names.extend(attrs.params)         # _mx_assign_params
            class_names.update([
                '_mx_copy_params', '_mx_assign_params',
                '__call__', '__getitem__', '__delitem__'])

            # How to pass args from __getitem__ to __call__
            if len(attrs.params) == len(attrs.required_params) == 1:
                getitem = self.getitem_asis
            elif len(attrs.required_params) > 1:
                getitem = self.getitem_unpack
            else:
                getitem = self.getitem_select

            itemspace_methods = self.itemspace_methods.format(
                args=attrs.arg_str,
                params=attrs.param_str,
                idx_args=attrs.key_str,
                param_copies=textwrap.indent(
                    self.param_assigns(attrs.params, copy=True), ' ' * 4),
                param_assigns=textwrap.indent(
                    self.param_assigns(attrs.params), ' ' * 4)
            )
            delitem = self.delitem_asis
        else:
            itemspace_dict = ''
            itemspace_methods = ''
            getitem = ''
            delitem = ''

        # _mx_copy_params on the enclosing ItemSpace roots assigns their
        # parameters here as well. See inherited_param_names.
        slot_names.extend(self.inherited_param_names(space))

        return self.class_template.format(
            name=space.name,
            slots_decl=self.slots_decl(space, slot_names, class_names),
            cells_name_list=textwrap.indent(self.cells_name_list(space), ' ' * 4),
            space_param_list=textwrap.indent(self.space_param_list(space), ' ' * 4),
            space_assigns=textwrap.indent(self.space_assigns(space), ' ' * 8),
            space_dict=textwrap.indent(self.space_dict(space), ' ' * 8),
            itemspace_dict=textwrap.indent(itemspace_dict, ' ' * 8),
            cache_vars=textwrap.indent("\n".join(cache_vars), ' ' * 8),
            ref_copies=textwrap.indent(
                self.ref_copies(space), ' ' * 8),
            ref_assigns=textwrap.indent(self.ref_assigns(space), ' ' * 8),
            methods=textwrap.indent(trans.transformed.code, ' ' * 4),
            cache_methods=textwrap.indent(''.join(cache_methods), ' ' * 4),
            itemspace_methods=textwrap.indent(itemspace_methods, ' ' * 4),
            getitem=textwrap.indent(getitem, ' ' * 4),
            delitem=textwrap.indent(delitem, ' ' * 4)
        )

    def space_assigns(self, parent):
        result = []
        for k in self.space_names(parent):
            pkg = SPACE_PKG_PREFIX + parent.name + '.'
            result.append(
                'self.' + k + " = " + pkg + SPACE_MODULE + "." + SPACE_CLS_PREFIX + k + "(self)")
        if result:
            result.insert(0, "# Space assignments")

        return "\n".join(result)

    def inherited_param_names(self, space: BaseSpace):
        """Parameter names of the parameterized Spaces enclosing ``space``.

        ``__call__`` assigns a Space's own parameters on every Space in its
        subtree through ``_mx_assign_params``, and copies the parameters of
        every enclosing ItemSpace root onto them through ``_mx_copy_params``.
        A Space class therefore needs slots for the parameters of every
        parameterized ancestor Space, not only for its own.
        """
        result = []
        parent = space.parent
        while isinstance(parent, BaseSpace):
            if parent.formula:
                class_name = SPACE_CLS_PREFIX + parent.name
                result[:0] = [mangle(class_name, k) for k
                              in get_space_formula_attrs(parent).params]
            parent = parent.parent

        return result

    def slots_decl(self, space: BaseSpace, names, class_names):
        """Render the ``__slots__`` declaration of ``space``'s class.

        ``names`` are the attributes assigned on instances of the class, in
        the order they are assigned, possibly with duplicates and not
        necessarily normalised. ``class_names`` are the names the class binds
        or inherits, which a slot must not repeat. Returns an empty string when ``use_slots`` is false,
        in which case the generated class is byte-identical to the one
        modelx v0.32.0 generates.
        """
        if not self.use_slots:
            return ''

        slots = []
        for name in names:
            name = normalize(name)
            if name in class_names:
                raise ValueError(
                    "%s cannot be exported with use_slots=True: the name %r "
                    "is assigned as an attribute of the Space, but the "
                    "exported class also defines it, either as a Cells of "
                    "the same name or as an inherited member. __slots__ "
                    "cannot declare a name that the class already binds. "
                    "Rename one of the two, or pass use_slots=False to "
                    "export as modelx v0.32.0 does."
                    % (space.fullname, name))
            if name not in slots:
                slots.append(name)

        return self.slots_template.format(
            names=textwrap.fill(
                ' '.join("'" + n + "'," for n in slots),
                width=79,
                initial_indent=' ' * 8,
                subsequent_indent=' ' * 8,
                break_long_words=False,
                break_on_hyphens=False))

    def param_assigns(self, params, copy=False):
        params = list(params)
        result = []
        for k in params:
            if copy:
                result.append('other.' + k + ' = self.' + k)
            else:
                result.append('_mx_space.' + k + ' = ' + k)

        if result:
            result.insert(0, "# Parameter assignment")
        else:
            result.append('pass')

        return "\n".join(result)

    def cells_name_list(self, space):
        str_elm = []
        if space.cells:
            str_elm.append("\n")
        for name in space.cells:
            str_elm.append("'" + name + "'")
            str_elm.append(",\n")
        return ''.join(str_elm)

    def space_param_list(self, space):
        str_elm = []
        if space.parameters:
            str_elm.append("\n")
            for name in space.parameters:
                str_elm.append("'" + name + "'")
                str_elm.append(",\n")
            return ''.join(str_elm)
        else:
            return ''


class MacroTranslator:
    """Translator for macros to _mx_macros.py"""
    
    module_template = textwrap.dedent("""\
    from .{MODEL_MODULE} import ({MODEL_VAR}, {model_name})
    
    {macro_defs}
    """)
    
    def __init__(self, model: Model):
        self.model = model
    
    @cached_property
    def code(self):
        return self.module_template.format(
            MODEL_MODULE=MODEL_MODULE,
            MODEL_VAR=MODEL_VAR,
            model_name=self.model.name,
            macro_defs=self.macro_defs
        )
    
    @cached_property
    def macro_defs(self):
        """Generate function definitions for all macros"""
        result = []
        for name, macro in self.model.macros.items():
            # Get the source code of the macro's formula
            formula = macro.formula
            if formula and formula.source:
                result.append(formula.source)
            else:
                # If no source, create a stub with original signature
                try:
                    sig = inspect.signature(formula.func if formula else lambda: None)
                    result.append(f"def {name}{sig}:\n    pass")
                except (ValueError, TypeError):
                    # Fallback if signature inspection fails
                    # Note: This creates a parameter-less stub, which may not match
                    # the original function signature. This is a known limitation
                    # when source code is unavailable (e.g., in REPL contexts).
                    result.append(f"def {name}():\n    pass")
        
        return "\n\n".join(result)

