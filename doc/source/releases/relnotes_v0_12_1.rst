
===============================
modelx v0.12.1 (6 Feb 2021)
===============================

This release is for fixing the following bugs.

Bug Fixes
=========

* Deleting derived Cells was allowed. Deleting an overridden Cells
  now makes the Cells derived

* :class:`~modelx.io.pandasio.PandasData` objects introduced in modelx 0.12.0
  were not properly written to and read from files

* A DynamicSpace assigned to a Reference became null in some cases
  after deserialized(`GH37`_)

* Error when reading references whose values are :obj:`True` or :obj:`False`
  from saved models(`GH39`_)

* Redundant qtpy dependency(`GH38`_)

.. _GH39: https://github.com/fumitoh/modelx/issues/39


.. _GH37: https://github.com/fumitoh/modelx/issues/37


.. _GH38: https://github.com/fumitoh/modelx/issues/38