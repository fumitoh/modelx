.. currentmodule:: modelx


.. _release-mxplugin-v0.9.0:

====================================
spyder-modelx v0.9.0 (23 July 2021)
====================================

Enhancements
=============

.. rubric:: *Calculate* option to MxDataViewer

Prior to this release, in order to show a calculated value of a Cells in MxDataViewer,
the value needs to be calculated beforehand.
This release introduces an option to calculate the value before
updating MxDataViewer to show it, so shat the user doesn't need to
calculate the value beforehand.

The option can be toggled on and off in the option box on MxDataViewer.

.. figure:: /images/relnotes/spymx_v0_9_0/CalcOption.png
   :align: center

   *Calculate* option on *MxDataViewer*


Bug Fixes
==========

* *MxExplorer* now shows global References defined at the model level.
* *MxAnalyzer* now shows numbers of Numpy numeric types, such as ``int32``.
* Fix *MxExplorer* to not show the message box on canceling *Delete Selected*.
