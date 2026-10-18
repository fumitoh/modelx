====================================
modelx v0.34.0 (unreleased)
====================================

This release is in development, and these notes are not complete yet.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
============

* Tools can tell what a value is from the name of its class
  (:ref:`toolapi-kinds`). A tool first checks that
  ``type(v).__module__`` is a str that starts with ``"modelx."``,
  then reads ``type(v).__name__``. The names of twelve classes are
  frozen tool API from this release: ``Model``, ``UserSpace``,
  ``ItemSpace``, ``DynamicSpace``, ``Cells``, ``DynamicCells``,
  ``Macro``, ``ReferenceProxy``, ``DynamicReferenceProxy``,
  ``PandasData``, ``ExcelRange`` and ``ModuleData``, and so is the
  promise that each is defined in a module of the :mod:`modelx` package.
  The module paths are not tool API. The check reads no attribute of
  the object, so it never reaches a user's member of a Model or a Space
  and never runs a formula, and it answers on a deleted object and on
  an object of a closed Model. Measured on CPython 3.11.15, it takes
  about 0.15 µs on a modelx object and 0.12 µs on any other value,
  the call included.

  A class name cannot warn when a tool reads it, so a listed name is
  renamed or split only after it has been marked as deprecated on
  :ref:`toolapi` and in these notes for at least two minor releases
  (:ref:`toolapi-deprecation`).

* modelx has two new classes: :class:`~modelx.core.cells.DynamicCells`,
  a subclass of :class:`~modelx.core.cells.Cells`, and
  :class:`~modelx.core.reference.DynamicReferenceProxy`, a subclass of
  :class:`~modelx.core.reference.ReferenceProxy`.
  A Cells of an :class:`~modelx.core.space.ItemSpace` or of a
  :class:`~modelx.core.space.DynamicSpace` is a DynamicCells,
  and the proxy of a Reference that an ItemSpace makes
  is a DynamicReferenceProxy: an argument of the ItemSpace,
  a Reference that its Space formula returns in ``'refs'``,
  and the ``_self``, ``_space`` and ``_model`` of the ItemSpace and of
  the DynamicSpaces in it.
  Together with ItemSpace and DynamicSpace, the class now tells
  whether an object is one that modelx made for an ItemSpace.
  A Reference of a Space seen through its ItemSpace, and a global
  Reference, keep a ReferenceProxy.

* :meth:`ReferenceProxy._is_derived()
  <modelx.core.reference.ReferenceProxy._is_derived>` is :obj:`True`
  for a Reference that a sub Space inherits from a base Space and has
  not redefined, and :obj:`False` for any other Reference.
  It is :obj:`None` for a proxy that does not stand for a Reference,
  so a tool that asks every proxy in a model gets an answer from each.
  ``_is_derived`` requested in
  :meth:`~modelx.core.model.Model._get_attrdict` now adds a key to
  the records of References, as it did only to those of Cells: on the
  model that modelx's spyder-modelx tests use, 33 Reference records gain
  it, 8 of them :obj:`True`.
  :meth:`ReferenceProxy.is_derived()
  <modelx.core.reference.ReferenceProxy.is_derived>` stays for
  modelx-bridge 0.10, and returns the same.

* Nodes have a ``_get_repr(fullname=True, add_value=False)`` method,
  :meth:`ItemNode._get_repr <modelx.core.node.ItemNode._get_repr>` and
  :meth:`ReferenceNode._get_repr
  <modelx.core.reference.ReferenceNode._get_repr>`.
  It gives the display name of the node's object followed by
  the node's arguments by parameter name, as in
  ``'Model1.Proj[1][5].bar()'`` or
  ``'BasicTerm_S.Projection[2].claims(t=3)'``, so a tool no longer
  formats the arguments itself. With ``add_value=True`` it adds
  ``=`` and the value, which is what ``repr()`` of a node shows.
  ``repr()`` of a node is unchanged, except for the ItemSpace labels
  fixed below: on a model without ItemSpaces, 37 nodes gave the same
  strings as with the code it replaces.


Backward Incompatible Changes
==============================

* A Cells of an ItemSpace or of a DynamicSpace is now a
  :class:`~modelx.core.cells.DynamicCells`, and the proxy of a
  Reference that an ItemSpace makes is a
  :class:`~modelx.core.reference.DynamicReferenceProxy`
  (see Enhancements).
  ``isinstance(c, Cells)`` and ``isinstance(r, ReferenceProxy)`` are
  :obj:`True` for them as before, but ``type(c) is Cells`` is
  :obj:`False` for a DynamicCells, and a test of a class name such as
  ``type(c).__name__ == 'Cells'`` misses it: test
  ``in {'Cells', 'DynamicCells'}`` instead.
  ``repr()`` and :attr:`~modelx.core.cells.Cells.info` show the new
  names: ``repr(Proj[1].bar)`` is ``<DynamicCells Model1.Proj[1].bar()>``,
  where it was ``<Cells Model1.Proj[1].bar()>``, the ``.info`` header
  reads ``DynamicCells: Model1.Proj[1].bar()``, and the proxy of the
  argument ``i`` of ``Proj[1]`` is
  ``<DynamicReferenceProxy Model1.Proj[1].i>``.
  The ``'type'`` of the dicts of ``_get_attrdict`` and ``_baseattrs``
  stays ``'Cells'`` and ``'Reference'``, so spyder-modelx shows them as
  before. The ``'value_type'`` of a Reference whose value is a Cells of
  an ItemSpace is the class name of the value, now ``'DynamicCells'``.

