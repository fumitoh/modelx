.. py:currentmodule:: modelx

==========
What's New
==========

.. warning::

   modelx is in its early alpha-release stage, and its specifications are
   subject to changes without consideration on backward compatibility.
   The source files of your models may need to be modified manually,
   if there are updates that break backward compatibility in newer versions
   of modelx.

   Likewise, model files saved with one version may not load with a newer version.
   When updating modelx to a newer version,
   make sure you rebuild model files saved using older versions of modelx
   from their source code.

Updates
=======

.. include:: updates.rst
   :start-after: Latest Updates Begin
   :end-before: Latest Updates End

:doc:`... See more updates<updates>`

.. toctree::
   :hidden:

   updates

Releases: modelx
================

.. _release-v0.0.18:

v0.0.18 (31 December 2018)
--------------------------
This release is mainly for adding interface functions/methods to
spyder-modelx :ref:`release-mxplugin-v0.0.7`

Enhancements
~~~~~~~~~~~~
- Add :attr:`~core.cells.CellNode.preds` and :attr:`~core.cells.CellNode.succs` properties
  to :class:`~core.cells.CellNode`.
- Add :meth:`~core.cells.Cells.node` to :class:`~core.cells.Cells`
- Rename ``literaldict`` property to ``_baseattrs`` for :class:`~core.base.Interface`,
  :class:`~core.base.BaseView` and their subclasses.
- Rename ``set_keys`` method of :class:`~core.base.SelectedView` to ``_set_keys`` .

Bug Fixes
~~~~~~~~~
- Raise not KeyError but AttributeError upon hasattr/getattr on Space.


.. _release-v0.0.17:

v0.0.17 (2 December 2018)
-------------------------
This release is mainly for adding interface to functions to
spyder-modelx :ref:`release-mxplugin-v0.0.6`

Enhancements
~~~~~~~~~~~~
- :func:`~core.api.get_object` to get a modelx object from its full name.

Bug Fixes
~~~~~~~~~
- Error when modelx tries to get IPython shell before it becomes available.

.. _release-v0.0.16:

v0.0.16 (21 October 2018)
-------------------------
spyder-modelx plugin introduces a new widget to view cells values in a table.
This release reflects some updates in modelx to make the new widget work.

Enhancements
~~~~~~~~~~~~
- :func:`~core.api.cur_model` and :func:`~core.api.cur_space` now accept
  model and space objects as their arguments respectively,
  in addition to the names of model or space objects.

- Add :attr:`~core.base.Interface.model` property to all Interface subclasses.

- Traceback messages upon erroneous formula calls are now limited
  to 6 trace stack entries.

- Error messages upon erroneous formula calls are now simplified
  not to show file traceback.


Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The parameters to :func:`~core.api.cur_model` and :func:`~core.api.cur_space`
  are renamed from ``name`` to ``model`` and ``space`` respectively,
  due to the enhancement for these functions to accept objects,
  in addition to the names of the objects.


.. _release-v0.0.15:

v0.0.15 (20 September 2018)
---------------------------

Enhancements
~~~~~~~~~~~~
- Importing a module overrides formulas if their cells already exist.

.. _release-v0.0.14:

v0.0.14 (3 September 2018)
--------------------------
This version is mainly for updating modelx Qt widgets,
in order for the widgets to work with
the initial version of spyder-modelx, Spyder plugin for modelx.

Enhancements
~~~~~~~~~~~~
- Add property :attr:`~core.base.Interface._baseattrs`
  and ``BaseView._baseattrs``. This property is used by spyder-modelx.


Bug Fixes
~~~~~~~~~
- Fix crashes when :func:`~core.api.cur_model` is called with ``name``
  argument to change the current model.

.. _release-v0.0.13:

v0.0.13 (5 August 2018)
-----------------------
Space implementation has been largely rewritten in this release to
make the inheritance logic more robust.

.. warning::

   Support for Python 3.4, 3.5 is dropped in this release.
   Now only Python 3.6 and 3.7 are supported.
   This is mainly due to the fact that modelx utilizes
   the order preservation nature of :class:`dict` introduced in Python 3.6.
   :class:`dict` performance improvement in Python 3.6 is also the reason
   to drop support for older versions.

   Support for NetworkX ver 1.x is also dropped in this release.
   NetworkX version 2.x is now required.

Enhancements
~~~~~~~~~~~~
- :meth:`~core.space.Space.add_bases` and :meth:`~core.space.Space.remove_bases` are added.
- :attr:`~core.space.Space.bases` is added.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Support for Python older than 3.6 is dropped. Now Python 3.6 or above is required.
- Support for NetworkX version 1 is dropped. Now NetworkX version 2 is required.
- Dynamic spaces now inherit their parent spaces by default.
- :meth:`~core.space.Space.new_cells` raises an error when the cells already exists.
- :attr:`~core.cells.Cells.formula` now returns Formula object instead of string.

Bug Fixes
~~~~~~~~~
- :func:`repr` on SpaceView and CellsView now list only selected items.


.. _release-v0.0.12:

v0.0.12 (16 June 2018)
----------------------

