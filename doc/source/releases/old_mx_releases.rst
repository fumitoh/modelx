.. py:currentmodule:: modelx

Older **modelx** releases
=========================

.. _release-v0.0.21:

v0.0.21 (23 March 2019)
-----------------------
Updates include refactoring to separate static and dynamic space classes,
use tuple for CellNode implementation,
gaining approximately 20% performance improvement.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Space class is now split into two separate concrete classes,
  :class:`~core.space.UserSpace`, :class:`~core.space.DynamicSpace` and
  one base class :class:`~core.space.BaseSpace`.

- ``module_`` parameter of the methods below are renamed to ``module``.

  * :meth:`~core.space.UserSpace.import_module`
  * :meth:`~core.space.UserSpace.import_funcs`
  * :meth:`~core.space.UserSpace.new_cells_from_module`
  * :meth:`~core.space.UserSpace.new_space_from_module`

- Methods and properties below on Space classes are renamed to be private,
  as these are expected not to be used directly by users for normal usage.

  * :meth:`~core.space.UserSpace._is_base`
  * :meth:`~core.space.UserSpace._is_sub`
  * :meth:`~core.space.UserSpace._is_static`
  * :meth:`~core.space.UserSpace._is_derived`
  * :meth:`~core.space.UserSpace._is_defined`
  * :meth:`~core.space.UserSpace._is_root`
  * :meth:`~core.space.UserSpace._is_dynamic`
  * :attr:`~core.space.UserSpace._self_cells`
  * :attr:`~core.space.UserSpace._derived_cells`
  * :attr:`~core.space.UserSpace._self_spaces`
  * :attr:`~core.space.UserSpace._derived_spaces`



Enhancements
~~~~~~~~~~~~

- IPython error traceback message is not suppressed by default.
  :func:`~setup_ipython` is added to suppress the default message.

- :func:`~set_recursion` is added to change the maximum depth of
  formula recursion.


Bug Fixes
~~~~~~~~~

- Fix :attr:`~core.space.UserSpace.formula` as setter by assignment
  expression i.e. alias to :meth:`~core.space.UserSpace.set_formula`.

- Fix :attr:`~core.model.Model.refs`.

.. _release-v0.0.20:

v0.0.20 (2 February 2019)
-------------------------

Enhancements
~~~~~~~~~~~~
- :class:`~core.cells.CellNode` repr to show "parameter=arguments".
- Add :attr:`~core.space.UserSpace.formula` property.

Bug Fixes
~~~~~~~~~
- Fix duplicate multiple bases of a dynamic space.

.. _release-v0.0.19:

v0.0.19 (13 January 2019)
-------------------------
Enhancements / bug fixes for defining and using dynamics spaces whose
base includes dynamics spaces.

Enhancements
~~~~~~~~~~~~
- Add ``name`` parameter to :func:`~open_model`.
- Pass dynamic arguments down to its children.
- Iterating over cells with single parameter returns values instead of tuples of single elements.
- View's _baseattrs to not include items with `_` prefixed names.

Bug Fixes
~~~~~~~~~
- Fix bases of derived dynamic spaces. If dynamic spaces are to be the base spaces of a dynamic sub space,
  then the static base spaces of the dynamic spaces become the base spaces in replacement for the
  dynamic spaces.
- Fix *AttributeError: 'BoundFunction' object has no attribute 'altfunc'* on unpickled models.
- Dedent function definitions for those defined inside blocks of other function definition.
- Fix error in conversion to DataFrame when merging indexes with different types.


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
- :func:`~get_object` to get a modelx object from its full name.

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
- :func:`~cur_model` and :func:`~cur_space` now accept
  model and space objects as their arguments respectively,
  in addition to the names of model or space objects.

- Add :attr:`~core.base.Interface.model` property to all Interface subclasses.

- Traceback messages upon erroneous formula calls are now limited
  to 6 trace stack entries.

