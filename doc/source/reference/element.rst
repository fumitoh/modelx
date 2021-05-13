Node types
=============

Node objects are used for dependency tracing.


.. currentmodule:: modelx.core

.. seealso::

    * :meth:`Cells.node <cells.Cells.node>`
    * :meth:`Cells.precedents <cells.Cells.precedents>`
    * :meth:`Cells.preds <cells.Cells.preds>`
    * :meth:`Cells.succs <cells.Cells.succs>`
    * :meth:`UserSpace.node <space.UserSpace.node>`
    * :meth:`UserSpace.precedents <space.UserSpace.precedents>`
    * :meth:`UserSpace.preds <space.UserSpace.preds>`
    * :meth:`UserSpace.succs <space.UserSpace.succs>`

.. contents:: 
   :depth: 1
   :local:


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
  ~BaseNode.preds
  ~BaseNode.succs
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
  ~ItemNode.preds
  ~ItemNode.succs
  ~ItemNode.value
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
  ~ReferenceNode.preds
  ~ReferenceNode.succs
  ~ReferenceNode.value
  ~ReferenceNode.precedents