Enhancements
~~~~~~~~~~~~
- :attr:`~core.space.Space.cells` returns an immutable mapping of cells named
  :class:`~core.space.CellsView` supporting
  :meth:`~core.space.CellsView.to_frame` method,
  which returns a DataFrame
  object containing cells values. If an iterator of
  arguments are given as ``arg``, values of the cells for the arguments
  are calculated and only the given arguments
  are included in the DataFrame index(es).
  For more, see :class:`the reference page<core.space.CellsView>`

- Cells are now of a Mapping type, which implements ``keys()``, ``values()``,
  ``items()`` methods to get their arguments and values.

- Subscription(``[]``) operator on :attr:`~core.space.Space.cells` now
  accepts multiple args of cell names and a sequence of cell names,
  such as ``['foo', 'bar']`` and ``[['foo', 'bar']]``, which returns
  an immutable mapping (view) that includes only specified cells.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- :attr:`~core.space.Space.frame` returns does not include empty or all-None cells.


Bug Fixes
~~~~~~~~~
- Fix issues specific to networkx v1.x.
- Fix :meth:`~core.space.SpaceContainer.import_module` to handle `bases` properly.

v0.0.11 (27 May 2018)
---------------------

Bug Fixes
~~~~~~~~~
- Fix Space.refs
- Fix conversion of scalar cells to Pandas objects


v0.0.10 (6 May 2018)
--------------------

Enhancements
~~~~~~~~~~~~
- Add ``is_*`` methods to Space.
- Rename a model by adding ``_BAKn`` to its original name
  when another model with the same name is created.
- Add :meth:`~core.model.Model.rename`.
- ``name in space`` expression is allowed where ``name`` is a string.
- ``_space`` local reference is available to refer to the parent space from its child cells.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- ``get_self`` function is removed.

Bug Fixes
~~~~~~~~~
- Call stack max depth is set to 1000 to run all lifelib samples successfully.
- Fix an error around graph unpickling.
- Keep the same derived objects after they are updated.

v0.0.9 (1 April 2018)
---------------------

Enhancements
~~~~~~~~~~~~
- Add :func:`show_tree<modelx.qtgui.api.show_tree>` to show model tree in inline mode.
- Add :func:`get_tree<modelx.qtgui.api.get_tree>` to get model tree in automatic mode.

Bug Fixes
~~~~~~~~~
- Make :func:`get_modeltree <modelx.qtgui.api.get_modeltree>` available directly under ``modelx``.


v0.0.8 (25 March 2018)
----------------------

Enhancements
~~~~~~~~~~~~
- Make :func:`get_modeltree <modelx.qtgui.api.get_modeltree>` available directly under ``modelx``.
- Add :meth:`~core.space.SpaceContainer.import_module` and :meth:`~core.space.Space.import_funcs` properties.
- Add :attr:`~core.space.Space.all_spaces` to contain all child spaces, including dynamic spaces.
- Add :py:attr:`~core.space.Space.self_spaces` and :py:attr:`~core.space.Space.derived_spaces` properties.
- Add :py:func:`~core.api.configure_python` and :py:func:`~core.api.restore_python`.
- Add :py:meth:`~core.space.Space.reload` to reload the source module.
- :py:class:`~core.model.Model` and :py:class:`~core.space.Space` to list their members on :func:`dir`.
- Raise an error upon zero division in formulas.
- Add :py:attr:`~core.base.Interface.parent` property.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Base spaces are now indelible.
- :attr:`~core.space.Space.spaces` now contains only statics spaces. Now :attr:`~core.space.Space.static_spaces` is an alias to  :attr:`~core.space.Space.spaces`.

Bug Fixes
~~~~~~~~~
- Remove overridden cells from :py:attr:`~core.space.Space.derived_cells`
- Update :py:attr:`~core.space.Space.self_cells` when new cells are added.
- Fix stack overflow with Anaconda 64-bit Python on Windows.

Thanks
~~~~~~
- Stanley Ng

v0.0.7 (27 February 2018)
-------------------------

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Renamed :py:class:`~core.space.Space` constructor parameter ``paramfunc`` to ``formula``.
- Renamed :py:meth:`~core.space.Space.new_cells` parameter ``func`` to ``formula``.
- Renamed :py:class:`~core.base.Interface` ``can_have_none`` to ``allow_none``.

Bug Fixes
~~~~~~~~~

- Fix :py:func:`~core.api.open_model` to make :py:func:`~core.api.cur_model`
  properly return unpickled model.


Releases: spyder-modelx
=======================

.. _release-mxplugin-v0.0.7:

v0.0.7 (31 December 2018)
-------------------------

- Add MxAnalyzer widget. See :ref:`MxAnalyzer` section for details.
- MxExplorer now shows reference items.
- MxExplorer now displays dynamic spaces as parametrized expressions.

.. _release-mxplugin-v0.0.6:

v0.0.6 (2 December 2018)
------------------------
- Add Formula list widget to MxExplorer.
- Support Spyder 3.3.2.

.. _release-mxplugin-v0.0.5:

v0.0.5 (21 October 2018)
------------------------
- Add MxDataView widget. See :ref:`MxDataView` section for details.