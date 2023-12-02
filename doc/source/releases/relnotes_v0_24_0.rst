==================================
modelx v0.24.0 (2 December 2023)
==================================

This release introduces several backward-incompatible changes.


To update to modelx v0.24.0, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Backward Incompatible Changes
==============================

1. Changes in Inheritance Behavior of UserSpaces with Child Spaces
------------------------------------------------------------------

In previous versions,
inheriting from a UserSpace with child spaces automatically included
those child spaces in the inheritance.

Starting from v0.24.0, child spaces are no longer inherited by default.
Consider the following example:

.. code-block::

    import modelx as mx

    m = mx.new_model("m")
    A = m.new_space("A")
    B = A.new_space("B")
    foo = A.new_cells("foo", formula=lambda x: x)
    C = m.new_space("C", bases=A)

    C.B    # Now raises AttributionError


Previously, creating a new space `C` inheriting from `A`
would automatically copy `B`, a child space of `A`, in `C`.
The updated behavior changes this; `B` is no longer inherited automatically.
The figure below compares the behavior before and after the change.

.. figure:: /images/relnotes/v0_24_0/UpdatedBehavior.png

To inherit `B` in `C`, you need to explicitly create a new space in `C`
and inherit from `B`.

.. code-block::

    C.new_space('B', bases=B)

Note: This change does not affect dynamic spaces.
Dynamic child spaces of a parameterized space are still copied:

.. code-block::

   A.parameters = ("i",)
   A[1].B   # Returns <DynamicSpace m.A[1].B>


2. Removal of Deprecated Backup and Restore Functions
-----------------------------------------------------

The backup and restore feature has been deprecated and is now removed.
The following functions and methods are no longer available:

* ``restore_model``
* ``open_model``
* ``Model.backup``
* ``Model.save``





