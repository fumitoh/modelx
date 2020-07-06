

===============================
modelx v0.8.0 (6 July 2020)
===============================

This release introduces new methods to copy Spaces and Cells,
functions and methods to save models to zip files, and
a feature to output input values to a log file.

Enhancements
============
.. py:currentmodule:: modelx

.. rubric:: Introduction of copy methods

The :meth:`UserSpace.copy<modelx.core.space.UserSpace.copy>` and
:meth:`Cells.copy<modelx.core.cells.Cells.copy>` methods are introduced.

.. rubric:: Writing/reading models to/from zip files (`GH33`_)

The new :func:`~zip_model` function and
:meth:`Model.zip<modelx.core.model.Model.zip>` method work exactly the same
as :func:`~write_model` and :meth:`Model.write<modelx.core.model.Model.write>`,
except that they write a model into a zip file.
The contents of the zip file is identical to the contents of a folder output by
:func:`~write_model` or :meth:`Model.write<modelx.core.model.Model.write>`,
i.e. unzipping the zip file produces the same files and folders
as the folders and files output by :func:`~write_model`
or :meth:`Model.write<modelx.core.model.Model.write>`.

.. rubric:: Input value logging (`GH32`_)

When writing a model, input values in Cells are stored in a binary file
with their object IDs.
The object IDs change every time the same model is written,
even though the input values themselves have not changed.
So it is not possible to know whether the input values have changed or not
just by looking at the output files.
To compensate for this limitation, a feature to output
the string representations of Cells input keys values
is introduced, as a parameter of the write and zip methods and functions.


:func:`~write_model`, :meth:`Model.write<modelx.core.model.Model.write>`,
the new :func:`~zip_model` function and
:meth:`Model.zip<modelx.core.model.Model.zip>` method now have
a parameter ``log_input``. If ``True`` is given, the string representations
of Cells input keys and values are output in a file named *_input_log.txt*
under the model folder.

The sample code below writes a model into a *model* folder and output
*_input_log.txt* under the *model* folder.

.. code-block::

    import modelx as mx

    m = mx.new_model()

    @mx.defcells
    def foo(x):
        return x

    foo[0] = 1
    foo[1] = "foo"

    m.write("model", log_input=True)

Below is the contents of *_input_log.txt* under the *model* folder::

    Space1.foo(x=0)=1
    Space1.foo(x=1)='foo'


.. _GH33: https://github.com/fumitoh/modelx/issues/33

.. _GH32: https://github.com/fumitoh/modelx/issues/32