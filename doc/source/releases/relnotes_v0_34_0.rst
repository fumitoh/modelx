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
  a resolved slot (see below),
  and the ``_self``, ``_space`` and ``_model`` of the ItemSpace and of
  the DynamicSpaces in it.
  Together with ItemSpace and DynamicSpace, the class now tells
  whether an object is one that modelx made for an ItemSpace.
  A Reference of a Space that its ItemSpace shares, and a global
  Reference, keep a ReferenceProxy.

* :meth:`ReferenceProxy._is_derived()
  <modelx.core.reference.ReferenceProxy._is_derived>` is :obj:`True`
  for a Reference that a sub Space inherits from a base Space and has
  not redefined, and for a resolved slot (see below),
  and :obj:`False` for any other Reference,
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

* A :class:`~modelx.core.reference.ReferenceProxy` is a tool object of
  its own (:ref:`toolapi-references`):

  * Two proxies of the same Reference are equal and have the same hash,
    however each was obtained, so a tool can keep proxies in a set or
    use them as dict keys. A proxy is never equal to an object that is
    not a proxy, and comparing it with one evaluates nothing.
  * :meth:`~modelx.core.reference.ReferenceProxy._is_valid` tells
    whether the Reference is still bound: it is :obj:`False` once the
    Reference is deleted or bound again, once its Space is deleted, and,
    for the References that an ItemSpace makes, once the ItemSpace is
    deleted, also when an ItemSpace with the same arguments is made
    again.
  * :attr:`ReferenceProxy._refmodes
    <modelx.core.reference.ReferenceProxy._refmodes>` is the tuple of
    the modes, ``('auto', 'absolute', 'relative')``.
  * ``_idstr``, ``_get_repr`` and ``_is_valid`` are defined on the
    class, so ``getattr(type(proxy), name, None)`` finds them.
    The proxy used to forward them, and the answers of ``_idstr`` and
    ``_get_repr`` are the same as forwarding gave on 367 proxies of a
    synthetic model and of lifelib's simplelife and BasicTerm_SE models,
    except for the resolved slots below.

* A Reference that an ItemSpace re-points at its own copy of its value
  is a Reference of the ItemSpace, a *resolved slot*
  (:ref:`toolapi-resolved-slots`). With ``P.rel = P.Child`` and a
  formula on ``P``, ``P[1].rel`` is ``P[1].Child``, and its proxy
  now stands for ``P[1]``'s copy of ``P.rel``: its ``name`` is ``'rel'``,
  its ``parent`` is ``P[1]``, its ``_idstr`` ``'P.__Space1.rel'``,
  its ``refmode`` that of ``P.rel``, and it is a
  :class:`~modelx.core.reference.DynamicReferenceProxy` whose
  ``_is_derived()`` is :obj:`True`.
  ``slot.parent.bases[0]._get_object(slot.name, as_proxy=True)``
  gives the proxy of ``P.rel``.
  Its value, and what formulas see, are unchanged: formula results and
  the number of nodes were the same as before on lifelib's simplelife,
  whose Projection items have 7 resolved slots each, and BasicTerm_SE.

* :meth:`UserSpace._get_inheritance()
  <modelx.core.space.UserSpace._get_inheritance>`, also on ItemSpace
  and DynamicSpace, tells in one call where each Cells and each
  Reference of a Space is defined (:ref:`toolapi-inheritance`).
  For each name in ``cells`` and in ``refs`` it gives the state,
  ``'defined'``, ``'overriding'`` or ``'derived'``, and the Space whose
  definition is in use, and for a Reference also its scope:
  ``'space'``, ``'base'``, ``'argument'``, ``'formula'``, ``'global'``
  or ``'builtins'``. It also gives ``bases`` and ``_direct_bases``.
  It reads no value, so it evaluates nothing.
  One call for every UserSpace of lifelib's BasicTerm_S,
  BasicTermASL_ME and simplelife took 17–19, 108–111 and 164–172 µs
  in all, on CPython 3.11.15.


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

