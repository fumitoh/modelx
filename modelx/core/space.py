# Copyright (c) 2017-2025 Fumito Hamamura <fumito.ham@gmail.com>

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
import weakref
import warnings
from collections import deque
from collections.abc import Sequence, Mapping
from types import FunctionType, ModuleType, MappingProxyType
from modelx.core.binding.namespace import NamespaceServer, BaseNamespace
from modelx.core.binding.boundfunc import AlteredFunction
from modelx.core.chainmap import CustomChainMap
from modelx.core.views import CellsView, SpaceView, RefView, _to_frame_inner

from modelx.core.base import (
    get_impl_list,
    get_interface_dict,
    get_interface_list,
    get_mixin_slots,
    Interface,
    Impl,
    sort_dict
)
from modelx.core.reference import (
    ReferenceImpl,
    NameSpaceReferenceImpl,
    ReferenceProxy
)
from modelx.core.execution.trace import (
    node_get_args,
    tuplize_key,
    get_node,
    key_to_node,
    KEY
)
from modelx.core.node import (
    NodeFactory,
    ParentNodeFactoryImpl,
)
from modelx.core.parent import (
    BaseParent,
    BaseParentImpl,
    EditableParent,
    EditableParentImpl,
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


class BaseSpace(BaseParent, NodeFactory):

    __slots__ = ()

    def __getattr__(self, name):

        if self._impl.system.callstack.counter:     # TODO: check executer.is_executing instead
            return getattr(self._impl.namespace, name)
        else:
            child = self._impl.get_attr(name)
            if child is None:
                raise AttributeError(f"Attribute '{name}' is not in space {str(self)}")
            else:
                return child.interface

    def __dir__(self):
        return list(self._impl.ns_dict)

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
        """List of base spaces from which this space inherits.

        Returns a list of :class:`UserSpace` objects that serve as base spaces
        for this space. Spaces inherit cells and references from their base spaces,
        following Python's Method Resolution Order (MRO) for multiple inheritance.

        When a space has base spaces:

        * Cells defined in base spaces are copied in the derived space
        * References from base spaces are copied in the derived space
        * Derived spaces can override inherited cells and references
        * Multiple bases are resolved using C3 linearization algorithm

        Returns:
            list of :class:`UserSpace`: Base spaces in MRO order

        Example:
            .. code-block:: python

                >>> base1 = model.new_space('Base1')
                >>> base2 = model.new_space('Base2')
                >>> derived = model.new_space('Derived')
                >>> derived.add_bases(base1, base2)
                >>> derived.bases
                [<UserSpace Model1.Base1>, <UserSpace Model1.Base2>]

                >>> base0 = model.new_space('Base0')
                >>> base1.add_bases(base0)
                >>> derived.bases
                [<UserSpace Model1.Base1>, <UserSpace Model1.Base0>, <UserSpace Model1.Base2>]

        See Also:
            :meth:`~UserSpace.add_bases`: Add base spaces
            :meth:`~UserSpace.remove_bases`: Remove base spaces
            :attr:`_direct_bases`: Only directly added bases
        """
        return get_interface_list(self._impl.bases)

    @property
    def _direct_bases(self):
        """Directly inherited base classes"""
        return get_interface_list(
            self._impl.spmgr.get_direct_bases(self._impl))

    def _is_base(self, other):
        """True if the space is a base space of ``other``, False otherwise."""
        return self._impl.is_base(other._impl)

    def _is_sub(self, other):
        """True if the space is a sub space of ``other``, False otherwise."""
        return self._impl.is_sub(other._impl)

    def _is_static(self):
        """True if the space is a static space, False if dynamic."""
        return isinstance(self._impl, UserSpaceImpl)

    def _is_root(self):
        """True if ths space is a dynamic space, False otherwise."""
        return isinstance(self._impl, ItemSpaceImpl)

    def _is_dynamic(self):
        """True if the space is in a dynamic space, False otherwise."""
        return self._impl.is_dynamic()

    @property
    def cells(self):
        """Read-only mapping of cells names to :class:`~modelx.core.cells.Cells` objects.

        Returns a dictionary-like view of all cells in this space.

        Returns:
            CellsView: Dictionary-like mapping of names to Cells

        Example:
            .. code-block:: python

                >>> space.cells
                {'foo': <Cells Model1.Space1.foo(x)>,
                'bar': <Cells Model1.Space1.bar(x, y)>}

                >>> # Access individual cells
                >>> space.cells['foo']
                <Cells Model1.Space1.foo(x)>

                >>> # Iterate over cell names
                >>> list(space.cells.keys())
                ['foo', 'bar']

        See Also:
            :meth:`~UserSpace.new_cells`: Create a new cells
            :class:`~modelx.core.cells.Cells`: Cells class documentation
        """
        return CellsView(self._impl.cells)

    _cells = cells

    @property
    def spaces(self):
        """Read-only mapping of names to child :class:`UserSpace` objects.

        Returns a dictionary-like view of all named child spaces in this space.
        This does not include :class:`ItemSpace` objects,
        which are accessed via :attr:`itemspaces`.

        Returns:
            SpaceView: Dictionary-like mapping of names to UserSpace objects

        Example:
            .. code-block:: python

                >>> parent.spaces
                {'Child1': <UserSpace Model1.Parent.Child1>,
                'Child2': <UserSpace Model1.Parent.Child2>}

                >>> parent.spaces['Child1']
                <UserSpace Model1.Parent.Child1>

        See Also:
            :attr:`named_spaces`: Alias for this property
            :attr:`itemspaces`: Dynamic parameterized spaces
            :meth:`~UserSpace.new_space`: Create child spaces
        """
        return SpaceView(self._impl.named_spaces)

    @property
    def named_spaces(self):
        """Read-only mapping of names to child :class:`UserSpace` objects.

        This is an alias for the :attr:`spaces` property. Returns a dictionary-like
        view of all static child spaces in this space.

        Returns:
            SpaceView: Dictionary-like mapping of names to UserSpace objects

        See Also:
            :attr:`spaces`: Primary property name

        .. versionadded:: 0.2.0
        """
        return SpaceView(self._impl.named_spaces)

    @property
    def static_spaces(self):
        """A mapping associating names to named spaces.

        Alias to :py:meth:`spaces`

        .. deprecated:: 0.2.0 Use :attr:`named_spaces` instead.
        """
        warnings.warn("static_spaces is deprecated. Use named_spaces instead.")
        return SpaceView(self._impl.named_spaces)

    @property
    def itemspaces(self):
        """Read-only mapping of parameter arguments to :class:`ItemSpace` objects.

        Returns a dictionary-like view of all :class:`ItemSpace` instances
        created from this parameterized space. Each key is a tuple (or single value)
        of arguments, and each value is the corresponding ItemSpace.

        This property is only meaningful for spaces with parameters defined.
        For spaces without parameters, this returns an empty mapping.

        The keys are automatically "untuplized" for single-parameter spaces,
        meaning a single value is used instead of a 1-tuple.

        Returns:
            MappingProxyType: Read-only mapping of arguments to ItemSpace objects

        Example:
            .. code-block:: python

                >>> space.parameters = ('x', 'y')
                >>> space[1, 2]  # Create ItemSpace
                >>> space[3, 4]  # Create another ItemSpace
                >>> space.itemspaces
                {(1, 2): <ItemSpace Model1.Space1[1, 2]>,
                (3, 4): <ItemSpace Model1.Space1[3, 4]>}

                >>> # Single parameter - keys are not tuples
                >>> space2.parameters = ('t',)
                >>> space2[10]
                >>> space2.itemspaces
                {10: <ItemSpace Model1.Space2[10]>}

        See Also:
            :attr:`parameters`: Parameter names for this space
            :class:`ItemSpace`: Dynamic parameterized space instances
            :meth:`clear_at`: Delete specific ItemSpace
            :meth:`clear_items`: Delete all ItemSpaces
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
        return SpaceView(self._impl.named_itemspaces)

    @property
    def parameters(self):
        """Tuple of parameter names for this space, or None if not parameterized.

        Returns the parameter names defined for this space. When parameters
        are defined, the space becomes parameterized and can create
        :class:`ItemSpace` instances by calling the space with arguments.

        Returns:
            tuple of str or None: Parameter names, or None if no parameters defined

        Example:
            .. code-block:: python

                >>> space.parameters
                None

                >>> space.parameters = ('x', 'y')
                >>> space.parameters
                ('x', 'y')

                >>> # Now the space can create ItemSpaces
                >>> space[1, 2]
                <ItemSpace Model1.Space1[1, 2]>

        See Also:
            :attr:`formula`: The formula that defines parameter behavior
            :meth:`has_params`: Check if parameters are defined
            :attr:`itemspaces`: Mapping of created ItemSpace instances

        Note:
            For :class:`UserSpace`, parameters can be set directly.
            For :class:`DynamicSpace` and :class:`ItemSpace`, this reflects
            the parameters of the base space.
        """
        if self._impl.formula is not None:
            return tuple(self._impl.formula.parameters)
        else:
            return None

    @property
    def refs(self):
        """Read-only mapping of reference names to their values.

        Returns a dictionary-like view of all references accessible in this space,
        including:

        * References defined in this space (for :class:`UserSpace`)
        * References inherited from base spaces
        * Global references defined at the model level
        * System references (``_self``, ``_space``, ``_model``)

        References provide access to external data, modules, or other modelx
        objects from within cell formulas.

        Returns:
            RefView: Dictionary-like mapping of names to reference values

        Example:
            .. code-block:: python

                >>> space.refs
                {'data': <DataFrame...>,
                 'discount_rate': 0.05,
                 '_self': <Namespace...>,
                 '_model': <Model Model1>}

                >>> # Access a reference value
                >>> space.refs['discount_rate']
                0.05

                >>> # Within formulas, references are accessed by name
                >>> @mx.defcells
                ... def present_value(t):
                ...     return cashflow(t) / (1 + discount_rate) ** t

        See Also:
            :meth:`~UserSpace.set_ref`: Set a reference
            :meth:`~UserSpace.absref`: Set absolute references
            :meth:`~UserSpace.relref`: Set relative references
            :attr:`~Model.refs`: Model-level global references

        Note:
            System references are excluded from this view. Use ``_impl.refs``
            for the full internal reference mapping.
        """
        return RefView(self._impl.refs_outer)

    @property
    def _own_refs(self):
        """A mapping associating names to self refs."""
        return RefView(self._impl.own_refs)

    @property
    def formula(self):
        """The formula that defines parameter behavior for this space.

        For parameterized spaces, the formula is a Python function that defines:

        * The parameter names (from function signature)
        * Optional logic for selecting base spaces for :class:`ItemSpace` instances
        * Optional logic for setting references in ItemSpaces

        The formula can return:

        * ``None`` (default): Use this space as base with no extra refs
        * ``dict``: Specify ``'base'`` space and/or ``'refs'`` to add

        Returns:
            Formula or None: The formula object, or None if not parameterized

        Example:
            ... code-block:: python

                >>> # Simple parameterization
                >>> space.formula = lambda x, y: None
                >>> space.parameters
                ('x', 'y')

                >>> # Advanced: select base space dynamically
                >>> @mx.defcells
                ... def param_formula(product_type):
                ...     if product_type == 'A':
                ...         return {'base': BaseA}
                ...     else:
                ...         return {'base': BaseB}
                >>> space.formula = param_formula

        See Also:
            :attr:`parameters`: Parameter names from the formula
            :meth:`~UserSpace.set_formula`: Set the formula
            :meth:`has_params`: Check if formula is defined

        Note:
            For :class:`UserSpace`, this can be get, set, or deleted.
            For dynamic spaces, this reflects the base space's formula.
        """
        return self._impl.formula

    # ----------------------------------------------------------------------
    # Manipulating subspaces

    def has_params(self):
        """Check whether this space has parameters defined.

        Returns :obj:`True` if the space has a parameter formula defined,
        meaning it can create :class:`ItemSpace` instances when accessed
        with arguments. Returns :obj:`False` otherwise.

        Returns:
            bool: True if parameters are defined, False otherwise

        Example:
            ... code-block:: python

                >>> space.has_params()
                False

                >>> space.parameters = ('x', 'y')
                >>> space.has_params()
                True

                >>> # Can now create ItemSpaces
                >>> if space.has_params():
                ...     item = space[1, 2]

        See Also:
            :attr:`parameters`: Get the parameter names
            :attr:`formula`: The underlying formula object
            :attr:`itemspaces`: Mapping of created ItemSpace instances
        """
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
        """Clear all cell values and delete all ItemSpaces recursively.

        This method performs a comprehensive cleanup by:

        1. Clearing both **input** and **calculated** values from all cells
        2. Processing cells in this space and all nested child spaces recursively
        3. Deleting all :class:`ItemSpace` instances in this space and child spaces

        This is useful for:

        * Freeing memory by removing all cached calculations
        * Resetting the model to a clean state
        * Preparing for a new calculation with different input data

        Example:
            ... code-block:: python

                >>> space.clear_all()
                >>> # All cell values cleared, all ItemSpaces deleted
                >>> len(space.itemspaces)
                0

        See Also:
            :meth:`clear_cells`: Clear only cell values (keep ItemSpaces)
            :meth:`clear_items`: Delete only ItemSpaces (keep cell values)
            :meth:`Model.clear_all<modelx.core.model.Model.clear_all>`: Model-level clearing

        Warning:
            This operation cannot be undone. Input values that were set
            programmatically will be lost and must be re-entered.

        .. versionchanged:: 0.16.0
            Changed to delete child ItemSpaces recursively and to clear
            recursive child Cells. :meth:`clear_items` works the same
            as this method before change.
        """
        self._impl.clear_all_cells(
            clear_input=True, recursive=True, del_items=True
        )

    def clear_items(self):
        """Delete all :class:`ItemSpace` objects in this space.

        Deletes all :class:`ItemSpace` instances that are direct children
        of this space. 

        Example:
            ... code-block:: python

                >>> space.parameters = ('x',)
                >>> space[1], space[2], space[3]  # Create ItemSpaces
                >>> len(space.itemspaces)
                3

                >>> space.clear_items()
                >>> len(space.itemspaces)
                0

        See Also:
            :meth:`clear_all`: Clear cells and delete ItemSpaces recursively
            :meth:`clear_at`: Delete a specific ItemSpace
            :attr:`itemspaces`: View all ItemSpace instances

        .. versionadded:: 0.16.0
        """
        self._impl.del_all_itemspaces()

    def clear_cells(self, clear_input=False, recursive=True):
        """Clear values from cells with flexible control over scope.

        Provides fine-grained control over which cell values to clear:

        * **Calculated values**: Always cleared (computed by formulas)
        * **Input values**: Optionally cleared (set programmatically)
        * **Scope**: Can be limited to this space or include all nested spaces

        Unlike :meth:`clear_all`, this method does not delete :class:`ItemSpace`
        instances, only clears values within cells.

        Args:
            clear_input (bool, optional): If :obj:`True`, input values
                are also cleared. If :obj:`False`, only calculated values
                are cleared. Defaults to :obj:`False`.

            recursive (bool, optional): If :obj:`True`, cells in all
                nested child spaces are also cleared. If :obj:`False`,
                only direct child cells of this space are cleared.
                Defaults to :obj:`True`.

        Example:
            ... code-block:: python

                >>> # Clear only calculated values in all nested spaces
                >>> space.clear_cells()

                >>> # Clear both input and calculated values, only in this space
                >>> space.clear_cells(clear_input=True, recursive=False)

                >>> # Clear only calculated values in this space
                >>> space.clear_cells(clear_input=False, recursive=False)

        See Also:
            :meth:`clear_all`: Clear cells and delete ItemSpaces
            :meth:`Cells.clear<modelx.core.cells.Cells.clear>`: Clear specific cells
            :meth:`Cells.clear_at<modelx.core.cells.Cells.clear_at>`: Clear specific cell value

        .. versionadded:: 0.16.0
        """
        self._impl.clear_all_cells(
            clear_input=clear_input, recursive=recursive)

    def __iter__(self):
        raise TypeError("'Space' is not iterable")

    def __call__(self, *args, **kwargs):
        return self._impl.get_itemspace(args, kwargs).interface

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_frame(self, *args):
        """Convert cells in this space to a pandas DataFrame.

        Creates a DataFrame with:

        * **Columns**: One column per cell in the space
        * **Index**: Cell parameter values (if cells share parameters)
        * **Values**: Computed or stored cell values

        This is useful for:

        * Viewing all cell values in tabular format
        * Exporting model results to pandas for analysis
        * Comparing values across different cells

        Args:
            *args: Optional iterable of argument tuples to include.
                If not provided, all available values are included.

        Returns:
            pandas.DataFrame: DataFrame containing cell values

        Example:
            ... code-block:: python

                >>> # Space with cells foo(x) and bar(x)
                >>> space.to_frame()
                    foo  bar
                x
                1     10   20
                2     11   22
                3     12   24

        See Also:
            :attr:`frame`: Property alias for to_frame()
            :meth:`Cells.to_frame<modelx.core.cells.Cells.to_frame>`: Convert single cells

        Note:
            Cells must have shareable parameters (same names in same order)
            for this to work properly.
        """
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
        result["bases"] = [base._idstr for base in self.bases]

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

        result["bases"] = [base._idstr for base in self.bases]
        result["parameters"] = self.parameters

        if extattrs:
            self._get_attrdict_extra(result, extattrs, recursive)

        return result


class UserSpace(BaseSpace, EditableParent):
    """Editable space serving as a container for cells, child spaces, and references.

    UserSpace is the primary space type that users create and modify directly.
    It serves as a static, editable container that can hold:

    * :class:`~modelx.core.cells.Cells` objects (formulas with cached values)
    * Child UserSpace objects (nested spaces)
    * References to external objects (data, modules, etc.)

    UserSpaces can be parameterized with a formula, which enables the creation
    of :class:`ItemSpace` instances dynamically when accessed with arguments.

    UserSpaces support inheritance through base spaces, allowing cells and
    references to be inherited and overridden in derived spaces.

    Key Characteristics:

    * **Editable**: Cells, spaces, and references can be added, modified, or removed
    * **Static**: Exists independently of any parameter values
    * **Named**: Has a fixed name within its parent's namespace
    * **Inheritable**: Can serve as a base for other UserSpaces

    See Also:
        :class:`DynamicSpace`: Read-only spaces created dynamically
        :class:`ItemSpace`: Parameterized instances of spaces
        :meth:`~modelx.core.model.Model.new_space`: Create a new UserSpace in a model

    .. versionchanged:: 0.0.23
        Renamed from StaticSpace to UserSpace
    """

    __slots__ = ()
    # ----------------------------------------------------------------------
    # Manipulating cells

    def new_cells(self, name=None, formula=None, is_cached=True):
        """Create a cells in the space.

        Args:
            name: If omitted, the model is named automatically ``CellsN``,
                where ``N`` is an available number.
            func: The function to define the formula of the cells.
            is_cached(optional): Whether to cache the results. :obj:`True` by default.

        Returns:
            The new cells.

        .. seealso::

            * :attr:`~modelx.core.cells.Cells.is_cached`
        """
        # Outside formulas only
        return self._impl.spmgr.new_cells(
            self._impl, name, formula, is_cached=is_cached).interface

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
        self._impl.spmgr.rename_space(self._impl, name)

    def add_bases(self, *bases):
        """Add base spaces."""
        return self._impl.model.updater.add_bases(self._impl, get_impl_list(bases))

    def remove_bases(self, *bases):
        """Remove base spaces."""
        return self._impl.model.updater.remove_bases(
            self._impl, get_impl_list(bases))

    def import_funcs(self, module):
        """Create a cells from a module.
        .. warning:: This method is deprecated and will be removed in a future release.
        """
        warnings.warn("'import_funcs' is deprecated and will be removed in a future release.")
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module)
        return get_interface_dict(newcells)

    def new_cells_from_module(self, module):
        """Create a cells from a module.

        Alias to :py:meth:`import_funcs`.
        """
        # Outside formulas only
        newcells = self._impl.new_cells_from_module(module)
        return get_interface_dict(newcells)

    def reload(self):
        """Reload the source module and update the formulas.

        .. warning:: This method is deprecated and will be removed in a future release.

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
        warnings.warn("'reload' is deprecated and will be removed in a future release.")
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

        .. warning:: This method is deprecated.

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

        .. versionchanged:: 0.20.0 this method is deprecated.
        """
        warnings.warn("'new_cells_from_excel' is deprecated and will be"
                      "removed in future release.")
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

        .. warning:: This method is deprecated.

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

        .. versionchanged:: 0.20.0 this method is deprecated.
        """
        warnings.warn("'new_cells_from_pandas' is deprecated and will be"
                      "removed in future release.")
        return self._impl.new_cells_from_pandas(obj, cells, param)

    def new_cells_from_csv(
            self, filepath, cells=None, param=None, *args, **kwargs):
        """Create cells from a comma-separated values (csv) file.

        .. warning:: This method is deprecated.

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

        .. versionchanged:: 0.20.0 this method is deprecated.
        """
        warnings.warn("'new_cells_from_csv' is deprecated and will be"
                      "removed in future release.")
        return self._impl.new_cells_from_csv(
            filepath,
            cells=cells,
            param=param,
            args=args,
            kwargs=kwargs
        )

    def sort_cells(self):
        """Sort child cells alphabetically

        Cells in the sub space that are inherited from this space,
        exept for those that are inherited from other base spaces
        prior to this space, are sorted as well.

        Example:

            Suppose the space ``s2`` below inherits from ``s1``, and
            cells ``eee`` and ``ccc`` are defined in ``s2``::

                >>> s1.cells
                {ddd,
                 bbb,
                 aaa}

                >>> s2.cells
                {ddd,
                 bbb,
                 aaa,
                 eee,
                 ccc}

                >>> s1.sort_cells()

                >>> s1.cells
                {aaa,
                 bbb,
                 ddd}

                >>> s2.cells
                {aaa,
                 bbb,
                 ddd,
                 eee,
                 ccc}

                >>> s2.sort_cells()

                >>> s2.cells
                {aaa,
                 bbb,
                 ddd,
                 ccc,
                 eee}

        .. versionadded:: 0.17.0
        """
        self._impl.spmgr.sort_cells(self._impl)

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
            return self._impl.get_attr(item) is not None

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
            raise AttributeError("'%s' is already defined" % name)
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

    @parameters.deleter
    def parameters(self):
        self._impl.del_formula()

    def del_formula(self):
        """Delete formula"""
        self._impl.del_formula()

    @Interface.doc.setter
    def doc(self, value):
        self._impl.doc = value


class ItemSpaceParent(ParentNodeFactoryImpl, AlteredFunction):

    __slots__ = ()
    __mixin_slots = (
        "_named_itemspaces",
        "itemspacenamer",
        "dynamic_cache",
        "param_spaces",
        "formula",
    )

    def __init__(self, formula):
        self._named_itemspaces = {}
        self.itemspacenamer = AutoNamer("__Space")

        if self.is_dynamic():
            self.dynamic_cache = self.parent.dynamic_cache
        else:
            # Cache interfaces for reuse after deletion
            self.dynamic_cache = weakref.WeakValueDictionary()

        # ------------------------------------------------------------------
        # Construct altfunc after space members are crated

        self.param_spaces = {}
        self.formula = None
        if formula is not None:
            self.set_formula(formula)

    # ----------------------------------------------------------------------
    # BaseNamespaceReferrer Implementation

    def on_namespace_change(self):
        self.del_all_itemspaces()

    # ----------------------------------------------------------------------
    # Dynamic Space Operation

    @property
    def named_itemspaces(self):
        return self._named_itemspaces

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

                self.is_altfunc_updated = False
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
            self.formula = None

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
            del self.named_itemspaces[space.name]
            del self.param_spaces[key]

    def get_itemspace(self, args, kwargs=None):
        """Create a dynamic root space

        Called from interface methods
        """
        node = get_node(self, args, kwargs)
        return self.system.executor.eval_node(node)

    def on_eval_formula(self, key):
        params = self.altfunc(*key)

        if params is None:
            # Default
            base = self._dynbase if self.is_dynamic() else self
            refs = None
        elif isinstance(params, Mapping):

            # Set base
            if "base" in params:
                bs = params["base"]._impl
                if isinstance(bs, UserSpaceImpl):
                    base = bs
                elif isinstance(bs, DynamicSpaceImpl):
                    base = bs._dynbase
                else:
                    raise ValueError("base must be a Space")

            elif "bases" in params: # TODO: Remove 'bases' support

                bs = params["bases"]
                if isinstance(bs, Sequence):
                    if len(bs) == 1:
                        bs = bs[0]
                    else:
                        raise ValueError("bases must have a single element")

                if bs is None:
                    # Default
                    base = self._dynbase if self.is_dynamic() else self
                elif isinstance(bs._impl, UserSpaceImpl):
                    base = bs._impl
                elif isinstance(bs._impl, DynamicSpace):
                    base = bs._impl._dynbase
                else:
                    raise ValueError("invalid value for bases")
            else:
                base = self._dynbase if self.is_dynamic() else self

            # Set refs
            refs = params.get("refs", None)
            # TODO: check if refs is a dict with str keys

        else:
            raise ValueError("Space formula must return either dict or None")

        dkey = (self.dynamic_key if self.is_dynamic() else ()) + (key,)

        space = ItemSpaceImpl(
            parent=self,
            base=base,
            name=None,
            refs=refs,
            arguments=node_get_args(key_to_node(self, key)),
            cache=self.dynamic_cache.get(dkey, None)
        )

        self.param_spaces[key] = space
        self.dynamic_cache[dkey] = space.interface
        return space

    # ----------------------------------------------------------------------
    # NodeFactoryImpl override

    def has_node(self, key):
        return key in self.param_spaces

    def get_value_from_key(self, key):
        return self.param_spaces[key].interface


_base_space_impl_base = (
    NamespaceServer,
    ItemSpaceParent,
    BaseParentImpl,
    Impl
)


class Namespace(BaseNamespace):

    __slots__ = ()

    _impl: 'BaseSpaceImpl'

    def __getattr__(self, name):    # TODO: Refactor.
        # Check if name is a Reference in the current Space
        ref = self._impl.refs.get(name)
        if ref is not None:
            assert isinstance(ref, ReferenceImpl)
            return self._impl.system.executor.add_reference(ref).interface

        try:
            return self._impl.ns_dict[name]
        except KeyError:
            raise AttributeError(f"{name!r} not found")

    def __contains__(self, item):
        return item in self._impl.ns_dict

    def __call__(self, *args, **kwargs):
        return self._impl.get_itemspace(args, kwargs).namespace

    def __getitem__(self, key):
        return self._impl.get_itemspace(tuplize_key(self, key)).namespace

    @property
    def _name(self):
        return self._impl.name

    @property
    def _cells(self):
        return {k: v.call for k, v in self._impl.cells.items()}

    @property
    def _parent(self):
        return self._impl.parent.namespace

    parent = _parent  # for backward compatibility


class BaseSpaceImpl(*_base_space_impl_base):
    """Read-only base Space class

    * Cells container
    * Ref container
    * BaseNamespace
    * Formula container
    * Implement Derivable
    """

    __slots__ = (
        "cells",
        "sys_refs",
        "own_refs",
        "refs",
        "refs_outer",
        "is_cached"
    ) + get_mixin_slots(*_base_space_impl_base)

    _ns_class = Namespace

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
            spmgr=parent.spmgr,
            doc=doc
        )

        # ------------------------------------------------------------------
        # Construct member containers

        self.own_refs = {}
        self.cells = {}
        self.named_spaces = {}
        self.sys_refs = {}
        self._init_refs(arguments)

        self.is_cached = True

        NamespaceServer.__init__(self)
        self.sys_refs.update(
            _self=NameSpaceReferenceImpl(self, '_self', self._namespace, self.sys_refs, set_item=False),
            _space=NameSpaceReferenceImpl(self, '_space', self._namespace, self.sys_refs, set_item=False),
            _model=NameSpaceReferenceImpl(self, '_model', self.model.namespace, self.sys_refs, set_item=False)
        )

        ItemSpaceParent.__init__(self, formula)
        AlteredFunction.__init__(self, self)

        container[name] = self

        # ------------------------------------------------------------------
        # Add initial refs members

        if refs is not None:
            for key, value in refs.items():
                self.own_refs[key] = ReferenceImpl(self, key, value, container=self.own_refs,
                              refmode="auto", set_item=False)


    def on_notify(self, subject):
        if subject is self.ns_server:
            assert subject is self
            AlteredFunction.on_notify(self, subject)
        else:
            NamespaceServer.on_notify(self, subject)

    def on_update_ns(self):
        for k, v in self.named_spaces.items():
            self._ns_dict[k] = v._namespace
        for k, v in self.refs.items():
            if isinstance(v, BaseNamespace):
                self._ns_dict[k] = v
            elif isinstance(v, NamespaceServer):
                self._ns_dict[k] = v._namespace
            else:
                self._ns_dict[k] = v.interface
        for k, v in self.cells.items():
            self._ns_dict[k] = v.call

    # ----------------------------------------------------------------------
    # ParentTraceObject implementation

    def get_nodes_for(self, key):
        root = self.param_spaces[key]
        queue = deque()
        queue.append(root)
        while queue:
            obj = queue.popleft()
            for c in obj.cells.values():
                for key in c.data:
                    yield c, key
            for k, _ in obj.param_spaces.items():
                yield obj, k
            for child in obj.named_spaces.values():
                queue.append(child)

    def __getstate__(self):
        d = {attr: getattr(self, attr)
                for c in type(self).mro()[:-1]
                for attr in c.__slots__ if attr != "dynamic_cache"}   # exclude object type
        return d

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)
        self.dynamic_cache = weakref.WeakValueDictionary()

    def _init_refs(self, arguments=None):
        raise NotImplementedError

    def get_attr(self, name):
        child = self.cells.get(name)
        if child is None:
            child = self.named_spaces.get(name)
        if child is None:
            child = self.refs.get(name)
        return child

    # --- Inheritance properties ---

    @property
    def bases(self):
        """Return an iterator over direct base spaces"""
        spaces = self.spmgr.get_deriv_bases(self)
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
            space = self.named_spaces.get(child)
            if space is not None:
                return space.get_impl_from_namelist(parts)
            space = self._named_itemspaces.get(child)
            if space is not None:
                return space.get_impl_from_namelist(parts)

            return None
        else:
            result = self.get_attr(child)
            if result is not None:
                return result
            else:
                return self.named_itemspaces.get(child)     # may be None

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
    # Pandas, Module, Excel I/O

    def to_frame(self, args):
        return _to_frame_inner(self.cells, args)

    def on_delete(self):
        for cells in self.cells.values():
            cells.clear_all_values(clear_input=True)
            cells.on_delete()
        super().on_delete()


