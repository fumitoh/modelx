# Copyright (c) 2017-2021 Fumito Hamamura <fumito.ham@gmail.com>

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
import pathlib
import uuid
import warnings
from collections import ChainMap
from collections.abc import Sequence
from types import FunctionType, ModuleType, MappingProxyType
from modelx.core.namespace import NamespaceServer, BaseNamespaceReferrer
from modelx.core.node import ObjectNode, get_node

from modelx.core.base import (
    add_stateattrs,
    add_statemethod,
    get_impls,
    get_interfaces,
    get_mixinslots,
    Interface,
    Impl,
    set_null_impl,
    Derivable,
    ImplDict,
    ImplChainMap,
    RefChainMap,
    BaseView,
    SelectedView
)
from modelx.core.formula import BoundFunction, HasFormula
from modelx.core.reference import ReferenceImpl, ReferenceProxy
from modelx.core.node import (
    node_get_args,
    tuplize_key,
    get_node,
    key_to_node,
    OBJ,
    KEY,
    ItemFactory,
    ItemFactoryImpl
)
from modelx.core.spacecontainer import (
    BaseSpaceContainer,
    BaseSpaceContainerImpl,
    EditableSpaceContainer,
    EditableSpaceContainerImpl,
)
from modelx.core.formula import Formula, ModuleSource
from modelx.core.cells import (
    Cells,
    DynamicCellsImpl,
    UserCellsImpl,
    shareable_parameters,
)
from modelx.core.util import AutoNamer, is_valid_name, get_module


class ParamFunc(Formula):
    __slots__ = ()


class SpaceDict(ImplDict):
    __slots__ = get_mixinslots(ImplDict)
    def __init__(self, space, data=None, observers=None):
        ImplDict.__init__(self, space, SpaceView, data, observers)


class CellsDict(ImplDict):
    __slots__ = get_mixinslots(ImplDict)
    def __init__(self, space, data=None, observers=None):
        ImplDict.__init__(self, space, CellsView, data, observers)


class RefDict(ImplDict):
    __slots__ = get_mixinslots(ImplDict)

    def __init__(self, parent, data=None, observers=None):
        ImplDict.__init__(self, parent, RefView, None, observers)
        if data is not None:
            for name, value in data.items():
                self.set_item(name, value)

    def set_item(self, name, value, skip_self=False):
        ImplDict.set_item(self, name,
                          self.wrap_impl(self.owner, name, value), skip_self)

    def del_item(self, name, skip_self=False):
        # TODO: Better way to get TraceManager
        self.owner.model.clear_attr_referrers(self.fresh[name])
        ImplDict.del_item(self, name, skip_self=skip_self)

    def wrap_impl(self, parent, name, value):

        if isinstance(value, ReferenceImpl):
            return value
        elif isinstance(value, Impl):
            raise RuntimeError("must not happen")
        else:
            return ReferenceImpl.get_class(value)(parent, name, value, container=self)


class DynBaseRefDict(RefDict):

    def wrap_impl(self, parent, name, value):

        assert isinstance(value, ReferenceImpl)

        if isinstance(value.interface, Interface) and value.interface._is_valid():

            if value.is_relative:   # value.is_relative is set to True
                                    # When value.is_defined and
                                    # value.refmode == "relative"

                impl = value.interface._impl.namedid
                root = self.owner.rootspace._dynbase.namedid
                rootlen = len(root)

                if root == impl:
                    return self.owner.rootspace
                elif root == impl[:rootlen]:
                    return self.owner.rootspace.get_impl_from_name(
                        impl[rootlen+1:]) # +1 to remove preceding dot
                else:
                    if value.refmode == "auto":
                        if value.is_defined:
                            return value
                        else:
                            return value.direct_bases[0]

                    elif value.refmode == "relative":
                        raise ValueError(
                            "'%s' referred as '%s' is out of '%s'" %
                            (impl, value.namedid, root)
                        )
                    else:
                        raise RuntimeError("must not happen")

            else:   # absolute
                return value
        else:
            return value


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

    CellsView objects are returned by :attr:`UserSpace.cells` property.
    When :attr:`UserSpace.cells` is called without subscription(``[]`` operator),
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
        cells.spacemgr.del_cells(cells.parent, name)

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
    """A mapping of space names to space objects."""

    def __delitem__(self, name):
        space = self._data[name]._impl
        # space.parent.del_space(name)
        space.model.updater.del_defined_space(space)


class NamedItemSpaceView(SpaceView):

    def _get_attrdict(self, extattrs=None, recursive=True):
        """For spyder-modelx to populate SpaceView for named_itemspace"""

        result = {"type": type(self).__name__}
        try:
            result["items"] = {
                name: item._baseattrs
                for name, item in self.items()
            }
        except:
            raise RuntimeError("%s literadict raised an error" % self)

        return result


class RefView(SelectedView):

    @property
    def _baseattrs(self):

        result = {"type": type(self).__name__}

        result["items"] = items = {}
        for name, item in self.items():
            if name[0] != "_":
                items[name] = ReferenceProxy(self.impl[name])._baseattrs

        return result


    def _get_attrdict(self, extattrs=None, recursive=True):

        result = {"type": type(self).__name__}
        result["items"] = items = {}

        for name, item in self.items():
            if name[0] != "_":
                items[name] = ReferenceProxy(
                    self.impl[name])._get_attrdict(extattrs, recursive)

        return result


