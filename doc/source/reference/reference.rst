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

.. _reference-proxy-identity:

Name, parent and docstring
^^^^^^^^^^^^^^^^^^^^^^^^^^

A ReferenceProxy answers :attr:`~ReferenceProxy.name`,
:attr:`~ReferenceProxy.fullname`, :attr:`~ReferenceProxy.parent`,
:attr:`~ReferenceProxy.model` and ``doc`` for the Reference
it stands for::

    >>> import modelx as mx

    >>> model = mx.new_model("Model1")

    >>> space = model.new_space("Space1")

    >>> space.foo = 1

    >>> model.bar = "bar"

    >>> foo = mx.get_object("Model1.Space1.foo", as_proxy=True)

    >>> foo.name, foo.fullname, foo.parent, foo.model
    ('foo', 'Model1.Space1.foo', <UserSpace Model1.Space1>, <Model Model1>)

    >>> print(foo.doc)
    None

* :attr:`~ReferenceProxy.parent` is the Space or the Model that holds
  the Reference:

  * A global Reference, which is set on a Model, has the Model as its
    parent, also when the proxy is obtained through a Space:
    ``mx.get_object("Model1.Space1.bar", as_proxy=True).parent``
    is ``Model1``.
  * A Reference that a sub Space inherits from its base Space
    has the sub Space as its parent.
  * In an :class:`~modelx.core.space.ItemSpace`, only the arguments
    and the References that the Space formula returns in ``'refs'``
    have the ItemSpace as their parent. The other References that the
    ItemSpace sees are the References of its Space, which have that
    Space as their parent, and the global References, with the
    exception in the known limitation below.

* :attr:`~ReferenceProxy.fullname` is the dotted name of the parent
  followed by the name, such as ``'Model1.Space1.foo'``,
  or ``'Model1.bar'`` for a global Reference. An ItemSpace appears in it
  under the name modelx gives it, such as ``'Model1.Space1.__Space1.i'``.

* ``doc`` is :obj:`None`. modelx creates References without docstrings:
  none of the ways to create one takes a docstring,
  and assigning to ``doc`` raises :obj:`AttributeError`.

In an ItemSpace, a Reference of its Space whose value is the Space
itself, or a Cells or a Space inside it, and whose
:attr:`~ReferenceProxy.refmode` is not ``'absolute'``,
refers to the ItemSpace's own copy of that value:
when ``Space1.rel`` is ``Space1.Child``, ``Space1[1].rel`` is
``Space1[1].Child``.

.. admonition:: Known limitation

   For such a Reference, the ReferenceProxy that
   :func:`~modelx.get_object` returns through the ItemSpace
   stands for the copy, not for the Reference:
   its :attr:`~ReferenceProxy.name`, :attr:`~ReferenceProxy.fullname`
   and :attr:`~ReferenceProxy.parent` are those of ``Space1[1].Child``,
   and :attr:`~ReferenceProxy.refmode` raises :obj:`AttributeError`.
   This is not part of the frozen contract (see :ref:`toolapi-tiers`)
   and may change.


.. _reference-proxy-refmode:

Reference modes
^^^^^^^^^^^^^^^

:attr:`~ReferenceProxy.refmode` is the mode the Reference was created
with:

* ``'auto'`` for a Reference created by assigning to an attribute of a
  :class:`~modelx.core.space.UserSpace`, as in ``space.foo = 1``,
  by :meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>` with ``'auto'``,
  or by the ``refs`` parameter of ``new_space``,
  and for a Reference that a Space formula returns in ``'refs'``;
* ``'absolute'`` for a Reference created by
  :meth:`UserSpace.absref <modelx.core.space.UserSpace.absref>`,
  or by :meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>` with ``'absolute'``;
* ``'relative'`` for a Reference created by
  :meth:`UserSpace.relref <modelx.core.space.UserSpace.relref>`,
  or by :meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>` with ``'relative'``;
* :obj:`None` for a global Reference, which is set on a Model,
  and for an argument of an :class:`~modelx.core.space.ItemSpace`.

.. admonition:: Known limitation

   :attr:`~ReferenceProxy.refmode` is :obj:`False` for a Reference that
   :meth:`~modelx.core.space.UserSpace.new_pandas`,
   :meth:`~modelx.core.space.UserSpace.new_module` or
   :meth:`~modelx.core.space.UserSpace.new_excel_range`
   creates in a :class:`~modelx.core.space.UserSpace`.
   This is not part of the frozen contract (see :ref:`toolapi-tiers`)
   and may change.

A Reference that a sub Space inherits from its base Space has the mode
of the base Reference. The mode matters only when the value is a modelx
object, such as a Cells or a Space; see
:meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>`.
A model saved by :func:`~modelx.write_model` keeps the mode only for
those References: when the value is not a modelx object,
the model that :func:`~modelx.read_model` reads back gives the Reference
the mode ``'auto'``, whatever mode it was created with.

