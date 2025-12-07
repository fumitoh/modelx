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

import builtins
import itertools
import pathlib
import zipfile
import gc
from types import ModuleType

import networkx as nx

from modelx.core.base import (
    Interface,
    Impl,
    Derivable,
    get_mixin_slots,
    null_impl
)
from modelx.core.reference import ReferenceImpl, ReferenceProxy
from modelx.core.cells import CellsImpl, UserCellsImpl
from modelx.core.node import OBJ, KEY, get_node, ObjectNode
from modelx.core.parent import (
    EditableParentImpl,
    EditableParent,
)
from modelx.core.space import UserSpaceImpl
from modelx.core.binding.namespace import BaseNamespace, NamespaceServer
from modelx.core.formula import NULL_FORMULA
from modelx.core.util import is_valid_name
from modelx.core.execution.trace import TraceManager
from modelx.core.chainmap import CustomChainMap
from modelx.core.views import RefView, MacroView
from modelx.core.macro import MacroImpl


class IOSpecOperation:

    __slots__ = ()

    def update_pandas(self, old_data, new_data=None):
        """Update a pandas object assigned to References

        Replace with ``new_data`` the value of such a Reference whose value is
        ``old_data``. Both ``new_data`` and ``old_data`` need to be
        `DataFrame`_ or `Series`_.
        If ``old_data`` is assigned to multiple References in a model,
        the values of all the References are replaced with ``new_data``,
        even the References
        are defined in different locations within the model.
        The identity of pandas objects is determined by the `id()`_ function.
        If ``new_data`` is not given, :class:`~modelx.core.cells.Cells`
        that are dependent on the References are cleared.

        If ``old_data`` has an associated
        :class:`~modelx.io.pandasio.PandasData`,
        this method associates the :class:`~modelx.io.pandasio.PandasData`
        to ``new_data``.

        This method is available for :class:`~modelx.core.model.Model`
        and :class:`~modelx.core.space.UserSpace`. The method
        performs identically regardless of the types of calling objects.

        .. _id():
           https://docs.python.org/3/library/functions.html#id

        .. _Series:
           https://pandas.pydata.org/docs/reference/api/pandas.Series.html

        .. _DataFrame:
           https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html

        Args:
            new_data: A pandas `Series`_ or `DataFrame`_ object
            old_data(optional): A pandas `Series`_ or `DataFrame`_ object

        .. versionadded:: 0.18.0

        See Also:
            * :meth:`new_pandas`
            * :class:`~modelx.io.pandasio.PandasData`

        """
        return self._impl.model.refmgr.update_value(old_data, new_data)

    def update_module(self, old_module, new_module=None):
        """Update an user-defined module assigned to References

        Update an user-defined Python module created by :meth:`new_module`.
        The ``new_module`` parameter is a path to the source file
        of a new user-defined module.
        If ``new_module`` is not given, the old module is reloaded
        from the same source file of the old module
        and a new module module is created.

        The values of References referring to the old module object
        are replaced with the new module object.

        If ``old_module`` is assigned to multiple References in a model,
        the value of all the References are updated, even the References
        are defined in different locations within the model.

        This method associates to the new module the
        :class:`~modelx.io.moduleio.ModuleData` object previously
        associated to the old module.

        This method is available for :class:`~modelx.core.model.Model`
        and :class:`~modelx.core.space.UserSpace`. The method
        performs identically regardless of the types of calling objects.

        Args:
            old_module: A user-defined Python module object.
            new_module: The path to the source file as a :obj:`str` or
                a path-like object.

        .. versionadded:: 0.18.0

        See Also:
            * :meth:`new_module`
            * :class:`~modelx.io.moduleio.ModuleData`

        """
        if not isinstance(old_module, ModuleType):
            raise ValueError("not a module object")
        return self._impl.model.refmgr.update_value(old_module, new_module)

    def get_spec(self, data):
        """Get *IOSpec* associated with ``data``

        Returns the *IOSpec* object associated with ``data``.
        ``data`` should be an object referenced in the model.
        An *IOSpec* object is an instance of a subclass of
        :class:`~modelx.io.baseio.BaseIOSpec`.
        If no *IOSpec* is associated with `data`, an error is raised.

        See Also:
            * :meth:`~modelx.core.model.Model.del_spec`
            * :class:`~modelx.io.baseio.BaseIOSpec`
            * :attr:`~modelx.core.model.Model.iospecs`
        """
        spec = self._impl.refmgr.get_spec(data)
        if spec is None:
            raise ValueError("spec not found")
        else:
            return spec

    def del_spec(self, data):
        """Delete *IOSpec* associate with ``data``

        Deletes the *IOSpec* object associated with ``data``.
        ``data`` should be an object referenced in the model.
        An *IOSpec* object is an instance of a subclass of
        :class:`~modelx.io.baseio.BaseIOSpec`.

        See Also:
            * :meth:`~modelx.core.model.Model.get_spec`
            * :class:`~modelx.io.baseio.BaseIOSpec`
            * :attr:`~modelx.core.model.Model.iospecs`
        """
        self._impl.refmgr._manager.del_spec(self.get_spec(data))

    @property
    def iospecs(self):
        """List of :class:`~modelx.io.baseio.BaseIOSpec` objects

        Returns a list of all objects of BaseIOSpec subclasses
        defined in this Model.

        :class:`~modelx.io.excelio.ExcelRange` and
        :class:`~modelx.io.pandasio.PandasData`
        are subclasses of :class:`~modelx.io.baseio.BaseIOSpec`.

        :class:`~modelx.io.excelio.ExcelRange`
        objects are created either by
        :meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>`
        or
        :meth:`UserSpace.new_excel_range<modelx.core.space.UserSpace.new_excel_range>`
        method.
        :class:`~modelx.io.pandasio.PandasData` objects are
        created either by
        :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`
        or
        :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
        method.

        See Also:
            * :meth:`~modelx.core.model.Model.get_spec`
            * :class:`~modelx.io.excelio.ExcelRange`
            * :class:`~modelx.io.pandasio.PandasData`
            * :meth:`UserSpace.new_excel_range<modelx.core.space.UserSpace.new_excel_range>`
            * :meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>`
            * :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
            * :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`

        .. versionchanged:: 0.20.0 renamed to ``iospecs`` from ``dataspecs``
        .. versionchanged:: 0.18.0 the property name is changed
            from ``dataclients`` to ``dataspecs``
        .. versionadded:: 0.9.0

        """
        return list(self._impl.refmgr.specs)