* Two :class:`~modelx.core.reference.ReferenceProxy` objects of the same
  Reference are equal, and their hashes are equal. Before, a proxy was
  equal only to itself: ``a == b`` was :obj:`False` for two proxies of
  ``Base.rate``, and ``{a, b}`` had 2 elements, where it now has 1.
  A Reference that an ItemSpace shares with its Space is one Reference,
  so ``P[1]._get_object("k", as_proxy=True)`` now equals
  ``P._get_object("k", as_proxy=True)``, and the proxy of a global
  Reference is the same through the Model and through any Space.
  ``proxy == obj`` is :obj:`False` for any ``obj`` that is not a
  proxy. Before, Python then asked ``obj``: for a Cells with parameters
  it raised :obj:`TypeError`, and for a Cells with no parameters it ran
  the Cells' formula. With the Cells on the left, ``cells == proxy`` is
  still the Cells' comparison.
  None of spyder-modelx, spymx-kernels, modelx-bridge and modelx-mcp
  compares proxies or keeps them in sets.

* :meth:`ReferenceProxy._is_valid()
  <modelx.core.reference.ReferenceProxy._is_valid>` is :obj:`False`
  for a proxy whose Reference is no longer bound (see Enhancements).
  Before, it was :obj:`True` for every proxy: after ``del space.x``
  and after ``space.x = 2``, after the Space of the Reference was
  deleted, and after the ItemSpace that made the Reference, such as an
  argument, was deleted, by ``del``, by ``clear_items()``, or by an edit
  such as binding a Reference of its Space or of a base of it, or any
  global Reference, whether new or bound again.
  ``repr()`` of such a proxy shows a null object, as for a deleted Cells:
  ``<ReferenceProxy null object>`` or
  ``<DynamicReferenceProxy null object>``, where it showed the
  Reference, as in ``<ReferenceProxy Model1.Base.rate>``.
  The other members of such a proxy still answer, and its ``value``
  is the value the Reference had. The proxies of a closed Model's
  References stay valid, as the closed Model does.

* Through an ItemSpace, or a DynamicSpace in it, the proxy of a
  Reference that refers to the ItemSpace's own copy of its value
  (see :ref:`reference-proxy-identity`) now stands for a Reference of
  the ItemSpace, its resolved slot (see Enhancements), not for the copy.
  For ``Proj.rel = Proj.Child`` in a model ``Model1``, the proxy of
  ``rel`` obtained through ``Proj[1]``:

  * ``name``: was ``'Child'``, and is ``'rel'``;
  * ``fullname``: was ``'Model1.Proj.__Space1.Child'``, and is
    ``'Model1.Proj.__Space1.rel'``;
  * ``_idstr``: was ``'Proj.__Space1.Child'``, and is
    ``'Proj.__Space1.rel'``;
  * ``_evalrepr``: was ``'Model1.Proj(1).Child'``, and is
    ``'Model1.Proj(1).rel'``;
  * ``_get_repr()``: was ``'Child'``, and is ``'rel'``;
  * ``refmode``: raised :obj:`AttributeError`, and is the mode of
    ``Proj.rel``, ``'auto'``;
  * ``is_derived()``: raised :obj:`AttributeError`, and is :obj:`True`,
    as is the new ``_is_derived()``;
  * the class: was :class:`~modelx.core.reference.ReferenceProxy`, and
    is :class:`~modelx.core.reference.DynamicReferenceProxy`;
  * ``_is_valid()``: was :obj:`True` for ever, and turns :obj:`False`
    when ``Proj[1]`` is deleted;
  * ``parent``: ``Proj[1]`` before and after.

  For a Reference whose value is the ItemSpace itself, such as
  ``Proj.me = Proj``, ``parent`` changes too: it was ``Proj`` and is
  ``Proj[1]``, and ``name`` was the ``__SpaceN`` name of the ItemSpace.
  For a value that is a Cells, such as ``Proj.relc = Proj.Child.w``,
  ``name`` was ``'w'``, ``_get_repr()`` ``'w()'`` and ``parent``
  ``Proj[1].Child``, and ``is_derived()`` was :obj:`True`.
  In each case, ``parent`` was the parent of the copy, and is the
  ItemSpace, or the DynamicSpace in it whose Space holds the Reference.
  The record of such a Reference in the ``'refs'`` of the dicts of
  ``_get_attrdict`` and ``_baseattrs`` changes in the same way:
  its ``'id'``, ``'name'``, ``'fullname'``, ``'repr'`` and ``'namedid'``
  were those of the copy. The value of the Reference, and what the
  formulas see, are unchanged.

