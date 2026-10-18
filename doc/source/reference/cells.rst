Cells
=======================

.. currentmodule:: modelx.core.cells

.. autoclass:: Cells


Basic properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.name
  ~Cells.fullname
  ~Cells.doc
  ~Cells.set_doc
  ~Cells.allow_none
  ~Cells.model
  ~Cells.parent
  ~Cells.properties
  ~Cells.set_property
  ~Cells.is_cached
  ~Cells.info


Cells operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.rename
  ~Cells.copy


.. _cells-value-operations:

Value operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.clear
  ~Cells.clear_all
  ~Cells.clear_at
  ~Cells.is_input
  ~Cells.items
  ~Cells.match
  ~Cells.value
  ~Cells.values

A Cells stores the values that its formula has calculated,
and the input values assigned to it, by their arguments.
Some operations only read or change the stored values,
and never run the formula.
Others run the formula when no value is stored for the arguments.

.. rubric:: Reading stored values without running the formula

The operations below read only the values that the Cells holds.
They never run the formula and never add a value, so
``len(model.tracegraph)`` (see :attr:`Model.tracegraph
<modelx.core.model.Model.tracegraph>`) stays the same:

* ``len(cells)``, ``iter(cells)`` and ``cells.keys()``.
  The keys of a Cells with one parameter are the arguments themselves,
  such as ``1``; the keys of any other Cells are tuples of arguments,
  such as ``(1, 2)``, or ``()`` for a Cells without parameters.
* ``key in cells``. Default arguments are not applied:
  for a Cells ``g(t, k=1)`` that holds ``g(1)``,
  ``(1, 1) in g`` is :obj:`True` and ``(1,) in g`` is :obj:`False`.
  For a Cells with one parameter whose argument is a tuple,
  see the known limitation below.
* ``cells.values()`` and ``cells.items()``.
  ``items()`` pairs each key that ``iter(cells)`` yields
  with the value stored for it,
  so ``dict(cells.items())`` is a :obj:`dict` of the stored values.
  ``value in cells.values()`` and ``(key, value) in cells.items()``
  also read only stored values,
  and ``(key, value) in cells.items()``, like ``key in cells``,
  applies no default arguments.
  A formula that reads them through a Reference to the Cells
  depends on each value it reads:
  its value is cleared when one of those values changes,
  but not when a value is added.
* :attr:`~Cells.series` and :attr:`~Cells.frame`, and :meth:`~Cells.to_series`
  and :meth:`~Cells.to_frame` called without arguments.
* ``cells.node(*args).has_value()``, and ``cells.node(*args).value``,
  which raises :obj:`ValueError` when no value is stored for ``args``.
* :meth:`~Cells.is_input`, :meth:`~Cells.preds`, :meth:`~Cells.succs`
  and :meth:`~Cells.precedents`, which raise :obj:`ValueError`
  when no value is stored for the arguments.

.. admonition:: Known limitation

   ``key in cells``, ``key in cells.keys()``, ``cells[key]``,
   ``cells.get(key)``, ``cells[key] = value`` and ``dict(cells)``
   read a key whose type is tuple as the tuple of all the arguments.
   This goes wrong for some keys that ``iter(cells)`` yields:

   * For a Cells ``h(x)`` with one parameter whose argument is itself
     a tuple. With ``h((1, 2))`` stored, ``iter(h)`` yields ``(1, 2)``,
     but ``(1, 2) in h`` is :obj:`False`,
     and ``h[(1, 2)]`` and ``dict(h)`` raise :obj:`TypeError`,
     because they read ``(1, 2)`` as two arguments.
     ``(1,) in h``, ``h[(1,)]``, ``h.get((1,))`` and
     ``h[(1,)] = value`` mean ``h(1)``, not ``h((1,))``,
     and with only ``h((1,))`` stored, ``dict(h)`` runs the formula
     for ``h(1)`` and gives its value for the key ``(1,)``.
   * For a Cells with ``*args``. For ``f(*args)``,
     ``key in f`` is :obj:`False` for every key that ``iter(f)`` yields.
     For ``f(a, *args)``, ``f[key]``, ``f.get(key)``, ``dict(f)``
     and ``f.node(*key)`` read other arguments.

   ``dict(cells.items())`` reads the stored values of any Cells.
   For a tuple argument of ``h(x)``, wrap it in another tuple,
   as in ``h[((1, 2),)]``, or use ``h.node((1, 2)).value``.
   This is not part of the frozen contract (see :ref:`toolapi-tiers`)
   and may change.