class Model(IOSpecOperation, EditableParent):
    """Top-level container representing a complete modelx model.

    Model is the root object in the modelx object hierarchy and serves as
    the primary container for organizing spaces, cells, and references.
    Each Model represents an independent, self-contained computational model
    with its own namespace and execution environment.

    A Model contains:

    * :class:`~modelx.core.space.UserSpace` objects (top-level spaces)
    * Global references accessible throughout the model
    * Serialization and I/O specifications

    Key Characteristics:

    * **Top-level container**: Root of the object hierarchy
    * **Independent namespace**: Each model has isolated global references
    * **Serializable**: Can be saved to/loaded from files or zip archives
    * **Exportable**: Can be exported as a Python package

    Creation:
        Models are created using the :func:`~modelx.new_model` function::

            >>> import modelx as mx
            >>> model = mx.new_model()
            >>> model
            <Model Model1>

            >>> # Create with specific name
            >>> model = mx.new_model('MyModel')
            >>> model
            <Model MyModel>

    Adding Spaces:
        Create child spaces to organize cells and nested structures::

            >>> space = model.new_space('Calculations')
            >>> space
            <UserSpace Calculations in MyModel>

    Global References:
        Set global references accessible from all spaces in the model::

            >>> import numpy as np
            >>> model.np = np
            >>> model.discount_rate = 0.05

    Persistence:
        Models can be saved and loaded in multiple formats::

            >>> # Save as directory structure with text files
            >>> model.write('path/to/model')

            >>> # Save as zip archive
            >>> model.zip('path/to/model.zip')

            >>> # Load a saved model
            >>> loaded = mx.read_model('path/to/model')

    Memory Management:
        Clear calculated values to free memory::

            >>> model.clear_all()  # Clear all cells and dynamic spaces in the model

    Multiple Models:
        Multiple models can coexist in the same session::

            >>> model1 = mx.new_model('Model1')
            >>> model2 = mx.new_model('Model2')
            >>> mx.get_models()
            {'Model1': <Model Model1>, 'Model2': <Model Model2>}

    Accessing Current Model:
        Get the currently active model::

            >>> mx.cur_model()
            <Model Model2>

    See Also:
        :func:`~modelx.new_model`: Create a new model
        :func:`~modelx.read_model`: Load a model from files
        :func:`~modelx.get_models`: Get all models in the session
        :func:`~modelx.cur_model`: Get the current model
        :class:`~modelx.core.space.UserSpace`: Container for cells and nested spaces
        :meth:`~modelx.core.model.Model.write`: Save model to files
        :meth:`~modelx.core.model.Model.zip`: Save model to zip archive

    .. versionchanged:: 0.18.0
        Added pandas and module update operations

    """

    __slots__ = ()

    def rename(self, name, rename_old=False):
        """Rename the model itself"""
        self._impl.system.rename_model(
            new_name=name, old_name=self.name, rename_old=rename_old)

    def clear_all(self):
        """Clears :class:`~modelx.core.cells.Cells` and :class:`~modelx.core.space.ItemSpace`.

        Clears both the input values and the calculated values of
        all the :class:`~modelx.core.cells.Cells` in the model and
        delete all the :class:`~modelx.core.space.ItemSpace` objects
        in the model.

        .. seealso::

            :meth:`UserSpace.clear_all<modelx.core.space.UserSpace.clear_all>`

        .. versionadded:: 0.16.0
        """
        for space in self._impl.spaces.values():
            space.clear_all_cells(
                clear_input=True,
                recursive=True,
                del_items=True
            )

    def close(self):
        """Close the model."""
        self._impl.system.close_model(self._impl)

    @Interface.doc.setter
    def doc(self, value):
        self._impl.doc = value

    @property
    def path(self):
        r"""A Path object representing the model's path.

        When a previously saved model is loaded with :func:`~modelx.read_model`,
        this property is set to a `pathlib.Path`_ object representing
        the path given to :func:`~modelx.read_model`::

            >>> import modelx as mx
            >>> model = mx.read_model(r"C:\Users\mxuser\Model")
            >>> model.path
            WindowsPath('C:/Users/mxuser/Model2')

        When a model is created with :py:func:`~modelx.new_model`,
        this property is set to ``None``::

            >>> model = mx.new_model()
            >>> model.path     # Returns None

        The user can set the path by assigning a string value to it::

            >>> model.path = "."
            >>> model.path
            WindowsPath('.')

        When a model is saved with :meth:`~Model.write` or
        :func:`~modelx.write_model`,
        this property is updated to a `pathlib.Path`_ object representing
        the path given to the method or function::

            >>> model.write(r"C:\Users\mxuser\Model2")
            >>> model.path
            WindowsPath('C:/Users/mxuser/Model2')

        The property is accessed within formulas as an attribute
        of a special Reference, ``model_``::

            >>> @mx.defcells
            >>> def foo():
            ...     return _model.path
            >>> foo()
            WindowsPath('C:/Users/mxuser/Model')

        Returns:
            A `pathlib.Path`_ object or :py:obj:`None`

        .. versionadded:: 0.25.0

        .. _pathlib.Path:
           https://docs.python.org/3/library/pathlib.html#pathlib.Path

        """
        return self._impl.system.executor.add_reference(
            self._impl.property_refs["path"]).interface

    @path.setter
    def path(self, path):
        self._impl.clear_attr_referrers(self._impl.property_refs["path"])
        self._impl.path = pathlib.Path(path)
        self._impl.property_refs['path'] = ReferenceImpl(
            self._impl, "path", self._impl.path, container=self._impl._property_refs,
            set_item=False)

    def write(self, model_path, backup=True, log_input=False):
        """Write model to files.

        This method performs the :py:func:`~modelx.write_model`
        on self. See :py:func:`~modelx.write_model` section for the details.

        .. versionchanged:: 0.8.0
        .. versionadded:: 0.0.22

        Args:
            model_path(str): Folder(directory) path where the model is saved.
            backup(bool, optional): Whether to backup an existing file with
                the same name if it already exists. Defaults to ``True``.
            log_input(bool, optional): If ``True``, input values in Cells are
                output to *_input_log.txt* under ``model_path``. Defaults
                to ``False``.
        """
        from modelx.serialize import write_model
        write_model(self._impl.system, self, model_path, is_zip=False,
                    backup=backup, log_input=log_input)

    def zip(self, model_path, backup=True, log_input=False,
            compression=zipfile.ZIP_DEFLATED, compresslevel=None):
        """Archive model to a zip file.

        This method performs the :py:func:`~modelx.zip_model`
        on self. See :py:func:`~modelx.zip_model` section for the details.

        .. versionchanged:: 0.9.0
            ``compression`` and ``compresslevel`` parameters are added.

        .. versionadded:: 0.8.0

        Args:
            model_path(str): Folder(directory) path where the model is saved.
            backup(bool, optional): Whether to backup an existing file with
                the same name if it already exists. Defaults to ``True``.
            log_input(bool, optional): If ``True``, input values in Cells are
                output to *_input_log.txt* under ``model_path``. Defaults
                to ``False``.
            compression(optional): Identifier of the ZIP compression method
                to use. This method uses `zipfile.ZipFile`_ class internally
                and ``compression`` and ``compresslevel`` arguments are
                passed to `zipfile.ZipFile`_ constructor.
                See `zipfile.ZipFile`_ manual page for available identifiers.
                Defaults to `zipfile.ZIP_DEFLATED`_.
            compresslevel(optional):
                Integer identifier to indicate the compression level to use.
                If not specified, the default compression level is used.
                See `zipfile.ZipFile`_ explanation on the Python Standard
                Library site for available integer identifiers for
                each compression method.
                For Python 3.6, this parameter is ignored.

        .. _zipfile.ZipFile:
           https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile

        .. _zipfile.ZIP_DEFLATED:
           https://docs.python.org/3/library/zipfile.html#zipfile.ZIP_DEFLATED

        """
        from modelx.serialize import write_model
        write_model(self._impl.system, self, model_path, is_zip=True,
                    backup=backup, log_input=log_input,
                    compression=compression, compresslevel=compresslevel)

    def export(self, path):
        """Export the model as a Python package.

        .. warning:: This feature is experimental.
            See the limitaions section in :py:func:`~modelx.export_model`.

        This method performs the :py:func:`~modelx.export_model`
        on self. See :py:func:`~modelx.export_model` section for the details.

        .. versionadded:: 0.22.0
        """
        from ..export.exporter import Exporter
        Exporter(self, path).export()

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __getattr__(self, name):
        return self._impl.get_attr(name)

    def __delattr__(self, name):
        self._impl.del_attr(name)

    def __dir__(self):
        result = list(self._impl._namespace)
        result.extend(self._impl._macros.keys())
        return result

    @property
    def tracegraph(self):
        """A directed graph of cells."""
        return self._impl.tracegraph

    @property
    def refs(self):
        """Return a mapping of global references."""
        return RefView(self._impl.global_refs)
    
    @property
    def macros(self):
        """Return a mapping of macros.
        
        Returns a dictionary-like view of all macros defined in the model.
        Macros are Python functions that can be saved within the model and
        executed to manipulate or query the model.
        
        Example:
            >>> import modelx as mx
            >>> m = mx.new_model('MyModel')
            
            >>> @mx.defmacro
            ... def get_name():
            ...     return mx_model.name
            
            >>> m.macros
            {'get_name': <Macro MyModel.get_name>}
            
            >>> m.get_name()
            'MyModel'
        
        See Also:
            :func:`~modelx.defmacro`: Decorator to create macros
            :class:`~modelx.core.macro.Macro`: Macro class documentation
        
        .. versionadded:: 0.30.0
        """
        return MacroView(self._impl._macros)

    def _get_from_name(self, name):
        """Get object by named id"""
        return self._impl.get_impl_from_name(name).interface

    def _get_object(self, name, as_proxy=False):
        parts = name.split(".")
        attr = parts.pop(0)

        if as_proxy and attr in self.refs:
            return ReferenceProxy(self._impl.global_refs[attr])
        else:
            return super()._get_object(name, as_proxy)

    def _get_attrdict(self, extattrs=None, recursive=True):
        """Get attributes"""
        result = super(Model, self)._get_attrdict(extattrs, recursive)

        if recursive:
            result["refs"] = self.refs._get_attrdict(extattrs, recursive)
        else:
            result["refs"] = tuple(self.refs)

        if extattrs:
            self._get_attrdict_extra(result, extattrs, recursive)

        return result

    def _get_refs(self, value):
        """Get references referring to a value"""
        refs = self._impl.refmgr._valid_to_refs[id(value)]
        return [ReferenceProxy(impl) for impl in refs]

    def _get_assoc_values(self):
        """Get a list of values in the model with their associates"""
        result = []

        for valid, refs in self._impl.refmgr._valid_to_refs.items():
            info = {}
            info["value"] = refs[0].interface
            info["spec"] = self._impl.system.iomanager.get_spec_from_value(
                io_group=self,
                value=refs[0].interface
            )
            info["refs"] = self._get_refs(info["value"])
            result.append(info)

        return result

    # ----------------------------------------------------------------------
    def generate_actions(self, targets, step_size=1000):
        """Generates actions for memory-optimized run

        Returns a list of *actions* for :meth:`execute_actions`
        to perform a memory-optimized calculation.
        See :meth:`execute_actions` for details.

        Args:
            targets: :obj:`list` of :class:`~modelx.core.node.ItemNode`.
            step_size(:obj:`int`, optional): Number of calculations in a step.

        Returns:
            :obj:`list` of *actions*.

        .. seealso::
            * :meth:`execute_actions`
        """

        calc_targets = []
        calculated = []
        try:
            for n in targets:
                obj, key = n._impl[OBJ], n._impl[KEY]
                if key not in obj.input_keys:
                    with self._impl.system.trace_stack(maxlen=None):
                        obj.get_value_from_key(key)
                        tracestack = self._impl.system.callstack.tracestack
                        for trace in tracestack:
                            if trace[0] == "ENTER":
                                calculated.append(trace[3])

                    calc_targets.append(n._impl)

            result = self._impl.get_calcsteps(
                calc_targets, calculated, step_size)

        finally:
            for n in calculated:
                n[OBJ].clear_value_at(n[KEY])

        return result

    def execute_actions(self, actions):
        """Performs memory-optimized run

        Performs a memory-optimized run.
        Memory-optimized runs are for calculating specified nodes (*targets*)
        by consuming less memory.
        Memory-optimized runs are useful when
        the intermediate results contain large data.

        A memory-optimized run actually involves two runs.
        The first run is invoked by calling
        :meth:`generate_actions` and
        the second run is performed by calling :meth:`execute_actions`.
        The :meth:`generate_actions` method runs the model to generate
        and return
        a list of *actions* from a list of *targets* passed to the
        ``targets`` parameter.
        The user should set a small data set in the model
        before calling :meth:`generate_actions`.
        The elements of ``targets`` should be
        :class:`~modelx.core.node.ItemNode` objects representing
        combinations of a :class:`~modelx.core.cells.Cells` object
        and its arguments.
        Node objects can be created by passing the arguments
        to :meth:`~modelx.core.cells.Cells.node` method.
        For example, the expression below creates a node object representing
        ``Model1.Space1.Cells3(x=2)``::

            Model1.Space1.Cells3.node(x=2)

        :meth:`generate_actions` runs the model to analyze
        the dependency of the target nodes.
        :meth:`generate_actions` identifies all the calculated nodes
        that the target nodes depend on, and
        sort the nodes in a topological order.
        Then the ordered nodes are split into groups so that
        each group has at most the number of nodes specified by
        ``step_size`` (1000 by default).
        Then :meth:`generate_actions` generates actions
        to process each group.
        For each group, *calc*, *paste*, and *clear* actions are generated in this order.
        Each action is associted with nodes that the action applies to.
        A *calc* action indicates its associated nodes
        should be calculated.
        A *paste* action indicates its associted nodes should be value-pasted
        so that the values of the nodes persist after their
        precedents are cleared.
        A *clear* action indicates its associated nodes should be cleared
        to save memory.

        :meth:`generate_actions` returns a list
        of actions. Each action is also represented by a list,
        whose first element is a string,
        which is either ``'calc'``, ``'paste'``, or ``'clear'``.
        The string indicates the type of action to perform.
        The second element is a list of :class:`~modelx.core.node.ItemNode`,
        to which the action indicated by the first element apply.
        Below is an example of the action list.
         
        .. code-block::

            [
                ['calc', [Model1.Space1.Cells1(), Model1.Space1.Cells2(x=0)]],
                ['paste', [Model1.Space1.Cells2(x=0), Model1.Space1.Cells1()]],
                ['clear', []],
                ['calc', [Model1.Space1.Cells2(x=1), Model1.Space1.Cells2(x=2)]],
                ['paste', [Model1.Space1.Cells2(x=2)]],
                ['clear', [Model1.Space1.Cells2(x=1), Model1.Space1.Cells2(x=0)]],
                ['calc', [Model1.Space1.Cells3(x=2)]],
                ['paste', [Model1.Space1.Cells3(x=2)]],
                ['clear', [Model1.Space1.Cells1(), Model1.Space1.Cells2(x=2)]]
            ]

        :meth:`execute_actions` executes actions passed as ``actions``.
        Before calling :meth:`execute_actions`, the user should
        set the entire data set instead of the small data set
        used for generating the actions.
        After the execusion, the target nodes are value-pasted, and
        the values of precedent nodes of the target nodes are all cleared.
        To clear the values call :meth:`~modelx.core.cells.Cells.clear_at`
        for the targets
        or call :meth:`Cells.clear_all<modelx.core.cells.Cells.clear_all>`
        or :meth:`Space.clear_all<modelx.core.space.UserSpace.clear_all>`
        or :meth:`Model.clear_all<modelx.core.model.Model.clear_all>`.

        Args:
            actions(:obj:`list`): The *actions* list

        .. seealso::
            * :meth:`generate_actions`
            * `Running a heavy model while saving memory <https://modelx.io/blog/2022/03/26/running-model-while-saving-memory/>`_,
              a blog post on https://modelx.io

        """

        gc_status = gc.isenabled()
        gc.disable()
        try:
            for step in actions:
                action, nodes = step

                if action == "calc":
                    for n in nodes:
                        node = n._impl
                        node[OBJ].get_value_from_key(node[KEY])

                elif action == "paste":
                    node_value_pairs = []
                    for n in nodes:
                        node = n._impl
                        node_value_pairs.append(
                            [node, node[OBJ].get_value_from_key(node[KEY])]
                        )
                    for node, value in node_value_pairs:
                        node[OBJ].set_value_from_key(node[KEY], value)

                elif action == "clear":
                    for n in nodes:
                        node = n._impl
                        node[OBJ].clear_value_at(node[KEY])

                    gc.collect()
                else:
                    raise RuntimeError("must not happen")
        finally:
            if gc_status:
                gc.enable()

    def compare_cells(self, func):
        """Tentative: Compare cells with the same name across different spaces in the model.

        ..  warning:: This is a tentative feature based on a use request 
                      (See `#196 <https://github.com/fumitoh/modelx/discussions/196>`_), 
                      and will be replaced with a more robust solution in future releases.

        This method searches for cells with a given name across all spaces in the model,
        groups them by their normalized formula, and displays the results.

        Args:

            func: Either a function object or a string representing the cell name to compare.
                  If a function object is provided, its __name__ attribute will be used.

        Returns:

            None. Results are printed to stdout.

        Output Format:

            Groups cells by their normalized formula and displays:

            - Group number
            - List of space names containing cells with identical formulas
            - The normalized formula (with empty lines removed)

        Notes:

            - Empty lines in formulas are removed during normalization
            - If a cell's formula is not accessible, it will be labeled as "<formula not accessible>"
            - If no spaces contain a cell with the given name, a message is printed
            - Formulas are considered identical after normalization (stripping and removing empty lines)

        Example:

            .. code-block:: python

                >>> import  modelx as mx

                >>> m = mx.new_model()

                >>> s1 = m.new_space()

                >>> @mx.defcells
                ... def foo(x):
                ...     return 1

                >>> s2 = mx.new_space()

                >>> @mx.defcells
                ... def foo(x):
                ...     return 2

                >>> m.compare_cells('foo')
                ------------------------------------------------------------
                [Group 1]
                Spaces    : Space1
                Formula (normalized):
                def foo(x):
                    return 1
                ------------------------------------------------------------
                ------------------------------------------------------------
                [Group 2]
                Spaces    : Space2
                Formula (normalized):
                def foo(x):
                    return 2
                ------------------------------------------------------------
        """

        func_name = getattr(func, '__name__', func)
        grouped = {}

        try:
            spaces_iter = self.spaces.values()
            
        except AttributeError:
            spaces_iter = self.spaces

        for space in spaces_iter:
            cell = getattr(space, func_name, None)
            if cell is None:
                continue
            try:
                formula = str(cell.formula).strip()
                lines = formula.split('\n')
                normalized_lines = []
                
                for line in lines:
                    
                    if line.strip():
                        normalized_lines.append(line)
                
                normalized_formula = '\n'.join(normalized_lines)            
            
            except Exception:
                formula = "<formula not accessible>"
                normalized_formula = formula
            grouped.setdefault(normalized_formula, []).append(space.name)

        if not grouped:
            print(f"No spaces contain a cell named '{func_name}'.")
            return

        for idx, (normalized_formula, names) in enumerate(grouped.items(), 1):
            print("\n" + "-"*60 + "\n")
            print(f"[Group {idx}]")
            print(f"Spaces    : {', '.join(sorted(names))}")
            print("Formula (normalized):")
            print(normalized_formula)
            print("\n" + "-"*60 + "\n")


    def new_space_from_model(
        self,
        source_model,
        name=None,
        *,
        refs_strategy="copy",
        refs_prefix=None,
        defined_only=False,
    ):
        """Create a top-level UserSpace from another Model.

        This method creates a new :class:`~modelx.core.space.UserSpace` in the model
        and copies all top-level spaces from ``source_model`` into the created space.
        The space acts as a namespace wrapper, allowing the source model's
        structure to be migrated within the target model.

        The method provides control over how references are handled during the migration
        process through the ``refs_strategy`` parameter, and allows filtering of
        the copied content through the ``defined_only`` parameter.

        Args:
            source_model (:class:`~modelx.core.model.Model`): The model whose top-level
                spaces will be copied into this model. Cannot be the same as the
                target model (``self``).
            name (:obj:`str`, optional): Name of the container space in the target model.
                If not specified, defaults to ``source_model.name``.
            refs_strategy (:obj:`str`, optional): Strategy for handling global references
                from ``source_model``. Must be one of:

                * ``"copy"`` (default) - Copy all global references from ``source_model``
                  (except ``__builtins__``) into the container space's references.
                  References are propagated to all descendant spaces.
                * ``"ignore"`` - Do not copy any references from ``source_model``.
                  Only the spaces and cells structure is copied.
                * ``"shadow"`` - Copy references from ``source_model`` only if they
                  don't already exist in the target model's global references.
                  Existing references in the target model take precedence.

            refs_prefix (:obj:`str`, optional): If specified, prefix to apply to reference
                names when copying from ``source_model``. For example, if
                ``refs_prefix="src_"``, a reference named ``data`` in ``source_model``
                will be copied as ``src_data`` in the container space. The original
                name is also preserved as an alias. Only applicable when
                ``refs_strategy`` is ``"copy"`` or ``"shadow"``.
            defined_only (:obj:`bool`, optional): If :obj:`True`, only defined (non-derived)
                :class:`~modelx.core.cells.Cells` and
                :class:`~modelx.core.space.UserSpace` objects are copied.
                Derived cells and spaces resulting from inheritance are excluded.
                Defaults to :obj:`False`.

        Returns:
            :class:`~modelx.core.space.UserSpace`: The created container space containing
            all copied spaces from ``source_model``.

        Raises:
            ValueError: If ``source_model`` is the same as the target model (``self``).

        Example:

            Create two models and embed one into the other::

                >>> import modelx as mx

                >>> # Create source model with spaces and references
                >>> source = mx.new_model("SourceModel")
                >>> source.param = 100
                >>> space1 = source.new_space("Space1")

                >>> @mx.defcells
                ... def calc(x):
                ...     return x * _model.param

                >>> # Create target model
                >>> target = mx.new_model("TargetModel")

                >>> # Embed source model as a space
                >>> container = target.new_space_from_model(source, name="Embedded")

                >>> # Access embedded content
                >>> container.Space1.calc(5)
                500

            Using ``refs_prefix`` to avoid name conflicts::

                >>> target.rate = 0.05  # Global reference in target
                >>> source.rate = 0.03  # Global reference in source

                >>> # Embed with prefix to distinguish references
                >>> container = target.new_space_from_model(
                ...     source,
                ...     name="Embedded",
                ...     refs_prefix="src_"
                ... )

                >>> # References are available with prefix
                >>> container.src_rate
                0.03
                >>> target.rate  # Target's original reference unchanged
                0.05

            Copy only defined cells and spaces::

                >>> base_space = source.new_space("Base")
                >>> derived_space = source.new_space("Derived")
                >>> derived_space.add_bases(base_space)

                >>> # Copy only defined content (excludes derived)
                >>> container = target.new_space_from_model(
                ...     source,
                ...     defined_only=True
                ... )

        See Also:
            * :meth:`~modelx.core.model.Model.new_space`
            * :meth:`~modelx.core.space.UserSpace.new_space`
            * :meth:`~modelx.core.space.UserSpace.add_bases`

        .. versionadded:: 0.29.2

        """
        if source_model is self:
            raise ValueError("Cannot embed a model into itself")

        if name is None:
            name = source_model.name

        refs = None
        if refs_strategy in ("copy", "shadow"):
            refs = {}
            for k, ref in source_model._impl.global_refs.items():
                if k == "__builtins__":
                    continue
                new_key = (f"{refs_prefix}{k}" if refs_prefix else k)
                if refs_strategy == "shadow" and new_key in self._impl.global_refs:
                    continue
                # Always include the original name as well; prefixed name is an alias
                if refs_prefix:
                    refs[k] = ref.interface
                refs[new_key] = ref.interface

        container_impl = self._impl.model.updater.new_space(
            parent=self._impl,
            name=name,
            refs=refs
        )
        container = container_impl.interface

        for child in source_model._impl.named_spaces.values():
            self._impl.model.updater.copy_space(
                parent=container_impl,
                source=child,
                name=child.name,
                defined_only=defined_only
            )


        # Propagate container refs into each descendant space so formulas can resolve names
        if refs_strategy in ("copy", "shadow") and refs:
            def _propagate(space_impl):
                # Add missing refs without overriding existing ones
                for rk, rv in refs.items():
                    if rk not in space_impl.own_refs:
                        self._impl.model.spmgr.new_ref(space_impl, rk, rv, refmode="auto")
                for child_impl in space_impl.named_spaces.values():
                    _propagate(child_impl)
            _propagate(container_impl)

        return container


