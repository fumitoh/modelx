.. currentmodule:: modelx

=========================================
spyder-modelx v0.11
=========================================

.. _release-mxplugin-v0.11.1:

spyder-modelx v0.11.1 (2 January 2022)
=========================================

This release is for supporting Spyder 5.1.


.. _release-mxplugin-v0.11.0:

spyder-modelx v0.11.0 (18 December 2021)
=========================================

Enhancements
--------------

The *Data* tab is addeted to *MxExplorer*.
The *Data* tab lists objects referenced in the selected model
and associated :class:`DataSpec <io.baseio.BaseDataSpec>`.

In the upper half of the Data tab, objects referenced in the model,
except for those that are of modelx types, are listed together
with the References referring the objects.
If the object selected in the upper pane has an associated
:class:`DataSpec <io.baseio.BaseDataSpec>`,
The parameters of the :class:`DataSpec <io.baseio.BaseDataSpec>`
are listed in the bottom half of the Data tab.

.. figure:: /images/relnotes/spymx_v0_11_0/data-tab.png

    The *Data* tab in *MxExplorer*

.. seealso:: :doc:`relnotes_v0_18_0`

Bug Fixes
--------------

* Fix error with Spyder 4+ on closing *MxConsole*.

