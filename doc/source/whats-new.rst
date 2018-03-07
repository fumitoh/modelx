.. py:currentmodule:: modelx.core

==========
What's New
==========

Change Log
==========

v0.0.8.dev (XX March 2018)
--------------------------

Enhancements
~~~~~~~~~~~~
- Add :py:attr:`~base.Interface.parent` property.


v0.0.7 (27 February 2018)
-------------------------

Breaking Changes
~~~~~~~~~~~~~~~~
- Renamed :py:class:`~space.Space` constructor parameter ``paramfunc`` to ``formula``.
- Renamed :py:meth:`~space.Space.new_cells` parameter ``func`` to ``formula``.
- Renamed :py:class:`~base.Interface` ``can_have_none`` to ``allow_none``.

Bug fixes
~~~~~~~~~

- Fix :py:func:`~api.open_model` to make :py:func:`~api.cur_model`
  properly return unpickled model.