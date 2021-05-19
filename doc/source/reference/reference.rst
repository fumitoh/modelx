Reference
===========

.. currentmodule:: modelx.core

A *Reference* is a name binding. It binds a name, such as ``foo``
to an object.
References are manually created by the user
as attributes of :class:`~space.UserSpace`::

    >>> space.foo = 1


When a Reference is created as an attribute of a :class:`~space.UserSpace`,
the name becomes available in the namespace associated with the
:class:`~space.UserSpace`.
The Formulas of child :class:`~cells.Cells` of the
:class:`~space.UserSpace` are evaluated in the namespace,
so the name that appears in the Formulas refers to the object
that the name is bound to by the Reference.
Continuing with the above example,
suppose a Cells ``baz`` is defiened in the same Space ``space`` as
``foo``::

    >>> space.baz.formula
    def baz():
        return foo

The ``foo`` in the ``baz`` definition referes to ``1``::

    >>> space.baz()
    1

References can also be created as attributes of :class:`~model.Model` objects.
Such References become accessible from any Space in the Model.
Suppose ``model`` is a :class:`~model.Model`  object
and the parent of ``space``::

    >>> model.bar = "bar"

``bar`` defined above is also defined in ``space``::

    >>> space.bar
    'bar'

And ``bar`` can be referred to from the Formulas of child
:class:`~cells.Cells` of ``model``::

    >>> def baz():
    ...     return bar

    >>> space.baz = baz

    >>> space.baz.formula
    def baz():
        return bar

    >>> space.baz()
    'bar'

Reference objects themselves are hidden from the user,
and the bound objects are always referenced by the names.
To access the attributes of
Reference objects, :class:`~reference.ReferenceProxy` objects are used.

ReferenceProxy
---------------

.. currentmodule:: modelx.core.reference

.. autoclass:: ReferenceProxy

Attributes
^^^^^^^^^^

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~ReferenceProxy.value
  ~ReferenceProxy.refmode

