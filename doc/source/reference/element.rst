Node types
=============

.. currentmodule:: modelx.core


Node objects are used to represent calculation *nodes*
in dependency tracing.
The :class:`~node.BaseNode` class is the abstract base class
for all Node classes. The :class:`~node.ItemNode` class
is for representing *elements* of :class:`~cells.Cells` objects
and Space objects such as :class:`~space.UserSpace`.
An *element* of a :class:`~cells.Cells` object is identified
by arguments to the :class:`~cells.Cells`.
If the :class:`~cells.Cells` has a value for the arguments,
whether it's calculted or input, the :meth:`~node.ItemNode.has_value`
returns :obj:`True` and :attr:`~node.ItemNode.value` returns the value.
Similarly to the :class:`~cells.Cells` element,
an element of a Space is identified by arguments to the Space.
Since a call to the Space returns an :class:`~space.ItemSpace`,
the value of the Space's element is the :class:`~space.ItemSpace` object
if it exists.

.. seealso::

    * :meth:`Cells.node <cells.Cells.node>`
    * :meth:`Cells.precedents <cells.Cells.precedents>`
    * :meth:`Cells.preds <cells.Cells.preds>`
    * :meth:`Cells.succs <cells.Cells.succs>`
    * :meth:`UserSpace.node <space.UserSpace.node>`
    * :meth:`UserSpace.precedents <space.UserSpace.precedents>`
    * :meth:`UserSpace.preds <space.UserSpace.preds>`
    * :meth:`UserSpace.succs <space.UserSpace.succs>`



BaseNode
-----------

.. currentmodule:: modelx.core.node

.. autoclass:: BaseNode

Attributes
^^^^^^^^^^

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~BaseNode.args
  ~BaseNode.has_value
  ~BaseNode.obj
  ~BaseNode.value


ItemNode
---------

.. currentmodule:: modelx.core.node

.. autoclass:: ItemNode

Attributes
^^^^^^^^^^

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~ItemNode.args
  ~ItemNode.has_value
  ~ItemNode.obj
  ~ItemNode.value
  ~ItemNode.preds
  ~ItemNode.succs
  ~ItemNode.precedents


ReferenceNode
----------------

.. currentmodule:: modelx.core.reference

.. autoclass:: ReferenceNode

Attributes
^^^^^^^^^^

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~ReferenceNode.args
  ~ReferenceNode.has_value
  ~ReferenceNode.obj
  ~ReferenceNode.value