class ModelNamespace(BaseNamespace):

    __slots__ = ()

    _impl: 'ModelImpl'

    def __getattr__(self, name):    # TODO: Refactor.
        # Check if name is a Reference in the current Space
        ref = self._impl.refs.get(name)
        if ref is not None:
            assert isinstance(ref, ReferenceImpl)
            return self._impl.system.executor.add_reference(ref).interface
        elif name in self._impl.named_spaces:
            return self._impl.named_spaces[name].interface
        else:
            raise AttributeError(f"{name!r} not found in {repr(self._impl.interface)}")

    def __contains__(self, item):
        return item in self._impl._namespace

    @property
    def _parent(self):
        return self

    parent = _parent    # for backward compatibility

    @property
    def path(self):
        path = self._impl._property_refs['path']
        assert isinstance(path, ReferenceImpl)
        return self._impl.system.executor.add_reference(path).interface


_model_impl_base = (
    TraceManager,
    EditableParentImpl,
    Impl
)


class ModelImpl(*_model_impl_base):

    interface_cls = Model

    __slots__ = (
        "namespace",
        "_namespace",
        "_global_refs",
        "_property_refs",
        "_macros",
        "_macro_namespace",
        "currentspace",
        "path",
        "refmgr"
    ) + get_mixin_slots(*_model_impl_base)

    def __init__(self, *, system, name):

        if not name:
            name = system._modelnamer.get_next(system.models)
        elif not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        Impl.__init__(self, system=system, parent=None, name=name, spmgr=SpaceManager(self))
        EditableParentImpl.__init__(self)
        TraceManager.__init__(self)

        self.currentspace = None
        self.path = None
        self._global_refs = {}
        self._global_refs['__builtins__'] = ReferenceImpl(
            self, '__builtins__', builtins, container=self._global_refs,
            set_item=False)
        self._property_refs = {}
        self._property_refs["path"] = ReferenceImpl(
            self, "path", self.path, container=self._property_refs,
            set_item=False)
        self._macros = {}
        self._macro_namespace = None
        self.named_spaces = {}
        self._namespace = CustomChainMap(self.named_spaces, self._global_refs)
        self.namespace = ModelNamespace(self)
        self.allow_none = False
        self.refmgr = ReferenceManager(self, system.iomanager)

    def rename(self, name):
        """Rename self. Must be called only by its system."""
        if is_valid_name(name):
            if name not in self.system.models:
                self.name = name
                return True  # Rename success
            else:  # Model name already exists
                return False
        else:
            raise ValueError("Invalid name '%s'." % name)

    def repr_self(self, add_params=True):
        return self.name

    def repr_parent(self):
        return ""

    @Impl.doc.setter
    def doc(self, value):
        self._doc = value

    @property
    def global_refs(self):
        return self._global_refs

    refs = global_refs
    own_refs = global_refs

    @property
    def property_refs(self):
        return self._property_refs

    def get_impl_from_name(self, name):
        """Retrieve an object by a dotted name relative to the model."""
        parts = name.split(".")
        space = self.spaces[parts.pop(0)]
        if parts:
            return space.get_impl_from_namelist(parts)
        else:
            return space

    def _check_sanity(self):

        for name, r in self.global_refs.items():
            if name != "__builtins__":
                assert id(r.interface) in self.refmgr._valid_to_refs

        self.refmgr._check_sanity()
        self.spmgr._check_sanity()

    @property
    def updater(self):
        return SpaceUpdater(self.spmgr)

    def del_ref(self, name):
        ref = self.global_refs[name]
        self.model.clear_attr_referrers(ref)
        ref.on_delete()
        del self.global_refs[name]
        for space in self.yield_spaces():
            space.on_notify(self.global_refs)

    def change_ref(self, name, value):
        self.del_ref(name)
        self.new_ref(name, value)

    def new_ref(self, name, value):
        ref = ReferenceImpl(
            self, name, value, container=self._global_refs,
            set_item=False)
        self._global_refs[name] = ref
        for space in self.yield_spaces():
            space.on_notify(self.global_refs)
        return ref

    def get_attr(self, name):
        if name in self.spaces:
            return self.spaces[name].interface
        elif name in self.global_refs:
            return self.global_refs[name].interface
        elif name in self._macros:
            return self._macros[name].interface
        else:
            raise AttributeError(
                "Model '{0}' does not have '{1}'".format(self.name, name)
            )

    def set_attr(self, name, value, refmode=None):
        if name in self.spaces:
            raise KeyError("Space named '%s' already exist" % self.name)
        elif name in self._macros:
            raise KeyError("Macro named '%s' already exists" % name)
        elif name in self.global_refs:
            self.refmgr.change_ref(self, name, value)
        else:
            self.refmgr.new_ref(self, name, value, refmode)

    def del_attr(self, name):

        if name in self.named_spaces:
            self.updater.del_defined_space(self.named_spaces[name])
        elif name in self._macros:
            self.del_macro(name)
        elif name in self.global_refs:
            self.refmgr.del_ref(self, name)
        else:
            raise KeyError("Name '%s' not defined" % name)
    
    # Macro methods
    
    def new_macro(self, name, formula):
        """Create a new macro
        
        Args:
            name: Name of the macro
            formula: Formula object or callable
            
        Returns:
            MacroImpl instance
        """
        if name in self._macros:
            raise ValueError(f"Macro '{name}' already exists")
        if name in self.spaces or name in self.global_refs:
            raise ValueError(f"Name '{name}' already used")
        
        macro = MacroImpl(
            system=self.system,
            parent=self,
            name=name,
            formula=formula
        )
        self._macros[name] = macro
        return macro
    
    def del_macro(self, name):
        """Delete a macro
        
        Args:
            name: Name of the macro to delete
        """
        if name not in self._macros:
            raise KeyError(f"Macro '{name}' not found")
        
        macro = self._macros[name]
        macro.on_delete()
        del self._macros[name]
    
    def get_macro_namespace(self):
        """Get the namespace for macro execution
        
        Returns a namespace dict with mx_model and the model's name
        pointing to the model interface.
        """
        if self._macro_namespace is None:
            self._macro_namespace = {}
        
        # Always update to ensure it has the current state
        self._macro_namespace['mx_model'] = self.interface
        self._macro_namespace[self.name] = self.interface
        self._macro_namespace['__builtins__'] = builtins
        
        # Add all macros to the namespace so they can call each other
        for macro_name, macro_impl in self._macros.items():
            self._macro_namespace[macro_name] = macro_impl.interface
        
        return self._macro_namespace

    @property
    def macros(self):
        """Return the macros dictionary"""
        return self._macros

    def to_node(self):
        return ObjectNode(get_node(self, None, None))