class BaseSpace(BaseSpaceContainer, ItemFactory):

    __slots__ = ()

    def __getattr__(self, name):

        if name in self._impl.namespace:
            return self._impl.get_attr(name)
        else:
            raise AttributeError  # Must return AttributeError for hasattr

    def __dir__(self):
        return self._impl.namespace.interfaces

    def _get_object(self, name, as_proxy=False):
        parts = name.split(".")
        attr = parts.pop(0)

        if as_proxy and attr in self.refs:
            return ReferenceProxy(self._impl.refs[attr])
        elif hasattr(self, attr):
            return super()._get_object(name, as_proxy)
        else:
            if attr in self._named_itemspaces:
                space = self._named_itemspaces[attr]
                if parts:
                    return space._get_object(".".join(parts), as_proxy)
                else:
                    return space
            else:
                raise NameError("'%s' not found" % name)

    @property
    def bases(self):
        """List of base classes."""
        return get_interfaces(self._impl.bases)

    @property
    def _direct_bases(self):
        """Directly inherited base classes"""
        return get_interfaces(
            self._impl.spacemgr.get_direct_bases(self._impl))

    def _is_base(self, other):
        """True if the space is a base space of ``other``, False otherwise."""
        return self._impl.is_base(other._impl)

    def _is_sub(self, other):
        """True if the space is a sub space of ``other``, False otherwise."""
        return self._impl.is_sub(other._impl)

    def _is_static(self):
        """True if the space is a static space, False if dynamic."""
        return isinstance(self._impl, UserSpaceImpl)

    def _is_derived(self):
        """True if the space is a derived space, False otherwise."""
        return self._impl.is_derived

    def _is_defined(self):
        """True if the space is a defined space, False otherwise."""
        return self._impl.is_defined

    def _is_root(self):
        """True if ths space is a dynamic space, False otherwise."""
        return isinstance(self._impl, ItemSpaceImpl)

    def _is_dynamic(self):
        """True if the space is in a dynamic space, False otherwise."""
        return self._impl.is_dynamic()

    @property
    def cells(self):
        """A mapping of cells names to the cells objects in the space."""
        return self._impl.cells.interfaces

    @property
    def spaces(self):
        """A mapping associating names to named spaces."""
        return self._impl.named_spaces.interfaces

    @property
    def named_spaces(self):
        """A mapping associating names to named spaces.

        Alias to :py:meth:`spaces`

        .. versionadded:: 0.2.0
        """
        return self._impl.named_spaces.interfaces

    @property
    def static_spaces(self):
        """A mapping associating names to named spaces.

        Alias to :py:meth:`spaces`

        .. deprecated:: 0.2.0 Use :attr:`named_spaces` instead.
        """
        warnings.warn("static_spaces is deprecated. Use named_spaces instead.")
        return self._impl.named_spaces.interfaces

    @property
    def itemspaces(self):
        """A mapping of arguments to :class:`ItemSpace` objects.

        A read-only mapping associating child :class:`ItemSpace` objects
        as its values to  their arguments as its keys.
        """

        def untuplize(k):
            length = len(k)
            if length > 1:
                return k
            elif length == 1:
                return k[0]
            else:
                return None

        d = {untuplize(k): v.interface
             for k, v in self._impl.param_spaces.items()}
        return MappingProxyType(d)

    @property
    def _named_itemspaces(self):
        """A mapping associating names to dynamic spaces."""
        return self._impl.named_itemspaces.interfaces

    @property
    def parameters(self):
        """A tuple of parameter strings."""
        if self._impl.formula is not None:
            return tuple(self._impl.formula.parameters)
        else:
            return None

    @property
    def refs(self):
        """A map associating names to objects accessible by the names."""
        return self._impl.refs.interfaces

    @property
    def _self_refs(self):
        """A mapping associating names to self refs."""
        return self._impl.self_refs.interfaces

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
        return self._impl.get_itemspace(tuplize_key(self, key)).interface

    def __delitem__(self, key):
        """Delete a child :class:`ItemSpace` object"""

        key = tuplize_key(self, key)
        if key in list(self._impl.param_spaces):
            self._impl.clear_itemspace_at(key)
        else:
            raise KeyError(key)

    def clear_at(self, *args, **kwargs):
        """Delete a child :class:`ItemSpace` object"""

        key = get_node(self, args, kwargs)[KEY]
        if key in list(self._impl.param_spaces):
            self._impl.clear_itemspace_at(key)
        else:
            raise KeyError(key)

    def clear_all(self):
        """Clears :class:`~modelx.core.cells.Cells` and :class:`~modelx.core.space.ItemSpace`.

        Clears both the input values and the calculated values of
        all the recursive child :class:`~modelx.core.cells.Cells` in this space
        and delete all the recursive child
        :class:`~modelx.core.space.ItemSpace` objects in the space.

        .. seealso::

            * :meth:`Model.clear_all<modelx.core.model.Model.clear_all>`
            * :meth:`clear_items`
            * :meth:`clear_cells`

        .. versionchanged:: 0.16.0 Changed to delete child ItemSpaces
            recursively and to clear recursive child Cells.
            :meth:`clear_items` works the same as this method before change.

        """
        self._impl.clear_all_cells(
            clear_input=True, recursive=True, del_items=True
        )

    def clear_items(self):
        """Deletes all the child :class:`ItemSpace` objects.

        Deletes all the child :class:`ItemSpace` objects in this space.
        This method does not delete :class:`ItemSpace` in child spaces
        of this space.

        .. seealso:: :meth:`clear_all`

        .. versionadded:: 0.16.0
        """
        self._impl.del_all_itemspaces()

    def clear_cells(self, clear_input=False, recursive=True):
        """Clears child :class:`~modelx.core.cells.Cells`.

        By default, clears all the calculated values of all the recursive child
        :class:`~modelx.core.cells.Cells`.
        If ``clear_input`` is :obj:`True`, all the input values of the child
        cells are also cleared in addition to the calculated values.
        If ``recursive`` is :obj:`False`, only the cells that are the direct
        children of this Space are cleared, and cells in the recursive child
        spaces are not cleared.

        Args:
            clear_input(:obj:`bool`): If :obj:`True`, input values
                of the Cells are also cleared. Defaults to :obj:`False`.

            recursive(:obj:`bool`): If :obj:`True`, Cells in
                the recursive child Spaces are also cleared.
                If :obj:`False`, only the child Cells of this Space
                are cleared.

        .. seealso:: :meth:`clear_all`

        .. versionadded:: 0.16.0
        """
        self._impl.clear_all_cells(
            clear_input=clear_input, recursive=recursive)

    def __iter__(self):
        raise TypeError("'Space' is not iterable")

    def __call__(self, *args, **kwargs):
        return self._impl.get_itemspace(args, kwargs).interface

    # ----------------------------------------------------------------------
    # Name referrer

    def get_referents(self):

        if self._impl.formula is None:
            return None
        else:
            refs = self._impl.altfunc.get_referents()
            result = refs.copy()

            for key, data in refs.items():
                if key != "builtins" and key != "missing":
                    result[key] = {name: obj.to_node() for
                                   name, obj in refs[key].items()}
            return result

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_frame(self, *args):
        """Convert the space itself into a Pandas DataFrame object."""
        return self._impl.to_frame(args)

    @property
    def frame(self):
        """Alias of :meth:`to_frame`."""
        return self._impl.to_frame(())

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = super()._baseattrs
        result["named_spaces"] = self.named_spaces._baseattrs
        # For backward compatibility with spyder-modelx -0.1.0
        result["static_spaces"] = self.named_spaces._baseattrs
        result["named_itemspaces"] = self._named_itemspaces._baseattrs_private
        # For backward compatibility with spyder-modelx -0.1.0
        result["dynamic_spaces"] = self._named_itemspaces._baseattrs_private
        result["cells"] = self.cells._baseattrs
        result["refs"] = self.refs._baseattrs
        result["bases"] = [base._namedid for base in self.bases]

        if self.has_params():
            result["params"] = ", ".join(self.parameters)
        else:
            result["params"] = ""

        return result


    def _get_attrdict(self, extattrs=None, recursive=True):
        """Get extra attributes"""
        result = super(BaseSpace, self)._get_attrdict(extattrs, recursive)

        for name in  [
            "named_spaces",
            "_named_itemspaces",
            "cells",
            "refs"
        ]:
            attr = getattr(self, name)
            if recursive:
                result[name] = attr._get_attrdict(extattrs, recursive)
            else:
                result[name] = tuple(attr)

        result["bases"] = [base._namedid for base in self.bases]
        result["parameters"] = self.parameters

        if extattrs:
            self._get_attrdict_extra(result, extattrs, recursive)

        return result


