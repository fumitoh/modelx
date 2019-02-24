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

import sys
import importlib
from collections import Sequence, ChainMap
from types import FunctionType, ModuleType

from modelx.core.base import (
    # ObjectArgs,
    get_impls,
    get_interfaces,
    Impl,
    ReferenceImpl,
    NullImpl,
    Derivable,
    ImplDict,
    ImplChainMap,
    BaseView,
    SelectedView,
    BoundFunction)
from modelx.core.node import (
    node_get_args, tuplize_key, get_node, OBJ, KEY)
from modelx.core.spacecontainer import (
    BaseSpaceContainer,
    BaseSpaceContainerImpl,
    EditableSpaceContainer,
    EditableSpaceContainerImpl)
from modelx.core.formula import Formula, ModuleSource
from modelx.core.cells import (
    Cells,
    CellsImpl,
    convert_args,
    shareable_parameters)
from modelx.core.util import AutoNamer, is_valid_name, get_module


class ParamFunc(Formula):
    def __init__(self, func, module_=None):
        Formula.__init__(self, func, module_)


class SpaceDict(ImplDict):

    def __init__(self, space, data=None, observers=None):
        ImplDict.__init__(self, space, SpaceView, data, observers)


class CellsDict(ImplDict):

    def __init__(self, space, data=None, observers=None):
        ImplDict.__init__(self, space, CellsView, data, observers)


class RefDict(ImplDict):

    def __init__(self, space, data=None, observers=None):

        if data is not None:
            for name, value in data.items():
                data[name] = self.get_ref(space, name, value)

        ImplDict.__init__(self, space, BaseView, data, observers)

    def set_item(self, name, ref, skip_self=False):
        ImplDict.set_item(self, name, ref, skip_self)

    # TODO: Should remove this to force refs created outside RefDict?
    @staticmethod
    def get_ref(space, name, value):
        if isinstance(value, Impl):   # TODO: Probably not correct.
            return value
        else:
            return ReferenceImpl(space, name, value)


def _to_frame_inner(cellsiter, args):

    from modelx.io.pandas import cellsiter_to_dataframe

    if len(args) == 1:
        if isinstance(args[0], Sequence) and len(args[0]) == 0:
            pass  # Empty sequence
        else:
            args = args[0]

    if len(args) and shareable_parameters(cellsiter) is None:
        raise RuntimeError("Parameters not shared")

    argkeys = []
    for arg in args:
        for cells in cellsiter.values():

            newarg = tuplize_key(cells, arg, remove_extra=True)
            cells.get_value(newarg)
            arg = tuplize_key(cells, arg, remove_extra=False)

            if arg not in argkeys:
                argkeys.append(arg)

    return cellsiter_to_dataframe(cellsiter, argkeys)


class CellsView(SelectedView):
    """A mapping of cells names to cells objects.

    CellsView objects are returned by :attr:`StaticSpace.cells` property.
    When :attr:`StaticSpace.cells` is called without subscription(``[]`` operator),
    the returned CellsView contains all the cells in the space.

    CellsView supports a normal subscription(``[]``) operation with one
    argument to retrieve a cells object from its name,
    but it also supports multiple arguments to indicate the names of cells
    to select,
    and returns another CellsView containing only the selected cells.

    For example, if ``space`` contains 3 cells ``foo``, ``bar`` and ``baz``::

        >> space.cells
        {foo,
         bar,
         baz}

        >> space.cells['bar', 'baz']
        {bar,
         baz}

    """
    def __delitem__(self, name):
        cells = self._data[name]._impl
        cells.space.del_cells(name)

    def to_frame(self, *args):
        """Convert the cells in the view into a DataFrame object.

        If ``args`` is not given, this method returns a DataFrame that
        has an Index or a MultiIndex depending of the number of
        cells parameters and columns each of which corresponds to each
        cells included in the view.

        ``args`` can be given to calculate cells values and limit the
        DataFrame indexes to the given arguments.

        The cells in this view may have different number of parameters,
        but parameters shared among multiple cells
        must appear in the same position in all the parameter lists.
        For example,
        Having ``foo()``, ``bar(x)`` and ``baz(x, y=1)`` is okay
        because the shared parameter ``x`` is always the first parameter,
        but this method does not work if the view has ``quz(x, z=2, y=1)``
        cells in addition to the first three cells, because ``y`` appears
        in different positions.

        Args:
            args(optional): multiple arguments,
               or an iterator of arguments to the cells.
        """
        if sys.version_info < (3, 6, 0):
            from collections import OrderedDict
            impls = OrderedDict()
            for name, obj in self.items():
                impls[name] = obj._impl
        else:
            impls = get_impls(self)

        return _to_frame_inner(impls, args)


