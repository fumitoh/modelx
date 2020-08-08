
===============================
modelx v0.9.0 (9 Aug 2020)
===============================

This release introduces the following
enhancements and changes.

Enhancements
============

.. rubric:: Introduction of new interface to Excel files

The :meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>`
and :meth:`UserSpace.new_excel_range<modelx.core.space.UserSpace.new_excel_range>`
methods are introduced. These methods create newly introduced
:class:`~modelx.io.excelio.ExcelRange`
objects and assign the objects to References.
:class:`~modelx.io.excelio.ExcelRange`
objects act like :obj:`dict` and the user can get and
set values by the subscription operation (``[]``).
Excel files accessed through :class:`~modelx.io.excelio.ExcelRange`
objects are saved inside
model folders, or outside of the model folders.

.. rubric:: ZIP file compression (`GH36`_)

Models written to ZIP files by
:func:`~modelx.zip_model` function or :meth:`~modelx.core.model.Model.zip`
method
are now compressed by default. The compression can be configured by
newly introduced ``compression`` and ``compresslevel`` parameters.

.. _GH36: https://github.com/fumitoh/modelx/issues/36


.. rubric:: Updated serializer

The serializer is updated and the structure of the model folders
is different from the previous version.
The updated serializer writes Model information
to *__init__.py* directly under the model folder.
The updated serializer creates a folder for each UserSpace with
the same name as the UserSpace,
and output information about the UserSpace
to *__init__.py* files under the folder.
The serializer puts data files under folders named *_data*.
Models output by older versions are also supported.


Backward Incompatible Changes
=============================


.. rubric:: Text files are output in UTF-8

Text files output by functions or methods to write Models,
such as :func:`~modelx.write_model` are now all in UTF-8.
Previously, text files were output in operating system's default
encoding for the most part, and some were in UTF-8.

