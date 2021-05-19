.. currentmodule:: modelx.core

===============================
modelx v0.15.0 (19 May 2021)
===============================

This release fixes bugs and introduces enhancements as follows.

Enhancements
============

Introduction of precedents method for tracing Reference values
---------------------------------------------------------------

A new method :meth:`~cells.Cells.precedents` is introduced.
The existing :meth:`~cells.Cells.preds` method returns a list of
nodes that the specified node depends on for calculating its value.
The :meth:`~cells.Cells.preds` only lists nodes of Cells and Spaces.
The newly introduced :meth:`~cells.Cells.precedents`
method enhances :meth:`~cells.Cells.preds`.
In addition to the nodes of Cells and Spaces returned by :meth:`~cells.Cells.preds`,
the :meth:`~cells.Cells.precedents` also includes nodes of Reference values that are
used by the specified node's calculation.
Here's an example.

.. code-block:: python

    import modelx as mx

    space = mx.new_space()
    space.new_space('Child')
    space.Child.new_space('GrandChild')

    space.x = 1
    space.Child.y = 2
    space.Child.GrandChild.z = 3

    @mx.defcells(space=space)
    def foo(t):
        return t

    @mx.defcells(space=space)
    def bar(t):
        return foo(t) + x + Child.y + Child.GrandChild.z


The ``bar`` Cells depends on one Cells ``foo``, and 3 References, ``x``,
``Child.y``, and ``Child.GrandChild.z``.
Below, ``bar.preds(3)`` returns a list containing ``foo(3)``,
which is the only Cells element that ``bar(3)`` depends on::

    >>> bar(3)
    9

    >>> bar.preds(3)
    [Model1.Space1.foo(t=3)=3]

The :meth:`~cells.Cells.precedents` method returns a list containing not only Cells elements,
but also References that the Cells depends on when calculating its value::

    >>> bar.precedents(3)
    [Model1.Space1.foo(t=3)=3,
     Model1.Space1.x=1,
     Model1.Space1.Child.GrandChild.z=3,
     Model1.Space1.Child.y=2]


Similarly to :meth:`Cells.precedents<cells.Cells.precedents>`,
:meth:`Space.precedents<space.UserSpace.precedents>`
is also introduced, which extends the
:meth:`Space.preds<space.UserSpace.preds>` in the same way.

Improved Multi-line repr of nodes
----------------------------------
The elements of lists returned by
:meth:`~cells.Cells.precedents`, :meth:`~cells.Cells.succs`
and :meth:`~cells.Cells.preds` are :class:`Node<node.BaseNode>`
objects and
can have numpy arrays and pandas DataFrames as their values. These values
have multi-line representation strings (repr). To print such
reprs nicely, a line break is inserted between the ``=`` and
the value's repr::

    Model1.Space1.Cells1()=
    array([[1, 2],
           [3, 4]])


Backward Incompatible Changes
=============================

* :class:`Element` is renamed to :class:`~node.ItemNode`.


Bug Fixes
=========

MacOS incompatibility
---------------------
Recent MacOS does not seem to allow changing stack size at runtime.
To avoid error on changing the stack size at modelx invocation,
modelx is refactored to use an executor in the main thread
for Linux and MaxOS.
Because of this change, the maximum number of recursion
on MacOS is made significantly lower than that of Linux's and Windows'.
