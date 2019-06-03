.. currentmodule:: modelx

============================
modelx v0.0.22 (4 June 2019)
============================

Overview
========

The most notable improvement among others in
this release is the introduction of a new feature to write/read models
to/from text files for better version control experience.

Prior to this release,
models could only be saved("pickled") into a binary file. Maintaining models
as binary files is not ideal for version control, as it disables the use of
rich features offered by modern version control systems such as
`git <https://git-scm.com/>`_.
When you wanted to save a model as text, you needed to write
the entire python script to build the model from the source files.
Changes made to the models interactively through IPython console could not
be saved as human-readable text.

This release introduces :py:func:`~write_model` function
(or equivalent :py:meth:`~core.model.Model.write` method) and
:py:func:`~read_model` function,
to write/read a model to/from a tree of folders containing text files.

The text files created by :py:func:`~write_model` function are written
as syntactically correct Python scripts with some literals expressed
in JSON.
However, in most cases they are not semantically correct. These
files can only be interpreted through :py:func:`~read_model` function.

Another notable improvement is the extended depth of formula recursion.
Previously the maximum depth of formula recursion was set to 1000 by default.
With this release the maximum depth is extended to 65000.

Enhancements
============

* Add :py:func:`~write_model` function, :py:meth:`~core.model.Model.write` method and
  :py:func:`~read_model` function.
* The maximum depth of formula recursion is extended from 1000 to 65000 by default.
* Add ``set_property`` method to :py:class:`~core.model.Model`,
  :py:class:`~core.space.StaticSpace`,
  :py:class:`~core.cells.Cells`.
* Add ``doc`` method to :py:class:`~core.model.Model`,
  :py:class:`~core.space.StaticSpace`,
  :py:class:`~core.cells.Cells`.
* :py:meth:`~core.space.StaticSpace.new_space_from_excel` can now
  create a static space when ``space_param_order`` is not given.


Backward Incompatible Changes
=============================
* Remove :py:attr:`~core.space.StaticSpace._self_cells` and
  :py:attr:`~core.space.StaticSpace._derived_cells`
  from :py:class:`~core.space.StaticSpace`

Bug Fixes
=========
* Fix :py:meth:`~core.space.StaticSpace.add_bases` and
  :py:meth:`~core.cells.Cells.set_formula`.

