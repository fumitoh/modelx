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
            if self._impl.model.currentspace:
                return self._impl.model.currentspace.interface
            else:
                return None
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


    def _get_attrdict(self, extattrs=None, recursive=True):
        """Get extra attributes"""

        result = super()._get_attrdict(extattrs, recursive)
        if recursive:
            result["spaces"] = self.spaces._get_attrdict(extattrs, recursive)
        else:
            result["spaces"] = tuple(self.spaces.keys())
        return result


class EditableSpaceContainer(BaseSpaceContainer):

    __slots__ = ()

    def __setattr__(self, name, value):
        if hasattr(type(self), name):
            attr = getattr(type(self), name)
            if isinstance(attr, property):
                if hasattr(attr, 'fset'):
                    attr.fset(self, value)
                else:
                    raise AttributeError("%s is read-only" % name)
            else:
                raise AttributeError("%s is not a property" % name)
        elif name in self.properties:
            object.__setattr__(self, name, value)
        else:
            self._impl.set_attr(name, value, refmode="auto")

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
        space = self._impl.model.currentspace = self._impl.model.updater.new_space(
            self._impl,
            name=name, bases=get_impls(bases), formula=formula, refs=refs
        )
        self._impl.system.currentmodel = space.model
        return space.interface

    def import_module(self, module=None, recursive=False, **params):
        """Create a child space from an module.

        Args:
            module: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to :meth:`new_space`

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
        self._impl.system.currentmodel = space.model
        return get_interfaces(space)

    def new_space_from_module(self, module, recursive=False, **params):
        """Create a child space from an module.

        Alias to :py:meth:`import_module`.

        Args:
            module: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to :meth:`new_space`

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
        self._impl.system.currentmodel = space.model
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
        self._impl.system.currentmodel = space.model
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
        space = self._impl.new_space_from_pandas(
            obj, space, cells, param, space_params, cells_params
        )
        self._impl.system.currentmodel = space.model
        return space.interface

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
        space = self._impl.new_space_from_csv(
            filepath, space, cells, param,
            space_params, cells_params, args, kwargs
        )
        self._impl.system.currentmodel = space.model
        return space.interface

    def new_excel_range(self, name,
            path, range_, sheet=None, keyids=None, loadpath=None):
        """Creates a Reference to an Excel range

        Reads an Excel range from an Excel file,
        creates an
        :class:`~modelx.io.excelio.ExcelRange` object
        and assigns it to a Reference
        named ``name``.

        The object returned by this method is an
        :class:`~modelx.io.excelio.ExcelRange` object.
        It is a mapping object, and has the same methods and operations
        as other mapping objects, such as :obj:`dict`.
        The user can read and write values to an Excel file through the
        object by the same operators and methods as :obj:`dict`.

        :class:`~modelx.io.excelio.ExcelRange` objects are
        associated to the Model of the bound References.

        Bindings between :class:`~modelx.io.excelio.ExcelRange` objects
        and References are kept track of in the belonging Model,
        an :class:`~modelx.io.excelio.ExcelRange` object is
        deleted when all the References bound to the object is deleted.

        :class:`~modelx.io.excelio.ExcelRange`
        objects cannot have Excel ranges overlapping with others.

        An :class:`~modelx.io.excelio.ExcelRange` object is
        deleted when all the References bound to the object is deleted.

        The Excel range is read from a workbook specified by
        ``loadpath`` and saved to ``path``.
        If no ``loadpath`` is given, ``path`` is used also
        for reading.

        The ``path`` is a path-like object, and can be either a
        relative or absolute path. If a relative path is given, the output
        file becomes an **internal data file**, and when this Model
        is saved by :func:`~modelx.write_model` or :func:`~modelx.zip_model`,
        the file is saved in the model folder or the zipped file
        output by the functions,
        and ``path`` is interpreted as a path relative to the model path.
        If an absolute path is given, the output file becomes
        an **external data file** and the file is saved outside the
        model folder or zip file.

        The ``range_`` parameter takes a string
        that indicates an Excel range, such as "A1:D5", or
        the name of a named range. When the name of a named range is specified,
        the ``sheet`` argument is ignored.

        The ``keyids`` paramter is for specifying rows and columns
        in the range to be interpreted as key rows and columns.
        The ``keyids`` parameter takes a list of strings, each element of which
        is a string starting with "r" or "c" followed by a 0-indexed integer.
        For example, ``["r0", "c1"]`` indicates that the 1st row and the
        2nd column in ``range_`` are interpreted as keys in that order.
        If ``keyids`` is not given, all rows and columns are interpreted
        as value rows and columns, and the values are
        assigned to 0-indexed integer keys.


        Example:

            Suppose below is the range "A1:D4" on Sheet1 in Book1.xlsx.

            +-----+-----+-----+
            |     | AA  | BB  |
            +-----+-----+-----+
            |  0  | 11  | 21  |
            +-----+-----+-----+
            |  1  | 12  | 22  |
            +-----+-----+-----+
            |  2  | 13  | 23  |
            +-----+-----+-----+

            The next code creates a Reference
            named ``x`` in a Space ``space``::

                >>> xlr = space.new_excel_range("x", "files/Book1.xlsx", "A1:D4",
                        sheet="Sheet1", keys=["r0", "c0"], loadpath="Book1.xlsx")

            The values in the range are accessible
            through the ``[]`` operator. "r0" in the ``keyids`` parameter
            denotes the first row, and "c0" denotes the first column.
            So keys to be passed in the ``[]`` operator are
            taken from the row and the column, for example::

                >>> xlr["BB", 1]
                22

                >>> space.x["BB", 1]
                22

                >>> dict(xlr)
                {('AA', 1): 11,
                 ('AA', 2): 12,
                 ('AA', 3): 13,
                 ('BB', 1): 21,
                 ('BB', 2): 22,
                 ('BB', 3): 23}

            Multiple :class:`~modelx.io.excelio.ExcelRange`
            objects cannot be created on overlapping ranges.
            When ``keyids`` is omitted, 0-indexed integer keys are assigned::

                >>> xlr2 = space.new_excel_range("y", "files/Book1.xlsx", "B2:D4",
                        sheet="Sheet1", loadpath="Book1.xlsx")
                ValueError: cannot add client

                >>> del space.x

                >>> xlr2 = space.new_excel_range("y", "files/Book1.xlsx", "B2:D4",
                        sheet="Sheet1", loadpath="Book1.xlsx")

                >>> dict(xlr2)
                {(0, 0): 11, (0, 1): 21, (1, 0): 12, (1, 1): 22, (2, 0): 13, (2, 1): 23}

        Note:
            This method reads and writes values from
            Excel files, not formulas.
            From formulas cells in the ``loadpath`` file, last-saved
            values stored in the file are read in.

        Args:
            name: A name of a Reference or a Cells object with no arguments.
            path: The path of the output Excel file.
                Can be a :obj:`str` or path-like object.
            range_(:obj:`str`): A range expression such as "A1:D5", or
                a named range name string.
            sheet: The sheet name of the range. Ignored when a named range is
                given to ``range_``.
            keyids(optional): A list of indicating rows and columns to be
                interpreted as keys. For example, ``['r0', 'c0']`` indicates
                the fist row and the first column are to interpreted as keys
                in that order.
            loadpath(optional): The path of the input Excel file.

        See Also:

            :class:`~modelx.io.excelio.ExcelRange`
            :attr:`~modelx.core.model.Model.dataclients`

        .. versionadded:: 0.9.0

        """
        return self._impl.new_excel_range(name,
            path, range_, sheet=sheet, keyids=keyids, loadpath=loadpath
        )

    def new_pandas(self, name, path, data, filetype, expose_data=True):
        """Assigns a pandas object to a Reference associating a
        new :class:`~modelx.io.pandasio.PandasData` object

        pandas `DataFrame`_ and `Series`_ objects can be assigned to
        References by the normal assignment operation,
        such as ``space.x = df``, but the pandas `DataFrame`_/`Series`_
        assigned this way are saved in a binary file together with
        other Reference objects. This method allows a `DataFrame`_/`Series`_
        object passed as ``data`` to be saved
        in a separate file.

        This method creates a :class:`~modelx.io.pandasio.PandasData` object
        that wraps a `DataFrame`_ or `Series`_ passed as ``data``,
        and assigns ``data`` or the :class:`~modelx.io.pandasio.PandasData`
        object to a Reference named ``name`` in this Space/Model.

        When the model is saved, the `DataFrame`_ or `Series`_ is
        written to a file whose path is given by the ``path`` parameter,
        and whose format is specified by the ``filetype`` parameter.
        If ``path`` is relative, it is interpreted relative to the model
        folder. The ``filetype`` can take either "excel" or "csv".

        If "excel" is given, the pandas object is written to an Excel file.
        The file name in ``path`` must have either ".xlsx", ".xlsm" or ".xls"
        extention.
        This method internally uses `pandas.read_excel`_ function and
        `to_excel`_ method for reading from and writing to Excel files,
        so appropriate Excel engines for reading and writing Excel files
        must be installed, depending on the types of Excel files.
        See `pandas' document`_ for the required packeges for Excel engines.

        By default, ``data`` is assigned to ``name``, and the associated
        :class:`~modelx.io.pandasio.PandasData` object is assigned to
        ``data._mx_dataclient``. If ``False`` is passed  to ``expose_data``,
        the :class:`~modelx.io.pandasio.PandasData` object is assigned
        to ``name``. To get ``data``, call the
        :class:`~modelx.io.pandasio.PandasData` or get its ``value`` attribute.

        .. _pandas.read_excel: https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html

        .. _to_excel: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_excel.html

        .. _pandas' document: https://pandas.pydata.org/docs/user_guide/io.html#excel-files

        .. _DataFrame: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html

        .. _Series: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html

        Example:

            The script below creates a sample DataFrame ``df``::

                >>> index = pd.date_range("20210101", periods=3)

                >>> df = pd.DataFrame(np.random.randn(3, 3), index=index, columns=list("XYZ"))

                >>> df
                                   X         Y         Z
                2021-01-01  0.184497  0.140037 -1.599499
                2021-01-02 -1.029170  0.588080  0.081129
                2021-01-03  0.028450 -0.490102  0.025208

            The code below assigns the DataFrame created above
            to a Reference named ``x`` in ``space``, and at the same time
            creates a :class:`~modelx.io.pandasio.PandasData` object and
            assigns it to the ``_mx_dataclient`` attribute of the DataFrame::

                >>> space.new_pandas("x", "Space1/df.xlsx", data=df, filetype="excel")

                >>> space.x
                                   X         Y         Z
                2021-01-01  0.184497  0.140037 -1.599499
                2021-01-02 -1.029170  0.588080  0.081129
                2021-01-03  0.028450 -0.490102  0.025208

                >>> space.x._mx_dataclient
                <modelx.io.pandasio.PandasData at 0x15ebc562356>


            When the model is saved, the DataFrame is written to an Excel file
            named `df.xlsx` placed under the `Space1` folder in `model`.

                >>> model.write("model")    # `model` is the parent of `space`

            When the model is read back by :func:`modelx.read_model` function,
            the DataFrame is read from the file::

                >>> model2 = mx.read_model("model", name="Model2")

                >>> model2.Space1.x
                                   X         Y         Z
                2021-01-01  0.184497  0.140037 -1.599499
                2021-01-02 -1.029170  0.588080  0.081129
                2021-01-03  0.028450 -0.490102  0.025208

            If ``False`` is passed to ``expose_data``,
            the :class:`~modelx.io.pandasio.PandasData` object instead of
            ``data`` itself is assigned to ``x``
            To get the DataFrame,
            call the :class:`~modelx.io.pandasio.PandasData` object
            or access its :attr:`~modelx.io.pandasio.PandasData.value` property::

                >>> space.x
                <modelx.io.pandasio.PandasData at 0x15efa565548>

                >>> space.x()     # or space.value
                                   X         Y         Z
                2021-01-01  0.184497  0.140037 -1.599499
                2021-01-02 -1.029170  0.588080  0.081129
                2021-01-03  0.028450 -0.490102  0.025208

        Args:
            name(:obj:`str`): Name of the Reference
            path: A path to a file to save the Pandas object. If a relative
                path is given, it is relative to the model folder.
            data: pandas DataFrame or Series
            filetype: String to indicate file format. ("excel" or "csv")
            expose_data(:obj:`bool`, optional): If ``True``, assigns
                ``data`` to ``name``, otherwise assigns the
                :class:`~modelx.io.pandasio.PandasData` object
                associted with ``data`` to ``name``. ``True`` by default.

        .. versionchanged:: 0.13.0
            Add the ``expose_data`` parameter. By default,
            ``data`` is assigned instead of
            its :class:`~modelx.io.pandasio.PandasData` object

        .. versionadded:: 0.12.0

        See Also:
            :class:`~modelx.io.pandasio.PandasData`

        """
        return self._impl.new_pandas(
            name, path, data, filetype, expose_data)

    def new_module(self, name, path, module):
        """Assigns a user module to a Reference associating a
        new :class:`~modelx.io.moduleio.ModuleData` object

        This module assigns a module ``module`` to a Reference ``name``.
        ``module`` can either be a path to the module file or
        a module object. In case a module is passed,
        the source code of the module needs to be retrievable.
        The source code of the module is then saved as the file
        specified by ``path`` when the model is saved.
        A new :class:`~modelx.io.moduleio.ModuleData` object is created
        and inserted to the module as ``_mx_dataclient`` attribute.
        The module associted by this method is not registered in
        ``sys.modules``, unless it has been registered beforehand.
        When the containing model is read back, the module's name
        is set to ``<unnamed module>``.

        This method should not be used for
        modules in the Python standard library or third party
        packages registered in ``sys.modules``,
        such as `math`_, `numpy`_ and `pandas`_. For such module,
        the normal assignment operation should be used, e.g.
        ``space.np = np``.

        .. _math: https://docs.python.org/3/library/math.html
        .. _numpy: https://numpy.org/
        .. _pandas: https://pandas.pydata.org/

        Example:

            Suppose the following code is saved in "sample.py" in the
            current directory.

            .. code-block:: python

                def triple(x)
                    return 3 * x

            The code below creates a Reference named "foo" in ``space``::

                >>> space.new_module("foo", "modules/sample.py", "sample.py")

            The module becomes accessible as ``foo`` in ``space``::

                >>> space.foo
                <module 'sample' from 'C:\\path\\to\\samplemodule.py'>

                >>> @mx.defcells(space)
                ... def bar(y):
                        return foo.triple(y)

                >>> space.foo.bar(3)
                9

            Let ``model`` be the ultimate parent model of ``space``. The next
            code creates a directory named "model" under the current directory,
            and within the "model" directory, the module is saved
            as "sample.py" in the "modules" sub-directory of the "model" dir,
            as specified by the ``path`` paramter to this method.

                >>> model.write("model")

        Args:
            name(:obj:`str`): Name of the Reference
            path: A path to a file to save the module. If a relative
                path is given, it is relative to the model folder.
            module: A path to a module file as a string or path-like object,
                or a module object.

        .. versionadded:: 0.13.0

        See Also:
            :class:`~modelx.io.moduleio.ModuleData`

        """
        return self._impl.new_module(name, path, module)