* :meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>`
  raises :obj:`ValueError` for a ``refmode`` that is not
  ``'auto'``, ``'absolute'`` or ``'relative'``, as its docstring says,
  and changes nothing. Before, it stored any mode, such as
  ``'sideways'``, :obj:`None` or ``42``, and for a Reference to a Cells
  or a Space such a mode made the creation of a sub Space fail later
  with ``ValueError: must not happen``, and, when the value was outside
  the Space, the creation of any ItemSpace of the Space fail with
  :class:`~modelx.core.errors.FormulaError` from
  ``RuntimeError: must not happen``.
  :func:`~modelx.read_model` does not check the mode, so a model saved
  with such a mode still reads, and fails in the same ways.

* :meth:`UserSpace.set_ref <modelx.core.space.UserSpace.set_ref>`,
  :meth:`~modelx.core.space.UserSpace.absref` and
  :meth:`~modelx.core.space.UserSpace.relref` raise
  :obj:`AttributeError` for the name of a Cells of the Space, defined or
  inherited, as ``'a' is already defined as a Cells``, and for the name
  of a child Space, as ``'Child' is already defined as a Space``,
  as the docstring of ``set_ref`` says, and change nothing.
  Before, the name of a Cells with no parameters set the input of the
  Cells and made no Reference, the name of a Cells with parameters
  raised :obj:`AttributeError` with another message, and the name of a
  child Space raised :obj:`ValueError` with no message.
  Assigning to the attribute, ``space.a = 3``, still sets the input of
  the Cells ``a``.
  :func:`~modelx.read_model` does not make this check either, so a model
  that 0.33 saved with a Reference and a Cells of one name still reads,
  as on 0.33.

* :meth:`Model.new_space <modelx.core.model.Model.new_space>`
  raises :obj:`ValueError` for the name of a Macro of the Model, as it
  does for the name of a Space or a global Reference, and so do
  :meth:`UserSpace.rename <modelx.core.space.UserSpace.rename>`
  and :meth:`UserSpace.copy <modelx.core.space.UserSpace.copy>`
  for a Space of the Model.
  Before, the Space was made and hid the Macro: ``model.mac`` gave the
  Space. ``new_space()`` without a name skips a Macro's name, so with a
  Macro named ``Space1`` it makes ``Space2``, where it made ``Space1``.
  A child Space of a Space can still have a Macro's name.
  No saved model can hold both: modelx 0.33 wrote such a model,
  but :func:`~modelx.read_model` raised
  ``ValueError: Name 'mac' already used`` for the file it wrote,
  on 0.33 too, and serializer version 6 leaves the Macros out.

* Assigning to a read-only property of a Model or a UserSpace, such as
  ``space.name = 'x'`` or ``space.bases = other``, raises
  :obj:`AttributeError`, as ``name is read-only``, where it raised
  :obj:`TypeError` (``'NoneType' object is not callable``).
  That covers 23 properties of UserSpace and 16 of Model.


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
  <modelx.core.reference.ReferenceProxy.is_derived>` no longer raises.
  Through an ItemSpace or a DynamicSpace in one, the proxy of a
  Reference that refers to the ItemSpace's own copy of its value
  (see :ref:`reference-proxy-identity`), such as ``P[1].rel`` for
  ``P.rel = P.Child`` or ``P[1].Child.up`` for ``P.Child.up = P``,
  made it raise :obj:`AttributeError` when the value was a Space,
  and it returned the flag of the copy, :obj:`True`, when the value was
  a Cells. It now returns :obj:`True` for both, because such a proxy is
  a resolved slot, which is derived (see Backward Incompatible Changes).
  A Reference of ``P`` to a Space outside ``P`` whose name begins with
  ``P``, such as ``P.r = PX``, made it raise :obj:`AttributeError`
  through ``P[1]``; it now returns :obj:`False`, the flag of ``P.r``.