def split_node(node):
    parent = ".".join(node.split(".")[:-1])
    name = node.split(".")[-1]
    return parent, name


def len_node(node):
    return len(node.split("."))


def trim_left(node, trimed_len):
    return ".".join(node.split(".")[trimed_len:])


def trim_right(node, trimed_len):
    if trimed_len == 0:
        return node
    else:
        return ".".join(node.split(".")[:-trimed_len])


def _get_shared_part(a_node, b_node, from_left=True):

    a_node = a_node.split(".")
    b_node = b_node.split(".")

    length = min(len(a_node), len(b_node))

    while length:

        if from_left:
            a_node, b_node = a_node[:length], b_node[:length]
        else:
            a_node, b_node = a_node[-length:], b_node[-length:]

        if a_node == b_node:
            return ".".join(a_node)

        length -= 1


def get_shared_asc(a_node, b_node):
    return _get_shared_part(a_node, b_node, from_left=True)


def get_shared_desc(a_node, b_node):
    return _get_shared_part(a_node, b_node, from_left=False)


def has_parent(node, parent):
    parent_len = len_node(parent)

    if len_node(node) <= parent_len:
        return False
    elif trim_right(node, len_node(node) - parent_len) == parent:
        return True
    else:
        return False


class SpaceGraph(nx.DiGraph):
    """New implementation of inheritance graph"""

    def ordered_preds(self, node):
        edges = [(self.edges[e]["index"], e) for e in self.in_edges(node)]
        return [e[0] for i, e in sorted(edges, key=lambda elm: elm[0])]

    def ordered_subs(self, node):
        g = nx.descendants(self, node)
        g.add(node)
        return nx.topological_sort(self.subgraph(g))

    def max_index(self, node):
        return max(
            [self.edges[e]["index"] for e in self.in_edges(node)],
            default=0
        )

    def get_mro(self, node):
        """Calculate the Method Resolution Order of bases using the C3 algorithm.

        Code modified from
        http://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/

        Args:
            bases: sequence of direct base spaces.

        Returns:
            mro as a list of bases including node itself
        """
        seqs = [self.get_mro(base)
                for base in self.ordered_preds(node)
                ] + [self.ordered_preds(node)]
        res = []
        while True:
            non_empty = list(filter(None, seqs))

            if not non_empty:
                # Nothing left to process, we're done.
                res.insert(0, node)
                return res

            for seq in non_empty:  # Find merge candidates among seq heads.
                candidate = seq[0]
                not_head = [s for s in non_empty if candidate in s[1:]]
                if not_head:
                    # Reject the candidate.
                    candidate = None
                else:
                    break

            if not candidate:  # Better to return None instead of error?
                raise TypeError(
                    "inconsistent hierarchy, no C3 MRO is possible"
                )

            res.append(candidate)

            for seq in non_empty:
                # Remove candidate.
                if seq[0] == candidate:
                    del seq[0]

    def _visit_tree_inner(self, node, include_self=True):
        que = [node]
        level = 0
        while que:
            n = que.pop(0)
            if n != node or include_self:
                yield level, n
            childs = [ch for ch in self.nodes
                      if ch[:len(n) + 1] == (n + ".")
                      and len_node(n) + 1 == len_node(ch)]
            que += childs
            level += 1

    def visit_tree(self, node, include_self=True):
        for _, n in self._visit_tree_inner(
                node,include_self=include_self):
            yield n

    def to_space(self, node):
        return self.nodes[node]["space"]

    def get_relative(self, subspace, basespace, basevalue):

        shared_parent = get_shared_asc(basespace, basevalue)
        if not shared_parent:
            return None
        shared_desc = get_shared_desc(subspace, basespace)
        if shared_desc:
            shared_desc = shared_desc.split(".")
        else:
            shared_desc = []

        subroot = trim_right(subspace, len(shared_desc))
        basroot = trim_right(basespace, len(shared_desc))

        while True:

            if basroot in self.get_mro(subroot):
                break

            if shared_desc:
                n = shared_desc.pop(0)
                subroot = ".".join(subroot.split(".") + [n])
                basroot = ".".join(basroot.split(".") + [n])
            else:
                raise RuntimeError("must not happen")

        if basroot == shared_parent or has_parent(shared_parent, basroot):
            relative_part = trim_left(basevalue, len_node(basroot))
            if relative_part:
                return subroot + "." + relative_part
            else:
                return subroot
        else:
            return None


