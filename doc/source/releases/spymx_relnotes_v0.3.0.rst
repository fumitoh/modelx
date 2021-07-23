.. currentmodule:: modelx

.. _release-mxplugin-v0.3.0:

====================================
spyder-modelx v0.3.0 (18 April 2020)
====================================

In this release of spyder-modelx,
context menu items are introduced for creating and deleteing modelx objects.
The Property pane is
added to MxExplorer, which lists properties of a selected object.
modelx needs to be updated to v0.4.0
for this version of spyder-modelx to work.

Enhancements
============

**Context Menu**

MxExplorer now has more context menu items, and the user can now
create and delete modelx object from the context menu.

.. figure:: /images/spyder/ContextMenu.png

**Property Pane**

The Property pane is added to MxExplorer.
The Property pane shows major properties of a selected object.

.. figure:: /images/spyder/PropertyPane.png



Bug Fixes
=========

- Fix MxAnalyzer error raised when tracing ItemSpaces.