``cells.node(*args).value`` reads every stored value without running
the formula, with ``args = (key,)`` for a Cells with one parameter
and ``args = key`` for any other Cells,
except a Cells with ``*args`` (see the known limitation above).

.. rubric:: Running the formula when no value is stored

The operations below return the stored value when there is one.
Otherwise they run the formula, and store the result
unless :attr:`~Cells.is_cached` is :obj:`False`:

* calling the Cells, ``cells(*args)``, and ``cells[key]``;
* ``cells.get(key)``;
* :attr:`~Cells.value`, for a Cells without parameters;
* :meth:`~Cells.to_series` and :meth:`~Cells.to_frame`
  called with arguments;
* :meth:`~Cells.match`.

A Cells whose :attr:`~Cells.is_cached` is :obj:`False` stores no values,
so every call runs its formula.

.. rubric:: Changing stored values without running the formula

* ``cells[key] = value`` and ``cells.value = value`` store an input value.
  A Cells whose :attr:`~Cells.is_cached` is :obj:`False` refuses them
  with :obj:`ValueError`.
* :meth:`~Cells.clear` deletes the calculated values and keeps the input
  values. :meth:`~Cells.clear_all` deletes both.
  :meth:`~Cells.clear_at` deletes the value for the given arguments,
  input or calculated, and ``del cells.value`` the value of a Cells
  without parameters.

Deleting or replacing a value also deletes the values that were
calculated from it, in this Cells and in other Cells.
None of these operations runs a formula, except that when
:func:`~modelx.set_recalc` has been called with :obj:`True`,
storing an input value recalculates the values that depended on
the value it replaces.


.. _cells-formula-operations:

Formula operations
------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.formula
  ~Cells.set_formula
  ~Cells.clear_formula
  ~Cells.parameters

The formula of a Cells is a :class:`~modelx.core.formula.Formula` object.
To set it, assign a function, a lambda expression or a string
to :attr:`~Cells.formula`::

    cells.formula = "lambda x: 2 * x"

To clear it, delete it::

    del cells.formula

After ``del cells.formula``, the formula's source is ``'lambda: None'``
and :attr:`~Cells.parameters` is ``()``.
All the values of the Cells are deleted, input values included,
together with the values that were calculated from them.
A Cells that a sub Space inherits from this Cells gets the same formula.
Deleting the formula of an inherited Cells in a sub Space makes that
Cells the sub Space's own, without a formula; the base Cells keeps its
formula. The formula of a Cells in an :class:`~modelx.core.space.ItemSpace`
cannot be deleted: ``del`` raises :obj:`ValueError`.

:meth:`~Cells.set_formula` and :meth:`~Cells.clear_formula` are deprecated.
Use the :attr:`~Cells.formula` property instead.

.. admonition:: Known limitation

   On this release, :meth:`~Cells.clear_formula` raises :obj:`TypeError`
   and leaves the formula and the values as they were.
   This is not part of the frozen contract (see :ref:`toolapi-tiers`)
   and may change.



Node operations
------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.node
  ~Cells.preds
  ~Cells.succs
  ~Cells.precedents


Exporting to Pandas objects
---------------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.series
  ~Cells.frame
  ~Cells.to_series
  ~Cells.to_frame


DynamicCells
------------

.. autoclass:: DynamicCells