class UserSpace(BaseSpace, EditableSpaceContainer):
    """Container of cells, other spaces, and cells namespace.

    UserSpace objects can contain cells and other spaces.
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

    def copy(self, parent, name=None, defined_only=False):
        """Make a copy of itself

        Create a new :class:`UserSpace` in ``parent`` by copying itself.
        If ``name`` is given, the copied :class:`UserSpace`
        is named ``name`` in stead of the original name.

        Args:
            parent(:class:`UserSpace`): parent of the copied :class:`UserSpace`
            name(:obj:`str`, optional): name of the copied :class:`UserSpace`
            defined_only(:obj:`bool`, optional): If ``True``, only defined
                Spaces are copied. Defaults to ``False``.
        """
        return self._impl.model.updater.copy_space(
            parent._impl, self._impl, name, defined_only).interface

    def rename(self, name):
        """Rename the space

        Rename the UserSpace itself to ``name``.
        A UserSpace cannot be renamed if it is subsequently derived
        by its recursive parent's inheritance.

        When the UserSpace is renamed, all the values, including input values,
        of the recursive child Cells in the UserSpace are cleared
        and all the recursive child ItemSpaces are deleted.

        If the UserSpace has subsequently derived sub spaces, these
        sub spaces are also renamed.

        .. versionadded:: 0.16.0
        """
        self._impl.spacemgr.rename_space(self._impl, name)

    def add_bases(self, *bases):
        """Add base spaces."""
        return self._impl.model.updater.add_bases(self._impl, get_impls(bases))

    def remove_bases(self, *bases):
        """Remove base spaces."""
        return self._impl.model.updater.remove_bases(
            self._impl, get_impls(bases))

    def import_funcs(self, module):
        """Create a cells from a module."""
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module)
        return get_interfaces(newcells)

    def new_cells_from_module(self, module):
        """Create a cells from a module.

        Alias to :py:meth:`import_funcs`.
        """
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module)
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

    def new_cells_from_excel(
        self,
        book,
        range_,
        sheet=None,
        names_row=None,
        param_cols=None,
        param_order=None,
        transpose=False,
        names_col=None,
        param_rows=None,
    ):
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

        See Also:
            :meth:`new_space_from_excel`: Create Spaces and Cells from Excel file.
        """
        return self._impl.new_cells_from_excel(
            book,
            range_,
            sheet,
            names_row,
            param_cols,
            param_order,
            transpose,
            names_col,
            param_rows,
        )

    def new_cells_from_pandas(self, obj, cells=None, param=None):
        """Create new cells from Pandas Series or DataFrame object.

        Return new cells created from Pandas Series or DataFrame object
        passed as ``obj``.

        ``obj`` can either be a Series or a DataFrame. If ``obj``
        is a Series, a single cells is created. The cells' name is taken
        from the Series' name, but can be overwritten if a valid name
        is passed as ``cells``.

        If ``obj`` is a DataFrame, a cells is created for each column.
        The cells' names can be overwritten by a sequence of valid names
        passed as ``cells``

        Keys and values of the cells data are copied from ``obj``.

        ``obj`` can have MultiIndex. If the index(es) of ``obj``
        has/have name(s), the parameter name(s) of the cells is/are
        set to the name(s), but can be overwritten by ``param``
        parameter. If the index(es) of ``obj`` has/have no name(s),
        and ``param`` is not given, error is raised.
        Error is raised when ``obj`` has duplicated indexes.

        Args:
            obj: Pandas Series or DataFrame object
            cells (str, optional): cells name.
                If ``obj`` has a valid name and this ``cells`` is not given,
                the name is used. If ``obj`` does not have a name and
                this ``cells`` is not given, the cells is named automatically.
            param: sequence of strings to set parameter name(s).
                A single string can also be passed to set a single parameter
                name when ``obj`` has a single
                level index (i.e. not MultiIndex).

        Returns:
            New cells if ``obj`` is a Series, CellsView if ``obj`` is DataFrame.

        See Also:
            :meth:`new_space_from_pandas`: Create Spaces and Cells from DataFrame or Series.
        """
        return self._impl.new_cells_from_pandas(obj, cells, param)

    def new_cells_from_csv(
            self, filepath, cells=None, param=None, *args, **kwargs):
        """Create cells from a comma-separated values (csv) file.

        This method internally calls Pandas `read_csv`_ function,
        and creates cells by passing
        the returned DataFrame object to :meth:`new_cells_from_pandas`.
        The ``filepath`` argument to this method is passed to
        to `read_csv`_ as ``filepath_or_buffer``,
        and the user can pass other arguments to `read_csv`_ by
        supplying those arguments to this method as
        variable-length parameters,
        ``args`` and ``kargs``.

        .. _read_csv:
            https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html

        Args:
            filepath (str, path object, or file-like object): Path to the file.
            cells: Sequence of strings to set cells name. string is also
                accepted if `read_csv`_ returns a Series because of
                its ``squeeze`` parameter set to ``True``.
            param: Sequence of strings to set parameter name(s).
                A single string can also be passed to set a single parameter
                name when ``frame`` has a single
                level index (i.e. not MultiIndex).
            args: Any positional arguments to be passed to `read_csv`_.
            kwargs: Any keyword arguments to be passed to `read_csv`_.

        See Also:
            :meth:`new_space_from_csv`: Create Spaces and Cells from CSV.
        """

        return self._impl.new_cells_from_csv(
            filepath,
            cells=cells,
            param=param,
            args=args,
            kwargs=kwargs
        )

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

        elif isinstance(item, UserSpace):
            return item._impl in self._impl.spaces.values()

        else:
            return False

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def absref(self, **kwargs):
        """Set absolute References

        Set References in the *absolute* reference mode by passing a pair
        of the References' names and values as keyword arguments.

        Setting a Reference by this method is equivalent to
        calling :meth:`set_ref` by passing "absolute" to ``refmode``.

        Example:
            ``A`` and ``B`` are UserSpaces and ``foo`` is a Cells in ``B``.
            The code blow assigns the Cells to References with
            the same names as the Cells in Space ``A``::

                >>> A.absref(foo=B.foo)

                >>> A.foo
                <Cells foo(x) in Model1.B>

            By passing multiple keyword assignments, multiple References
            can be assigned.
            Below ``bar`` and ``baz`` are Cells in ``B``::

                >>> A.absref(bar=B.bar, baz=B.baz)

                >>> A.bar
                <Cells bar(x) in Model1.B>

                >>> A.baz
                <Cells baz(x) in Model1.B>

        See Also:
            :meth:`set_ref`
            :meth:`relref`

        """
        for name, value in kwargs.items():
            self.set_ref(name, value, refmode="absolute")

    def relref(self, **kwargs):
        """Set relative References

        Set References in the *relative* reference mode by passing a pair
        of the References' names and values as keyword arguments.

        Setting a Reference by this method is equivalent to
        calling :meth:`set_ref` by passing "relative" to ``refmode``.

        Example:
            ``A`` and ``B`` are UserSpaces and ``foo`` is a Cells in ``B``.
            The code blow assigns the Cells to References with
            the same names as the Cells in Space ``A``::

                >>> A.absref(foo=B.foo)

                >>> A.foo
                <Cells foo(x) in Model1.B>

            By passing multiple keyword assignments, multiple References
            can be assigned.
            Below ``bar`` and ``baz`` are Cells in ``B``::

                >>> A.absref(bar=B.bar, baz=B.baz)

                >>> A.bar
                <Cells bar(x) in Model1.B>

                >>> A.baz
                <Cells baz(x) in Model1.B>

        See Also:
            :meth:`set_ref`
            :meth:`absref`

        """
        for name, value in kwargs.items():
            self.set_ref(name, value, refmode="relative")

    def set_ref(self, name, value, refmode):
        """Set a Reference

        Set a Reference that assigns ``value`` to ``name`` in this Space.

        Args:
            name: Reference name
            value: Reference value
            refmode: "auto", "absolute" or "relative" to indicate
                reference mode

        See Also:
            :meth:`relref`
            :meth:`absref`
        """
        if hasattr(type(self), name):
            raise AttributeError("cannot set '%s'" % name)
        elif name in self.properties:
            raise AttributeError("cannot set '%s'" % name)
        else:
            self._impl.set_attr(name, value, refmode=refmode)


    def __delattr__(self, name):
        if hasattr(type(self), name):
            attr = getattr(type(self), name)
            if isinstance(attr, property):
                if hasattr(attr, 'fdel'):
                    attr.fdel(self)
                else:
                    raise AttributeError("cannot delete %s" % name)
        else:
            self._impl.del_attr(name)

    # ----------------------------------------------------------------------
    # Formula

    @BaseSpace.formula.setter
    def formula(self, formula):
        self._impl.set_formula(formula)

    @formula.deleter
    def formula(self):
        self._impl.del_formula()

    def set_formula(self, formula):
        """Set if the parameter function."""
        self._impl.set_formula(formula)

    @BaseSpace.parameters.setter
    def parameters(self, parameters):
        """Set formula from parameter list"""
        src = "lambda " + ", ".join(parameters) + ": None"
        self._impl.set_formula(src)

    def del_formula(self):
        """Delete formula"""
        self._impl.del_formula()

    @Interface.doc.setter
    def doc(self, value):
        self._impl.doc = value


