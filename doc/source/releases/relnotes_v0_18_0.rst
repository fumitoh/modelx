
==================================
modelx v0.18.0 (25 December 2021)
==================================

This release introduces the following enhancements and changes.

Enhancements
============

.. currentmodule:: modelx.core

A modelx model now internally maintains a map between input values and
references referring to the input values.
The mapping allows you to replace an object referenced by multiple references.
By making use of the mapping,
:meth:`Model.update_pandas<model.Model.update_pandas>` and
:meth:`UserSpace.update_pandas<space.UserSpace.update_pandas>` are
introduced for replacing a pandas object referenced in a model,
and :meth:`Model.update_module<model.Model.update_module>`
and :meth:`UserSpace.update_module<space.UserSpace.update_module>`
are introduced for replacing an user module.

* :meth:`Model.update_pandas<model.Model.update_pandas>`
* :meth:`UserSpace.update_pandas<space.UserSpace.update_pandas>`
* :meth:`Model.update_module<model.Model.update_module>`
* :meth:`UserSpace.update_module<space.UserSpace.update_module>`

A new version of the Spyder plugin for modelx is released
to show the internal map visually.
It adds a *data* tab in *MxExplorer*, which lists all the
objects input in the selected model, and shows
for each object referring *References* and the associated
:class:`DataSpace<modelx.io.baseio.BaseDataSpec>` if any.

.. figure:: /images/relnotes/spymx_v0_11_0/data-tab.png

    The *Data* tab in the Spyder plugin for modelx

.. seealso:: :doc:`spymx_relnotes_v0.11.0`

Backward Incompatible Changes
=============================

* Models saved by older versions of modelx can be opened by v0.18.0,
  but once they are saved, the models cannot be read by the older versions
  of modelx. Models saved by v0.18.0 cannot be opened by older modelx.

* :meth:`~modelx.core.model.Model.backup` and :func:`~modelx.restore_model`
  are now deprecated. Use :meth:`~modelx.core.model.Model.zip` or
  :func:`~modelx.zip_model` instead to save a model into a single file.

* The ``expose_data`` parameters of
  :meth:`Model.new_pandas<model.Model.new_pandas>` and
  :meth:`UserSpace.new_pandas<space.UserSpace.update_pandas>` are
  removed. Associated :class:`~modelx.io.pandasio.PandasData`
  objects are always hidden.

* The ``dataclients`` property is now renamed to :attr:`~modelx.core.model.Model.dataspecs`.

* The ``BaseDataClient`` class is now renamed to :class:`~modelx.io.baseio.BaseDataSpec`.

.. _math: https://docs.python.org/3/library/math.html
.. _numpy: https://numpy.org/
.. _pandas: https://pandas.pydata.org/
.. _DataFrame: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html
.. _Series: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html
