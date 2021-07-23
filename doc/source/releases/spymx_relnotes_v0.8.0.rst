.. currentmodule:: modelx


.. _release-mxplugin-v0.8.0:

====================================
spyder-modelx v0.8.0 (19 May 2021)
====================================

This release is to support :meth:`~core.cells.Cells.precedents`
introduced in modelx v0.15.0.

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

    spyder-modelx v0.8.0 requires modelx v0.15.0 or newer.


Enhancements
=============

The *precedents* tab in *MxAnalyzer* now lists References with values.

.. code-block:: python

    import modelx as mx

    space = mx.new_space()
    space.new_space('Child')
    space.Child.new_space('GrandChild')

    space.x = 1
    space.Child.y = 2
    space.Child.GrandChild.z = 3

    @mx.defcells(space=space)
    def foo(t):
        return t

    @mx.defcells(space=space)
    def bar(t):
        return foo(t) + x + Child.y + Child.GrandChild.z

    bar(1)


.. figure:: /images/relnotes/spymx_v0_8_0/PredsInMxAnalyzer.png
   :align: center

   Precedents tab in MxAnalyzer before change

.. figure:: /images/relnotes/spymx_v0_8_0/PrecedentsInMxAnalyzer.png
   :align: center

   New Precedents tab in MxAnalyzer
