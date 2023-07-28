==================================
modelx v0.22.0 (29 July 2023)
==================================

This release introduces the following enhancements, bug fixes and changes.


To update modelx, run the following command::

    >>> pip install modelx --upgrade

If you're using Anaconda, use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
============

.. py:currentmodule:: modelx

Introduction of the Export feature
----------------------------------

This release introduce an experimental export feature that
allows users to export modelx models as self-contained Python packages.
The feature is available as an API function or a method on the Model class:

* :func:`export_model`
* :meth:`Model.export<core.model.Model.export>`

They both function the same.

.. seealso:: `New Feature: Export Models as Self-contained Python Packages <https://modelx.io/blog/2023/07/27/export-feature-intro/>`_ , a blog post on https://modelx.io

An option to report local variables in error trace
-----------------------------------------------------

:func:`get_traceback` now has an option ``show_locals``, to indicate
whether the tracebacks should report the values of local variables.
It is set to ``False`` by default.


Bug Fixes
============

* Fix error when writing multiple models with the same files (`GH81 <https://github.com/fumitoh/modelx/issues/81>`_)
* Fix error with OpenPyXL 3.1+
* Fix error in trace_locals


Changes
==========

* The following methods are now deprecated and
  they simply call their corresponding construction methods and assign input values from the files.
  They no longer carry the metadata of their input files to store the data in separate files.

  - :meth:`Model.new_space_from_excel<core.model.Model.new_space_from_excel>`
  - :meth:`Model.new_space_from_csv<core.model.Model.new_space_from_csv>`
  - :meth:`Model.new_space_from_pandas<core.model.Model.new_space_from_pandas>`
  - :meth:`UserSpace.new_space_from_excel<core.space.UserSpace.new_space_from_excel>`
  - :meth:`UserSpace.new_space_from_csv<core.space.UserSpace.new_space_from_csv>`
  - :meth:`UserSpace.new_space_from_pandas<core.space.UserSpace.new_space_from_pandas>`
  - :meth:`UserSpace.new_cells_from_excel<core.space.UserSpace.new_cells_from_excel>`
  - :meth:`UserSpace.new_cells_from_csv<core.space.UserSpace.new_cells_from_csv>`
  - :meth:`UserSpace.new_cells_from_pandas<core.space.UserSpace.new_cells_from_pandas>`


* :func:`get_traceback` now reports local variables only when ``show_locals`` is ``True``.

* modelx now depends on `LibCST <https://libcst.readthedocs.io/en/latest/>`_.

