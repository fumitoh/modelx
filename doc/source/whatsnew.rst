.. py:currentmodule:: modelx.core

==========
What's New
==========

modelx is in its early alpha-release stage, and its specifications are
subject to changes without consideration on backward compatibility.
The source files of you models may need be modified manually,
if there are updates that break backward compatibility in newer versions
of modelx.

Likewise, model files saved with one version may not load with a newer version.
When updating modelx to a newer version,
make sure you rebuild model files saved using older versions of modelx
from their source code.


Releases
========

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