class ItemSpaceParent(ItemFactoryImpl, BaseNamespaceReferrer, HasFormula):

    __cls_stateattrs = [
        "_named_itemspaces",
        "itemspacenamer",
        "param_spaces",
        "formula",
        "altfunc"
    ]

    def __init__(self, formula):
        self._named_itemspaces = ImplDict(self, SpaceView)
        self.itemspacenamer = AutoNamer("__Space")

        # ------------------------------------------------------------------
        # Construct altfunc after space members are crated

        self.param_spaces = {}
        self.formula = None
        if formula is not None:
            self.set_formula(formula)

    # ----------------------------------------------------------------------
    # BaseNamespaceReferrer Implementation

    def on_namespace_change(self, is_all, names):
        if is_all:
            self.del_all_itemspaces()
        elif self.formula and self.altfunc.global_names:
            if any(n for n in names if n in self.altfunc.global_names):
                self.del_all_itemspaces()

    # ----------------------------------------------------------------------
    # Dynamic Space Operation

    @property
    def named_itemspaces(self):
        return self._named_itemspaces.fresh

    @property
    def data(self):
        return self.param_spaces

    def set_formula(self, formula):

        if formula is None:
            if self.formula is not None:
                self.del_formula()
        else:
            if self.formula is None:
                if isinstance(formula, ParamFunc):
                    self.formula = formula
                else:
                    self.formula = ParamFunc(formula, name="_formula")
                self.altfunc = BoundFunction(self)
                self.altfunc.set_update()
            else:
                self.del_formula()
                self.set_formula(formula)

    def del_formula(self):
        """Delete formula

        All child itemspaces are deleted
        """
        if self.formula is None:
            return
        else:
            self.del_all_itemspaces()
            self.altfunc = self.formula = None

    def _get_dynamic_base(self, bases_):
        """Create or get the base space from a list of spaces

        if a direct base space in `bases` is dynamic, replace it with
        its base.
        """
        bases = tuple(
            base._dynbase if base.is_dynamic() else base for base in bases_
        )

        if len(bases) == 1:
            return bases[0]

        elif len(bases) > 1:
            return self.model.get_dynamic_base(bases)

        else:
            RuntimeError("must not happen")

    def _new_itemspace(
        self,
        bases,
        name=None,
        refs=None,
        arguments=None
    ):
        """Create a new dynamic root space."""
        space = ItemSpaceImpl(
            parent=self,
            base=self._get_dynamic_base(bases),
            name=name,
            refs=refs,
            arguments=arguments,
        )
        return space

    def del_all_itemspaces(self):
        for key in list(self.param_spaces):
            self.clear_itemspace_at(key)

    def clear_itemspace_at(self, key):
        if self.has_node(key):
            self.model.clear_with_descs(key_to_node(self, key))

    def on_clear_trace(self, key):
        self._del_itemspace(key)

    def _del_itemspace(self, key):
        if key in list(self.param_spaces):
            space = self.param_spaces[key]
            space.on_delete()
            self.named_itemspaces.del_item(space.name)
            del self.param_spaces[key]

    def get_itemspace(self, args, kwargs=None):
        """Create a dynamic root space

        Called from interface methods
        """
        node = get_node(self, args, kwargs)
        return self.system.executor.eval_node(node)

    def on_eval_formula(self, key):
        params = self.altfunc.fresh.altfunc(*key)

        if params is None:
            params = {"bases": [self]}  # Default
        else:
            if "bases" in params:
                bases = get_impls(params["bases"])
                if isinstance(bases, UserSpaceImpl):
                    params["bases"] = [bases]
                elif bases is None:
                    params["bases"] = [self]  # Default
                else:
                    params["bases"] = bases
            else:
                params["bases"] = [self]

        params["arguments"] = node_get_args(key_to_node(self, key))
        space = self._new_itemspace(**params)
        self.param_spaces[key] = space
        return space

    # ----------------------------------------------------------------------
    # ItemFactoryImpl override

    def has_node(self, key):
        return key in self.param_spaces

    def get_value_from_key(self, key):
        return self.param_spaces[key].interface