class DynamicBase(BaseSpaceImpl):

    __slots__ = ("_dynamic_subs",) + get_mixin_slots(BaseSpaceImpl)

    def __init__(self):
        self._dynamic_subs = []

    def on_notify(self, subject):
        ItemSpaceParent.on_namespace_change(self)
        # Use dict instead of list to avoid duplicates
        for r in {s.rootspace: True for s in self._dynamic_subs}:
            r.parent.del_all_itemspaces()
        BaseSpaceImpl.on_notify(self, subject)

    def change_dynsub_refs(self, name):

        for dynsub in self._dynamic_subs:
            baseref = self.own_refs[name]
            dynsub._dynbase_refs.set_item(name, baseref)

    def clear_subs_rootitems(self):
        for dynsub in self._dynamic_subs.copy():
            root = dynsub.rootspace
            root.parent.clear_itemspace_at(root.argvalues_if)


_user_space_impl_base = (
    DynamicBase,
    EditableParentImpl
)

class UserSpaceImpl(*_user_space_impl_base):
    """Editable base Space class

    * cell creation
    * ref assignment
    """

    interface_cls = UserSpace

    __slots__ = (
        "cellsnamer",
        "source"
    ) + get_mixin_slots(*_user_space_impl_base)

    def __init__(
        self,
        parent,
        name,
        container,
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
        EditableParentImpl.__init__(self)

        self.cellsnamer = AutoNamer("Cells")

        if isinstance(source, ModuleType):
            self.source = source.__name__
        else:
            self.source = source

    def _init_refs(self, arguments=None):
        self.refs = CustomChainMap(self.own_refs, self.sys_refs, self.model._global_refs)
        self.refs_outer = CustomChainMap(self.own_refs, self.model._global_refs)

    @Impl.doc.setter
    def doc(self, value):
        self._doc = value

    # ----------------------------------------------------------------------
    # Cells creation

    def new_cells_from_module(self, module, override=True):
        # Outside formulas only

        module = get_module(module)
        newcells = {}

        for name in dir(module):
            func = getattr(module, name)
            if isinstance(func, FunctionType):
                # Choose only the functions defined in the module.
                if func.__module__ == module.__name__:
                    if name in self.cells and override:
                        self.spmgr.set_cells_formula(
                            self.cells[name], func)
                        newcells[name] = self.cells[name]
                    else:
                        newcells[name] = self.spmgr.new_cells(
                            self, name, func)

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
        param_rows=None
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

        for cellsdata in cellstable.items():
            cells = self.spmgr.new_cells(
                self,
                name=cellsdata.name, formula=blank_func)
            for args, value in cellsdata.items():
                cells.set_value(args, value)

    def new_cells_from_pandas(self, obj, cells, param):
        from modelx.io.pandas import new_cells_from_pandas
        return new_cells_from_pandas(self, obj, cells, param)

    def new_cells_from_csv(
            self, filepath, cells, param, args, kwargs):
        import pandas as pd
        from modelx.io.pandas import new_cells_from_pandas

        return new_cells_from_pandas(
            self, pd.read_csv(filepath, *args, **kwargs), cells, param)

    # ----------------------------------------------------------------------
    # Attribute access

    def set_attr(self, name, value, refmode=False):
        """Implementation of attribute setting

        ``space.name = value`` by user script
        Called from ``Space.__setattr__``
        """
        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'" % name)

        if self.get_attr(name) is not None:
            if name in self.refs:
                if name in self.own_refs:
                    self.model.refmgr.change_ref(self, name, value, refmode)
                elif self.refs[name].parent is self.model:
                    self.model.refmgr.new_ref(self, name, value, refmode)
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
            self.model.refmgr.new_ref(self, name, value, refmode)

    def del_attr(self, name):
        """Implementation of attribute deletion

        ``del space.name`` by user script
        Called from ``UserSpace.__delattr__``
        """
        if self.get_attr(name) is not None:
            if name in self.cells:
                self.spmgr.del_cells(self, name)
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

        if name in self.own_refs:
            self.model.refmgr.del_ref(self, name)
        elif name in self.is_derived():
            raise KeyError("Derived ref '%s' cannot be deleted" % name)
        elif name in self.arguments:
            raise ValueError("Argument cannot be deleted")
        elif name in self.sys_refs:
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
            self.spmgr.new_cells(
                self, name=name, formula=funcs[name])

        for name in cells_to_update:
            self.cells[name].reload(module=modsrc)

    def on_inherit(self, updater, bases, attr):

        attrs = {
            "cells": self.on_del_cells,
            "own_refs": self.on_del_ref
        }

        selfdict = getattr(self, attr)
        basedict = CustomChainMap(*[getattr(b, attr) for b in bases])
        selfkeys = list(selfdict)

        for name in basedict: # ChainMap iterates from the last map

            bs = [bm[name] for bm in basedict.maps
                  if name in bm and bm[name].is_defined()]

            if name not in selfdict:

                if attr == "cells":
                    selfdict[name] = UserCellsImpl(
                        space=self, name=name, formula=None,
                        is_derived=True)

                elif attr == "own_refs":
                    selfdict[name] = ReferenceImpl(
                        self, name, None,
                        container=self.own_refs,
                        is_derived=True,
                        refmode=bs[0].refmode,
                        set_item=False
                    )
                else:
                    raise RuntimeError("must not happen")

            else:
                # Remove & add back for reorder
                selfdict[name] = selfdict.pop(name)
                selfkeys.remove(name)

            if selfdict[name].is_derived():
                selfdict[name].on_inherit(updater, bs)

        for name in selfkeys:
            if selfdict[name].is_derived():
                attrs[attr](name)
            else:   # defined
                selfdict[name] = selfdict.pop(name)

    def on_del_cells(self, name):
        cells = self.cells[name]
        self.model.clear_obj(cells)
        del self.cells[name]
        self.on_notify(self.cells)
        cells.on_delete()

    def on_sort_cells(self, space):

        for c in space.cells.values():
            self.model.clear_obj(c)

        if self.bases:

            # Select names in space but not in space's bases

            bases = [self] + list(self.bases)    # bases lists space's bases
            while True:
                if bases.pop(0) is space:
                    break

            keys = list(space.cells)
            d = {}
            for b in bases:
                d.update(b.cells)

            for k in d:
                try:
                    keys.remove(k)
                except ValueError:
                    pass

            keys = sorted(keys)

        else:
            assert self is space
            keys = None

        sort_dict(self.cells, keys)

    def on_change_ref(self, name, value, is_derived, refmode,
                      is_relative):
        ref = self.own_refs[name]
        self.on_del_ref(name)
        self.on_create_ref(name, value, is_derived, refmode)
        self.model.clear_attr_referrers(ref)
        self.change_dynsub_refs(name)
        return ref

    def on_create_ref(self, name, value, is_derived, refmode):
        ref = ReferenceImpl(self, name, value,
                            container=self.own_refs,
                            is_derived=is_derived,
                            refmode=refmode,
                            set_item=False)
        self.own_refs[name] = ref
        self.on_notify(self.own_refs)
        return ref

    def on_del_ref(self, name):
        self.model.clear_attr_referrers(self.own_refs[name])
        self.own_refs[name].on_delete()
        del self.own_refs[name]
        self.on_notify(self.own_refs)

    def on_rename(self, name):
        self.model.clear_obj(self)
        self.clear_all_cells(clear_input=True, recursive=True, del_items=True)
        old_name = self.name
        self.name = name
        self.parent.named_spaces[name] = self.parent.named_spaces.pop(old_name)
        if isinstance(self.parent, NamespaceServer):    # TODO: Refactor
            self.parent.on_notify(self.parent.named_spaces)


class DynamicSpace(BaseSpace):
    """Read-only space created dynamically as a child of another dynamic space.

    DynamicSpace objects are automatically created when accessing child spaces
    within a parameterized space hierarchy. They mirror the structure of their
    base UserSpace but exist within the context of specific parameter values.

    Unlike :class:`ItemSpace` which represents the root of a parameterized space
    instance, DynamicSpace represents nested child spaces within that instance.

    Creation:
        DynamicSpaces are created automatically when:

        * An :class:`ItemSpace` is created from a parameterized UserSpace
        * The base UserSpace contains child spaces
        * These child spaces are accessed within the ItemSpace context

    Key Characteristics:

    * **Read-only**: Cannot add, modify, or remove cells, spaces, or references
    * **Dynamic**: Created on-demand when parent ItemSpace is instantiated
    * **Derived**: Mirrors the structure and formulas of a base UserSpace
    * **Contextual**: Exists within a specific parameter context from parent ItemSpace

    Example:
        >>> space = model.new_space()
        >>> space.parameters = ('x',)
        >>> child = space.new_space('Child')  # UserSpace
        >>> item = space[1]  # ItemSpace created
        >>> item.Child  # DynamicSpace (not ItemSpace)
        <DynamicSpace Child in Model1.space[1]>

    See Also:
        :class:`UserSpace`: The base space that DynamicSpace derives from
        :class:`ItemSpace`: Root dynamic space with parameters
        :class:`BaseSpace`: Base class for all space types
    """
    __slots__ = ()


class DynamicSpaceImpl(BaseSpaceImpl):
    """The implementation of Dynamic Space class."""

    interface_cls = DynamicSpace

    __slots__ = (
        "_dynbase",
        "_allargs",
        "rootspace",
        "_dynbase_refs"
    ) + get_mixin_slots(BaseSpaceImpl)

    def __init__(
        self,
        parent,
        name,
        container,
        base,
        refs=None,
        arguments=None,
        cache=None
    ):
        self._dynbase = base
        base._dynamic_subs.append(self)
        self._init_root(parent)
        if cache:
            cache._impl = self
            self.interface = cache # must be set before Impl.__init__
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

    def _init_refs(self, arguments=None):
        self._allargs = self._init_allargs()
        self._dynbase_refs = {}
        self.refs = CustomChainMap(
                *self._allargs.maps,     # underlying parent's _allargs
                self.own_refs,
                self.sys_refs,
                self._dynbase_refs,
                self.model._global_refs)

        self.refs_outer = CustomChainMap(
                *self._allargs.maps,     # underlying parent's _allargs
                self.own_refs,
                self._dynbase_refs,
                self.model._global_refs)

    def _init_dynbaserefs(self):
        # Populate _dynbase_refs creating relative reference within
        # the dynamic space tree.
        # Called from ItemSpaceParent.__init__ at last.
        for name, ref in self._dynbase.own_refs.items():
            self._dynbase_refs[name] = self.wrap_impl(ref)

        for space in self.named_spaces.values():
            space._init_dynbaserefs()

    def wrap_impl(self, value):

        assert isinstance(value, ReferenceImpl)

        if isinstance(value.interface, Interface) and value.interface._is_valid():

            if value.is_relative:   # value.is_relative is set to True
                                    # When value.is_defined and
                                    # value.refmode == "relative"

                impl = value.interface._impl.idstr
                root = self.rootspace._dynbase.idstr
                rootlen = len(root)

                if root == impl:
                    return self.rootspace
                elif root == impl[:rootlen]:
                    return self.rootspace.get_impl_from_name(
                        impl[rootlen+1:]) # +1 to remove preceding dot
                else:
                    if value.refmode == "auto":
                        if value.is_defined():
                            return value
                        else:
                            return value.direct_bases[0]

                    elif value.refmode == "relative":
                        raise ValueError(
                            "'%s' referred as '%s' is out of '%s'" %
                            (impl, value.idstr, root)
                        )
                    else:
                        raise RuntimeError("must not happen")

            else:   # absolute
                return value
        else:
            return value


    def _init_allargs(self):
        if isinstance(self.parent, UserSpaceImpl):
            allargs = [self._arguments]
        elif isinstance(self, ItemSpaceImpl):
            allargs = [self._arguments, *self.parent._allargs.maps]
        else:
            allargs = [*self.parent._allargs.maps]

        return CustomChainMap(*allargs)

    def on_delete(self):
        for space in list(self.named_spaces.values()):
            space.on_delete()
            del self.named_spaces[space.name]
        self.del_all_itemspaces()
        self._dynbase._dynamic_subs.remove(self)
        super().on_delete()

    @property
    def arguments(self):
        return self._arguments

    def is_dynamic(self):
        return True

    @property
    def dynamic_key(self):
        # Non-ItemSpace
        return self.parent.dynamic_key + (self.name,)

    @property
    def bases(self):
        if self._dynbase:
            return [self._dynbase]
        else:
            return []


class ItemSpace(DynamicSpace):
    """Root dynamic space created by calling a parameterized UserSpace with arguments.

    ItemSpace is a subclass of :class:`DynamicSpace` that represents
    the top-level space instance for a specific set of parameter values.
    When a UserSpace has a parameter formula defined, accessing it with
    arguments (via ``[]`` subscription or ``()`` call) creates an ItemSpace
    that serves as the root of a dynamic space hierarchy.

    Each ItemSpace:

    * Corresponds to a unique combination of parameter values
    * Contains cells with formulas inherited from the base UserSpace
    * Creates child DynamicSpaces for any nested spaces in the base
    * Is cached and reused when accessed with the same arguments

    Creation:
        ItemSpaces are created automatically when a parameterized UserSpace
        is accessed with arguments::

            >>> space = model.new_space()
            >>> space.parameters = ('x', 'y')
            >>> space[1, 2]  # Creates ItemSpace with x=1, y=2
            <ItemSpace space[1, 2] in Model1>

    Key Characteristics:

    * **Root dynamic space**: Top of the dynamic space hierarchy for given parameters
    * **Parameterized**: Has specific argument values (accessible via :attr:`argvalues`)
    * **Read-only**: Cannot be edited after creation
    * **Cached**: Same arguments return the same ItemSpace instance
    * **Deletable**: Can be removed via :meth:`~UserSpace.clear_at` or ``del space[args]``

    The key distinction from :class:`DynamicSpace`:

    * ItemSpace = root of dynamic hierarchy (has parameters)
    * DynamicSpace = nested child within that hierarchy (no parameters)


    See Also:
        :class:`DynamicSpace`: Non-root dynamic spaces in the hierarchy
        :class:`UserSpace`: The base space that ItemSpace derives from
        :attr:`UserSpace.parameters`: Define parameters for a space

    .. versionadded:: 0.0.21
        Split from DynamicSpace class
    """
    __slots__ = ()

    @property
    def _idtuple(self):
        return self.parent._idtuple + (self.argvalues,)

    @property
    def argvalues(self):
        """A tuple containing the argument values used to create this ItemSpace."""
        return self._impl.argvalues_if


class ItemSpaceImpl(DynamicSpaceImpl):

    interface_cls = ItemSpace

    __slots__ = (
        "_arguments",
        "argvalues",
        "argvalues_if"
    ) + get_mixin_slots(DynamicSpaceImpl)

    def __init__(
        self,
        parent,
        base,
        name,
        refs,
        arguments,
        cache
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
            self, parent, name, parent._named_itemspaces, base, refs, arguments, cache
        )
        self._bind_args(self.arguments)
        self._init_child_spaces(self)
        self._init_dynbaserefs()

    def _init_root(self, parent):
        self.rootspace = self

    def _init_child_spaces(self, space):
        for name, base in space._dynbase.named_spaces.items():
            dkey = space.dynamic_key + (name,)
            cache = self.dynamic_cache.get(dkey, None)
            child = DynamicSpaceImpl(space, name, space.named_spaces, base, cache=cache)
            self._init_child_spaces(child)
            self.parent.dynamic_cache[dkey] = child.interface

    def _init_refs(self, arguments=None):
        args = {}
        for k, v in arguments.items():
            args[k] = ReferenceImpl(self, k, v, container=args, set_item=False)
        self._arguments = args
        DynamicSpaceImpl._init_refs(self)


    def _bind_args(self, args):
        boundargs = self.parent.formula.signature.bind(**args)
        self.argvalues = tuple(boundargs.arguments.values())
        self.argvalues_if = tuple(get_interface_list(self.argvalues))

    # ----------------------------------------------------------------------
    # repr methods

    def repr_parent(self):
        return self.parent.repr_parent()

    def repr_self(self, add_params=True):

        if add_params:
            args = [repr(arg) for arg in get_interface_list(self.argvalues)]
            param = ", ".join(args)
            return "%s[%s]" % (self.parent.name, param)
        else:
            return self.name

    @property
    def evalrepr(self):
        """TraceObject repr"""
        args = [repr(arg) for arg in get_interface_list(self.argvalues)]
        param = ", ".join(args)
        return "%s(%s)" % (self.parent.evalrepr, param)

    @property
    def dynamic_key(self):
        if self.parent.is_dynamic():
            return self.parent.dynamic_key + (self.argvalues_if,)
        else:
            return (self.argvalues_if,)