class SpaceView(BaseView):

    def __delitem__(self, name):
        space = self._data[name]._impl
        space.parent.del_space(name)


class RefView(SelectedView):

    @property
    def _baseattrs(self):

        result = {'type': type(self).__name__}

        result['items'] = items = {}
        for name, item in self.items():
            if name[0] != '_':
                itemattrs = {'repr': name,
                             'id': id(item),
                             'type': type(item).__name__}
                items[name] = itemattrs

        return result


class BaseSpace(BaseSpaceContainer):

    __slots__ = ()

    def __getattr__(self, name):
        if name in self._impl.namespace:
            return self._impl.namespace[name]
        else:
            raise AttributeError  # Must return AttributeError for hasattr

    def __dir__(self):
        return self._impl.namespace

    @property
    def bases(self):
        """List of base classes."""
        return get_interfaces(self._impl.bases)

    def is_base(self, other):
        """True if the space is a base space of ``other``, False otherwise."""
        return self._impl.is_base(other._impl)

    def is_sub(self, other):
        """True if the space is a sub space of ``other``, False otherwise."""
        return self._impl.is_sub(other._impl)

    def is_static(self):
        """True if the space is a static space, False if dynamic."""
        return self._impl.is_static()

    def is_derived(self):
        """True if the space is a derived space, False otherwise."""
        return self._impl.is_derived

    def is_defined(self):
        """True if the space is a defined space, False otherwise."""
        return self._impl.is_defined()

    def is_dynamic(self):
        """True if ths space is a dynamic space, False otherwise."""
        return isinstance(self._impl, RootDynamicSpaceImpl)

    def in_dynamic(self):
        """True if the space is in a dynamic space, False otherwise."""
        return self._impl.in_dynamic()

    @property
    def cells(self):
        """A mapping of cells names to the cells objects in the space."""
        return self._impl.cells.interfaces

    @property
    def self_cells(self):
        """A mapping that associates names to cells defined in the space"""
        return self._impl.self_cells.interfaces

    @property
    def derived_cells(self):
        """A mapping associating names to derived cells."""
        return self._impl.derived_cells.interfaces

    @property
    def all_spaces(self):
        """A mapping associating names to all(static and dynamic) spaces."""
        return self._impl.spaces.interfaces

    @property
    def spaces(self):
        """A mapping associating names to static spaces."""
        return self._impl.static_spaces.interfaces

    @property
    def static_spaces(self):
        """A mapping associating names to static spaces.

        Alias to :py:meth:`spaces`
        """
        return self._impl.static_spaces.interfaces

    @property
    def dynamic_spaces(self):
        """A mapping associating names to dynamic spaces."""
        return self._impl.dynamic_spaces.interfaces

    @property
    def self_spaces(self):
        """A mapping associating names to self spaces."""
        return self._impl.self_spaces.interfaces

    @property
    def derived_spaces(self):
        """A mapping associating names to derived spaces."""
        return self._impl.derived_spaces.interfaces

    @property
    def argvalues(self):
        """A tuple of space arguments."""
        return self._impl.argvalues_if

    @property
    def parameters(self):
        """A tuple of parameter strings."""
        return tuple(self._impl.formula.parameters)

    @property
    def refs(self):
        """A map associating names to objects accessible by the names."""
        return self._impl.refs.interfaces

    @property
    def formula(self):
        """Property to get, set, delete formula."""
        return self._impl.formula

    # ----------------------------------------------------------------------
    # Manipulating subspaces

    def has_params(self):
        """Check if the parameter function is set."""
        # Outside formulas only
        return bool(self._impl.formula)

    def __getitem__(self, key):
        return self._impl.get_dynspace(tuplize_key(self, key)).interface

    def __iter__(self):
        raise TypeError("'Space' is not iterable")

    def __call__(self, *args, **kwargs):
        return self._impl.get_dynspace(args, kwargs).interface

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_frame(self, *args):
        """Convert the space itself into a Pandas DataFrame object."""
        return self._impl.to_frame(args)

    @property
    def frame(self):
        """Alias of ``to_frame()``."""
        return self._impl.to_frame(())

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = super()._baseattrs
        result['static_spaces'] = self.static_spaces._baseattrs
        result['dynamic_spaces'] = self.dynamic_spaces._baseattrs
        result['cells'] = self.cells._baseattrs
        result['refs'] = self.refs._baseattrs

        if self.has_params():
            result['params'] = ', '.join(self.parameters)
        else:
            result['params'] = ''

        args = self.argvalues
        if args is not None:
            result['argvalues'] = ', '.join([repr(arg) for arg in args])
        else:
            result['argvalues'] = ''

        return result