@add_stateattrs
class BaseSpaceImpl(
    NamespaceServer,
    ItemSpaceParent,
    BaseSpaceContainerImpl,
    Impl
):
    """Read-only base Space class

    * Cells container
    * Ref container
    * Namespace
    * Formula container
    * Implement Derivable
    """

    # ----------------------------------------------------------------------
    # Serialization by pickle

    __cls_stateattrs = [
            "_cells",
            "_local_refs",
            "_self_refs",
            "_refs"
    ]

    def __init__(
        self,
        parent,
        name,
        container,
        formula=None,
        refs=None,
        arguments=None,
        doc=None
    ):
        Impl.__init__(
            self,
            system=parent.system,
            parent=parent,
            name=name,
            doc=doc
        )
        self.spacemgr = parent.spacemgr

        # ------------------------------------------------------------------
        # Construct member containers

        self._self_refs = self._init_self_refs()
        self._cells = CellsDict(self)
        self._named_spaces = SpaceDict(self)
        self._local_refs = {"_self": self, "_space": self}
        self._refs = self._init_refs(arguments)

        NamespaceServer.__init__(
            self,
            ImplChainMap(
                self, None, [self._cells, self._refs, self._named_spaces],
                map_ids=("cells", "refs", "spaces")
            )
        )
        BaseNamespaceReferrer.__init__(self, server=self)

        self.lazy_evals = self._namespace
        ItemSpaceParent.__init__(self, formula)
        self._all_spaces = ImplChainMap(
            self, SpaceView, [self._named_spaces, self._named_itemspaces]
        )
        container.set_item(name, self)

        # ------------------------------------------------------------------
        # Add initial refs members

        if refs is not None:
            for key, value in refs.items():
                ReferenceImpl.get_class(value)(self, key, value, container=self._self_refs,
                              refmode="auto")

    def _init_self_refs(self):
        raise NotImplementedError

    def _init_refs(self, arguments=None):
        raise NotImplementedError

    def get_attr(self, name):

        value = self.namespace[name]

        if self.system.callstack.counter:
            if isinstance(value, ReferenceImpl):
                self.system.refstack.append(
                    (self.system.callstack.counter - 1, value)
                )

        return self.namespace.interfaces[name]

    @property
    def cells(self):
        return self._cells.fresh

    @property
    def refs(self):
        return self._refs.fresh

    @property
    def self_refs(self):
        return self._self_refs.fresh

    @property
    def local_refs(self):
        return self._local_refs

    # --- Inheritance properties ---

    @property
    def bases(self):
        """Return an iterator over direct base spaces"""
        spaces = self.spacemgr.get_deriv_bases(self)
        return spaces

    @staticmethod
    def _get_members(other):
        return other.named_spaces

    def is_base(self, other):
        return self in other.bases

    def is_sub(self, other):
        return other in self.bases

    # --- Dynamic space properties ---

    def is_dynamic(self):
        raise NotImplementedError

    def clear_all_cells(
            self, clear_input=False, recursive=False, del_items=False):
        for cells in self.cells.values():
            cells.clear_all_values(clear_input=clear_input)
        if del_items:
            self.del_all_itemspaces()
        if recursive:
            for space in self.named_spaces.values():
                space.clear_all_cells(
                    clear_input=clear_input,
                    recursive=recursive,
                    del_items=del_items
                )

    # ----------------------------------------------------------------------
    # Component properties

    def get_impl_from_name(self, name):
        """Retrieve an object by a dotted name relative to the space."""
        return self.get_impl_from_namelist(name.split("."))

    def get_impl_from_namelist(self, parts: list):
        # parts list is changed in this method

        child = parts.pop(0)

        if parts:
            return self.all_spaces[child].get_impl_from_namelist(parts)
        else:
            if child in self.namespace:
                return self._namespace[child]
            elif child in self.named_itemspaces:
                return self._named_itemspaces[child]
            else:
                raise RuntimeError("name '%s' not found" % child)

    # ----------------------------------------------------------------------
    # repr methods

    def repr_self(self, add_params=True):
        return self.name

    def repr_parent(self):
        if self.parent.repr_parent():
            return self.parent.repr_parent() + "." + self.parent.repr_self()
        else:
            return self.parent.repr_self()

    # ----------------------------------------------------------------------
    # Space properties

    def __getstate__(self):
        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.stateattrs
        }
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self):
        """Called after unpickling to restore some attributes manually."""
        BaseSpaceContainerImpl.restore_state(self)

    # ----------------------------------------------------------------------
    # Pandas, Module, Excel I/O

    def to_frame(self, args):
        return _to_frame_inner(self.cells, args)

    def on_delete(self):
        for cells in self.cells.values():
            cells.clear_all_values(clear_input=True)
            cells.on_delete()
        super().on_delete()