* ``_is_dynamic()``, ``_is_static()`` and ``_is_root()`` are removed
  from :class:`~modelx.core.space.UserSpace`,
  :class:`~modelx.core.space.ItemSpace` and
  :class:`~modelx.core.space.DynamicSpace`. Nothing in modelx called
  them, nor did spyder-modelx, spymx-kernels 0.4.0, modelx-bridge 0.10.0
  or modelx-mcp 0.1.0.
  The class of the Space gives each answer, after the module check of
  :ref:`toolapi-kinds`, and this works on modelx 0.33 too:

  * ``s._is_dynamic()``: ``type(s).__name__ in ('ItemSpace', 'DynamicSpace')``;
  * ``s._is_static()``: ``type(s).__name__ == 'UserSpace'``;
  * ``s._is_root()``: ``type(s).__name__ == 'ItemSpace'``.

  On every Space that has not been deleted, these give what the methods
  returned. A deleted Space still answers by its class, where
  ``_is_dynamic()`` raised
  :class:`~modelx.core.errors.DeletedObjectError`.

* ``(key, value) in cells.items()`` reads only the stored values of the
  Cells, as :meth:`Cells.items<modelx.core.cells.Cells.items>` itself does.
  It is :obj:`False` when no value is stored for ``key``; it used to run
  the formula for ``key``, store the value and compare it. Like
  ``key in cells``, it no longer applies default arguments: for a Cells
  ``g(t, k=1)`` that returns ``(t, k)`` and holds ``g(1)``,
  ``((1,), (1, 1)) in g.items()`` used to be :obj:`True` and is now
  :obj:`False`, while ``((1, 1), (1, 1)) in g.items()`` is :obj:`True`
  as before.


Bug Fixes
============

* :meth:`Cells.values<modelx.core.cells.Cells.values>` and
  :meth:`Cells.items<modelx.core.cells.Cells.items>` now return the stored
  values of a Cells with one parameter whose argument is a tuple, and of a
  Cells with ``*args`` after another parameter.
  They used to look each key up again as ``cells[key]``, which reads a
  tuple as the tuple of all the arguments. For a Cells ``h(x)``, with
  ``h((1, 2))`` stored they raised :obj:`TypeError`; with ``h((1,))``
  stored they returned the value of ``h(1)`` in its place, or, when
  ``h(1)`` was not stored, ran its formula, stored the value and raised
  :obj:`RuntimeError`. For a Cells ``f(a, *args)``, they ran the formula
  and raised :obj:`RuntimeError` whatever the arguments.
  Each value is now read by the key it is stored under, which also makes
  ``values()`` about 40% and ``items()`` about 30% faster: 53 ms instead
  of 95 ms for ``list(h.values())`` over 100,000 values.
  ``values()`` and ``items()`` return ``CellsValuesView`` and
  ``CellsItemsView`` objects, which are instances of
  :class:`collections.abc.ValuesView` and
  :class:`collections.abc.ItemsView`.

  ``key in cells``, ``cells[key]``, ``cells.get(key)`` and
  ``dict(cells)`` still read a tuple key as the tuple of all the
  arguments; see :ref:`cells-value-operations`.

* An ItemSpace now shows its arguments in its display string whatever
  ``add_params`` is, and an ItemSpace of an ItemSpace shows the
  arguments of its parent item, so
  ``_get_repr(fullname=True, add_params=False)`` is the display name of
  every object and no ``__SpaceN`` name shows in it
  (:ref:`toolapi-identity`). For ``Proj`` with the formula
  ``lambda i: None`` and a child Space ``Child`` with a formula:

  * ``Proj[1]._get_repr(fullname=True, add_params=False)`` was
    ``'Model1.__Space1'`` and is ``'Model1.Proj[1]'``;
  * ``Proj[1][5]._get_repr(fullname=True)`` was
    ``'Model1.__Space1[5]'`` and is ``'Model1.Proj[1][5]'``, and with
    ``add_params=False`` it was ``'Model1.__Space2'``, which left out
    ``Proj[1]``;
  * ``Proj[1].Child[2]._get_repr(fullname=True, add_params=False)`` was
    ``'Model1.Proj[1].__Space1'`` and is ``'Model1.Proj[1].Child[2]'``.

  The same strings show in ``repr()``, as in
  ``<DynamicCells Model1.Proj[1][5].bar()>``, where it was
  ``<Cells Model1.__Space1[5].bar()>``, in the ``.info`` header, in the
  ``'repr'`` and ``'repr_parent'`` keys of the dicts of
  ``_get_attrdict`` and ``_baseattrs``, in the ``repr()`` of nodes, and
  in the ``_input_log.txt`` that ``write_model(..., log_input=True)``
  writes. The names that identify objects, ``_name``, ``_idstr`` and
  ``_evalrepr``, are unchanged.

