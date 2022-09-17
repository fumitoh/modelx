==================================
modelx v0.20.0 (17 September 2022)
==================================

This release introduces the following enhancements, changes and bug fixes.

To update modelx, run the following command::

    >>> pip install modelx --upgrade

If you're using Anaconda, use the ``conda`` command instead::

    >>> conda update modelx

If you're using the Spyder plugin for modelx, the
:doc:`spymx-kernels<spymx_kernels_relnotes>` pakcage is also updated,
so update it as well by either::

    >>> pip install smymx-kernels --upgrade

or on Anaconda,

    >>> conda update spymx-kernels


Enhancements
============

.. py:currentmodule:: modelx.core

Saving multiple pandas DataFrame and Series objects in one Excel file
----------------------------------------------------------------------
Prior to v0.20.0, pandas DataFrame and Series objects
referenced in a model are written to separate files when the model is saved.

With modelx v0.20.0, :meth:`Model.new_pandas<model.Model.new_pandas>` and
:meth:`UserSpace.new_pandas<space.UserSpace.new_pandas>`
have the ``sheet`` parameter to indicate the name of the sheet the
pandas object is written on.
This enables multiple pandas objects to be written to separate sheets
in the same Excel file.


New methods and properties for *IOSpec* operations
---------------------------------------------------
.. py:currentmodule:: modelx.io

*IOSpec* objects are those whose types are derived from
:class:`~baseio.BaseIOSpec`,
such as :class:`~pandasio.PandasData` and :class:`~moduleio.ModuleData`.
*IOSpec* objects are associated with data objects referenced in models,
and specify how the data objects should be written to files.

The methods and properties below are introduced to
handle *IOSpec* objects.

.. py:currentmodule:: modelx

* :meth:`Model.get_spec<core.model.Model.get_spec>` method is introduced.
* :meth:`Model.del_spec<core.model.Model.del_spec>` method is introduced.
* :attr:`BaseSpecIO.path<io.baseio.BaseIOSpec.path>` property is introduced.
* :attr:`PandasData.sheet<io.pandasio.PandasData.sheet>` property is introduced.


Backward Incompatible Changes
=============================

Deprecated old methods
------------------------

.. py:currentmodule:: modelx.core

From v0.20.0, the following methods are deprecated.
These methods were introduced in early versions of modelx
long before the intoduction of
:meth:`Model.new_pandas<model.Model.new_pandas>` and
:meth:`UserSpace.new_pandas<space.UserSpace.new_pandas>`.
Instead of using these methods, consider using
:meth:`Model.new_pandas<model.Model.new_pandas>` and
:meth:`UserSpace.new_pandas<space.UserSpace.new_pandas>` for storing data in models.

* :meth:`Model.new_space_from_excel<model.Model.new_space_from_excel>`
* :meth:`UserSpace.new_space_from_excel<space.UserSpace.new_space_from_excel>`
* :meth:`Model.new_space_from_pandas<model.Model.new_space_from_pandas>`
* :meth:`UserSpace.new_space_from_pandas<space.UserSpace.new_space_from_pandas>`
* :meth:`Model.new_space_from_csv<model.Model.new_space_from_csv>`
* :meth:`UserSpace.new_space_from_csv<space.UserSpace.new_space_from_csv>`
* :meth:`UserSpace.new_cells_from_excel<space.UserSpace.new_cells_from_excel>`
* :meth:`UserSpace.new_cells_from_pandas<space.UserSpace.new_cells_from_pandas>`


Removed methods
------------------
The following methods are removed from :class:`~space.UserSpace`.
The user should use :meth:`Model.update_pandas<model.Model.update_pandas>`
and :meth:`Model.update_module<model.Model.update_module>` instead.

* ``UserSpace.update_pandas``
* ``UserSpace.update_module``


Renamed classes and methods
----------------------------

* ``BaseDataSpec`` is renamed to :class:`~modelx.io.baseio.BaseIOSpec`.
* ``Model.dataspecs`` is renamed to :attr:`Model.iospecs<model.Model.iospecs>`.


Other changes
-------------
* The ``filetype`` parameter of
  :meth:`Model.new_pandas<model.Model.new_pandas>` and
  :meth:`UserSpace.new_pandas<space.UserSpace.new_pandas>`
  is deprecated and ``file_type`` is introduced to replace it.


Bug Fixes
============

* Bug in changing the formula of a cells in a base space where
  the derived cells of the cells were defined in sub spaces of the base space.

* Deprecation warning on reading Series.