class DynamicBase(BaseSpaceImpl):

    __cls_stateattrs = [
     "_dynamic_subs"
    ]

    def __init__(self):
        BaseNamespaceReferrer.__init__(self, self)
        self._dynamic_subs = []

    def on_namespace_change(self, is_all, names):
        ItemSpaceParent.on_namespace_change(self, is_all, names)
        for dyns in self._dynamic_subs:
            dyns.notify_referrers(is_all, names)

    def change_dynsub_refs(self, name):

        for dynsub in self._dynamic_subs:
            baseref = self.self_refs[name]
            dynsub._dynbase_refs.set_item(name, baseref)


@add_stateattrs
class UserSpaceImpl(
    DynamicBase,
    EditableSpaceContainerImpl,
    Derivable
):
    """Editable base Space class

    * cell creation
    * ref assignment
    """

    interface_cls = UserSpace

    __cls_stateattrs = [
     "cellsnamer",
     "source"
    ]

    def __init__(
        self,
        parent,
        name,
        container,
        is_derived,
        formula=None,
        refs=None,
        source=None,
        doc=None
    ):
        BaseSpaceImpl.__init__(
            self,
            parent=parent,
            name=name,
            container=container,
            formula=formula,
            refs=refs,
            doc=doc
        )
        DynamicBase.__init__(self)
        EditableSpaceContainerImpl.__init__(self)
        Derivable.__init__(self, is_derived)

        self.cellsnamer = AutoNamer("Cells")

        if isinstance(source, ModuleType):
            self.source = source.__name__
        else:
            self.source = source

    def _init_self_refs(self):
        return RefDict(self)

    def _init_refs(self, arguments=None):
        return RefChainMap(
            self,
            RefView,
            [self._self_refs, self._local_refs, self.model._global_refs]
        )

    @Impl.doc.setter
    def doc(self, value):
        self._doc = value

    # ----------------------------------------------------------------------
    # Cells creation

    def new_cells(self, name=None, formula=None, is_derived=False,
                  source=None):

        cells = self.spacemgr.new_cells(
            self, name=name, formula=formula, is_derived=is_derived,
            source=source)

        return cells

    def new_cells_from_module(self, module, override=True):
        # Outside formulas only

        module = get_module(module)
        newcells = {}

        for name in dir(module):
            func = getattr(module, name)
            if isinstance(func, FunctionType):
                # Choose only the functions defined in the module.
                if func.__module__ == module.__name__:
                    if name in self.namespace and override:
                        self.spacemgr.change_cells_formula(
                            self.cells[name], func)
                        newcells[name] = self.cells[name]
                    else:
                        newcells[name] = self.new_cells(name, func)

        return newcells

    def new_cells_from_excel(
        self,
        book,
        range_,
        sheet=None,
        names_row=None,
        param_cols=None,
        param_order=None,
        transpose=False,
        names_col=None,
        param_rows=None,
        call_id=None
    ):
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
        import modelx.io.excel_legacy as xl

        cellstable = xl.CellsTable(
            book,
            range_,
            sheet,
            names_row,
            param_cols,
            param_order,
            transpose,
            names_col,
            param_rows,
        )

        if cellstable.param_names:
            sig = "=None, ".join(cellstable.param_names) + "=None"
        else:
            sig = ""

        blank_func = "def _blank_func(" + sig + "): pass"

        source = {
            "method": "new_cells_from_excel",
            "args": [str(pathlib.Path(book).absolute()), range_],
            "kwargs": {
                "sheet": sheet,
                "names_row": names_row,
                "param_cols": param_cols,
                "param_order": param_order,
                "transpose": transpose,
                "names_col": names_col,
                "param_rows": param_rows,
                "call_id": call_id or str(uuid.uuid4())
            }
        }

        for cellsdata in cellstable.items():
            cells = self.new_cells(name=cellsdata.name, formula=blank_func,
                                   source=source)
            for args, value in cellsdata.items():
                cells.set_value(args, value)

    def new_cells_from_pandas(self, obj, cells, param, call_id=None):
        from modelx.io.pandas import new_cells_from_pandas

        source = {
            "method": "new_cells_from_pandas",
            "args": [obj],
            "kwargs": {
                "cells": cells,
                "param": param,
                "call_id": call_id or str(uuid.uuid4())
            }
        }

        return new_cells_from_pandas(self, obj, cells, param, source)

    def new_cells_from_csv(
            self, filepath, cells, param, args, kwargs, call_id=None):
        import pandas as pd
        from modelx.io.pandas import new_cells_from_pandas

        source = {
            "method": "new_cells_from_csv",
            "args": [filepath],
            "kwargs": {
                "cells": cells,
                "param": param,
                "args": args,
                "kwargs": kwargs,
                "call_id": call_id or str(uuid.uuid4())
            }
        }

        return new_cells_from_pandas(
            self, pd.read_csv(filepath, *args, **kwargs), cells, param, source)

    # ----------------------------------------------------------------------
    # Attribute access

    def set_attr(self, name, value, refmode=False):
        """Implementation of attribute setting

        ``space.name = value`` by user script
        Called from ``Space.__setattr__``
        """
        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'" % name)

        if name in self.namespace:
            if name in self.refs:
                if name in self.self_refs:
                    self.spacemgr.change_ref(self, name, value, refmode)
                elif self.refs[name].parent is self.model:
                    self.spacemgr.new_ref(self, name, value, refmode)
                else:
                    raise RuntimeError("must not happen")

            elif name in self.cells:
                if self.cells[name].is_scalar():
                    self.cells[name].set_value((), value)
                else:
                    raise AttributeError("Cells '%s' is not a scalar." % name)
            else:
                raise ValueError
        else:
            self.spacemgr.new_ref(self, name, value, refmode)

    def del_attr(self, name):
        """Implementation of attribute deletion

        ``del space.name`` by user script
        Called from ``UserSpace.__delattr__``
        """
        if name in self.namespace:
            if name in self.cells:
                self.spacemgr.del_cells(self, name)
            elif name in self.spaces:
                self.model.updater.del_defined_space(self.spaces[name])
            elif name in self.refs:
                self.del_ref(name)
            else:
                raise RuntimeError("Must not happen")
        else:
            raise KeyError("'%s' not found in Space '%s'" % (name, self.name))

    def is_dynamic(self):
        return False

    # --- Member deletion -------------------------------------

    def del_ref(self, name):

        if name in self.self_refs:
            self.spacemgr.del_ref(self, name)
        elif name in self.is_derived:
            raise KeyError("Derived ref '%s' cannot be deleted" % name)
        elif name in self.arguments:
            raise ValueError("Argument cannot be deleted")
        elif name in self.local_refs:
            raise ValueError("Ref '%s' cannot be deleted" % name)
        elif name in self.model.global_refs:
            raise ValueError(
                "Global ref '%s' cannot be deleted in space" % name
            )
        else:
            raise KeyError("Ref '%s' does not exist" % name)

    # ----------------------------------------------------------------------
    # Reloading

    def reload(self):
        if self.source is None:
            return

        module = importlib.reload(get_module(self.source))
        modsrc = ModuleSource(module)
        funcs = modsrc.funcs
        newfuncs = set(funcs)
        oldfuncs = {
            cells.formula.name
            for cells in self.cells.values()
            if cells.formula.module == module.__name__
        }

        cells_to_add = newfuncs - oldfuncs
        cells_to_clear = oldfuncs - newfuncs
        cells_to_update = oldfuncs & newfuncs

        for name in cells_to_clear:
            self.cells[name].reload(module=modsrc)

        for name in cells_to_add:
            self.new_cells(name=name, formula=funcs[name])

        for name in cells_to_update:
            self.cells[name].reload(module=modsrc)

    def inherit(self, updater, bases, attr):

        if bases and self.is_derived:
            self.set_formula(bases[0].formula)

        attrs = {
            "cells": self.on_del_cells,
            "self_refs": self.on_del_ref
        }

        selfdict = getattr(self, attr)
        basedict = ChainMap(*[getattr(b, attr) for b in bases])

        missing = set(basedict) - set(selfdict)
        shared = set(selfdict) & set(basedict)
        diffs = set(selfdict) - set(basedict)

        for name in missing | shared:

            bs = [bm[name] for bm in basedict.maps
                  if name in bm and bm[name].is_defined]

            if name in missing:

                if attr == "cells":
                    selfdict[name] = UserCellsImpl(
                        space=self, name=name, formula=None,
                        is_derived=True)

                elif attr == "self_refs":
                    selfdict[name] = ReferenceImpl.get_class(None)(
                        self, name, None,
                        container=self._self_refs,
                        is_derived=True,
                        refmode=bs[0].refmode
                    )
                else:
                    raise RuntimeError("must not happen")

            if selfdict[name].is_derived:
                selfdict[name].inherit(updater, bs)

        for name in diffs:
            if selfdict[name].is_derived:
                attrs[attr](name)

    def on_del_cells(self, name):
        cells = self.cells[name]
        self.model.clear_obj(cells)
        self.cells.del_item(name)
        cells.on_delete()

    def on_change_ref(self, name, value, is_derived, refmode,
                      is_relative):
        ref = self.self_refs[name]
        self.on_del_ref(name)
        self.on_create_ref(name, value, is_derived, refmode)
        self.model.clear_attr_referrers(ref)
        self.change_dynsub_refs(name)
        return ref

    def on_create_ref(self, name, value, is_derived, refmode):
        ref = ReferenceImpl.get_class(value)(self, name, value,
                            container=self._self_refs,
                            is_derived=is_derived,
                            refmode=refmode,
                            set_item=False)
        self._self_refs.add_item(name, ref)
        return ref

    def on_del_ref(self, name):
        self.self_refs[name].on_delete()
        self.self_refs.del_item(name)

    def on_rename(self, name):
        self.model.clear_obj(self)
        self.clear_all_cells(clear_input=True, recursive=True, del_items=True)
        self.parent.named_spaces.delete_item(self.name)
        self.name = name
        self.parent.named_spaces.add_item(name, self)