* ``_direct_bases`` of an ItemSpace or a DynamicSpace now lists its one
  base, the UserSpace whose members it has, as ``bases`` does
  (:ref:`toolapi-inheritance`). It named Spaces that are not its bases:
  for ``P`` with the bases ``Base1`` and ``Base2`` and a child Space
  ``Child``, ``P[1]._direct_bases`` and ``P[1].Child._direct_bases``
  both gave ``[Base1, Base2]``, and with another Space ``S(B)`` in the
  model they gave ``[Base1, B, Base2]``. They now give ``[P]`` and
  ``[P.Child]``. The inheritance graph took the internal name of a
  dynamic Space, such as ``'P.__Space1'``, which is not in the graph,
  for the names of its characters, so the bases came from the Spaces
  named ``P`` and ``S``.

* The names in ``extattrs`` of ``_get_attrdict`` are now looked up on
  the class of each object, never on the object itself
  (:ref:`toolapi-wire`). On a Model or a Space, a name that its class
  does not define reached the user's member of that name, if there was
  one, such as a Reference, a Cells or a Space, and called it when it
  was callable. On a model with global References named ``__len__``,
  ``_is_derived``, ``formula`` and ``parameters``, a Space Reference and
  a Cells named ``argvalues``, and a Space formula returning a
  Reference named ``_is_derived``, the names that spyder-modelx requests
  for its tree called those user functions 20 times in one walk, and
  those for its Properties pane called the Model's ``formula`` and
  ``parameters`` globals; they now call none, and the only keys left
  out are those whose values came from those members. On five lifelib
  models, the dicts are the same as before. A property whose value is
  callable, such as the ``value`` of a proxy of a Reference to a
  function, is no longer called.

* The dicts of the ``refs`` view of an ItemSpace no longer raise for
  a Reference that the Space formula returns under a key that is not a
  str, as in ``lambda i: {"refs": {1: "one"}}``, which no formula can
  read. ``_get_attrdict`` of the view, of the ItemSpace and of every
  object that has it in its tree, the Model's included, raised
  :obj:`KeyError`, as did ``_baseattrs`` of the view, and the Model's
  ``_baseattrs`` raised :obj:`RuntimeError`; the dicts now leave such
  a key out.
  A global Reference or a returned Reference named ``''`` made them
  raise :obj:`IndexError`; it is now listed.

* ``RefView._baseattrs_private`` no longer raises :obj:`RuntimeError`.
  It gives the ``_baseattrs`` of every Reference in the view, those
  whose names start with an underscore included.

* The ``_get_attrdict`` and ``_baseattrs`` of an
  :class:`~modelx.core.node.ItemNode` with no stored value, of a Cells
  or of a Space, no longer raise :obj:`ValueError`. ``'predslen'``,
  ``'succslen'`` and ``'precedentslen'`` are :obj:`None` there,
  as ``'value'`` already was.

* :meth:`ReferenceProxy.is_derived()
  <modelx.core.reference.ReferenceProxy.is_derived>` returns
  :obj:`None` on a proxy that does not stand for a Reference, as
  ``_is_derived()`` does. Through an ItemSpace or a DynamicSpace in
  one, the proxy of a Reference that refers to the ItemSpace's own
  copy of its value (see :ref:`reference-proxy-identity`), such as
  ``P[1].rel`` for ``P.rel = P.Child`` or ``P[1].Child.up`` for
  ``P.Child.up = P``, made it raise :obj:`AttributeError` when the
  value was a Space, and it returned :obj:`True` when the value was a
  Cells. A Reference to a Space whose name begins with
  the name of the Space, such as ``PX`` for ``P``, made it raise
  :obj:`AttributeError` too. These proxies are known limitations of
  :ref:`toolapi`.

* :func:`copy.copy` of a :class:`~modelx.core.reference.ReferenceProxy`
  works on Python 3.11 and later, and keeps its class. The copy's
  ``value`` raised :obj:`AttributeError`, because from Python 3.11 the
  copy took the state of the proxy from :class:`object`, a tuple,
  where on Python 3.10 it took the Reference.
