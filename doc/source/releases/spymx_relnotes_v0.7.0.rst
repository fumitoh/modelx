.. currentmodule:: modelx


.. _release-mxplugin-v0.7.1:

====================================
spyder-modelx v0.7.1 (8 May 2021)
====================================

This version supports Spyder 5.0.0.

This pulgins should work with Spyder versions from 3.2.4 through the newest,
but tests are conducted with a limited number of Spyder versions.
The tested versions of Spyder are posted on
`the Discussion site <https://github.com/fumitoh/modelx/discussions/48>`_.

.. _release-mxplugin-v0.7.0:

====================================
spyder-modelx v0.7.0 (24 April 2021)
====================================

This release introduces significantly enhanced MxAnalyzer.
The :doc:`/spyder` page is updated to reflect the recent enhancements.

To use modelx and spyder-modelx out of the box without any installation,
a custom WinPython is provided on
`the Download page <https://lifelib.io/download.html>`_ on lifelib.io.



The safest way to update your existing installation is to
update modelx and spyder-modelx manually:

.. code-block::

    $ pip install --upgrade modelx

    $ pip install --upgrade --no-deps spyder-modelx


.. warning::

   Anaconda users should not forget ``--no-deps`` option when
   installing or upgrading spyder-modelx
   using *pip*. Otherwise, *pip* may overwrite packages that Spyder
   depends on.

.. note::

    spyder-modelx v0.7.0 requires modelx v0.13.1 or newer.



Enhancements
=============

MxAnalyzer has now enhanced as follows.

New Formula pane
-----------------

Each tab in MxAnalyzer now has two split panes in it.
The upper pane is for the dependency tree,
and the lower pane shows the formula of the selected object in the tree.

.. figure:: /images/relnotes/spymx_v0_7_0/EnhancedMxAnalyzer.png
   :align: center

   Dependency tree and Formula pane in MxAnalyzer


Enhanced Value column
----------------------

The *Value* column in the dependency tree now shows
the type of each object if it's not a scalar value.
By double-clicking on the *Value* column or right-clicking and selecting
*Show Value* from the context menu, the value of the selected
element is shown in a pop-up window.
The pop-up window shows values of :obj:`list`, :obj:`set`, :obj:`tuple`,
:obj:`dict`, `numpy`_ `array`_, in addition to
`pandas`_ `DataFrame`_, `Series`_, and `Index`_ in a tabular format.

.. figure:: /images/relnotes/spymx_v0_7_0/MxAnalyzerShowValueMenu.png
   :align: center

   *Show Value* context menu item on MxAnalyzer

.. figure:: /images/relnotes/spymx_v0_7_0/MxAnalyzerPopUpSeries.png
   :align: center

   Pop-up window showing the values of a Series

.. _numpy: https://numpy.org/
.. _array: https://numpy.org/doc/stable/reference/generated/numpy.array.html
.. _pandas: https://pandas.pydata.org/
.. _DataFrame: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html
.. _Series: https://pandas.pydata.org/docs/reference/api/pandas.Series.html
.. _Index: https://pandas.pydata.org/docs/reference/api/pandas.Index.html


Setting object from MxExplorer
-------------------------------

Prior to this release, the object to analyze can only be
set as an expression entered by the user
which is to be evaluated in MxConsole.
This release enables the user to set the object to analyze from MxExplorer.
By clicking the newly added *Analyze Selected* item in the MxExplorer context
menu, the selected object is set in MxAnalyzer (currently,
only Cells can be selected).
The prior method of entering an expression continues to be available.
The radio buttons in the upper left corner are for
controlling which method to use.

.. figure:: /images/relnotes/spymx_v0_7_0/MxExplorerAnalyzeMenu.png
   :align: center

   *Analyze Selected* context menu item on MxExplorer

.. figure:: /images/relnotes/spymx_v0_7_0/EnhancedMxAnalyzerObjectBox.png
   :align: center

   Indicator in MxAnalyzer showing the selected Cells


Bug Fixs
=============

* Fixed the bug that MxAnalyzer fails to unfold the top row
  and Spyder subsequently crashes (`GH11`_).

.. _GH11: https://github.com/fumitoh/modelx/issues/11

