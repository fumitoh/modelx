.. currentmodule:: modelx

==============================
modelx v0.0.23 (9 August 2019)
==============================

New Features
============

This release introduces methods to create Space and Cells
from Pandas objects or CSV files.

When the model is written out,
the data source Pandas objects are saved as files in the folder
of the parent space.
The CSV files are copied in the parent space folder.

**Methods to Create Cells**

* :meth:`UserSpace.new_cells_from_pandas<core.space.UserSpace.new_cells_from_pandas>`
* :meth:`UserSpace.new_cells_from_csv<core.space.UserSpace.new_cells_from_csv>`

The first method above creates one or more cells in the parent space
from a Pandas DataFrame or Series object passed as an argument.
If a DataFrame is passed, created cells correspond to
the DataFrame's columns.
The second method creates cells from a CSV file.
In either case, the created cells are populated with values read
from the date source.


**Methods to Create a Space and Cells**

* :meth:`Model.new_space_from_pandas<core.model.Model.new_space_from_pandas>`
* :meth:`UserSpace.new_space_from_pandas<core.space.UserSpace.new_space_from_pandas>`
* :meth:`Model.new_space_from_csv<core.model.Model.new_space_from_csv>`
* :meth:`UserSpace.new_space_from_csv<core.space.UserSpace.new_space_from_csv>`

Those methods above create a UserSpace in the parent object (Model or UserSpace)
from the data source (DataFrame/Series or CSV file) and
then creates one or more Cells in the created space.
The created UserSpace can have parameters by specifying which
parameters should be interpreted as Space parameters in stead of Cells
parameters.
When the UserSpace has parameters, DynamicSpaces are also created
in the UserSpace, and Cells in the DynamicSpaces are also populated
with values from the data source.


Other Enhancements
==================

* :py:func:`~write_model` and :py:func:`~read_model` now supports
  writing/reading models with multiple cells created together by
  the same execution of
  :meth:`~core.space.UserSpace.new_cells_from_excel` method.

* Added :attr:`modelx.models` attribute, an alias for :func:`get_models`

Backward Incompatible Changes
=============================
* ``StaticSpace`` is now renamed to :class:`~core.space.UserSpace`.


Bug Fixes
=========
* Fix the default values of ``names_row`` and ``param_cols`` parameters of
  :meth:`~core.space.UserSpace.new_cells_from_excel`

* Fix an error when passing a lambda function whose definition spans
  across multiple lines in a function call.
