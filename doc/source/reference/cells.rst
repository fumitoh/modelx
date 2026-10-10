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
  ~Cells.match
  ~Cells.value

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
* ``cells.values()`` and ``cells.items()``, with the exception in the
  note below.
* :attr:`~Cells.series` and :attr:`~Cells.frame`, and :meth:`~Cells.to_series`
  and :meth:`~Cells.to_frame` called without arguments.
* ``cells.node(*args).has_value()``, and ``cells.node(*args).value``,
  which raises :obj:`ValueError` when no value is stored for ``args``.
* :meth:`~Cells.is_input`, :meth:`~Cells.preds`, :meth:`~Cells.succs`
  and :meth:`~Cells.precedents`, which raise :obj:`ValueError`
  when no value is stored for the arguments.

.. note::

   ``cells.values()`` and ``cells.items()`` look each key up again
   as ``cells[key]``. For a Cells with one parameter whose argument
   is a tuple, the key is then read as the arguments themselves:
   with ``h((1, 2))`` stored, ``values()`` and ``items()`` raise
   :obj:`TypeError`.
   With ``h((1,))`` stored, they read ``h(1)`` in its place:
   if ``h(1)`` is not stored, they run the formula for ``h(1)``,
   store its value, and then raise :obj:`RuntimeError`
   because the Cells changed during the iteration;
   if ``h(1)`` is stored, they return the value of ``h(1)``
   for the key ``(1,)``.
   ``(1, 2) in h`` is :obj:`False` for the same reason;
   ``((1, 2),) in h`` is :obj:`True`.
   ``cells.node(*args).value`` reads every stored value without running
   the formula, with ``args = (key,)`` for a Cells with one parameter
   and ``args = key`` for any other Cells.

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
In modelx 0.33, :meth:`~Cells.clear_formula` raises :obj:`TypeError`
and leaves the formula and the values as they were.



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
