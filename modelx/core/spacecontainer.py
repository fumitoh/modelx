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

import warnings
import pathlib
import uuid
from modelx.core.base import (
    add_stateattrs, get_impls, get_interfaces, Interface
)
from modelx.core.util import AutoNamer, get_module, get_param_func


class BaseSpaceContainer(Interface):
    """A common base class shared by Model and Space.

    This base class defines methods to serve as child space container,
    which are common between Model and Space.
    The methods defined in this class are available both in
    :py:class:`Model <modelx.core.model.Model>` and
    :py:class:`UserSpace <modelx.core.space.UserSpace>`.

    """

    __slots__ = ()

    @property
    def spaces(self):
        """A mapping of the names of child spaces to the Space objects"""
        return self._impl.spaces.interfaces

    @property
    def _all_spaces(self):
        """A mapping associating names to all(static and dynamic) spaces."""
        return self._impl.all_spaces.interfaces

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
        result["spaces"] = self.spaces._baseattrs
        return result


class EditableSpaceContainer(BaseSpaceContainer):

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
        space = self._impl.model.currentspace = self._impl.spacemgr.new_space(
            self._impl,
            name=name, bases=get_impls(bases), formula=formula, refs=refs
        )

        return space.interface

    def import_module(self, module=None, recursive=False, **params):
        """Create a child space from an module.

        Args:
            module: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to ``new_space``

        Returns:
            The new child space created from the module.
        """
        if module is None:
            if "module_" in params:
                warnings.warn(
                    "Parameter 'module_' is deprecated. Use 'module' instead.")
                module = params.pop("module_")
            else:
                raise ValueError("no module specified")

        if "bases" in params:
            params["bases"] = get_impls(params["bases"])

        space = (
            self._impl.model.currentspace
        ) = self._impl.new_space_from_module(
            module, recursive=recursive, **params
        )
        return get_interfaces(space)

    def new_space_from_module(self, module, recursive=False, **params):
        """Create a child space from an module.

        Alias to :py:meth:`import_module`.

        Args:
            module: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to ``new_space``

        Returns:
            The new child space created from the module.
        """
        if "bases" in params:
            params["bases"] = get_impls(params["bases"])

        space = (
            self._impl.model.currentspace
        ) = self._impl.new_space_from_module(
            module, recursive=recursive, **params
        )
        return get_interfaces(space)

    def new_space_from_excel(
        self,
        book,
        range_,
        sheet=None,
        name=None,
        names_row=0,
        param_cols=(0,),
        space_param_order=None,
        cells_param_order=None,
        transpose=False,
        names_col=None,
        param_rows=None,
    ):
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

        See Also:
            :meth:`new_cells_from_excel`: Create Cells from Excel file.
        """

        space = self._impl.new_space_from_excel(
            book,
            range_,
            sheet,
            name,
            names_row,
            param_cols,
            space_param_order,
            cells_param_order,
            transpose,
            names_col,
            param_rows,
        )

        return get_interfaces(space)

    def new_space_from_pandas(
            self, obj, space=None, cells=None, param=None,
            space_params=None, cells_params=None):
        """Create child spaces from Pandas DataFrame or Series.

        Create a space named ``space`` and optionally
        and cells in it from Pandas DataFrame or Series passed in ``obj``.
        If ``space`` is not given, the space is named ``SpaceN`` where
        ``N`` is automatically given by modelx.
        Parameter names are taken from ``obj`` indexes, unless ``param``
        is given to override index names.

        ``obj`` can have MultiIndex as its index.
        If the index(es) of ``obj``
        has/have name(s), the parameter name(s) of the cells is/are
        set to the name(s), but can be overwritten by ``param``
        parameter. If the index(es) of ``obj`` has/have no name(s),
        and ``param`` is not given, error is raised.

        Args:
            obj: DataFrame or Series.
            space: Space name.
            param: Sequence of strings to set parameter name(s).
                A single string can also be passed to set a single parameter
                name when ``frame`` has a single
                level index (i.e. not MultiIndex).
            space_params: Sequence of strings or integers to specify
                space parameters by name or index.
            cells_params: Sequence of strings or integers to specify
                cells parameters by name or index.

        See Also:
            :meth:`new_cells_from_pandas`: Create Cells from DataFrame or Series.
        """
        return get_interfaces(self._impl.new_space_from_pandas(
            obj, space, cells, param, space_params, cells_params
        ))

    def new_space_from_csv(
            self, filepath, space=None, cells=None, param=None,
            space_params=None, cells_params=None, *args, **kwargs):
        """Create spaces from from a comma-separated values (csv) file.

        This method internally calls Pandas `read_csv`_ function,
        and creates cells by passing
        the returned DataFrame object to :meth:`new_space_from_pandas`.
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
            space: Sequence of strings to set cells name. string is also
                accepted if `read_csv`_ returns a Series because of
                its ``squeeze`` parameter set to ``True``.
            cells: Sequence of strings to overwrite headers for cells names.
            param: Sequence of strings to set parameter name(s).
                A single string can also be passed to set a single parameter
                name when ``frame`` has a single
                level index (i.e. not MultiIndex).
            space_params: Sequence of strings or integers to specify
                space parameters by name or index.
            cells_params: Sequence of strings or integers to specify
                cells parameters by name or index.
            args: Any positional arguments to be passed to `read_csv`_.
            kwargs: Any keyword arguments to be passed to `read_csv`_.

        See Also:
            :meth:`new_cells_from_csv`: Create Cells from CSV.
        """
        return self._impl.new_space_from_csv(
            filepath, space, cells, param,
            space_params, cells_params, args, kwargs).interface


@add_stateattrs
class BaseSpaceContainerImpl:
    """Base class of Model and Space to work as container of spaces.

    **Space Deletion**
    new_space(name)
    del_space(name)

    """

    __cls_stateattrs = [
        "_named_spaces",
        "_all_spaces"
    ]   # must be defined in subclasses

    # ----------------------------------------------------------------------
    # Serialization by pickle

    def __getstate__(self):

        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.stateattrs
        }

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""

        for space in self._all_spaces.values():
            space.restore_state(system)

    # ----------------------------------------------------------------------
    # Properties

    @property
    def spaces(self):
        return self._named_spaces.fresh

    @property
    def all_spaces(self):
        return self._all_spaces.fresh

    def has_space(self, name):
        return name in self.spaces

    @property
    def namespace(self):
        raise NotImplementedError


@add_stateattrs
class EditableSpaceContainerImpl(BaseSpaceContainerImpl):

    __cls_stateattrs = ["spacenamer"]

    def __init__(self):
        self.spacenamer = AutoNamer("Space")

    def new_space_from_module(self, module, recursive=False, **params):

        params["source"] = module = get_module(module)

        if "name" not in params or params["name"] is None:
            # xxx.yyy.zzz -> zzz
            name = params["name"] = module.__name__.split(".")[-1]
        else:
            name = params["name"]

        if "doc" not in params:
            params["doc"] = module.__doc__

        space = self.spacemgr.new_space(self, **params)
        space.new_cells_from_module(module)

        if recursive and hasattr(module, "_spaces"):
            for name in module._spaces:
                submodule = module.__name__ + "." + name
                space.new_space_from_module(module=submodule, recursive=True)

        return space

    def new_space_from_excel(
        self,
        book,
        range_,
        sheet=None,
        name=None,
        names_row=None,
        param_cols=None,
        space_param_order=None,
        cells_param_order=None,
        transpose=False,
        names_col=None,
        param_rows=None,
        call_id=None
    ):

        import modelx.io.excel as xl

        if space_param_order is None:
            # if [] then dynamic space without params
            param_order = cells_param_order
        else:
            param_order = space_param_order + cells_param_order

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

        if space_param_order is None:
            cells_params = cellstable.param_names
            param_func = None
        else:
            space_params = cellstable.param_names[:len(space_param_order)]
            cells_params = cellstable.param_names[len(space_param_order):]
            param_func = get_param_func(space_params)

        source = {
            "method": "new_space_from_excel",
            "args": [str(pathlib.Path(book).absolute()), range_],
            "kwargs": {
                "sheet": sheet,
                "name": name,
                "names_row": names_row,
                "param_cols": param_cols,
                "space_param_order": space_param_order,
                "cells_param_order": cells_param_order,
                "transpose": transpose,
                "names_col": names_col,
                "param_rows": param_rows,
                "call_id": call_id or str(uuid.uuid4()),
            }
        }
        space = self.spacemgr.new_space(
            self, name=name, formula=param_func, source=source)

        for cellsdata in cellstable.items():
            space.new_cells(name=cellsdata.name,
                            formula=get_param_func(cells_params))

        # Split for-loop to avoid clearing the preceding cells
        # each time a new cells is created in the base space.

        if space_param_order is None:
            for cellsdata in cellstable.items():
                for args, value in cellsdata.items():
                    cells = space.cells[cellsdata.name]
                    cells.set_value(args, value)
        else:
            for cellsdata in cellstable.items():
                for args, value in cellsdata.items():
                    space_args = args[:len(space_params)]
                    cells_args = args[len(space_params):]
                    subspace = space.get_itemspace(space_args)
                    cells = subspace.cells[cellsdata.name]
                    cells.set_value(cells_args, value)

        return space

    def new_space_from_pandas(self, obj, space, cells, param,
                              space_params, cells_params, call_id=None):
        from modelx.io.pandas import new_space_from_pandas

        source = {
            "method": "new_space_from_pandas",
            "args": [obj],
            "kwargs": {
                "space": space,
                "cells": cells,
                "param": param,
                "space_params": space_params,
                "cells_params": cells_params,
                "call_id": call_id or str(uuid.uuid4())
            }
        }

        return new_space_from_pandas(self, obj, space, cells, param,
                                     space_params, cells_params, source)

    def new_space_from_csv(self, filepath, space, cells, param,
            space_params, cells_params, args, kwargs, call_id=None):
        from modelx.io.pandas import new_space_from_pandas
        import pandas as pd

        source = {
            "method": "new_space_from_csv",
            "args": [filepath],
            "kwargs": {
                "space": space,
                "cells": cells,
                "param": param,
                "space_params": space_params,
                "cells_params": cells_params,
                "args": args,
                "kwargs": kwargs,
                "call_id": call_id or str(uuid.uuid4())
            }
        }

        return new_space_from_pandas(
            self, pd.read_csv(filepath, *args, **kwargs),
            space, cells, param,
            space_params, cells_params, source)