class StaticSpace(BaseSpace, EditableSpaceContainer):
    """Container of cells, other spaces, and cells namespace.

    StaticSpace objects can contain cells and other spaces.
    Spaces have mappings of names to objects that serve as global namespaces
    of the formulas of the cells in the spaces.
    """
    __slots__ = ()
    # ----------------------------------------------------------------------
    # Manipulating cells

    def new_cells(self, name=None, formula=None):
        """Create a cells in the space.

        Args:
            name: If omitted, the model is named automatically ``CellsN``,
                where ``N`` is an available number.
            func: The function to define the formula of the cells.

        Returns:
            The new cells.
        """
        # Outside formulas only
        return self._impl.new_cells(name, formula).interface

    def add_bases(self, *bases):
        """Add base spaces."""
        return self._impl.add_bases(get_impls(bases))

    def remove_bases(self, *bases):
        """Remove base spaces."""
        return self._impl.remove_bases(bases)

    def import_funcs(self, module_):
        """Create a cells from a module."""
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module_)
        return get_interfaces(newcells)

    def new_cells_from_module(self, module_):
        """Create a cells from a module.

        Alias to :py:meth:`import_funcs`.
        """
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module_)
        return get_interfaces(newcells)

    def reload(self):
        """Reload the source module and update the formulas.

        If the space was created from a module, reload the module and
        update the formulas of its cells.

        If a cell in the space is not created from a function definition
        in the source module of the space, it is not updated.

        If the formula of a cell in the space was created from a function
        definition in the source module of the space and the definition is
        missing from the updated module, the formula is cleared and
        values calculated directly or indirectly depending the cells
        are cleared.

        If the formula of a cell in the space has not been changed
        before and after reloading the source module, the values held
        in the cell and relevant cells are retained.

        Returns:
            This method returns the space itself.
        """
        self._impl.reload()
        return self

    def new_cells_from_excel(self, book, range_, sheet=None,
                                names_row=None, param_cols=None,
                                param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create multiple cells from an Excel range.

        This method reads values from a range in an Excel file,
        create cells and populate them with the values in the range.
        To use this method, ``openpyxl`` package must be installed.

        The Excel file to read data from is specified by ``book``
        parameters. The ``range_`` can be a range address, such as "$G4:$K10",
        or a named range. In case a range address is given,
        ``sheet`` must also be given.

        By default, cells data are interpreted as being laid out side-by-side.
        ``names_row`` is a row index (starting from 0) to specify the
        row that contains the names of cells and parameters.
        Cells and parameter names must be contained in a single row.
        ``param_cols`` accepts a sequence (such as list or tuple) of
        column indexes (starting from 0) that indicate columns that
        contain cells arguments.

        **2-dimensional cells definitions**

        The optional ``names_col`` and ``param_rows`` parameters are used,
        when data for one cells spans more than one column.
        In such cases, the cells data is 2-dimensional, and
        there must be parameter row(s) across the columns
        that contain arguments of the parameters.
        A sequence of row indexes that indicate parameter rows
        is passed to ``param_rows``.
        The names of those parameters must be contained in the
        same rows as parameter values (arguments), and
        ``names_col`` is to indicate the column position at which
        the parameter names are defined.

        **Horizontal arrangement**

        By default, cells data are interpreted as being placed
        side-by-side, regardless of whether one cells corresponds
        to a single column or multiple columns.
        ``transpose`` parameter is used to alter this orientation,
        and if it is set to ``True``, cells values are
        interpreted as being placed one above the other.
        "row(s)" and "col(s)" in the parameter
        names are interpreted inversely, i.e.
        all indexes passed to "row(s)" parameters are interpreted
        as column indexes,
        and all indexes passed to "col(s)" parameters as row indexes.


        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            names_row (optional): an index number indicating
                what row contains the names of cells and parameters.
                Defaults to the top row (0).
            param_cols (optional): a sequence of index numbers
                indicating parameter columns.
                Defaults to only the leftmost column ([0]).
            names_col (optional): an index number, starting from 0,
                indicating what column contains additional parameters.
            param_rows (optional): a sequence of index numbers, starting from
                0, indicating rows of additional parameters, in case cells are
                defined in two dimensions.
            transpose (optional): Defaults to ``False``.
                If set to ``True``, "row(s)" and "col(s)" in the parameter
                names are interpreted inversely, i.e.
                all indexes passed to "row(s)" parameters are interpreted
                as column indexes,
                and all indexes passed to "col(s)" parameters as row indexes.
            param_order (optional): a sequence to reorder the parameters.
                The elements of the sequence are the indexes of ``param_cols``
                elements, and optionally the index of ``param_rows`` elements
                shifted by the length of ``param_cols``.
        """
        return self._impl.new_cells_from_excel(
            book, range_, sheet, names_row, param_cols,
            param_order, transpose,
            names_col, param_rows)

    # ----------------------------------------------------------------------
    # Checking containing subspaces and cells

    def __contains__(self, item):
        """Check if item is in the space.

        item can be either a cells or space.

        Args:
            item: a cells or space to check.

        Returns:
            True if item is a direct child of the space, False otherwise.
        """
        if isinstance(item, str):
            return item in self._impl.namespace

        elif isinstance(item, Cells):
            return item._impl in self._impl.cells.values()

        elif isinstance(item, StaticSpace):
            return item._impl in self._impl.spaces.values()

        else:
            return False

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __setattr__(self, name, value):
        if name in self.properties:
            object.__setattr__(self, name, value)
        else:
            self._impl.set_attr(name, value)

    def __delattr__(self, name):
        self._impl.del_attr(name)


    # ----------------------------------------------------------------------
    # Formula

    # TODO: Factor out formula related methods and properties
    #  common between Cells and Spaces

    @property
    def formula(self):
        """Property to get, set, delete formula."""
        return self._impl.formula

    @formula.setter
    def formula(self, formula):
        self._impl.set_formula(formula)

    def set_formula(self, formula):
        """Set if the parameter function."""
        self._impl.set_formula(formula)


class BaseSpaceImpl(Derivable, BaseSpaceContainerImpl):
    """Read-only base Space class

    * Cells container
    * Ref container
    * Namespace
    * Formula container
    * Implement Derivable
    """
    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = [
        '_mro_cache',
        'update_mro',
        '_cells',
        '_static_spaces',
        '_dynamic_spaces',
        '_local_refs',
        '_self_refs',
        '_refs',
        '_namespace_impl',
        'is_dynamic',
        'param_spaces',
        'formula',
        'cellsnamer',
        'name',
        'source',
        'altfunc'
    ] + BaseSpaceContainerImpl.state_attrs + Derivable.state_attrs

    assert len(state_attrs) == len(set(state_attrs))

    def __init__(self, parent, name, formula=None,
                 refs=None, source=None, arguments=None):

        BaseSpaceContainerImpl.__init__(self)
        Derivable.__init__(self, parent.system)

        self.name = name
        self.parent = parent
        self.cellsnamer = AutoNamer('Cells')

        self._mro_cache = None
        self.update_mro = True

        if isinstance(source, ModuleType):
            self.source = source.__name__
        else:
            self.source = None

        # ------------------------------------------------------------------
        # Construct member containers

        self._dynamic_spaces = ImplDict(self, SpaceView)
        self._dynamic_subs = []
        self._self_refs = RefDict(self)
        self._cells = CellsDict(self)
        self._static_spaces = SpaceDict(self)
        self._spaces = ImplChainMap(self, SpaceView,
                                    [self._static_spaces,
                                     self._dynamic_spaces])

        self._local_refs = {'_self': self, '_space': self}

        self._refs = self._create_refs(arguments)

        self._namespace_impl = ImplChainMap(self, None,
                                            [self._cells,
                                             self._refs,
                                             self._spaces])

        self.lazy_evals = self._namespace_impl

        # ------------------------------------------------------------------
        # Add initial refs members

        if refs is not None:
            refsimpl = {name: ReferenceImpl(self, name, value)
                        for name, value in refs.items()}
            self._self_refs.update(refsimpl)
            self._self_refs.set_update()

        # ------------------------------------------------------------------
        # Construct altfunc after space members are crated

        self.param_spaces = {}
        self.formula = None
        if formula is not None:
            self.set_formula(formula)

        # ------------------------------------------------------------------
        # For repr of LazyEvalDict, LazyEvalImpl

        self._cells.debug_name = '_cells'
        self._static_spaces.debug_name = '_static_spaces'
        self._dynamic_spaces.debug_name = '_dynamic_spaces'
        self._self_refs.debug_name = '_self_refs'
        self._refs.debug_name = '_refs'
        self._namespace_impl.debug_name = '_namespace_impl'

    def _create_refs(self, arguments=None):
        raise NotImplementedError

    @property
    def fullname(self):
        return self.parent.fullname + '.' + self.name

    @property
    def model(self):
        return self.parent.model

    @property
    def cells(self):
        return self._cells.get_updated()

    @property
    def static_spaces(self):
        return self._static_spaces.get_updated()

    @property
    def dynamic_spaces(self):
        return self._dynamic_spaces.get_updated()

    @property
    def refs(self):
        return self._refs.get_updated()

    @property
    def self_refs(self):
        return self._self_refs.get_updated()

    @property
    def local_refs(self):
        return self._local_refs

    @property
    def namespace_impl(self):
        return self._namespace_impl.get_updated()

    @property
    def namespace(self):
        return self._namespace_impl.get_updated().interfaces

    # --- Inheritance properties ---

    @property
    def direct_bases(self):
        """Return an iterator over direct base spaces"""
        return self.model.spacegraph.predecessors(self)

    @property
    def self_bases(self):
        raise NotImplementedError

    # Overridden temporarily to add dynamic spaces
    @property
    def parent_bases(self):
        if self.parent.is_model():
            return []
        elif self in self.parent.dynamic_spaces.values():
            return []
        else:
            parent_bases = self.parent.bases
            result = []
            for space in parent_bases:
                bases = self._get_members(space)
                if self.name in bases:
                    result.append(bases[self.name])
            return result

    @staticmethod
    def _get_members(other):
        return other.static_spaces

    @property
    def mro(self):
        if self.update_mro:
            self._mro_cache = self.model.spacegraph.get_mro(self)
            self.update_mro = False

        return self._mro_cache

    def is_base(self, other):
        return self in other.bases

    def is_sub(self, other):
        return other in self.bases

    def is_defined(self):
        if self.is_static():
            return not self.is_derived
        return False

    # --- Dynamic space properties ---

    def is_static(self):
        raise NotImplementedError

    def in_dynamic(self):
        raise NotImplementedError

    def _set_space(self, space):
        if isinstance(space, RootDynamicSpaceImpl):
            self._dynamic_spaces.set_item(space.name, space)
        else:
            self._static_spaces.set_item(space.name, space)

    def _new_cells(self, name, formula, is_derived):
        cells = CellsImpl(space=self, name=name, formula=formula)
        self._cells.set_item(cells.name, cells)
        cells.is_derived = is_derived
        return cells

    def _new_ref(self, name, value, is_derived):
        ref = ReferenceImpl(self, name, value)
        self.self_refs.set_item(name, ref)
        ref.is_derived = is_derived
        return ref

    # ----------------------------------------------------------------------
    # Reference operation

    def inherit(self, **kwargs):

        if 'event' in kwargs:
            event = kwargs['event']
        else:
            event = None

        if self.bases and self.bases[0].formula is not None:
            if not isinstance(self, RootDynamicSpaceImpl):
                if event != 'new_cells' and event != 'cells_set_formula':
                    self.set_formula(self.bases[0].formula)

        attrs = ('cells', 'self_refs', 'static_spaces')
        for attr in attrs:
            selfmap = getattr(self, attr)
            basemap = ChainMap(*[getattr(base, attr) for base in self.bases])
            for name in basemap:
                if name not in self.namespace_impl:
                    selfmap[name] = self._new_member(attr, name,
                                                     is_derived=True)
                    clear_value = False
                else:
                    if 'clear_value' in kwargs:
                        clear_value = kwargs['clear_value']
                    else:
                        clear_value = True

                kwargs['clear_value'] = clear_value
                selfmap[name].inherit(**kwargs)

            names = set(selfmap) - set(basemap)
            for name in names:
                member = selfmap[name]
                if member.is_derived:
                    selfmap.del_item(name)
                    if attr == 'static_spaces':
                        self.model.spacegraph.remove_node(member)
                else:
                    member.inherit(**kwargs)

        for dynspace in self._dynamic_subs:
            dynspace.inherit(**kwargs)

    def _new_member(self, attr, name, is_derived=False):
        if attr == 'static_spaces':
            if not self.in_dynamic():
                space = self._new_space(name, is_derived=is_derived)
            else:
                space = DynamicSpaceImpl(parent=self, name=name)
                space.is_derived = is_derived

            self._set_space(space)
            if not self.in_dynamic():
                self.model.spacegraph.add_space(space)
            return space
        elif attr == 'cells':
            return self._new_cells(name, formula=None, is_derived=is_derived)
        elif attr == 'self_refs':
            return self._new_ref(name, None, is_derived=is_derived)
        else:
            raise RuntimeError("must not happen")

    # ----------------------------------------------------------------------
    # Component properties

    def has_descendant(self, other):
        if self.spaces:
            if other in self.spaces.values():
                return True
            else:
                return any(child.has_descendant(other)
                           for child in self.spaces.values())
        else:
            return False

    def has_linealrel(self, other):
        return self.has_ascendant(other) or self.has_descendant(other)

    def get_object(self, name):
        """Retrieve an object by a dotted name relative to the space."""

        parts = name.split('.')
        child = parts.pop(0)

        if parts:
            return self.spaces[child].get_object('.'.join(parts))
        else:
            return self._namespace_impl[child]

    # ----------------------------------------------------------------------
    # Dynamic Space Operation

    def set_formula(self, formula):
        if self.formula is None:
            if isinstance(formula, ParamFunc):
                self.formula = formula
            else:
                self.formula = ParamFunc(formula)
            self.altfunc = BoundFunction(self)
        else:
            raise ValueError("formula already assigned.")

    def eval_formula(self, node):
        return self.altfunc.get_updated().altfunc(*node[KEY])

    def _get_dynamic_base(self, bases_):
        """Create or get the base space from a list of spaces

        if a direct base space in `bases` is dynamic, replace it with
        its base.
        """
        bases = tuple(base.bases[0] if base.in_dynamic() else base
                      for base in bases_)

        if len(bases) == 1:
            return bases[0]

        elif len(bases) > 1:
            return self.model.get_dynamic_base(bases)

        else:
            RuntimeError("must not happen")

    def _new_dynspace(self, name=None, bases=None, formula=None,
                      refs=None, arguments=None, source=None,
                      is_derived=False):
        """Create a new dynamic root space."""

        if name is None:
            name = self.spacenamer.get_next(self.namespace)

        if name in self.namespace:
            raise ValueError("Name '%s' already exists." % name)

        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        space = RootDynamicSpaceImpl(
            parent=self, name=name, formula=formula,
            refs=refs, source=source, arguments=arguments)

        space.is_derived = is_derived

        self._set_space(space)

        if bases: # i.e. not []
            dynbase = self._get_dynamic_base(bases)
            space._dynbase = dynbase
            dynbase._dynamic_subs.append(space)

        return space

    def get_dynspace(self, args, kwargs=None):
        """Create a dynamic root space

        Called from interface methods
        """

        node = get_node(self, *convert_args(args, kwargs))
        key = node[KEY]

        if key in self.param_spaces:
            return self.param_spaces[key]

        else:
            last_self = self.system.self
            self.system.self = self

            try:
                space_args = self.eval_formula(node)

            finally:
                self.system.self = last_self

            if space_args is None:
                space_args = {'bases': [self]}  # Default
            else:
                if 'bases' in space_args:
                    bases = get_impls(space_args['bases'])
                    if isinstance(bases, StaticSpaceImpl):
                        space_args['bases'] = [bases]
                    elif bases is None:
                        space_args['bases'] = [self]    # Default
                    else:
                        space_args['bases'] = bases
                else:
                    space_args['bases'] = [self]

            space_args['arguments'] = node_get_args(node)
            space = self._new_dynspace(**space_args)
            self.param_spaces[key] = space
            space.inherit(clear_value=False)
            return space

    # ----------------------------------------------------------------------
    # Space properties

    def __repr__(self):
        return '<SpaceImpl: ' + self.fullname + '>'

    def repr_self(self, add_params=True):

        if add_params and isinstance(self, RootDynamicSpaceImpl):
            args = [repr(arg) for arg in get_interfaces(self.argvalues)]
            param = ', '.join(args)
            return "%s[%s]" % (self.parent.name, param)
        else:
            return self.name

    def repr_parent(self):

        if isinstance(self, RootDynamicSpaceImpl):
            return self.parent.repr_parent()
        else:
            if self.parent.repr_parent():
                return self.parent.repr_parent() + '.' + self.parent.repr_self()
            else:
                return self.parent.repr_self()

    def __getstate__(self):
        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""
        super().restore_state(system)
        BaseSpaceContainerImpl.restore_state(self, system)

        for cells in self._cells.values():
            cells.restore_state(system)

    # ----------------------------------------------------------------------
    # Pandas, Module, Excel I/O

    def to_frame(self, args):
        return _to_frame_inner(self.cells, args)


class StaticSpaceImpl(BaseSpaceImpl, EditableSpaceContainerImpl):
    """Editable base Space class

    * cell creation
    * ref assignment
    """
    if_class = StaticSpace
    state_attrs = ['_dynamic_subs'
        ] + BaseSpaceImpl.state_attrs + EditableSpaceContainerImpl.state_attrs
    assert len(state_attrs) == len(set(state_attrs))

    def __init__(self, parent, name, formula=None,
                 refs=None, source=None, arguments=None):

        BaseSpaceImpl.__init__(self, parent, name, formula, refs, source)

        self._refs = ImplChainMap(self, RefView,
                                  [self.model._global_refs,
                                   self._local_refs,
                                   self._self_refs])

        self._namespace_impl = ImplChainMap(self, None,
                                            [self._cells,
                                             self._refs,
                                             self._spaces])

        self.lazy_evals = self._namespace_impl

    def _create_refs(self, arguments=None):
        return ImplChainMap(self, RefView,
                            [self.model._global_refs,
                             self._local_refs,
                             self._self_refs])

    def new_cells(self, name=None, formula=None, is_derived=False):

        if name in self.namespace:
            raise ValueError("'%s' already exist" % name)
        else:
            cells = self._new_cells(name, formula, is_derived)
            cells.inherit()
            self.model.spacegraph.update_subspaces_upward(self,
                                                          from_parent=False,
                                                          event='new_cells')
            return cells

    def new_cells_from_module(self, module_, override=True):
        # Outside formulas only

        module_ = get_module(module_)
        newcells = {}

        for name in dir(module_):
            func = getattr(module_, name)
            if isinstance(func, FunctionType):
                # Choose only the functions defined in the module.
                if func.__module__ == module_.__name__:
                    if name in self.namespace_impl and override:
                        self.cells[name].set_formula(func)
                        newcells[name] = self.cells[name]
                    else:
                        newcells[name] = self.new_cells(name, func)

        return newcells

    def new_cells_from_excel(self, book, range_, sheet=None,
                             names_row=None, param_cols=None,
                             param_order=None,
                             transpose=False,
                             names_col=None, param_rows=None):
        """Create multiple cells from an Excel range.

        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            names_row: Cells names in a sequence, or an integer number, or
              a string expression indicating row (or column depending on
              ```orientation```) to read cells names from.
            param_cols: a sequence of them
                indicating parameter columns (or rows depending on ```
                orientation```)
            param_order: a sequence of integers representing
                the order of params and extra_params.
            transpose: in which direction 'vertical' or 'horizontal'
            names_col: a string or a list of names of the extra params.
            param_rows: integer or string expression, or a sequence of them
                indicating row (or column) to be interpreted as parameters.
        """
        import modelx.io.excel as xl

        cellstable = xl.CellsTable(book, range_, sheet,
                                   names_row, param_cols, param_order,
                                   transpose, names_col, param_rows)

        if cellstable.param_names:
            sig = "=None, ".join(cellstable.param_names) + "=None"
        else:
            sig = ""

        blank_func = "def _blank_func(" + sig + "): pass"

        for cellsdata in cellstable.items():
            cells = self.new_cells(name=cellsdata.name, formula=blank_func)
            for args, value in cellsdata.items():
                cells.set_value(args, value)

    # --- Reference creation -------------------------------------

    def new_ref(self, name, value, is_derived=False):
        ref = self._new_ref(name, value, is_derived)
        ref.inherit()
        if not self.in_dynamic():
            self.model.spacegraph.update_subspaces(self)
        return ref

    # ----------------------------------------------------------------------
    # Attribute access

    def set_attr(self, name, value):
        """Implementation of attribute setting

        ``space.name = value`` by user script
        Called from ``Space.__setattr__``
        """
        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'" % name)

        if name in self.namespace:
            if name in self.refs:
                if name in self.self_refs:
                    self.new_ref(name, value)
                else:
                    raise KeyError("Ref '%s' cannot be changed" % name)

            elif name in self.cells:
                if self.cells[name].is_scalar():
                    self.cells[name].set_value((), value)
                else:
                    raise AttributeError("Cells '%s' is not a scalar." % name)
            else:
                raise ValueError
        else:
            self.new_ref(name, value)

    def del_attr(self, name):
        """Implementation of attribute deletion

        ``del space.name`` by user script
        Called from ``StaticSpace.__delattr__``
        """
        if name in self.namespace:
            if name in self.cells:
                self.del_cells(name)
            elif name in self.spaces:
                self.del_space(name)
            elif name in self.refs:
                self.del_ref(name)
            else:
                raise RuntimeError("Must not happen")
        else:
            raise KeyError("'%s' not found in Space '%s'" % (name, self.name))

    def is_static(self):
        return True

    def in_dynamic(self):
        return False

    # ----------------------------------------------------------------------
    # Inheritance

    @property
    def self_bases(self):
        return self.mro[1:]

    def add_bases(self, bases):
        self.model.spacegraph.check_mro(bases)
        for other in bases:
            self.model.spacegraph.add_edge(other, self)
        self.inherit()
        self.model.spacegraph.update_subspaces(self)

    def remove_base(self, other):  # TODO: Replace this with remove bases
        self.model.spacegraph.remove_edge(other, self)
        self.inherit()
        self.model.spacegraph.update_subspaces(self)

    def remove_bases(self, bases):  # bases are interfaces
        for base in get_impls(bases):
            self.remove_base(base)

    # --- Member deletion -------------------------------------

    def del_space(self, name):
        """Delete a space."""
        if name not in self.spaces:
            raise ValueError("Space '%s' does not exist" % name)

        if name in self.static_spaces:
            space = self.static_spaces[name]
            if space.is_derived:
                raise ValueError("%s has derived spaces"
                                 % repr(space.interface))
            else:
                self.static_spaces.del_item(name)
                self.model.spacegraph.remove_node(space)
                self.inherit()
                self.model.spacegraph.update_subspaces(self)
                # TODO: Destroy space

        elif name in self.dynamic_spaces:
            # TODO: Destroy space
            self.dynamic_spaces.del_item(name)

        else:
            raise ValueError("Derived cells cannot be deleted")

    def del_cells(self, name):
        """Implementation of cells deletion

        ``del space.name`` where name is a cells, or
        ``del space.cells['name']``
        """
        if name in self.cells:
            cells = self.cells[name]
            self.cells.del_item(name)
            self.inherit()
            self.model.spacegraph.update_subspaces(self)

        elif name in self.dynamic_spaces:
            cells = self.dynamic_spaces.pop(name)
            self.dynamic_spaces.set_update()

        else:
            raise KeyError("Cells '%s' does not exist" % name)

        NullImpl(cells)

    def del_ref(self, name):

        if name in self.self_refs:
            del self.self_refs[name]
            self.self_refs.set_update()
        elif name in self.is_derived:
            raise KeyError("Derived ref '%s' cannot be deleted" % name)
        elif name in self.arguments:
            raise ValueError("Argument cannot be deleted")
        elif name in self.local_refs:
            raise ValueError("Ref '%s' cannot be deleted" % name)
        elif name in self.model.global_refs:
            raise ValueError(
                "Global ref '%s' cannot be deleted in space" % name)
        else:
            raise KeyError("Ref '%s' does not exist" % name)

    # ----------------------------------------------------------------------
    # Reloading

    def reload(self):
        if self.source is None:
            return

        module_ = importlib.reload(get_module(self.source))
        modsrc = ModuleSource(module_)
        funcs = modsrc.funcs
        newfuncs = set(funcs)
        oldfuncs = {cells.formula.name for cells in self.cells.values()
                    if cells.formula.module_ == module_.__name__}

        cells_to_add = newfuncs - oldfuncs
        cells_to_clear = oldfuncs - newfuncs
        cells_to_update = oldfuncs & newfuncs

        for name in cells_to_clear:
            self.cells[name].reload(module_=modsrc)

        for name in cells_to_add:
            self.new_cells(name=name, formula=funcs[name])

        for name in cells_to_update:
            self.cells[name].reload(module_=modsrc)


class DynamicSpace(BaseSpace):
    pass


class DynamicSpaceImpl(BaseSpaceImpl):
    """The implementation of Dynamic Space class."""

    if_class = DynamicSpace

    state_attrs = [
        '_dynbase',
        '_parentargs'] + BaseSpaceImpl.state_attrs

    assert len(state_attrs) == len(set(state_attrs))

    def __init__(self, parent, name, formula=None,
                 refs=None, source=None, arguments=None):

        BaseSpaceImpl.__init__(self, parent, name,
                               formula, refs, source, arguments)

    def _create_refs(self, arguments=None):
        self._parentargs = self._create_parentargs()

        return ImplChainMap(self, RefView,
                                  [self.model._global_refs,
                                   self._local_refs,
                                   self._parentargs,
                                   self._self_refs])

    def _create_parentargs(self):
        if isinstance(self.parent, StaticSpaceImpl):
            parentargs = []
        elif isinstance(self.parent, RootDynamicSpaceImpl):
            parentargs = [self.parent._arguments, self.parent._parentargs]
        else:
            parentargs = [self.parent._parentargs]

        return ImplChainMap(self, None, parentargs)

    @property
    def self_bases(self):
        return []

    @property
    def arguments(self):
        return self._arguments.get_updated()

    @property
    def parentargs(self):
        return self._arguments.get_updated()

    def is_static(self):
        return False

    def in_dynamic(self):
        return True


class RootDynamicSpaceImpl(DynamicSpaceImpl):

    state_attrs = ['_arguments'] + DynamicSpaceImpl.state_attrs
    assert len(state_attrs) == len(set(state_attrs))

    def __init__(self, parent, name, formula=None,
                 refs=None, source=None, arguments=None):

        DynamicSpaceImpl.__init__(self, parent, name,
                                  formula, refs, source, arguments)
        self._bind_args(arguments)

    def _create_refs(self, arguments=None):
        self._arguments = RefDict(self, data=arguments)
        self._parentargs = self._create_parentargs()

        return ImplChainMap(self, RefView,
                                  [self.model._global_refs,
                                   self._local_refs,
                                   self._parentargs,
                                   self._arguments,
                                   self._self_refs])

    def _bind_args(self, args):
        self.boundargs = self.parent.formula.signature.bind(**args)
        self.argvalues = tuple(self.boundargs.arguments.values())
        self.argvalues_if = tuple(get_interfaces(self.argvalues))

    @property
    def self_bases(self):
        if self._dynbase is not None:
            return self._dynbase.mro
        else:
            return []

    def restore_state(self, system):

        super().restore_state(system)

        # From Python 3.5, signature is pickable,
        # pickling logic involving signature may be simplified.
        self._bind_args(self._arguments)