* :func:`copy.copy` of a :class:`~modelx.core.reference.ReferenceProxy`
  works on Python 3.11 and later, and keeps its class. The copy's
  ``value`` raised :obj:`AttributeError`, because from Python 3.11 the
  copy took the state of the proxy from :class:`object`, a tuple,
  where on Python 3.10 it took the Reference.

* In the ItemSpaces of a Space ``P``, a Reference of ``P``, or of a
  Space inside ``P``, to a Space outside ``P`` whose name begins with the
  name of ``P``, such as ``P.r = PX``, or to a Cells or a Space inside
  such a Space, works. modelx took ``PX`` to be inside ``P``, because
  its full name begins with ``P``'s, and found no copy of it in ``P[1]``.
  So ``P[1].r`` was missing, and every formula of ``P[1]`` that read
  ``r`` raised :obj:`AttributeError`
  (``'NoneType' object has no attribute 'interface'``);
  ``P[1]._get_object("r")`` raised :obj:`NameError`, and with
  ``as_proxy=True`` it gave a proxy whose ``value`` and ``name`` raised
  :obj:`AttributeError`;
  ``model._get_from_name("P.__Space1.r")`` raised :obj:`AttributeError`;
  and the dicts of ``_get_attrdict`` of ``P[1]``, of its ``refs`` view and
  of the Model raised :obj:`AttributeError`, and the Model's
  ``_baseattrs`` :obj:`RuntimeError`, so spyder-modelx could not show
  the Model.
  ``P[1].r`` is now ``PX``, as ``P.r`` is, and its proxy is that of
  ``P.r``. A Reference made by ``relref``, whose value must be inside
  ``P``, now makes ``P[1]`` fail as for any other Space outside ``P``,
  with :class:`~modelx.core.errors.FormulaError` from
  ``ValueError: 'PX' referred as 'P.r' is out of 'P'``,
  where ``P[1]`` was made and its formulas failed as above.

* An ItemSpace can be made from a Space whose derived Reference has
  the mode ``'auto'`` and refers, relative to the sub Space, to a Space
  outside it. With ``Y`` derived from ``X``, ``Y.P`` derived from
  ``X.P``, ``X.P.r = X.Other`` and a ``Y.Other``, ``Y.P.r`` is
  ``Y.Other``, and making ``Y.P[1]`` raised
  ``AttributeError: 'ReferenceImpl' object has no attribute
  'direct_bases'``. ``Y.P[1].r`` is now ``Y.Other``, as ``Y.P.r`` is.

* In the ItemSpaces of a Space ``P``, a Reference of ``P`` to an
  ItemSpace of a Space inside ``P``, such as ``P.r = P.Child[3]``,
  works. No ItemSpace has a copy of ``P.Child[3]``, and the formulas of
  ``P[1]`` that read ``r`` raised :obj:`AttributeError`, as above.
  ``P[1].r`` is now ``P.Child[3]``, as ``P.r`` is.

* A formula of an ItemSpace, or of a DynamicSpace in it, can read a
  Reference that refers to the ItemSpace's own copy of its value
  (see :ref:`reference-proxy-identity`) as an attribute of a namespace,
  such as ``_space.rel`` for ``P.rel = P.Child``, or ``rel.up`` for
  ``P.Child.up = P``. It raised :obj:`AssertionError`.