class BaseSpaceContainerImpl:
    """Base class of Model and Space to work as container of spaces.

    **Space Deletion**
    new_space(name)
    del_space(name)

    """
    __slots__ = ()
    __mixin_slots = (
        "_named_spaces",
        "_all_spaces"
    )

    # ----------------------------------------------------------------------
    # Serialization by pickle

    def __getstate__(self):
        return {key: getattr(self, key) for key in self.stateattrs}

    def __setstate__(self, state):
        for attr in state:
            setattr(self, attr, state[attr])

    def restore_state(self):
        """Called after unpickling to restore some attributes manually."""

        for space in self._all_spaces.values():
            space.restore_state()

    # ----------------------------------------------------------------------
    # Properties

    @property
    def spaces(self):
        return self._named_spaces.fresh

    @property
    def named_spaces(self):
        return self._named_spaces.fresh

    @property
    def all_spaces(self):
        return self._all_spaces.fresh

    def has_space(self, name):
        return name in self.spaces

    @property
    def namespace(self):
        raise NotImplementedError


class EditableSpaceContainerImpl(BaseSpaceContainerImpl):

    __slots__ = ()
    __mixin_slots = ("spacenamer",)

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

        space = self.model.updater.new_space(self, **params)
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

        import modelx.io.excel_legacy as xl

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
        space = self.model.updater.new_space(
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

    def new_excel_range(self, name, path, range_, sheet, keyids, loadpath):

        from modelx.io.excelio import ExcelRange

        cargs = {"range_": range_,
                 "sheet": sheet,
                 "keyids": keyids}
        dargs = {"load_from": loadpath}

        result = self.system.iomanager.new_client(path, ExcelRange,
                                         model=self.model.interface,
                                         client_args=cargs,
                                         data_args=dargs)

        try:
            self.set_attr(name, result)
        except (ValueError, KeyError, AttributeError):
            self.system.iomanager.del_client(result)
            raise KeyError("cannot assign '%s'" % name)

        return result

    def new_pandas(self, name, path, data, filetype, expose_data):

        from modelx.io.pandasio import PandasData

        cargs= {"filetype": filetype,
                "data": data,
                "is_hidden": expose_data}

        client = self.system.iomanager.new_client(
            path,
            PandasData,
            model=self.model.interface,
            client_args=cargs
        )
        ref = client.value if expose_data else client

        try:
            self.set_attr(name, ref)
        except (ValueError, KeyError, AttributeError):
            self.system.iomanager.del_client(client)
            raise KeyError("cannot assign '%s'" % name)

        return ref

    def new_module(self, name, path, module):

        from modelx.io.moduleio import ModuleData

        client = self.system.iomanager.new_client(
            path,
            ModuleData,
            model=self.model.interface,
            client_args={"module": module},
            data_args={"module": module}
        )

        try:
            self.set_attr(name, client.value)
        except (ValueError, KeyError, AttributeError):
            self.system.iomanager.del_client(client)
            raise KeyError("cannot assign '%s'" % name)

        return client.value

    def set_attr(self, name, value, refmode):
        raise NotImplementedError

    def on_del_space(self, name):
        space = self.named_spaces[name]
        self.named_spaces.del_item(name)
        space.on_delete()
