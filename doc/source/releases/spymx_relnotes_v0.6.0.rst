.. currentmodule:: modelx

.. _release-mxplugin-v0.6.0:

====================================
spyder-modelx v0.6.0 (29 March 2021)
====================================

This release introduce following enhancements and new features.

.. note::

    spyder-modelx v0.6.0 requires modelx v0.13.1 or newer.


* `Enhanced MxDataViewer`_
* `Enhanced MxExplorer`_
* `Message bar in MxAnalyzer`_

Enhancements
=============

Enhanced MxDataViewer
---------------------

The former *MxDataView* is now renamed as *MxDataViewer*,
and it can now show values of :obj:`list`, :obj:`set`, :obj:`tuple`,
:obj:`dict`, `numpy`_ `array`_, in addition to
`pandas`_ `DataFrame`_, `Series`_, and Index in a tabular format.
It now also shows the values and types of scalar objects,
such as :obj:`int` and :obj:`str`.

Not only *MxDataViewer* is capable of showing the value of the expression
entered by the user as it was previously,
*MxDataViewer* is now connected to *MxExplorer*,
and it gives an option to show the value of the selected
Cells or Reference in *MxExplorer*.

The value shown in *MxDataViewer* is now updated manually
by the *Update* button.


.. figure:: /images/relnotes/spymx_v0_6_0/MxDataViewerDataFrame.png
   :align: center

   MxDataViewer showing a pandas Series

.. figure:: /images/relnotes/spymx_v0_6_0/MxDataViewerListInDict.png
   :align: center

   MxDataViewer showing a dict and its nested lists

.. _numpy: https://numpy.org/
.. _array: https://numpy.org/doc/stable/reference/generated/numpy.array.html
.. _pandas: https://pandas.pydata.org/
.. _DataFrame: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html
.. _Series: https://pandas.pydata.org/docs/reference/api/pandas.Series.html
.. _Index: https://pandas.pydata.org/docs/reference/api/pandas.Index.html


Enhanced MxExplorer
---------------------

Two new columns, *Is Derived* and *No. Data* are added to *MxExplorer*.
The *Is Derived* column shows whether each Cells or Space is derived or not.
The *No. Data* columns shows the number of values in each Cells.

In the *Properties* tab, the split between the *Property* pane
and the *Formula* pane is adjustable, allowing the user to expand
either pane.


.. figure:: /images/relnotes/spymx_v0_6_0/MxExplorer.png
   :align: center

   MxExplorer with the new columns

Writing a model to a zipfile and also reading a model from a
zip file are supported from the context menu items.

.. figure:: /images/relnotes/spymx_v0_6_0/ReadModelZipOption.png
   :align: center

   "Read Model" dialog box

.. figure:: /images/relnotes/spymx_v0_6_0/WriteModelZipOption.png
   :align: center

   "Write Model" dialog box

Message bar in MxAnalyzer
---------------------------

A message bar is added at the bottom of the *MxAnalyzer* widget to indicate
errors when expressions entered in the *Object* and *Args* boxes cannot
be evaluated.


.. figure:: /images/relnotes/spymx_v0_6_0/MxAnalyzerErrorMsg.png
   :align: center

   MxAnalyzer showing an error message

