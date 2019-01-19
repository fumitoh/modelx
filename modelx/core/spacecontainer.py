# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

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

from modelx.core.base import (
    get_impls,
    get_interfaces,
    Impl,
    Interface)
from modelx.core.util import AutoNamer, is_valid_name, get_module


class SpaceContainer(Interface):
    """A common base class shared by Model and Space.

    This base class defines methods to serve as child space container,
    which are common between Model and Space.
    The methods defined in this class are available both in
    :py:class:`Model <modelx.core.model.Model>` and
    :py:class:`Space <modelx.core.space.Space>`.

    """
    __slots__ = ()

    def new_space(self, name=None, bases=None, formula=None, refs=None):
        """Create a child space.

        Args:
            name (str, optional): Name of the space. Defaults to ``SpaceN``,
                where ``N`` is a number determined automatically.
            bases (optional): A space or a sequence of spaces to be the base
                space(s) of the created space.
            formula (optional): Function to specify the parameters of
                dynamic child spaces. The signature of this function is used
                for setting parameters for dynamic child spaces.
                This function should return a mapping of keyword arguments
                to be passed to this method when the dynamic child spaces
                are created.

        Returns:
            The new child space.
        """
        space = self._impl.model.currentspace \
            = self._impl.new_space(name=name, bases=get_impls(bases),
                                   formula=formula, refs=refs)

        return space.interface

    def import_module(self, module_, recursive=False, **params):
        """Create a child space from an module.

        Args:
            module_: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to ``new_space``

        Returns:
            The new child space created from the module.
        """
        if 'bases' in params:
            params['bases'] = get_impls(params['bases'])

        space = self._impl.model.currentspace \
            = self._impl.new_space_from_module(module_,
                                               recursive=recursive,
                                               **params)
        return get_interfaces(space)

    def new_space_from_module(self, module_, recursive=False, **params):
        """Create a child space from an module.

        Alias to :py:meth:`import_module`.

        Args:
            module_: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to ``new_space``

        Returns:
            The new child space created from the module.
        """
        if 'bases' in params:
            params['bases'] = get_impls(params['bases'])

        space = self._impl.model.currentspace \
            = self._impl.new_space_from_module(module_,
                                                  recursive=recursive,
                                                  **params)
        return get_interfaces(space)

    def new_space_from_excel(self, book, range_, sheet=None,
                                name=None,
                                names_row=None, param_cols=None,
                                space_param_order=None,
                                cells_param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create a child space from an Excel range.

        To use this method, ``openpyxl`` package must be installed.

        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            name (str, optional): Name of the space. Defaults to ``SpaceN``,
                where ``N`` is a number determined automatically.
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
            space_param_order: a sequence to specify space parameters and
                their orders. The elements of the sequence denote the indexes
                of ``param_cols`` elements, and optionally the index of
                ``param_rows`` elements shifted by the length of
                ``param_cols``. The elements of this parameter and
                ``cell_param_order`` must not overlap.
            cell_param_order (optional): a sequence to reorder the parameters.
                The elements of the sequence denote the indexes of
                ``param_cols`` elements, and optionally the index of
                ``param_rows`` elements shifted by the length of
                ``param_cols``. The elements of this parameter and
                ``cell_space_order`` must not overlap.

        Returns:
            The new child space created from the Excel range.
        """

        space = self._impl.new_space_from_excel(
            book, range_, sheet, name,
            names_row, param_cols,
            space_param_order,
            cells_param_order,
            transpose,
            names_col, param_rows)

        return get_interfaces(space)

    @property
    def spaces(self):
        """A mapping of the names of child spaces to the Space objects"""
        return self._impl.spaces.interfaces

    # ----------------------------------------------------------------------
    # Current Space method

    def cur_space(self, name=None):
        """Set the current space to Space ``name`` and return it.

        If called without arguments, the current space is returned.
        Otherwise, the current space is set to the space named ``name``
        and the space is returned.
        """
        if name is None:
            return self._impl.model.currentspace.interface
        else:
            self._impl.model.currentspace = self._impl.spaces[name]
            return self.cur_space()

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = super()._baseattrs
        result['spaces'] = self.spaces._baseattrs
        return result


class SpaceContainerImpl(Impl):
    """Base class of Model and Space to work as container of spaces.

    **Space Deletion**
    new_space(name)
    del_space(name)

    """

    state_attrs = ['_spaces',   # must be defined in subclasses
                   'spacenamer'] + Impl.state_attrs

    if_class = SpaceContainer

    def __init__(self, system):

        Impl.__init__(self)

        self.system = system
        self.spacenamer = AutoNamer('Space')

    # ----------------------------------------------------------------------
    # Serialization by pickle

    def __getstate__(self):

        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""

        self.system = system
        for space in self._spaces.values():
            space.restore_state(system)

    # ----------------------------------------------------------------------
    # Properties

    def is_model(self):
        return self.parent is None

    def is_space(self):
        return not self.is_model()

    @property
    def model(self):
        return NotImplementedError

    @property
    def spaces(self):
        return self._spaces.get_updated()

    def has_space(self, name):
        return name in self.spaces

    @property
    def namespace(self):
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Create space

    def _new_space(self, name=None, formula=None,
                   refs=None, arguments=None, source=None,
                   is_derived=False):

        from modelx.core.space import SpaceImpl

        space = SpaceImpl(parent=self, name=name, formula=formula,
                          refs=refs, arguments=arguments, source=source)

        self._set_space(space)
        space.is_derived = is_derived

        return space

    def new_space(self, name=None, bases=None, formula=None,
                  *, refs=None, arguments=None, source=None, is_derived=False,
                  prefix=''):
        """Create a new child space.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            formula: Function whose parameters used to set space parameters.
            refs: a mapping of refs to be added.
            arguments: ordered dict of space parameter names to their values.
            source: A source module from which cell definitions are read.
            prefix: Prefix to the autogenerated name when name is None.
        """
        from modelx.core.space import SpaceImpl

        if name is None:
            name = self.spacenamer.get_next(self.namespace, prefix)

        if name in self.namespace:
            raise ValueError("Name '%s' already exists." % name)

        if not prefix and not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        space = self._new_space(name=name, formula=formula,
                                refs=refs, source=source,
                                is_derived=is_derived)

        if not space.in_dynamic():

            self.model.spacegraph.add_node(space)
            self.model.spacegraph.update_subspaces(space)

            # Set up direct base spaces and mro
            if bases is not None:
                if isinstance(bases, SpaceImpl):
                    bases = [bases]

                space.add_bases(bases)

        return space

    def _set_space(self, space):
        """To be overridden in subclasses."""
        raise NotImplementedError

    def new_space_from_module(self, module_, recursive=False, **params):

        params['source'] = module_ = get_module(module_)

        if 'name' not in params or params['name'] is None:
            # xxx.yyy.zzz -> zzz
            name = params['name'] = module_.__name__.split('.')[-1]
        else:
            name = params['name']

        space = self.new_space(**params)
        space.new_cells_from_module(module_)

        if recursive and hasattr(module_, '_spaces'):
            for name in module_._spaces:
                submodule = module_.__name__ + '.' + name
                space.new_space_from_module(module_=submodule, recursive=True)

        return space

    def new_space_from_excel(self, book, range_, sheet=None,
                                name=None,
                                names_row=None, param_cols=None,
                                space_param_order=None,
                                cells_param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):

        import modelx.io.excel as xl

        param_order = space_param_order + cells_param_order

        cellstable = xl.CellsTable(book, range_, sheet,
                                   names_row, param_cols,
                                   param_order,
                                   transpose,
                                   names_col, param_rows)

        space_params = cellstable.param_names[:len(space_param_order)]
        cells_params = cellstable.param_names[len(space_param_order):]

        if space_params:
            space_sig = "=None, ".join(space_params) + "=None"
        else:
            space_sig = ""

        if cells_params:
            cells_sig = "=None, ".join(cells_params) + "=None"
        else:
            cells_sig = ""

        param_func = "def _param_func(" + space_sig + "): pass"
        blank_func = "def _blank_func(" + cells_sig + "): pass"

        space = self.new_space(name=name, formula=param_func)

        for cellsdata in cellstable.items():
            space.new_cells(name=cellsdata.name,formula=blank_func)

        # Split for-loop to avoid clearing the preceding cells
        # each time a new cells is created in the base space.

        for cellsdata in cellstable.items():
            for args, value in cellsdata.items():
                space_args = args[:len(space_params)]
                cells_args = args[len(space_params):]
                subspace = space.get_dynspace(space_args)
                cells = subspace.cells[cellsdata.name]
                cells.set_value(cells_args, value)

        return space

    def del_space(self, name):
        space = self.spaces.del_item(name)
        self.model.spacegraph.remove_node(space)
        for space in self.spaces.values():
            space.inherit()