class Instruction:

    def __init__(self, func, args=(), arghook=None, kwargs=None):

        self.func = func
        self.args = args
        self.arghook = arghook
        self.kwargs = kwargs if kwargs else {}

    def execute(self):
        if self.arghook:
            args, kwargs = self.arghook(self)
        else:
            args, kwargs = self.args, self.kwargs

        return self.func(*args, **kwargs)

    @property
    def funcname(self):
        return self.func.__name__

    def __repr__(self):
        return "<Instruction: %s>" % self.funcname


class InstructionList(list):

    def execute(self, clear=True):
        result = None
        for inst in self:
            result = inst.execute()
        if clear:
            self.clear()
        return result


class SharedSpaceOperations:

    def __init__(self, model):
        self.model = model
        self._graph = SpaceGraph()

    def _can_add(self, parent, name, klass):
        """Check name conflict for a given name.

        :obj:`False` if ``name`` is already defined not
        as an instance of ``klass``
        in ``parent`` or in any of ``parent`` descendants.
        :obj:`False` if ``name`` is already defined
        as an instance of ``klass`` and ``overwirte`` is :obj:`True`,
        otherwise :obj:`True`.
        """
        # TODO: Reflect the overwriting order of names
        if parent is self.model:
            return name not in parent.namespace
        else:   # parent is a Space
            child = parent.get_attr(name)
            if child is not None:
                return not isinstance(child, Impl)

        sub = self._find_name_in_subs(parent, name, skip_self=True)   # start from parent
        if sub is None:
            return True
        elif isinstance(sub, klass):
            return True
        else:
            return False

    def _find_name_in_subs(self, parent, name, skip_self=False):
        for subspace in self._get_subs(parent, skip_self=skip_self):
            child = subspace.get_attr(name)
            if child is not None:
                return child
        return None

    def _get_space_bases(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        nodes = self._graph.get_mro(space.idstr)[idx:]
        return [self._graph.to_space(n) for n in nodes]

    def get_deriv_bases(self, deriv: Derivable, defined_only=False,
                        graph: SpaceGraph=None):
        if graph is None:
            graph = self._graph

        if isinstance(deriv, UserSpaceImpl):    # Not Dynamic spaces
            return self._get_space_bases(deriv, graph)

        pnode = deriv.parent.idstr

        bases = []
        for bspace in graph.get_mro(pnode)[1:]:
            base_members = deriv._get_members(graph.to_space(bspace))
            if deriv.name in base_members:
                b = base_members[deriv.name]
                if not defined_only or b.is_defined():
                    bases.append(b)

        return bases

    def get_direct_bases(self, space):
        node = space.idstr
        preds = self._graph.ordered_preds(node)
        return [self._graph.to_space(n) for n in preds]

    def update_subs(self, space, skip_self=True):

        for attr in ("cells", "own_refs"):
            for s in self._get_subs(space, skip_self):
                b = self._get_space_bases(s, self._graph)
                s.on_inherit(self, b, attr)

    def _get_subs(self, space, skip_self=True):
        idx = 1 if skip_self else 0
        return [
            self._graph.to_space(desc) for desc in list(
                self._graph.ordered_subs(space.idstr))[idx:]
        ]

    def get_relative_interface(self, parent, base):

        basespace = base.parent.idstr
        basevalue = base.interface._impl.idstr

        subimpl = self._graph.get_relative(
            parent.idstr, basespace, basevalue)

        if subimpl:
            impl = self.model.get_impl_from_name(subimpl)
            if impl:
                return True, impl.interface
            else:
                return True, base.interface._impl.interface_cls(null_impl)
        else:
            return False, base.interface


class SpaceManager(SharedSpaceOperations):

    def rename_space(self, space, name):

        # Check name does not exit already
        parent = space.parent
        if not self._can_add(
                parent, name, UserSpaceImpl):
            raise ValueError("Cannot rename '%s' to '%s'" % (space.name, name))

        # Create name mapping
        mapping = {}
        old_id = tuple(space.idstr.split("."))
        new_id = old_id[:-1] + (name,)
        for node in self._graph.visit_tree(
                space.idstr, include_self=True):

            old_child = tuple(node.split("."))
            assert old_id == old_child[:len(old_id)]
            mapping[node] = ".".join(new_id + old_child[len(new_id):])

        if not space.parent.is_model():
            # Clear parent's dynsub, not s's
            space.parent.clear_subs_rootitems()

        # Call on_rename callbacks
        space.on_rename(name)

        # Rename nodes
        nx.relabel_nodes(self._graph, mapping, copy=False)

    def del_cells(self, space, name):
        cells = space.cells[name]
        if cells.is_derived():
            raise ValueError("cannot delete derived")
        space.on_del_cells(name)
        self.update_subs(space, skip_self=False)

    def del_ref(self, space, name):
        space.on_del_ref(name)
        self.update_subs(space, skip_self=False)

    def new_cells(self, space, name=None, formula=None, data=None,
                  is_derived=False, is_cached=True, edit_source=True):

        # FIX: Creating a Cells of the same name in ``space``

        if not self._can_add(space, name, CellsImpl):
            raise ValueError("Cannot create cells '%s'" % name)

        cells = UserCellsImpl(
            space=space, name=name, formula=formula,
            data=data, is_derived=is_derived, is_cached=is_cached, edit_source=edit_source)
        space.clear_subs_rootitems()

        name = cells.name   # If name is none, auto-named in __init__

        for subspace in self._get_subs(space):
            if name in subspace.cells:
                continue
            else:
                subspace.clear_subs_rootitems()
                derived = UserCellsImpl(
                    space=subspace,
                    base=cells, is_derived=True, add_to_space=False,
                    is_cached=is_cached
                )
                base_cells = {}
                for b in reversed(subspace.bases):
                    base_cells.update(b.cells)

                idx = list(base_cells).index(name)
                cells_after = list(subspace.cells)[idx:]
                subspace.cells[name] = derived
                subspace.on_notify(subspace.cells)

                for k in cells_after:
                    subspace.cells[k] = subspace.cells.pop(k)

        return cells

    def copy_cells(self, space: UserSpaceImpl,
                   source: UserCellsImpl, name=None):
        """``space`` can be of another Model"""

        if space.model is not self.model:
            return space.spmgr.copy_cells(space, source, name)

        if name is None:
            name = source.name

        data = {k: v for k, v in source.data.items() if k in source.input_keys}
        return self.new_cells(space, name=name, formula=source.formula,
                       data=data, is_derived=False)

    def rename_cells(self, cells, name):
        """Renames the Cells name"""
        if not is_valid_name(name):
            raise ValueError("name '%s' is invalid" % name)

        if not self._can_add(cells.parent, name, CellsImpl):
            raise ValueError("cannot create cells '%s'" % name)

        if cells.bases:
            raise ValueError("'%s' is a sub Cells of '%s'" % (
                cells.get_repr(fullname=True, add_params=False),
                cells.bases[0].get_repr(fullname=True, add_params=False)))

        old_name = cells.name

        for space in self._get_subs(cells.parent, skip_self=False):
            space.clear_subs_rootitems()
            space.cells[old_name].on_rename(name)

    def sort_cells(self, space):
        """Sort cells in a space

        - Applies only to defined UserSpaces
        - Only cells defined in the space (neither derived/overridden)
          are sorted and placed before the derived/overridden cells.
        - Derived/overridden cells in the sub spaces are also sorted.
        """
        for subspace in self._get_subs(space, skip_self=False):
            subspace.on_sort_cells(space=space)

    def set_cells_property(self, cells, flags, func, enable_cache):
        """Set formula and/or is_enabled"""
        define = True
        for space in self._get_subs(cells.parent, skip_self=False):
            c = space.cells[cells.name]
            if (c is not cells and c.is_defined() and
                    self.get_deriv_bases(c, defined_only=True)[0] is cells):
                continue   # Skip when c's base is not cells
            space.clear_subs_rootitems()
            space.cells[cells.name].on_set_property(
                flags, define, func, enable_cache
            )
            define = False  # Do not define derived cells

    def set_cells_formula(self, cells, func):
        self.set_cells_property(cells, UserCellsImpl.PROP_FORMULA, func, True)

    def set_cache(self, cells, enable_cache):
        self.set_cells_property(cells, UserCellsImpl.PROP_CACHE, None, enable_cache)

    def del_cells_formula(self, cells):
        self.set_cells_formula(cells, NULL_FORMULA)

    def _check_subs_relrefs(self, space, name, value, refmode):

        # Check if relative ref is possible when refmode is 'relative'
        if isinstance(value, Interface) and refmode == "relative":
            basevalue = value._impl.idstr
            for subspace in self._get_subs(space):
                if name in subspace.own_refs:
                    break
                else:
                    subvalue = self._graph.get_relative(
                        subspace.idstr, space.idstr,
                        basevalue)
                    if not subvalue:
                        raise ValueError(
                            "Cannot create relative reference for '%s' in '%s'"
                            % (basevalue, subspace.idstr)
                        )

    def new_ref(self, space, name, value, refmode):

        other = self._find_name_in_subs(space, name)
        if other is not None:
            if not isinstance(other, ReferenceImpl):
                raise ValueError("Cannot create reference '%s'" % name)
            elif other not in self.model.global_refs.values():
                raise ValueError("Cannot create reference '%s'" % name)

        self._check_subs_relrefs(space, name, value, refmode)
        result = space.on_create_ref(name, value, is_derived=False,
                            refmode=refmode)

        for subspace in self._get_subs(space):
            is_relative = False
            if name in subspace.own_refs:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = self.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = subspace.on_create_ref(name, value, is_derived=True,
                                   refmode=refmode)
            ref.is_relative = is_relative

        return result

    def change_ref(self, space, name, value, refmode):
        """Assigns a new value to an existing name."""

        self._check_subs_relrefs(space, name, value, refmode)
        # self._set_defined(space.idstr)
        # space.set_defined()

        is_relative = False if refmode == "absolute" else True

        space.on_change_ref(name, value, is_derived=False, refmode=refmode,
                            is_relative=is_relative)

        for subspace in self._get_subs(space):
            is_relative = False
            subref = subspace.own_refs[name]
            if subref.is_defined():
                break
            elif subref.defined_bases[0] is not space.own_refs[name]:
                break
            if isinstance(value, Interface) and value._is_valid():
                if (refmode == "auto"
                        or refmode == "relative"):
                    is_relative, value = self.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = subspace.on_change_ref(name, value,
                                         is_derived=True, refmode=refmode,
                                         is_relative=is_relative)
            ref.is_relative = is_relative

    def _check_sanity(self):

        nodes = set(self._graph.nodes)
        spaces = dict(self.model.named_spaces)

        # consistency between spaces and nodes
        while spaces:
            k, v = spaces.popitem()
            assert k == v.name
            assert v.idstr in nodes
            assert v is self._graph.nodes[v.idstr]["space"]
            nodes.remove(v.idstr)
            spaces.update(v.named_spaces)

        assert not nodes # Check all nodes are reached


class SpaceUpdater(SharedSpaceOperations):

    def __init__(self, manager):
        self.manager = manager
        super().__init__(manager.model)

        self._instructions = InstructionList()
        self._graph = self.manager._graph.copy()

    def _update_manager(self):

        self.manager._graph = self._graph

    def _update_derived_space(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        space.on_inherit(self, bases, 'cells')
        self._instructions.append(
            Instruction(self._update_derived_refs, (node,))
        )

    def _update_derived_refs(self, node):
        space = self._graph.to_space(node)
        bases = self._get_space_bases(space, self._graph)
        space.on_inherit(self, bases, 'own_refs')

    def _remove_hook(self, graph, node):

        parent_node, name = split_node(node)

        if parent_node in self.manager._graph:
            parent = self.manager._graph.to_space(parent_node)
        elif parent_node:
            parent = graph.to_space(parent_node)
        else:
            parent = self.model

        method = parent.on_del_space

        self._instructions.append(
            Instruction(method, (name,))
        )

    def new_space(
            self,
            parent,
            name=None,
            bases=None,
            formula=None,
            refs=None,
            source=None,
            prefix="",
            doc=None
    ):
        """Create a new child space.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            formula: Function whose parameters used to set space parameters.
            refs: a mapping of refs to be added.
            source: A source module from which cell definitions are read.
            prefix: Prefix to the autogenerated name when name is None.
        """
        if name is None:
            while True:
                name = parent.spacenamer.get_next(parent.namespace, prefix)
                if self.manager._can_add(parent, name, UserSpaceImpl):
                    break

        elif not self.manager._can_add(parent, name, UserSpaceImpl):
            raise ValueError("Cannot create space '%s'" % name)

        if not prefix and not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        if bases is None:
            bases = []
        elif isinstance(bases, UserSpaceImpl):
            bases = [bases]

        node = name if parent.is_model() else parent.idstr + "." + name

        spaces = [s for s in bases]
        if not parent.is_model():
            spaces.insert(0, parent)

        self._graph.add_node(node)

        for b in bases:
            base = b.idstr
            self._graph.add_edge(
                base,
                node,
                level=0,
                index=self._graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

        self._graph.get_mro(node)  # Check if MRO is possible

        # Check if MRO is possible for each node in sub graph
        for n in nx.descendants(self._graph, node):
            self._graph.get_mro(n)

        space = UserSpaceImpl(
            parent,
            name,
            container=parent.named_spaces,
            formula=formula,
            refs=refs,
            source=source,
            doc=doc
        )

        if isinstance(parent, NamespaceServer):
            parent.on_notify(parent.named_spaces)   # Fix: bug GH203

        self._graph.nodes[node]["space"] = space
        self._graph.nodes[node]["state"] = "created"

        self._instructions.append(
            Instruction(self._update_derived_space, (node,)))
        for _,  v in nx.edge_dfs(self._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,)))

        try:
            self._instructions.execute()
        except BaseException:
            del parent.named_spaces[name]
            raise

        self._update_manager()

        return space

    def add_bases(self, space, bases):
        """Add bases to space in graph
        """
        node = space.idstr
        basenodes = [base.idstr for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            self._graph.add_edge(
                b,
                node,
                level=0,
                index=self._graph.max_index(node) + 1
            )

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("cyclic inheritance")

        for n in itertools.chain({node}, nx.descendants(
                self._graph, node)):
            self._graph.get_mro(n)

        for desc in itertools.chain(
                {node},
                nx.descendants(self._graph, node)):

            mro = self._graph.get_mro(desc)

            # Check name conflict between spaces, cells, refs
            members = {}
            for attr in ["spaces", "cells", "refs"]:
                namechain = []
                for sname in mro:
                    space = self._graph.to_space(sname)
                    namechain.append(set(getattr(space, attr).keys()))
                members[attr] = set().union(*namechain)

            conflict = set().intersection(*[n for n in members.values()])
            if conflict:
                raise NameError("name conflict: %s" % conflict)

        self._instructions.append(
            Instruction(self._update_derived_space, (node,)))
        for _,  v in nx.edge_dfs(self._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,)))

        self._instructions.execute()
        self._update_manager()

    def remove_bases(self, space, bases):

        node = space.idstr
        basenodes = [base.idstr for base in bases]

        for base in [node] + basenodes:
            if base not in self.manager._graph:
                raise ValueError("Space '%s' not found" % base)

        for b in basenodes:
            self._graph.remove_edge(b, node)

        self._instructions.append(
            Instruction(self._update_derived_space, (node,))
        )
        for _, v in nx.edge_bfs(self.manager._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,))
            )

        self._instructions.execute()
        self._update_manager()

    def del_defined_space(self, space):

        node = space.idstr

        if node not in self.manager._graph:
            raise ValueError("Space '%s' not found" % node)

        # Remove node and its child tree
        nodes_removed = list()
        for child in self._graph.visit_tree(node):
            nodes_removed.append(child)
            self._remove_hook(self._graph, child)

        for _, v in nx.edge_bfs(self.manager._graph, node):
            self._instructions.append(
                Instruction(self._update_derived_space, (v,))
            )

        self._graph.remove_nodes_from(nodes_removed)

        self._instructions.execute()
        self._update_manager()

        if space is self.model.currentspace:
            self.model.currentspace = None

    def copy_space(
            self,
            parent: EditableParentImpl,
            source: UserSpaceImpl,
            name=None,
            defined_only=False
    ):
        if parent.has_ascendant(source):
            raise ValueError("Cannot copy to child")

        if parent.model is not self.model:
            return parent.model.updater.copy_space(
                parent, source, name, defined_only)

        if name is None:
            name = source.name

        if self.manager._can_add(
            parent, name, EditableParentImpl):
            return self._copy_space_recursively(
                parent, source, name, defined_only
            )
        else:
            raise ValueError("Cannot create space '%s'" % name)

    def _copy_space_recursively(
            self, parent, source, name, defined_only):

        space = self.new_space(
            parent,
            name=name,
            bases=None,
            formula=source.formula,
            refs={k: v.interface for k, v in source.own_refs.items()},
            source=source.source,
            prefix="",
            doc=source.doc
        )

        for cells in source.cells.values():
            if cells.is_defined():
                self.manager.copy_cells(space, cells)

        for child in source.named_spaces.values():
            self._copy_space_recursively(
                space, child, child.name, defined_only)

        return space


