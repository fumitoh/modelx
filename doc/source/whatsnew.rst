.. py:currentmodule:: modelx.core

==========
What's New
==========

modelx is in its early alpha-release stage, and its specifications are
subject to changes without consideration on backward compatibility.
The source files of you models may need to be modified manually,
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

Releases
========

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
- Add :meth:`~model.Model.rename`.
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
- Add :meth:`~space.SpaceContainer.import_module` and :meth:`~space.Space.import_funcs` properties.
- Add :attr:`~space.Space.all_spaces` to contain all child spaces, including dynamic spaces.
- Add :py:attr:`~space.Space.self_spaces` and :py:attr:`~space.Space.derived_spaces` properties.
- Add :py:func:`~api.configure_python` and :py:func:`~api.restore_python`.
- Add :py:meth:`~space.Space.reload` to reload the source module.
- :py:class:`~model.Model` and :py:class:`~space.Space` to list their members on :func:`dir`.
- Raise an error upon zero division in formulas.
- Add :py:attr:`~base.Interface.parent` property.

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Base spaces are now indelible.
- :attr:`~space.Space.spaces` now contains only statics spaces. Now :attr:`~space.Space.static_spaces` is an alias to  :attr:`~space.Space.spaces`.

Bug Fixes
~~~~~~~~~
- Remove overridden cells from :py:attr:`~space.Space.derived_cells`
- Update :py:attr:`~space.Space.self_cells` when new cells are added.
- Fix stack overflow with Anaconda 64-bit Python on Windows.

Thanks
~~~~~~
- Stanley Ng

v0.0.7 (27 February 2018)
-------------------------

Backwards Incompatible Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Renamed :py:class:`~space.Space` constructor parameter ``paramfunc`` to ``formula``.
- Renamed :py:meth:`~space.Space.new_cells` parameter ``func`` to ``formula``.
- Renamed :py:class:`~base.Interface` ``can_have_none`` to ``allow_none``.

Bug Fixes
~~~~~~~~~

- Fix :py:func:`~api.open_model` to make :py:func:`~api.cur_model`
  properly return unpickled model.
