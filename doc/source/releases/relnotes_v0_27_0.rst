==================================
modelx v0.27.0 (25 August 2024)
==================================

This release introduces the following enhancements and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============


Introduction of Uncached Cells
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`~modelx.core.cells.Cells` class now includes a new property,
:attr:`~modelx.core.cells.Cells.is_cached`, which indicates whether a cells is cache-enabled.
By setting this property to :obj:`False`, a cells becomes cache-disabled,
meaning that a call to the cells does not cache its returned value,
and the cells is executed every time it's called.

To create an uncached cells,
the :func:`~modelx.defcells` function now includes an ``is_cached`` parameter,
which specifies whether to create or update a cached or uncached cells.

Additionally,
the :func:`~modelx.uncached` decorator has been introduced
as an alias for :func:`defcells(is_cached=False)<modelx.defcells>`.
This decorator allows for the straightforward creation of uncached cells.
:func:`~modelx.cached` has also been introduced as an alies for :func:`~modelx.defcells`.

.. code-block:: python

    import modelx as mx

    @mx.cached
    def cash_inflows():
        return [1, 2, 3]

    @mx.cached
    def cash_outflows():
        return [2, 1, 0]

    @mx.uncached
    def get_pv(cashflows: list):
        rate = 0.05
        disc = 1 / (1 + rate)
        return sum(v * disc**(i + 1) for i, v in enumerate(cashflows))

    @mx.cached
    def pv_inflows():
        return get_pv(cash_inflows())

    @mx.cached
    def pv_outflows():
        return get_pv(cash_outflows())

    @mx.cached
    def pv_netflows():
        return get_pv([i - o for i, o in zip(cash_inflows(), cash_outflows())])

    print(f"pv_netflows(): {pv_netflows()}")
    print(f"pv_inflows() - pv_outflows(): {pv_inflows() - pv_outflows()}")

In the example above, ``get_pv`` is defined as an uncached cells,
meaning that it does not store the result of its execution.
Unlike cached cells, uncached cells can accept unhashable arguments,
such as lists, because they do not need to use the arguments as keys to store results.

Without the uncached cells ``get_pv``, the functions ``pv_inflows``, ``pv_outflows``,
and ``pv_netflows`` would need to repeat the same code for calculating the present
value of their respective cash flows: ``inflows``, ``outflows``, and ``netflows``.

Using uncached cells allows you to define logic shared by multiple cells in one place,
reducing code duplication and improving maintainability.


.. rubric:: API changes

* :func:`~modelx.defcells` now has an optional parameter ``is_cached``.
* The :meth:`~modelx.core.space.UserSpace.new_cells` method of
  :class:`~modelx.core.space.UserSpace` has an optional parameter ``is_cached``.
* :class:`~modelx.core.cells.Cells` now has a property :attr:`~modelx.core.cells.Cells.is_cached`.
* :func:`~modelx.uncached` has been introduced.
* :func:`~modelx.cached` has been introduced as an alies for :func:`~modelx.defcells`.


Other API Changes
^^^^^^^^^^^^^^^^^^^

* Formula trace messages now print traces up to 20 lines (`GH144`_)

.. _GH144: https://github.com/fumitoh/modelx/issues/144

Bug Fixes
============

* Inheritance not working properly in a certain case (`GH138`_)
* Inheritance not working properly in a certain case (`GH141`_)

.. _GH138: https://github.com/fumitoh/modelx/issues/138
.. _GH141: https://github.com/fumitoh/modelx/issues/141