class DynamicSpace(BaseSpace):
    """Dynamically created space.

    Dynamic spaces of a parametric space
    are created by accessing its elements for the first time,
    through subscription ``[]`` or call ``()`` operations on the parametric
    space.

    Dynamic spaces are not editable like static spaces.
    """
    __slots__ = ()


@add_stateattrs
class DynamicSpaceImpl(BaseSpaceImpl):
    """The implementation of Dynamic Space class."""

    interface_cls = DynamicSpace

    __cls_stateattrs = [
        "_dynbase",
        "_allargs",
        "rootspace",
        "_base_refs",
        "_dynbase_refs"
    ]

    def __init__(
        self,
        parent,
        name,
        container,
        base,
        refs=None,
        arguments=None,
    ):
        self._dynbase = base
        base._dynamic_subs.append(self)
        self._init_root(parent)
        BaseSpaceImpl.__init__(
            self,
            parent,
            name,
            container,
            base.formula,
            refs,
            arguments,
            base.doc
        )
        self._init_cells()

    def _init_root(self, parent):
        self.rootspace = parent.rootspace

    def _init_cells(self):
        for base in self._dynbase.cells.values():
            DynamicCellsImpl(space=self, base=base, is_derived=True)

    def _init_self_refs(self):
        return RefDict(self)

    def _init_refs(self, arguments=None):
        self._allargs = self._init_allargs()
        self._dynbase_refs = DynBaseRefDict(self)
        self._dynbase_refs.observe(self._dynbase.self_refs)
        # _dynbase_refs are populated from self._dynbase.self_refs
        # later by _init_dynbaserefs called last
        # from ItemSpaceParent.__init__, because
        # dynamic spaces and leafs are not yet constructed here.

        # Make _dynbase_refs updated
        # _dynbase_refs.needs_update must always False
        self._dynbase_refs.fresh

        return ImplChainMap(
            self,
            RefView,
            [
                *self._allargs.maps,     # underlying parent's _allargs
                self._self_refs,
                self._local_refs,
                self._dynbase_refs,
                self.model._global_refs
            ],
        )

    def _init_dynbaserefs(self):
        # Populate _dynbase_refs creating relative reference within
        # the dynamic space tree.
        # Called from ItemSpaceParent.__init__ at last.
        for name, ref in self._dynbase.self_refs.items():
            self._dynbase_refs.set_item(name, ref)

        for space in self.named_spaces.values():
            space._init_dynbaserefs()

    def _init_allargs(self):
        if isinstance(self.parent, UserSpaceImpl):
            allargs = [self._arguments]
        elif isinstance(self, ItemSpaceImpl):
            allargs = [self._arguments, *self.parent._allargs.maps]
        else:
            allargs = [*self.parent._allargs.maps]

        return ImplChainMap(self, None, allargs)

    def on_delete(self):
        for space in list(self.named_spaces.values()):
            space.on_delete()
            self.named_spaces.del_item(space.name)
        self.del_all_itemspaces()
        self._dynbase._dynamic_subs.remove(self)
        super().on_delete()

    @property
    def arguments(self):
        return self._arguments.fresh

    @property
    def allargs(self):
        return self._arguments.fresh

    def is_dynamic(self):
        return True

    @property
    def bases(self):
        if self._dynbase:
            return [self._dynbase]
        else:
            return []

    @property
    def is_derived(self):
        return True


