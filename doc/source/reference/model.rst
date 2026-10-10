Model
=======================

.. currentmodule:: modelx.core.model

.. autoclass:: Model


Model properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.name
  ~Model.fullname
  ~Model.doc
  ~Model.path
  ~Model.model
  ~Model.parent
  ~Model.allow_none
  ~Model.properties
  ~Model.spaces
  ~Model.refs
  ~Model.macros
  ~Model.iospecs
  ~Model.tracegraph
  ~Model.info


.. _model-tracegraph:

The trace graph
---------------

:attr:`~Model.tracegraph` is the graph in which modelx traces
which values were calculated from which.
Its nodes hold objects internal to modelx. To inspect dependencies, use
:meth:`Cells.node <modelx.core.cells.Cells.node>`,
:meth:`Cells.preds <modelx.core.cells.Cells.preds>`,
:meth:`Cells.succs <modelx.core.cells.Cells.succs>` and
:meth:`Cells.precedents <modelx.core.cells.Cells.precedents>`.

The length of the graph, ``len(model.tracegraph)``,
counts what the model holds:

* one for each value stored in a Cells whose
  :attr:`~modelx.core.cells.Cells.is_cached` is :obj:`True`,
  in every Space of the model, including the
  :class:`~modelx.core.space.ItemSpace` objects and the Spaces in them.
  Input values count as well as calculated values;
* plus one for each :class:`~modelx.core.space.ItemSpace`.

A Cells whose :attr:`~modelx.core.cells.Cells.is_cached` is :obj:`False`
stores no values and adds nothing. References are never counted.
So the length changes only when values are stored or deleted,
or ItemSpaces are created or deleted. Operations that only read stored
values leave it unchanged (see :ref:`cells-value-operations`)::

    >>> import modelx as mx

    >>> m = mx.new_model("Model1")

    >>> s = m.new_space("Space1", formula=lambda i: None)

    >>> fib = s.new_cells("fib", formula=lambda n: n if n < 2 else fib(n - 1) + fib(n - 2))

    >>> s.fib(10)
    55

    >>> len(m.tracegraph)   # fib(0) to fib(10)
    11

    >>> s[1].fib(5)
    5

    >>> len(m.tracegraph)   # 11, plus fib(0) to fib(5) in Space1[1], plus Space1[1]
    18

    >>> m.clear_all()

    >>> len(m.tracegraph)
    0

On ``BasicTerm_S`` of the ``basiclife`` library of
`lifelib <https://lifelib.io>`_, after ``Projection.pv_net_cf()`` and
``Projection[2].pv_net_cf()``, the length is 5,465: 1,832 values in
``Projection``, 3,632 values in ``Projection[2]``,
and ``Projection[2]`` itself.

Model operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.close
  ~Model.rename
  ~Model.set_property


Macro operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.new_macro


Saving operations
-----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.write
  ~Model.zip
  ~Model.export


Child Space operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.cur_space
  ~Model.new_space
  ~Model.clear_all
  ~Model.import_module
  ~Model.new_space_from_csv
  ~Model.new_space_from_excel
  ~Model.new_space_from_module
  ~Model.new_space_from_pandas
  ~Model.new_space_from_model
  ~Model.compare_cells


Reference operations
--------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.new_pandas
  ~Model.new_module
  ~Model.new_excel_range
  ~Model.update_pandas
  ~Model.update_module
  ~Model.get_spec
  ~Model.del_spec


Run operations
--------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.generate_actions
  ~Model.execute_actions