- Error messages upon erroneous formula calls are now simplified
  not to show file traceback.


Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The parameters to :func:`~cur_model` and :func:`~cur_space`
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
- Fix crashes when :func:`~cur_model` is called with ``name``
  argument to change the current model.

.. _release-v0.0.13:

v0.0.13 (5 August 2018)
-----------------------
Space implementation has been largely rewritten in this release to
make the inheritance logic more robust.

.. warning::

   Support for Python 3.4, 3.5 is dropped in this release.
   Now only Python 3.6 and newer are supported.
   This is mainly due to the fact that modelx utilizes
   the order preservation nature of :class:`dict` introduced in Python 3.6.
   :class:`dict` performance improvement in Python 3.6 is also the reason
   to drop support for older versions.

   Support for NetworkX ver 1.x is also dropped in this release.
   NetworkX version 2.x is now required.

Enhancements
~~~~~~~~~~~~
- :meth:`~core.space.UserSpace.add_bases` and :meth:`~core.space.UserSpace.remove_bases` are added.
- :attr:`~core.space.UserSpace.bases` is added.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Support for Python older than 3.6 is dropped. Now Python 3.6 or above is required.
- Support for NetworkX version 1 is dropped. Now NetworkX version 2 is required.
- Dynamic spaces now inherit their parent spaces by default.
- :meth:`~core.space.UserSpace.new_cells` raises an error when the cells already exists.
- :attr:`~core.cells.Cells.formula` now returns Formula object instead of string.

Bug Fixes
~~~~~~~~~
- :func:`repr` on SpaceView and CellsView now list only selected items.


.. _release-v0.0.12:

v0.0.12 (16 June 2018)
----------------------

Enhancements
~~~~~~~~~~~~
- :attr:`~core.space.UserSpace.cells` returns an immutable mapping of cells named
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

- Subscription(``[]``) operator on :attr:`~core.space.UserSpace.cells` now
  accepts multiple args of cell names and a sequence of cell names,
  such as ``['foo', 'bar']`` and ``[['foo', 'bar']]``, which returns
  an immutable mapping (view) that includes only specified cells.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- :attr:`~core.space.UserSpace.frame` returns does not include empty or all-None cells.


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
- Add :meth:`~core.space.SpaceContainer.import_module` and :meth:`~core.space.UserSpace.import_funcs` properties.
- Add :attr:`~core.space.UserSpace.all_spaces` to contain all child spaces, including dynamic spaces.
- Add :py:attr:`~core.space.UserSpace.self_spaces` and :py:attr:`~core.space.UserSpace.derived_spaces` properties.
- Add :py:func:`~configure_python` and :py:func:`~restore_python`.
- Add :py:meth:`~core.space.UserSpace.reload` to reload the source module.
- :py:class:`~core.model.Model` and :py:class:`~core.space.UserSpace` to list their members on :func:`dir`.
- Raise an error upon zero division in formulas.
- Add :py:attr:`~core.base.Interface.parent` property.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Base spaces are now indelible.
- :attr:`~core.space.UserSpace.spaces` now contains only statics spaces. Now :attr:`~core.space.UserSpace.static_spaces` is an alias to  :attr:`~core.space.UserSpace.spaces`.

Bug Fixes
~~~~~~~~~
- Remove overridden cells from :py:attr:`~core.space.UserSpace.derived_cells`
- Update :py:attr:`~core.space.UserSpace.self_cells` when new cells are added.
- Fix stack overflow with Anaconda 64-bit Python on Windows.

Thanks
~~~~~~
- Stanley Ng

v0.0.7 (27 February 2018)
-------------------------

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Renamed :py:class:`~core.space.UserSpace` constructor parameter ``paramfunc`` to ``formula``.
- Renamed :py:meth:`~core.space.UserSpace.new_cells` parameter ``func`` to ``formula``.
- Renamed :py:class:`~core.base.Interface` ``can_have_none`` to ``allow_none``.

Bug Fixes
~~~~~~~~~

- Fix :py:func:`~open_model` to make :py:func:`~cur_model`
  properly return unpickled model.
