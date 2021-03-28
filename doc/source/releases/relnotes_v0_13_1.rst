
===============================
modelx v0.13.1 (28 March 2021)
===============================

This release fixes bugs and adds a private method for spyder-modelx v0.6.0.

Enhancements
============

* The ``_get_attrdict`` method is added for spyder-modelx v0.6.0 to replace
  ``_baseattrs`` and ``_to_attrdict``


Bug Fixes
=========

* Redundant openpyxl dependency
* Writing Series without header with pandas older than v0.24.0
* The ``_is_derived`` property of Dinamic Spaces and Cells now returns ``True``
* Error in reading dyanmic inputs when the model is being renamed(`GH42`_)


.. _GH42: https://github.com/fumitoh/modelx/issues/42