class ItemSpace(DynamicSpace):
    """Dynamically created space.

    Dynamic spaces of a parametric space
    are created by accessing its elements for the first time,
    through subscription ``[]`` or call ``()`` operations on the parametric
    space.

    Dynamic spaces are not editable like static spaces.
    """
    __slots__ = ()

    @property
    def _tupleid(self):
        return self.parent._tupleid + (self.argvalues,)

    @property
    def argvalues(self):
        """A tuple of space arguments."""
        return self._impl.argvalues_if


@add_stateattrs
class ItemSpaceImpl(DynamicSpaceImpl):

    interface_cls = ItemSpace

    __cls_stateattrs = ["_arguments"]

    def __init__(
        self,
        parent,
        base,
        name=None,
        refs=None,
        arguments=None,
    ):
        if name is None:
            name = parent.itemspacenamer.get_next(base.named_itemspaces)
        elif (is_valid_name(name)
              and name not in parent.namespace
              and name not in parent.named_itemspaces):
            pass
        else:
            raise ValueError("invalid name")

        DynamicSpaceImpl.__init__(
            self, parent, name, parent._named_itemspaces, base, refs, arguments
        )
        self._bind_args(self.arguments)
        self._init_child_spaces(self)
        self._init_dynbaserefs()

    def _init_root(self, parent):
        self.rootspace = self

    def _init_child_spaces(self, space):
        for name, base in space._dynbase.named_spaces.items():
            child = DynamicSpaceImpl(space, name, space._named_spaces, base)
            self._init_child_spaces(child)

    def _init_refs(self, arguments=None):
        self._arguments = RefDict(self, data=arguments)
        refs = DynamicSpaceImpl._init_refs(self)
        refs.observe(self._arguments)
        return refs

    def _bind_args(self, args):
        self.boundargs = self.parent.formula.signature.bind(**args)
        self.argvalues = tuple(self.boundargs.arguments.values())
        self.argvalues_if = tuple(get_interfaces(self.argvalues))

    def restore_state(self):

        super().restore_state()

        # From Python 3.5, signature is pickable,
        # pickling logic involving signature may be simplified.
        self._bind_args(self._arguments)

    # ----------------------------------------------------------------------
    # repr methods

    def repr_parent(self):
        return self.parent.repr_parent()

    def repr_self(self, add_params=True):

        if add_params:
            args = [repr(arg) for arg in get_interfaces(self.argvalues)]
            param = ", ".join(args)
            return "%s[%s]" % (self.parent.name, param)
        else:
            return self.name

    @property
    def evalrepr(self):
        """Evaluable repr"""
        args = [repr(arg) for arg in get_interfaces(self.argvalues)]
        param = ", ".join(args)
        return "%s(%s)" % (self.parent.evalrepr, param)
