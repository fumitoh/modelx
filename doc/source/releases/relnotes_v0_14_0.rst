.. currentmodule:: modelx

===============================
modelx v0.14.0 (2 May 2021)
===============================

This release fixes bugs and introduces enhancements as follows.

Enhancements
============

Enhanced Cells.doc property and new :meth:`~core.cells.Cells.set_doc` method  (`GH44`_)
----------------------------------------------------------------------------------------

Prior to this release :attr:`Cells.doc<core.cells.Cells.doc>`
property was read-only, and
it was linked to the docstring of the Cells's Formula, so
the property for lambda Cells was always None.

With this release, :attr:`Cells.doc<core.cells.Cells.doc>`
property now works as setter.
If a Cells has a no-lambda Formula, then the setter replaces
the docstirng of the Formula::

    >>> @mx.defcells
    ... def foo(x):
    ...     """This is foo"""
    ...     return x

    >>> foo.doc
    'This is foo'

    >>> foo.doc = "foo's doc is updated"

    >>> foo.formula
    def foo(x):
        """foo's doc is updated"""
        return x

    >>> foo.doc
    "foo's doc is updated"

When setting the docstring of a Cells
by :attr:`Cells.doc<core.cells.Cells.doc>` property,
the input string is not automatically indented::

    >>> doc = """This is foo
    ...
    ... Unindented docstring
    ... """

    >>> foo.doc = doc

    >>> foo.formula
    def foo(x):
        """This is foo

    Unindented docstring
    """
        return x

The newly introduced :meth:`Cells.set_doc<core.cells.Cells.set_doc>` method
has the :obj:`bool` parameter ``insert_indents``,
and if it's :obj:`True`, the second and subsequent lines of ``doc``
are auto-indented::

    >>> foo.set_doc(doc, insert_indents=True)

    >>> foo.formula
    def foo(x):
        """This is foo

        Unindented docstring
        """
        return x

If a Cells' Formula is defined by a lambda function,
the doc is kept in the Cells separately from the function::

    >>> space.new_cells(name="bar", formula=lambda x: x)
    <Cells Model1.Space1.bar(x)>

    >>> space.bar.doc = "I am bar"

    >>> space.bar.doc
    'I am bar'

.. seealso::

    :attr:`Cells.doc<core.cells.Cells.doc>`
    :meth:`Cells.set_doc<core.cells.Cells.set_doc>`


modelx version saved in *_system.json*
---------------------------------------

When a Model is written to files by
:meth:`Model.write<core.model.Model.write>`,
:func:`~write_model`, :meth:`Model.zip<core.model.Model.zip>`,
or :func:`~zip_model`, the version of the modelx is output
in *_system.json* in addition to the serizalizer version.


Bug Fixes
=========

* :attr:`Model.doc<core.model.Model.doc>` was mistakenly treated
  as a Reference.

* Fixed an error on rebinding a Reference that is referenced
  directly and indirectly by multiple Cells (`GH43`_).

* Fixed an error that was raised when a model was saved, if the model
  had saved previously by
  :func:`~zip_model` or :meth:`Model.zip<core.model.Model.zip>`
  and if the model contained
  a module created by :meth:`~core.space.UserSpace.new_module` (`GH45`_).

* On creating a new Space by :func:`~new_space`, :func:`~cur_model` is
  set to the Space's Model.

.. _GH43: https://github.com/fumitoh/modelx/issues/43
.. _GH44: https://github.com/fumitoh/modelx/issues/44
.. _GH45: https://github.com/fumitoh/modelx/issues/45

