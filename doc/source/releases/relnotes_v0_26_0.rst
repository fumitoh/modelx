==================================
modelx v0.26.0 (15 July 2024)
==================================

This release introduces the following enhancements.

To update to modelx v0.25.0, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============


``_parent`` and ``_name`` properties added to Model, Space and Cells
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``_parent`` and ``_name`` properties are added to
Model, Space and Cells, as aliases to ``parent`` and ``name``.
In formulas, use ``_space._parent`` and ``_sapce._name``
instead of ``_space.parent`` and ``_sapce.name``
to refer to the parent or the name of the parent space,
to make exported models work.


``_cells`` properties added to Space
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``_cells`` property is added to Space as an alies to ``cells``.
In formulas, use ``_space._cells``
instead of ``_space.cells``
to refer to the cells dictionary of the parent space,
to make exported models work.


``del UserSpace.parameters`` to delete parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now the ``del`` statement works to delete the parameters of UserSpace objects.


``del UserSpace[]`` in exported models to delete item space
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In exported model, the ``del`` statement can be used
to delete an ItemSpace, as the example shows below.
This is for freeing up the memory space used for the ItemSpace.

.. code-block:: python

    from Model_nomx import mx_model

    mx_model.Space[1]

    del mx_model.Space[1]

