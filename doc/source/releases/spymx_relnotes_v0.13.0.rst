.. currentmodule:: modelx

.. _release-mxplugin-v0.13.0:

spyder-modelx v0.13.0 (30 July 2022)
=========================================

This release introduces enhanced MxDataView and supports Spyder 5.3.0 - 5.3.2.

Enhanced MxDataView
--------------------
This release introduces an enhanced MxDataView widget for Spyder5.
For Spyder4, MxDataView in this release still works the same as the previous release's.

MxDataView is used for viewing the values of modelx objects, such as Cells and References.
It is useful especially when you examine data objects,
such as numpy arrays and pandas Series and DataFrames,
but the previous MxDataView had the following limitations and issues:

* Only one data object can be shown at a time.
* The selected object in MxDataView is linked to the selected object
  in MxExplorer, which is inconvenient when you want to keep checking the value
  of the same object as you change the formulas of other objects.
* The *Expression* box has rarely been used.

To address the issues above, MxDataView is now enhanced as follows:

* The MxDataView widget now has tabs in it, allowing
  you to view multiple data objects at the same time.
* To select an object in MxDataView, you now need to explicitly select
  the object from the context menu or the tool bar of MxExplorer.
* The *Expression* box is removed.

.. figure:: /images/relnotes/spymx_v0_13_0/NewMxDataView.png

    Tabs and context menu in MxDataView

.. figure:: /images/relnotes/spymx_v0_13_0/MenuInMxExplorerForMxDataView.png

    New items in toolbar and context menu of MxExplorer for selecting objects in MxDataView

Support for Spyder 5.3.x
------------------------------
This release supports Spyder 5.3.0, 5.3.1, 5.3.2 and possibly future versions of Spyder 5.