class ReferenceManager:

    def __init__(self, model, iomanager):
        self._model = model
        self._manager = iomanager
        self._valid_to_refs = {}         # id(value) -> [refs]

    def _check_sanity(self):

        for refs in self._valid_to_refs.values():
            for r in refs:
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=r.interface)
                if spec is not None:
                    assert r.interface is spec.value
                    spec._check_sanity()

    def has_spec(self, value):
        spec = self._manager.get_spec_from_value(self._model.interface, value)
        return spec is not None

    def get_spec(self, value):
        return self._manager.get_spec_from_value(self._model.interface, value)

    @property
    def values(self):
        return list(ref[0].interface for ref in self._valid_to_refs.values())

    @property
    def specs(self):
        result = []
        for r in self._valid_to_refs.values():
            spec = self.get_spec(r[0].interface)
            if spec is not None:
                result.append(spec)
        return result

    def new_ref(self, impl, name, value, refmode):

        if isinstance(impl, ModelImpl):
            ref = impl.new_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            ref = impl.model.spmgr.new_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(value, Interface):
            refs = self._valid_to_refs.setdefault(id(value), [])
            assert all(ref is not r for r in refs)
            refs.append(ref)

    def del_ref(self, impl, name):

        refdict = impl.own_refs
        ref = refdict[name]
        valid = id(ref.interface)
        val = ref.interface

        if isinstance(impl, ModelImpl):
            impl.del_ref(name)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.del_ref(impl, name)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(val, Interface):
            refs = self._valid_to_refs.get(valid)
            assert refs
            refs.remove(ref)
            if not refs:
                del self._valid_to_refs[valid]
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=val
                )
                if spec:
                    self._manager.del_spec(spec)

    def change_ref(self, impl, name, value, refmode=None):

        refdict = impl.own_refs
        prev_ref = refdict[name]
        prev_valid = id(prev_ref.interface)
        prev_val = prev_ref.interface

        if isinstance(impl, ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        refs = self._valid_to_refs.get(prev_valid, None)
        if refs is not None:        # None in case prev_ref is derived
            if prev_ref in refs:
                refs.remove(prev_ref)
            if not refs:    # ref is empty
                del self._valid_to_refs[prev_valid]
                spec = self._manager.get_spec_from_value(self._model.interface, prev_val)
                if spec:
                    self._manager.del_spec(spec)

        if not isinstance(value, Interface):
            self._valid_to_refs.setdefault(id(value), []).append(refdict[name])

    def del_all_spec(self):
        specs = self.specs.copy()
        while specs:
            self._manager.del_spec(specs.pop())

    def update_value(self, old_value, new_value=None, **kwargs):

        prev_id = id(old_value)
        refs = self._valid_to_refs.get(prev_id, None)
        spec = self._manager.get_spec_from_value(self._model.interface, old_value)

        if refs is None:
            raise ValueError("value not referenced")

        if new_value is None:
            new_value = old_value

        if spec is not None:
            self._manager.update_spec_value(spec, new_value, kwargs)
            new_value = spec.value

        newrefs = []
        while refs:
            ref = refs.pop()
            impl = ref.parent
            name = ref.name
            refmode = ref.refmode
            value = new_value
            self._impl_change_ref(impl, name, value, refmode)
            newrefs.append(impl.own_refs[name])

        self._valid_to_refs.pop(prev_id)
        self._valid_to_refs[id(new_value)] = newrefs

    @staticmethod
    def _impl_change_ref(impl, name, value, *refmode):

        if isinstance(impl, ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")
