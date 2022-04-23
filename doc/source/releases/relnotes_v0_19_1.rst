
==================================
modelx v0.19.1 (24 April 2022)
==================================

.. currentmodule:: modelx.core

Bug Fixes
============

This release allows :class:`~node.ItemNode` objects
to be saved in a model properly (`GH63`_) by
:meth:`~model.Model.write` and restored by :func:`~modelx.read_model`.
This fix makes it possible to save an action returned
by :meth:`~model.Model.generate_actions` in the model
and to reuse it by :meth:`~model.Model.execute_actions`.

.. seealso::

    * :class:`~modelx.core.node.ItemNode`
    * :meth:`~model.Model.generate_actions`
    * :meth:`~model.Model.execute_actions`
    * `Running a heavy model while saving memory <https://modelx.io/blog/2022/03/26/running-model-while-saving-memory/>`_ , a blog post on https://modelx.io

.. _GH63: https://github.com/fumitoh/modelx/issues/63

