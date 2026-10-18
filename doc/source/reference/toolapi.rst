.. _toolapi:

API for tools
=============

This page is for authors of software that reads and drives modelx models
from the outside: IDE plugins such as spyder-modelx,
kernel-side libraries such as modelx-bridge,
and MCP servers such as modelx-mcp.
It lists the members of modelx objects that such software can rely on,
says which of them are frozen, and shows how a tool detects
what the installed modelx provides.
Users who write models do not need anything on this page.

Most examples on this page use this model:

    >>> import modelx as mx

    >>> m = mx.new_model("Model1")

    >>> base = m.new_space("Base")

    >>> foo = base.new_cells("foo", formula=lambda x: 2 * x)

    >>> base.rate = 0.05

    >>> sub = m.new_space("Sub", bases=base)

    >>> proj = m.new_space("Proj", formula=lambda i: None)

    >>> child = proj.new_space("Child")

    >>> bar = proj.new_cells("bar", formula=lambda: i)

    >>> m.scale = 10

    >>> item = proj[1]


.. _toolapi-underscore:

The underscore convention
-------------------------

A member of a modelx object whose name starts with an underscore is
**not private**.
On :class:`~modelx.core.model.Model`, the Space classes
(:class:`~modelx.core.space.UserSpace`,
:class:`~modelx.core.space.ItemSpace` and
:class:`~modelx.core.space.DynamicSpace`),
:class:`~modelx.core.cells.Cells` and its subclass
:class:`~modelx.core.cells.DynamicCells`,
:class:`~modelx.core.macro.Macro`,
:class:`~modelx.core.reference.ReferenceProxy` and its subclass
:class:`~modelx.core.reference.DynamicReferenceProxy`, the view classes,
the node classes, :class:`~modelx.core.formula.Formula`
and the IOSpec classes,
an underscore member is public: it belongs to the *API for tools*,
which is meant for other software, not for users writing models.

The underscore keeps these members out of the way of the names
that users give to their own objects.
Most routes that name an object refuse a name that starts with
an underscore:
:func:`~modelx.new_model`, ``new_space``, ``copy``,
``Model.rename``, ``Cells.rename``, :func:`~modelx.defmacro`,
``space.x = value``,
:meth:`~modelx.core.space.UserSpace.set_ref`,
:meth:`~modelx.core.space.UserSpace.absref` and
:meth:`~modelx.core.space.UserSpace.relref` raise :obj:`ValueError`
for such a name.

.. admonition:: Known limitation

   On this release, other routes do not refuse such a name:

   * ``new_cells`` and :func:`~modelx.defcells` replace it,
     like any other name that is not valid,
     with an automatic name such as ``Cells1``:
     ``new_cells("_hidden")`` creates a Cells named ``Cells1``.
   * Global References (``model._x = value``, and
     :meth:`Model.new_pandas <modelx.core.model.Model.new_pandas>`,
     :meth:`~modelx.core.model.Model.new_module` and
     :meth:`~modelx.core.model.Model.new_excel_range`),
     References created by ``new_space(refs=...)``,
     the parameters of a Space formula
     and the ``refs`` that a Space formula returns accept it.
   * :meth:`UserSpace.rename <modelx.core.space.UserSpace.rename>`
     checks no name. It accepts ``'_x'``, and also ``''``, ``'1x'``,
     ``'a-b'`` and ``'class'``, which are not valid names.

   A later release may warn about such names on the routes
   in the first two items, and then refuse them.
   This is not part of the frozen contract and may change.

An object named through one of these routes can have the name of a tool
member.
Attribute access from outside the model then finds the class member,
while a Formula that uses the name reads the user's object.
This is why a tool tests for a member on the class,
as described in :ref:`toolapi-detection`.

Some underscore attributes are not tool API:
the ``_impl`` attribute of an object, the ``_impls`` attribute of a view,
and the ``_io`` and ``_manager`` attributes of an IOSpec.
They, and everything reached through them, are internal;
see :ref:`toolapi-not`.
Names with two leading and two trailing underscores, such as ``__len__``,
are Python's special names, not tool API members.


.. _toolapi-tiers:

Frozen members and other members
--------------------------------

The tool API has two tiers.

Frozen
    The members listed on this page, from modelx 0.34.0,
    the first release with this page.
    A frozen member changes only through the deprecation process below.
    What is frozen is the member and its behaviour as this page
    describes it, except the behaviour that a note headed
    **Known limitation** describes (see below).

    A test, ``modelx/tests/core/api/test_tool_api_surface.py``,
    pins the signature of every listed member against a golden file:
    that the member exists, its kind (property, method or other
    attribute) and, for a method, its parameters as
    :func:`inspect.signature` gives them.
    It also pins the classes of :mod:`modelx.core.errors` listed in
    :ref:`toolapi-errors`, with their base classes,
    and the twelve class names that :ref:`toolapi-kinds` lists:
    for an object of each, the name of its class and that the class
    passes the module check.
    The test looks each member up on the class of an object that
    a tool holds, as :ref:`toolapi-detection` describes,
    and checks the members that a ReferenceProxy forwards on a proxy.
    It pins the members that this page lists, on the classes it lists
    them on, with three differences of class only:

    * The members listed on Cells and on ReferenceProxy,
      the forwarded ones included,
      are pinned also on their subclasses
      :class:`~modelx.core.cells.DynamicCells` and
      :class:`~modelx.core.reference.DynamicReferenceProxy`,
      the classes of a Cells of an ItemSpace and of the proxy of
      an argument of an ItemSpace.
    * ``Formula._get_attrdict`` is pinned on
      :class:`~modelx.core.formula.Formula` and also on its two subclasses
      ``NullFormula`` and ``ParamFunc``, the classes of the formula of
      a Cells without a formula and of the formula of a Space.
    * ``BaseIOSpec._get_attrdict`` is not pinned on
      :class:`~modelx.io.baseio.BaseIOSpec` itself, because no object
      that a tool holds is of that class. It is pinned on
      :class:`~modelx.io.moduleio.ModuleData`, which inherits it,
      and on :class:`~modelx.io.pandasio.PandasData` and
      :class:`~modelx.io.excelio.ExcelRange`, which extend it.
      The last two are checked only where pandas and openpyxl are
      installed.

    That test pins no behaviour.
    ``modelx/tests/core/api/test_tool_contracts.py`` tests some of
    the behaviour that this page describes, and pins none of the
    known limitations.

Tool API, not frozen
    Every other member that modelx defines on the classes above
    whose name starts with an underscore and is not a special name
    such as ``__len__``,
    except the attributes that :ref:`toolapi-not` lists.
    For example,
    ``Formula._reload``, ``BaseIOSpec._on_update``,
    ``CellsView._set_keys``, ``SpaceView._baseattrs_private`` and
    ``_get_attrdict_extra``.
    They are public for tools, but a release may change or remove one,
    with a note in the release notes.
    A tool that needs one of them to stay as it is can ask for it
    to be listed on this page, which makes it frozen.
    Attributes that a class gets from Python's :mod:`collections.abc`
    or :mod:`typing` base classes, such as ``_abc_impl`` on Cells and
    ``_is_protocol`` on the views, are not tool API.

Additions are not changes:
a frozen member may gain an optional keyword parameter,
and a dict that it returns may gain keys.
A tool should ignore keys that it does not know.
A fix that makes a member behave as this page describes is a bug fix,
listed under "Bug Fixes" in the release notes.

A note headed **Known limitation** describes behaviour of this release
that is a defect, or that a later release is planned to change,
such as an exception that a member raises by accident
or a value that is wrong in some cases.
That behaviour is not part of the frozen contract,
even when it is the behaviour of a frozen member:
it may change in any release, without the deprecation process,
and the tests named above do not pin it.
A tool should not rely on it.

There is no registry of tool members at run time,
and the tool API has no version number of its own.
This page and the release notes are the record of what exists,
and a tool detects what the installed modelx provides
as described in :ref:`toolapi-detection`.


.. _toolapi-deprecation:

Deprecation
-----------

To change or remove a frozen member, modelx follows these steps:

#. The member is marked as deprecated on this page
   and in the "Deprecations" section of the release notes.

#. Using the member emits a ``ToolAPIDeprecationWarning``,
   a subclass of :obj:`UserWarning`.
   This warning class does not exist in this release.
   It will be added to :mod:`modelx.core.errors` in a later release.

#. The member keeps working, with the warning,
   for at least two minor releases.

#. After that, the member is removed only when the released
   modelx-bridge and modelx-mcp pass their tests without it.
   The removal is listed under "Backward Incompatible Changes"
   in the release notes.

The class names that :ref:`toolapi-kinds` lists are the one exception.
A tool reads ``type(obj).__name__`` without running any code of modelx,
so modelx cannot warn when a tool uses a name.
Such a name follows the steps above without the warning:
it is marked as deprecated on this page and in the "Deprecations"
section of the release notes at least two minor releases before
the class is renamed or split,
and the rename or split is made only when the released modelx-bridge
and modelx-mcp pass their tests with it.
It is listed under "Backward Incompatible Changes" in the release notes.

No frozen member and no listed class name is deprecated in this release.


.. _toolapi-detection:

Detecting what modelx provides
------------------------------

Members
    Look a member up on the class, never on the instance::

        getattr(type(obj), name, None)

    A Model or a Space answers an attribute that its class does not define
    with one of its own members of that name,
    such as a child Space, a Cells or a Reference,
    global References included.
    So :func:`hasattr` on the instance can find a user's object
    instead of a tool member.
    The example below names a global Reference with an underscore,
    which this release accepts but a later release may refuse
    (see the known limitation under :ref:`toolapi-underscore`):

    >>> m2 = mx.new_model("Model2")

    >>> s2 = m2.new_space("Space1")

    >>> m2._new_member = 1

    >>> hasattr(m2, "_new_member"), hasattr(s2, "_new_member")
    (True, True)

    >>> getattr(type(m2), "_new_member", None) is None
    True

    >>> m2.close()

    A :class:`~modelx.core.reference.ReferenceProxy` answers some members
    by forwarding them (see :ref:`toolapi-wire`).
    Every member that this page lists as forwarded is answered
    on every release that has this page, so a tool does not need to detect it.

    .. admonition:: Known limitation

       On this release the forwarded members are not attributes of the
       ReferenceProxy class: ``getattr(type(proxy), "_idstr", None)``
       is :obj:`None` although ``proxy._idstr`` works.
       Which of them the class defines and which it forwards
       is not part of the frozen contract and may change:
       a later release may define some of them on the class.

Kinds
    Tell a modelx object from any other value, and which kind of
    object it is, by the name of its class,
    after checking that the class is defined in a module of modelx,
    as described in :ref:`toolapi-kinds`.

Top-level names
    Look a top-level name up in the module's namespace::

        vars(modelx).get(name)

    When the :mod:`modelx` module has no attribute of a name,
    ``modelx.<name>`` returns the open Model of that name,
    so :func:`getattr` on the module can return a Model:

    >>> fe = mx.new_model("FormulaError")

    >>> getattr(mx, "FormulaError")
    <Model FormulaError>

    >>> vars(mx).get("FormulaError") is None
    True

    >>> fe.close()

Behaviour
    Compare ``modelx.VERSION``, a tuple of integers,
    with the version that introduced the behaviour::

        if modelx.VERSION >= (0, 33, 0):
            ...


.. _toolapi-identity:

Identity and addressing
-----------------------

These members name and find objects.
Model, the Space classes, Cells and Macro define
``_idstr``, ``_idtuple``, ``_evalrepr``, ``_get_repr``,
``_name``, ``_parent``, ``_get_object`` and ``_is_valid``.
A ReferenceProxy defines ``_evalrepr``, and also answers
``_idstr``, ``_idtuple``, ``_get_repr``, ``_name``, ``_parent``
and ``_is_valid``
(see "ReferenceProxy forwarding" under :ref:`toolapi-wire`).
The node classes define a ``_get_repr`` of their own,
with other parameters.

``_idstr``
    The dotted name of the object without the name of its Model:
    ``''`` for a Model.
    An ItemSpace appears under its ``__SpaceN`` name,
    which modelx gives the ItemSpace when it creates it.
    An ItemSpace that is deleted and created again with the same arguments
    gets a new ``__SpaceN`` name,
    so an ``_idstr`` that contains one is valid only while that ItemSpace lives.
    On a ReferenceProxy, a global Reference has its name alone as its
    ``_idstr``, from whichever Space the proxy was obtained,
    and an argument of an ItemSpace has the ``_idstr`` of the ItemSpace
    followed by its name.
    The ``'namedid'`` key of :ref:`attrdicts <toolapi-wire>` holds it.

    >>> [obj._idstr for obj in (m, base, foo, item, item.bar, item.Child)]
    ['', 'Base', 'Base.foo', 'Proj.__Space1', 'Proj.__Space1.bar', 'Proj.__Space1.Child']

    >>> base._get_object("scale", as_proxy=True)._idstr
    'scale'

    >>> item._get_object("i", as_proxy=True)._idstr
    'Proj.__Space1.i'

``_idtuple``
    A tuple that starts with the name of the Model,
    followed by the name of each object down to this one.
    An ItemSpace contributes its argument values,
    :attr:`~modelx.core.space.ItemSpace.argvalues`, instead of its name.

    >>> item.bar._idtuple
    ('Model1', 'Proj', (1,), 'bar')

``_evalrepr``
    The full name of the object in call syntax, with the name of its Model.
    An ItemSpace appears as a call to its Space,
    with each argument formatted by :func:`repr`.

    >>> item.Child._evalrepr
    'Model1.Proj(1).Child'

``_get_repr(fullname=False, add_params=True)``
    The display string of the object.
    With ``fullname=True`` it starts with the name of the Model.
    With ``add_params=True`` a Cells shows its parameters.
    An ItemSpace shows its arguments whatever ``add_params`` is,
    and an ItemSpace of an ItemSpace shows the arguments of its parent
    item before its own.
    So ``_get_repr(fullname=True, add_params=False)`` is
    the display name of every object, and no ``__SpaceN`` name is in it.

    >>> foo._get_repr(), foo._get_repr(fullname=True)
    ('foo(x)', 'Model1.Base.foo(x)')

    >>> foo._get_repr(fullname=True, add_params=False)
    'Model1.Base.foo'

    >>> item._get_repr(), item.bar._get_repr(fullname=True)
    ('Proj[1]', 'Model1.Proj[1].bar()')

    >>> item._get_repr(fullname=True, add_params=False)
    'Model1.Proj[1]'

    >>> item[5]._get_repr(), item[5].bar._get_repr(fullname=True, add_params=False)
    ('Proj[1][5]', 'Model1.Proj[1][5].bar')

    .. versionchanged:: 0.34.0
       Before, ``add_params=False`` gave the ``__SpaceN`` name of an
       ItemSpace, as in ``'Model1.__Space1'`` for ``Proj[1]``,
       and an ItemSpace of an ItemSpace named its parent item by
       its ``__SpaceN`` name, as in ``'__Space1[5]'`` for ``Proj[1][5]``.

``_name``, ``_parent``
    The same as ``name`` and ``parent``.
    The ``_name`` of an ItemSpace is its ``__SpaceN`` name,
    and the ``_parent`` of a Model is :obj:`None`.

``_get_object(name, as_proxy=False)``
    Finds an object by a dotted name relative to this object.
    Each part is read as an attribute of the object before it.
    So a part can be a child Space, a Cells, a Reference, which gives its value,
    or an ItemSpace by its ``__SpaceN`` name.
    The last part can also be an attribute that is not a modelx object,
    such as ``cells`` or ``formula``; spyder-modelx relies on this.
    With ``as_proxy=True``, a part that names a Reference of a Model or a Space
    gives a :class:`~modelx.core.reference.ReferenceProxy`
    instead of its value.
    A name that is not found raises :obj:`NameError`.
    :func:`modelx.get_object` resolves the name of the Model,
    then calls this method of the Model.

    >>> m._get_object("Base.foo")
    <Cells Model1.Base.foo(x)>

    >>> m._get_object("Base.rate"), m._get_object("Base.rate", as_proxy=True)
    (0.05, <ReferenceProxy Model1.Base.rate>)

    >>> m._get_object("Proj.__Space1.bar")
    <DynamicCells Model1.Proj[1].bar()>

    >>> m._get_object("Base.foo.formula")
    lambda x: 2 * x

    >>> mx.get_object("Model1.Base.cells")
    {foo}

    .. admonition:: Known limitation

       With ``as_proxy=True``, the parts after a Reference are ignored:
       ``m._get_object("Base.rate.real", as_proxy=True)``
       returns the proxy of ``rate``.
       This is not part of the frozen contract and may change.

    .. admonition:: Known limitation

       A name that continues past an object that is not a modelx object,
       such as the value of a Reference or a leaf attribute,
       as in ``"Base.rate.real"`` or ``"Base.foo.formula.source"``,
       raises :obj:`AttributeError` on this release,
       because the lookup asks that object for its ``_get_object``
       (for ``"Base.rate.real"``,
       ``'float' object has no attribute '_get_object'``).
       :func:`modelx.get_object` raises the same.
       The type and the message of this exception are not part of
       the frozen contract and may change.

    .. admonition:: Known limitation

       In the ItemSpaces of a Space, a Reference of the Space to a Space
       whose name begins with the name of the Space is not found,
       or gives a broken proxy with ``as_proxy=True``;
       see :ref:`the note on such References <toolapi-prefix-ref>`.
       This is not part of the frozen contract and may change.

``Model._get_from_name(name)``
    Finds an object by its ``_idstr``.
    It finds a name whose first part is a Space of the Model
    and whose parts after it are child Spaces, ItemSpaces by their
    ``__SpaceN`` names, Cells, or References, which give their values.
    For every Space and every Cells,
    ``model._get_from_name(obj._idstr) is obj``.

    >>> m._get_from_name("Proj.__Space1.Child") is item.Child
    True

    .. admonition:: Known limitation

       On this release ``_get_from_name`` does not find the Model
       itself (``''``), a global Reference or a Macro:
       their names raise :obj:`KeyError`, as does a first part
       that is not the name of a Space of the Model.
       A later part that is not found, and a name that continues past
       the value of a Reference, raise :obj:`AttributeError`
       (``'NoneType' object has no attribute 'interface'``),
       as a side effect of the lookup.
       A later part ``__builtins__``, ``_self``, ``_space`` or ``_model``,
       as in ``'Base.__builtins__'`` or ``'Base._self'``,
       resolves to the :mod:`builtins` module
       or to an internal namespace object of modelx, which is not tool API,
       although only ``__builtins__`` is in ``refs``;
       a later release may refuse these four names.
       What it returns for them, which other names it finds,
       and what it raises for the names it does not find,
       are not part of the frozen contract and may change.
       See also :ref:`the known limitation on a Reference to a Space
       whose name begins with the name of the Space <toolapi-prefix-ref>`.

``_named_itemspaces`` (Spaces)
    A mapping of the ItemSpaces that the Space has created and that exist,
    by their ``__SpaceN`` names.
    The public ``itemspaces`` maps the same ItemSpaces by their arguments.
    ItemSpaces are not in ``spaces`` or ``named_spaces``.

    >>> dict(proj._named_itemspaces)
    {'__Space1': <ItemSpace Model1.Proj[1]>}

``_is_valid()``
    :obj:`False` once the object has been deleted.
    Most other members of a deleted object raise
    :class:`~modelx.core.errors.DeletedObjectError`.

    .. admonition:: Known limitation

       A :class:`~modelx.core.macro.Macro` returns :obj:`True` after
       it has been deleted, and a ReferenceProxy returns :obj:`True`
       after its Reference has been deleted or given another value.
       This is not part of the frozen contract and may change.

    .. admonition:: Known limitation

       Closing a Model does not make the Model or its objects
       invalid on this release: their ``_is_valid()`` stays :obj:`True`.
       This is not part of the frozen contract and may change.

    .. admonition:: Known limitation

       An ItemSpace that a tool holds after it was deleted,
       and a DynamicSpace in it, become valid again
       when the Space creates the item again with the same arguments,
       because modelx reuses the same objects on this release.
       The ItemSpace's ``_idstr`` then has a new ``__SpaceN`` name.
       The Cells in it are not revived:
       a Cells of the deleted item that a tool holds stays invalid.
       This is not part of the frozen contract and may change.

``_get_repr(fullname=True, add_value=False)`` (nodes)
    The display string of a node:
    the display name of the node's object,
    as ``_get_repr(fullname, add_params=False)`` of the object gives it,
    followed, for an :class:`~modelx.core.node.ItemNode`,
    by its arguments by parameter name, each formatted by :func:`repr`.
    A :class:`~modelx.core.reference.ReferenceNode` has no arguments.
    With ``add_value=True``, a node that has a value is followed by
    ``=`` and the :func:`repr` of the value, with a line break before
    a value whose :func:`repr` spans lines.
    That is the :func:`repr` of the node.
    A node with no value gives the same string either way.
    A tool does not need to format the arguments itself.

    >>> foo(3)
    6

    >>> foo.node(3)._get_repr(), foo.node(3)._get_repr(add_value=True)
    ('Model1.Base.foo(x=3)', 'Model1.Base.foo(x=3)=6')

    >>> foo.node(4)._get_repr(fullname=False, add_value=True)
    'foo(x=4)'

    >>> item.bar()
    1

    >>> [node._get_repr() for node in item.bar.precedents()]
    ['Model1.Proj[1].i']

    >>> proj.node(1)._get_repr()
    'Model1.Proj(i=1)'

    .. versionadded:: 0.34.0

.. currentmodule:: modelx.core.model

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Model._idstr
  Model._idtuple
  Model._evalrepr
  Model._get_repr
  Model._name
  Model._parent
  Model._get_object
  Model._is_valid
  Model._get_from_name

.. currentmodule:: modelx.core.space

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  UserSpace._idstr
  UserSpace._idtuple
  UserSpace._evalrepr
  UserSpace._get_repr
  UserSpace._name
  UserSpace._parent
  UserSpace._get_object
  UserSpace._is_valid
  UserSpace._named_itemspaces
  ItemSpace._idstr
  ItemSpace._idtuple
  ItemSpace._evalrepr
  ItemSpace._get_repr
  ItemSpace._name
  ItemSpace._parent
  ItemSpace._get_object
  ItemSpace._is_valid
  ItemSpace._named_itemspaces
  DynamicSpace._idstr
  DynamicSpace._idtuple
  DynamicSpace._evalrepr
  DynamicSpace._get_repr
  DynamicSpace._name
  DynamicSpace._parent
  DynamicSpace._get_object
  DynamicSpace._is_valid
  DynamicSpace._named_itemspaces

.. currentmodule:: modelx.core.cells

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Cells._idstr
  Cells._idtuple
  Cells._evalrepr
  Cells._get_repr
  Cells._name
  Cells._parent
  Cells._get_object
  Cells._is_valid

.. currentmodule:: modelx.core.macro

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Macro._idstr
  Macro._idtuple
  Macro._evalrepr
  Macro._get_repr
  Macro._name
  Macro._parent
  Macro._get_object
  Macro._is_valid

.. currentmodule:: modelx.core.reference

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ReferenceProxy._evalrepr

.. currentmodule:: modelx.core.node

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ItemNode._get_repr

.. currentmodule:: modelx.core.reference

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ReferenceNode._get_repr


.. _toolapi-kinds:

Kinds of objects
----------------

A tool tells what a value is from its class.
It first checks that the class is one of modelx's own:
that ``type(v).__module__`` is a str that starts with ``"modelx."``.
Then it reads the name of the class, ``type(v).__name__``.
There is no member for this,
so the check reads nothing from the object itself:

    >>> KINDS = frozenset({
    ...     'Model', 'UserSpace', 'ItemSpace', 'DynamicSpace',
    ...     'Cells', 'DynamicCells', 'Macro',
    ...     'ReferenceProxy', 'DynamicReferenceProxy',
    ...     'PandasData', 'ExcelRange', 'ModuleData'})

    >>> def kind(v):
    ...     t = type(v)
    ...     mod = t.__module__    # not always a str
    ...     if not (isinstance(mod, str) and mod.startswith('modelx.')):
    ...         return None       # never a user's own class named Model
    ...     return t.__name__ if t.__name__ in KINDS else None

    >>> [kind(obj) for obj in (m, base, item, item.Child, foo, item.bar)]
    ['Model', 'UserSpace', 'ItemSpace', 'DynamicSpace', 'Cells', 'DynamicCells']

    >>> kind(base._get_object("rate", as_proxy=True)), kind(item._get_object("i", as_proxy=True))
    ('ReferenceProxy', 'DynamicReferenceProxy')

    >>> kind(base.rate), kind(m.spaces), kind(foo.node(3))
    (None, None, None)

The twelve names are:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Objects
   * - ``'Model'``
     - A Model.
   * - ``'UserSpace'``
     - A static Space, one that ``new_space`` or a model file creates,
       such as ``Base``, ``Sub`` and ``Proj.Child``.
   * - ``'ItemSpace'``
     - A Space that calling or subscripting a Space with a formula
       creates, such as ``Proj[1]``,
       also when that Space is itself an ItemSpace or a DynamicSpace,
       as for ``Proj[1][5]``.
   * - ``'DynamicSpace'``
     - The copy of a child Space in an ItemSpace, such as ``Proj[1].Child``,
       and of a child Space of that copy.
   * - ``'Cells'``
     - A Cells of a UserSpace, defined there or inherited from a base Space.
   * - ``'DynamicCells'``
     - A Cells of an ItemSpace or of a DynamicSpace
       (:class:`~modelx.core.cells.DynamicCells`).
   * - ``'Macro'``
     - A Macro.
   * - ``'ReferenceProxy'``
     - The proxy of a global Reference, and of a Reference of a UserSpace,
       also when it is obtained through an ItemSpace of the Space.
   * - ``'DynamicReferenceProxy'``
     - The proxy of a Reference that an ItemSpace makes:
       an argument of the ItemSpace, a Reference that its Space formula
       returns in ``'refs'``, and the ``_self``, ``_space`` and ``_model``
       of the ItemSpace and of the DynamicSpaces in it
       (:class:`~modelx.core.reference.DynamicReferenceProxy`).
   * - ``'PandasData'``, ``'ExcelRange'``, ``'ModuleData'``
     - The IOSpec objects that ``new_pandas``, ``new_excel_range`` and
       ``new_module`` create, as ``Model.iospecs`` lists them.
       An ExcelRange is also the value of its Reference.

These twelve names are frozen,
and so is the promise that each of these classes is defined
in a module of the :mod:`modelx` package.
The modules themselves, such as ``modelx.core.model``
or ``modelx.io.excelio``, are not tool API (see :ref:`toolapi-not`).
A later release may add a name, and its release notes then say so;
until a tool adds the name to its own set,
``kind`` gives :obj:`None` for objects of that class.
A listed name is renamed or split only through the deprecation process,
without a warning (see :ref:`toolapi-deprecation`).

* The name is the exact kind.
  An ItemSpace is ``'ItemSpace'``, never ``'DynamicSpace'``,
  although its class is a subclass of DynamicSpace.
  An :func:`isinstance` test needs the class, and so an import from
  a module that is not tool API.
* :class:`type` reads no attribute of the object,
  so the check never reaches a user's member of a Model or a Space,
  never runs a formula, and answers also on a deleted object
  and on an object of a closed Model.
* The module check is needed:
  a Reference can hold an instance of a user's own class named
  ``Model`` or ``Cells``, and only its module tells it from a modelx object.
  The check must not assume that ``__module__`` is a str either:
  the proxy classes of the wrapt package, for example,
  make it a property.

  >>> class Cells:
  ...     pass

  >>> type(Cells()).__name__, kind(Cells())
  ('Cells', None)

* :obj:`None` is also the answer for the views and the nodes,
  for the objects that a formula sees as ``_self``, ``_space`` and
  ``_model``, and for every value that is not a modelx object,
  such as a number, a DataFrame or a module.
* A ReferenceProxy reports its own kind, and its ``value`` the kind
  of the value: the proxy of a Reference to a Space is
  ``'ReferenceProxy'``, and its value ``'UserSpace'``.
* A tool that asks about any Cells tests
  ``kind(v) in {'Cells', 'DynamicCells'}``,
  about any Reference ``kind(v) in {'ReferenceProxy', 'DynamicReferenceProxy'}``,
  about any IOSpec ``kind(v) in {'PandasData', 'ExcelRange', 'ModuleData'}``,
  and about any Space, whether the kind ends in ``'Space'``.
* :class:`~modelx.core.cells.DynamicCells` is a subclass of Cells,
  and :class:`~modelx.core.reference.DynamicReferenceProxy`
  of ReferenceProxy.
  What this page says of Cells holds for DynamicCells,
  and what it says of ReferenceProxy for DynamicReferenceProxy,
  unless it says otherwise.
  ``type(c) is Cells`` is :obj:`False` for a DynamicCells.
* The ``'type'`` key of the dicts of the snapshot wire is
  a different contract: it is ``'Cells'`` for a DynamicCells and
  ``'Reference'`` for both proxy classes (see :ref:`toolapi-wire`).

The check works the same on modelx 0.33, with one difference:
there, every Cells is a ``'Cells'`` and every proxy a
``'ReferenceProxy'``.
On 0.33, the kind of the ``parent`` of a Cells tells whether
the Cells is in an ItemSpace or a DynamicSpace,
and that works on later releases too.

.. versionadded:: 0.34.0
   :class:`~modelx.core.cells.DynamicCells` and
   :class:`~modelx.core.reference.DynamicReferenceProxy`.

Dynamic objects
    An object is *dynamic* when modelx made it for an ItemSpace:
    the ItemSpace itself and the DynamicSpaces in it, their Cells,
    and the References that the ItemSpace makes,
    which are its arguments, the References that its Space formula
    returns in ``'refs'``, and its ``_self``, ``_space`` and ``_model``.
    Its kind is one of four:

    >>> DYNAMIC = frozenset({'ItemSpace', 'DynamicSpace', 'DynamicCells',
    ...                      'DynamicReferenceProxy'})

    >>> [kind(obj) in DYNAMIC for obj in (proj, item, item.Child, foo, item.bar)]
    [False, True, True, False, True]

    Not dynamic are the Model, every UserSpace and its Cells,
    the global References, the References of a UserSpace,
    also when they are seen through an ItemSpace of the Space,
    and Macros.

    .. admonition:: Known limitation

       Seen through an ItemSpace or a DynamicSpace in it,
       a Reference that refers to the ItemSpace's own copy of its value,
       as the note under :ref:`reference-proxy-identity` describes
       (``P[1].rel`` for ``P.rel = P.Child``,
       or ``P[1].Child.up`` for ``P.Child.up = P``),
       has a proxy that stands for the copy,
       and the proxy is a ReferenceProxy on this release.
       So is the proxy of a Reference to a Space whose name begins
       with the name of the Space
       (see :ref:`the note on such References <toolapi-prefix-ref>`).
       This is not part of the frozen contract and may change.

    Until modelx 0.34.0, the Space classes had ``_is_dynamic()``,
    ``_is_static()`` and ``_is_root()``.
    They were removed in 0.34.0, and the kind gives each answer.
    On every Space that has not been deleted, it equals what the method
    returned, on 0.33 too:

    .. list-table::
       :header-rows: 1
       :widths: 40 60

       * - Removed
         - Use instead
       * - ``s._is_dynamic()``
         - ``kind(s) in {'ItemSpace', 'DynamicSpace'}``
       * - ``s._is_static()``
         - ``kind(s) == 'UserSpace'``
       * - ``s._is_root()``
         - ``kind(s) == 'ItemSpace'``

What a kind can do
    .. list-table::
       :header-rows: 1
       :widths: 40 60

       * - Question
         - Answer
       * - Has child Spaces, in ``spaces``
         - ``'Model'``, and every kind that ends in ``'Space'``.
       * - Has Cells, in ``cells``
         - Every kind that ends in ``'Space'``.
       * - Creates ItemSpaces when it is called or subscripted
         - A kind that ends in ``'Space'``, when its ``formula``
           is not :obj:`None`.
           The formula can have no parameters:
           a Space whose formula is ``lambda: None`` has ``()``
           as its ``parameters``, and calling it with no arguments
           gives an ItemSpace.
           An ItemSpace or a DynamicSpace has the formula that its
           base, ``bases[0]``, had when the ItemSpace was made,
           so ``Proj[1][5]`` is an ItemSpace,
           and so is ``P[1].Child[2]`` when ``P.Child`` has a formula.
           The base is not always the parent: an ItemSpace of a Space
           whose formula returns another Space as ``'base'`` has the
           formula of that Space. So a tool reads the object's own
           ``formula``.
           A Space without a formula has :obj:`None` as its
           ``parameters`` too.
       * - Takes new child Spaces and References
         - ``'Model'`` and ``'UserSpace'``.
           An ItemSpace and a DynamicSpace take none,
           and a UserSpace, not a Model, takes new Cells.
       * - The Space that created an ItemSpace
         - Its ``parent``.
           For an ItemSpace of an ItemSpace, walk ``parent`` while the
           kind is ``'ItemSpace'``: from ``Proj[1][5]`` the walk ends at
           ``Proj``. It ends at a DynamicSpace for an ItemSpace of
           a DynamicSpace, such as ``P[1].Child[2]``.

    >>> proj.formula is not None, item.Child.formula is None
    (True, True)

    >>> item[5].parent is item, item.parent is proj
    (True, True)

    .. admonition:: Known limitation

       Calling or subscripting a Space without a formula raises
       :obj:`AttributeError` on this release
       (``'NoneType' object has no attribute 'signature'``).
       The type and the message of this exception are not part of
       the frozen contract and may change.

    .. admonition:: Known limitation

       On this release, a formula given to a Space does not reach
       the ItemSpaces and DynamicSpaces already made from it,
       other than the Space's own ItemSpaces, which it deletes.
       When ``P.Child`` gets a formula after ``P[1]`` was made,
       ``P[1].Child.formula`` stays :obj:`None`,
       and ``P[1].Child[2]`` raises :obj:`AttributeError` as above,
       until ``P[1]`` is deleted, for example by ``P.clear_items()``,
       and made again.
       This is not part of the frozen contract and may change.


.. _toolapi-inheritance:

Inheritance and dynamic objects
-------------------------------

Only Cells and References are inherited.
Spaces and Models have no "derived" concept:
since modelx 0.24.0 the child Spaces of a base Space
are not copied into its sub Spaces,
so no Space is ever inherited.
The Space classes and Model have no ``_is_derived`` member,
and asking a Space instance for one looks up a member of that name.
An ItemSpace or a DynamicSpace is a *dynamic* copy of a static Space,
told apart by its class (see :ref:`toolapi-kinds`),
not by a derived flag.

``Cells._is_derived()``
    :obj:`True` if the Cells was copied from a base Space
    and has not been redefined in its own Space.
    Setting an input value does not change it,
    and assigning a formula makes it :obj:`False`.
    Every Cells in an ItemSpace or a DynamicSpace, a DynamicCells,
    returns :obj:`True`.

``Cells._is_defined()``
    ``not _is_derived()``.

    >>> sub.foo._is_derived(), foo._is_derived(), item.bar._is_derived()
    (True, False, True)

``ReferenceProxy._is_derived()``
    :obj:`True` if the Reference was copied from a base Space
    into a sub Space and has not been redefined there.
    It is :obj:`False` for a Space's own Reference,
    also when it overrides a Reference of a base Space,
    for a global Reference, also through a Space,
    for an argument of an ItemSpace,
    for a Reference that a Space formula returns,
    and for the ``_self``, ``_space`` and ``_model`` of a Space.
    Through an ItemSpace, a Reference of its Space
    gives the flag of that Reference.
    It is :obj:`None` for a proxy that does not stand for a Reference,
    so a tool that asks every proxy in a model gets an answer from each,
    and no exception.

    >>> sub._get_object("rate", as_proxy=True)._is_derived()
    True

    >>> base._get_object("rate", as_proxy=True)._is_derived()
    False

    >>> item._get_object("i", as_proxy=True)._is_derived()
    False

    .. versionadded:: 0.34.0

    .. admonition:: Known limitation

       On this release, two kinds of proxies obtained through an ItemSpace,
       or through a DynamicSpace in it,
       do not stand for a Reference, and ``_is_derived()`` is :obj:`None`
       on them:

       * the proxy of a Reference that refers to the ItemSpace's own copy
         of its value, as the note under :ref:`reference-proxy-identity`
         describes, such as ``P[1].rel`` for ``P.rel = P.Child``,
         or ``P[1].Child.up`` for ``P.Child.up = P``,
         which stands for the copy;
       * the proxy of a Reference to a Space whose name
         begins with the name of the Space, such as ``P.r = PX``
         (see :ref:`the note on such References <toolapi-prefix-ref>`).

       This is not part of the frozen contract and may change.

``ReferenceProxy.is_derived()``
    Kept for modelx-bridge 0.10; use ``_is_derived()``.
    It returns the same.

    .. versionchanged:: 0.34.0
       It is the same as ``_is_derived()``.
       Before, on the proxies of the known limitation above,
       it raised :obj:`AttributeError`, or returned :obj:`True`
       for an ItemSpace's copy of a Cells.

With the kinds of :ref:`toolapi-kinds`, a tool sorts the Cells and
the References of a Space:

* inherited from a base Space: ``_is_derived()`` is :obj:`True`
  and the kind is not in ``DYNAMIC``;
* made for an ItemSpace: the kind is in ``DYNAMIC``;
* defined in the Space itself: ``_is_derived()`` is :obj:`False`
  and the kind is not in ``DYNAMIC``.

A Reference of a Space seen through an ItemSpace of the Space
is sorted as in that Space, which is its ``parent``.

>>> [(kind(c), c._is_derived()) for c in (foo, sub.foo, item.bar)]
[('Cells', False), ('Cells', True), ('DynamicCells', True)]

``_is_base(other)``, ``_is_sub(other)`` (Spaces)
    ``x._is_sub(y)`` is ``y in x.bases``,
    and ``y._is_base(x)`` is the same test.
    A Space is neither a base nor a sub Space of itself.
    The only base of an ItemSpace or a DynamicSpace is the static Space
    it was made from.

    >>> sub._is_sub(base), base._is_base(sub), proj._is_base(item)
    (True, True, True)

``_own_refs`` (Spaces)
    A mapping of the References defined in or inherited by the Space,
    without the global References and ``__builtins__``
    that the public ``refs`` also lists.

    >>> dict(sub._own_refs), list(sub.refs)
    ({'rate': 0.05}, ['__builtins__', 'scale', 'rate'])

    In an ItemSpace or a DynamicSpace, ``_own_refs`` holds only
    the References that the Space formula returns in ``'refs'``.
    It does not hold the arguments, the References of the static Space
    that the ItemSpace or the DynamicSpace was made from,
    or the global References.
    No Space formula is called to make a DynamicSpace,
    so the ``_own_refs`` of a DynamicSpace is always empty.
    Read ``refs`` for the full set:

    >>> m3 = mx.new_model("Model3")

    >>> q = m3.new_space("Q", formula=lambda i, j=2: {"refs": {"fr": i * j}})

    >>> q.k = 5

    >>> q.new_space("C").cref = 9

    >>> dict(q[1]._own_refs), list(q[1].refs)
    ({'fr': 2}, ['__builtins__', 'k', 'fr', 'i', 'j'])

    >>> dict(q[1].C._own_refs), list(q[1].C.refs)
    ({}, ['__builtins__', 'cref', 'i', 'j'])

    >>> m3.close()

``_direct_bases`` (Spaces)
    The list of the Spaces that were given as the bases of the Space,
    in order.
    The public ``bases`` is the full method resolution order instead.
    An ItemSpace or a DynamicSpace has one base, the UserSpace
    whose members it has, so its ``_direct_bases`` is the same list
    as its ``bases``.

    >>> sub._direct_bases, item._direct_bases, item.Child._direct_bases
    ([<UserSpace Model1.Base>], [<UserSpace Model1.Proj>], [<UserSpace Model1.Proj.Child>])

    .. versionchanged:: 0.34.0
       Before, on an ItemSpace or a DynamicSpace, it could name Spaces
       that are not its bases: for a Space ``P`` with the bases ``Base1``
       and ``Base2`` and a child Space ``Child``,
       ``P[1].Child._direct_bases`` named ``Base1`` and ``Base2``.
       A tool that supports modelx 0.33 reads ``bases`` there.

``ItemSpace.argvalues``
    The tuple of the argument values the ItemSpace was created with,
    with default values filled in.
    The values are the objects themselves:
    an argument that is a Space is the Space.
    Only ItemSpace defines it.

    >>> item.argvalues
    (1,)

.. currentmodule:: modelx.core.cells

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Cells._is_derived
  Cells._is_defined

.. currentmodule:: modelx.core.reference

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ReferenceProxy._is_derived
  ReferenceProxy.is_derived

.. currentmodule:: modelx.core.space

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  UserSpace._is_base
  UserSpace._is_sub
  UserSpace._own_refs
  UserSpace._direct_bases
  ItemSpace._is_base
  ItemSpace._is_sub
  ItemSpace._own_refs
  ItemSpace._direct_bases
  DynamicSpace._is_base
  DynamicSpace._is_sub
  DynamicSpace._own_refs
  DynamicSpace._direct_bases

.. autosummary::

  ItemSpace.argvalues


.. _toolapi-wire:

The snapshot wire
-----------------

These members describe objects as dicts,
for tools that show a model in another process, such as spyder-modelx.

``_get_attrdict(extattrs=None, recursive=True)``
    Returns a dict that describes the object.
    Model, the Space classes, Cells, Macro, ReferenceProxy, the views,
    the node classes, Formula and the IOSpec classes define it.
    With ``recursive=True``, the dicts of the child objects of a Model
    or a Space are nested in its dict;
    with ``recursive=False``, they are given as tuples of names.
    A view lists the dicts of its members either way,
    and the ``'obj'`` of a node is always a dict.
    The keys are:

    .. list-table::
       :header-rows: 1
       :widths: 25 75

       * - Object
         - Keys
       * - Model, Spaces, Cells, Macro
         - ``'type'``: the class name, except ``'Cells'``
           for a DynamicCells; ``'id'``: the :func:`id` of
           the object's internal implementation;
           ``'name'``; ``'fullname'``;
           ``'repr'``: ``_get_repr()``; ``'namedid'``: ``_idstr``.
       * - Model
         - adds ``'spaces'`` and ``'refs'``.
       * - Spaces
         - add ``'spaces'``, ``'named_spaces'``, ``'_named_itemspaces'``,
           ``'cells'``, ``'refs'``,
           ``'bases'``: the ``_idstr`` of each of ``bases``,
           and ``'parameters'``.
       * - Cells
         - adds ``'parameters'``.
       * - ReferenceProxy
         - the keys of the first row, with ``'type'`` set to
           ``'Reference'`` for both proxy classes, and ``'value_type'``:
           the class name of the value, such as ``'DynamicCells'``
           for a Cells of an ItemSpace.
       * - Views
         - ``'type'``, ``'items'``: a dict of the members' dicts,
           and ``'keys'``: the list of the members' names.
           The ``refs`` view has no ``'keys'``,
           and its ``'items'`` leaves out names that start with
           an underscore, ``__builtins__`` included.
       * - Nodes
         - ``'type'``, ``'obj'``: the dict of the node's object,
           ``'args'``, ``'value'``,
           ``'valid'``: the :func:`id` of the value,
           ``'predslen'``, ``'succslen'``, ``'precedentslen'``:
           the lengths of ``preds``, ``succs`` and ``precedents``,
           ``'repr_parent'`` and ``'repr'``.
           ``'value'``, ``'valid'`` and the three lengths are
           :obj:`None` for an ItemNode with no stored value,
           of a Cells or of a Space.
       * - Formula
         - ``'source'``.
       * - IOSpecs
         - ``'type'``, ``'path'``, ``'load_from'`` and ``'value'``.
           :class:`~modelx.io.pandasio.PandasData` adds ``'filetype'``
           and ``'sheet'``, and :class:`~modelx.io.excelio.ExcelRange`
           adds ``'range'``, ``'sheet'`` and ``'keyids'``.

    ``'id'`` identifies a live object; like any :func:`id`,
    it can be reused after the object is deleted.
    ``'valid'`` identifies the value object, so a changed value
    can have the same ``'valid'``; it is not a revision number.
    ``'value'`` is the value itself, not a description of it.
    ``'repr'`` and ``'repr_parent'`` are display strings,
    as ``_get_repr`` gives them (see :ref:`toolapi-identity`):
    an ItemSpace in them shows its arguments.
    With ``recursive=False``, ``'refs'`` lists every name,
    ``__builtins__`` and names that start with an underscore included,
    and also a key that is not a str,
    which a Space formula can return in ``'refs'``,
    as in ``lambda i: {"refs": {1: "one"}}``.
    No formula can read such a ref,
    and the dicts of the ``refs`` view leave it out.

    >>> foo.node(3)._get_attrdict()["predslen"], foo.node(9)._get_attrdict()["predslen"]
    (0, None)

    .. versionchanged:: 0.34.0
       Before, the dicts of an ItemNode with no stored value raised
       :obj:`ValueError`, and a key that is not a str
       in the ``refs`` of an ItemSpace made its ``refs`` view's dicts,
       and the dict of every object that has the ItemSpace in its tree,
       raise :obj:`KeyError`.
       For an ItemSpace of an ItemSpace and the objects in it,
       ``'repr'`` and ``'repr_parent'`` named the parent item by its
       ``__SpaceN`` name.

    .. _toolapi-prefix-ref:

    .. admonition:: Known limitation

       Take a Space ``P`` that has a formula.
       A Reference of ``P``, or of a Space inside ``P``,
       is broken in the ItemSpaces of ``P`` and in the Spaces inside them
       when its mode is not ``'absolute'`` and its value is a Space
       outside ``P`` whose full name begins with the full name of ``P``,
       such as a sibling Space ``PX``,
       or a Cells or a Space inside such a Space.
       With ``P.r = PX``,
       ``P[1].refs`` lists ``r``, but ``P[1].r`` is missing,
       and a formula in ``P[1]`` that reads ``r`` fails.
       ``P[1]._get_object("r")`` raises :obj:`NameError`.
       ``P[1]._get_object("r", as_proxy=True)`` returns a proxy
       whose ``value``, ``name``, ``_idstr``, ``_evalrepr``,
       ``_get_repr()``, ``refmode`` and
       ``_get_attrdict()`` raise :obj:`AttributeError`,
       and whose ``_is_derived()`` and ``is_derived()`` are :obj:`None`.
       ``model._get_from_name("P.__Space1.r")`` raises
       :obj:`AttributeError`.
       The dict of ``P[1]`` with ``recursive=True``, and the dicts and
       ``_baseattrs_private`` of its ``refs`` view, raise
       :obj:`AttributeError`
       (``'NoneType' object has no attribute 'name'``),
       and so does the dict of every object that has ``P[1]`` in its tree,
       the Model's included, so spyder-modelx cannot show the Model.
       The Model's ``_baseattrs`` raises :obj:`RuntimeError`.
       This is not part of the frozen contract and may change.

    .. admonition:: Known limitation

       An ItemSpace's dict can hold two records
       with the same ``'id'`` and ``'namedid'``.
       In an ItemSpace and in the DynamicSpaces in it, a Reference can
       refer to the ItemSpace's own copy of its value, as the note under
       :ref:`reference-proxy-identity` describes
       (``P[1].rel`` for ``P.rel = P.Child``,
       or ``P[1].Child.up`` for ``P.Child.up = P``).
       Its record in the ``'refs'`` of that Space has the ``'type'``
       ``'Reference'``, but its ``'id'``, ``'namedid'``, ``'name'`` and
       ``'fullname'`` are those of the copy, the same as in the copy's
       own record.
       So do not key records by ``'id'`` or ``'namedid'`` alone.
       This is not part of the frozen contract and may change.

    ``extattrs`` is a list of further names to add to the dicts.
    It is passed down to every object that the walk reaches.
    A Macro, a Formula and an IOSpec ignore it.
    A view passes it to its members and adds nothing to its own dict.
    A node passes it to its object, so the names are added to
    the node's ``'obj'``, not to the node's own dict:
    ask for ``formula`` and read ``record['obj']['formula']``.
    For each name that is not already a key,
    modelx looks the name up on the class of the object
    and on its base classes, never on the object itself.
    So no member of a Model or a Space, such as a user's Reference,
    Cells or Space, is read or called, whatever its name.
    What the class defines gives the value:

    * A property, or another data descriptor such as a slot, is read.
      A value whose class defines ``_get_attrdict`` is replaced by its
      dict, made with the same ``extattrs`` and ``recursive``,
      and any other value is added as it is,
      also when it is callable.
    * A function, or another method, is bound to the object and
      called with no arguments, and its result is added.
    * Any other class attribute is added as it is.

    A ReferenceProxy also answers the properties and the methods
    that it forwards (see ReferenceProxy forwarding below),
    such as ``allow_none``.
    A name that the class does not define is left out,
    and so is a property that raises :obj:`AttributeError`,
    so expect the key to be missing on an object whose class
    does not define the name.

    These names are answered by a class attribute, run no formula,
    and give a literal, :obj:`None` or the dict of a Formula,
    ``{'source': ...}``:

    .. list-table::
       :header-rows: 1
       :widths: 25 35 40

       * - Name
         - Answered on
         - Value
       * - ``_is_derived``
         - Cells and ReferenceProxy; no Space or Model
         - :obj:`True` or :obj:`False`; also :obj:`None` on a
           ReferenceProxy that does not stand for a Reference
       * - ``_evalrepr``
         - Model, Spaces, Cells and ReferenceProxy
         - a str
       * - ``__len__``
         - Cells
         - the number of stored values
       * - ``formula``, ``parameters``
         - Spaces and Cells
         - the dict of the Formula, or :obj:`None`;
           a tuple of str, or :obj:`None`
       * - ``allow_none``
         - Model, Spaces, Cells and ReferenceProxy
         - :obj:`True`, :obj:`False` or :obj:`None`

    Do not request:

    * a name whose value is a modelx object or a list of them, such as
      ``_direct_bases``: the objects themselves go into the dict;
    * ``argvalues``: its values are the arguments of an ItemSpace
      themselves, which can be Spaces or objects that cannot be pickled.
      The ``_evalrepr`` of an ItemSpace shows its arguments
      after the ``_evalrepr`` of its Space;
    * a method that does work, such as ``clear_all``,
      which Model, the Space classes and Cells define: it is called.

    >>> foo._get_attrdict(["_is_derived", "_evalrepr"], recursive=False)["_evalrepr"]
    'Model1.Base.foo'

    >>> rec = m._get_attrdict(["_is_derived", "_evalrepr"], recursive=False)

    >>> "_is_derived" in rec, rec["_evalrepr"]
    (False, 'Model1')

    .. versionchanged:: 0.34.0
       Names are looked up on the class only.
       Before, modelx read the attribute from the object,
       so on a Model or a Space a name that its class does not define
       reached the user's member of that name, if there was one,
       such as a Reference, a Cells or a Space,
       and a callable value was called.
       A tool that also supports modelx 0.33 requests a name
       that it did not request before only when
       ``modelx.VERSION >= (0, 34, 0)``.

``_baseattrs``
    The older form of ``_get_attrdict``, kept for existing tools.
    It always nests the dicts of child objects, and takes no ``extattrs``.
    Its keys differ: a Space has ``'named_itemspaces'``
    and ``'params'``, a string, in place of ``'_named_itemspaces'``
    and ``'parameters'``, plus ``'static_spaces'`` and ``'dynamic_spaces'``;
    a Cells has ``'params'``;
    a Model has no ``'refs'``;
    a node has no ``'valid'`` or ``'precedentslen'``;
    a view has no ``'keys'``, and in every view
    ``'items'`` leaves out names that start with an underscore.
    A Space's ``'named_itemspaces'`` and ``'dynamic_spaces'``
    are the exception: they list its ItemSpaces by their ``__SpaceN`` names.

``Model._get_assoc_values()``
    A list with one dict for each value that a Reference holds,
    keyed ``'value'``, ``'spec'`` and ``'refs'``.
    ``'spec'`` is the IOSpec of the value, such as a
    :class:`~modelx.io.pandasio.PandasData`, or :obj:`None`,
    and ``'refs'`` is a list of ReferenceProxy objects.
    It covers the values assigned through attribute assignment,
    ``set_ref``, ``absref`` and ``relref``, and the ``new_*`` methods
    that create IOSpecs.
    It leaves out modelx objects, References created by
    ``new_space(refs=...)``, and the inherited copies of References.
    Values are told apart by identity.

``Model._get_refs(value)``
    The list of ReferenceProxy objects for the References that
    ``_get_assoc_values()`` associates with ``value``,
    found by identity.
    It raises :obj:`KeyError` for any other value.

    >>> m._get_refs(base.rate)
    [<ReferenceProxy Model1.Base.rate>]

ReferenceProxy forwarding
    A :class:`~modelx.core.reference.ReferenceProxy` defines
    ``value``, ``refmode``, ``_evalrepr``, ``_get_attrdict``,
    ``_baseattrs``, ``_is_derived()`` and ``is_derived()`` itself.
    It also answers ``name``, ``fullname``, ``parent``, ``model``,
    ``doc``, ``allow_none``, ``_idtuple``, ``_idstr``, ``_get_repr``,
    ``_is_valid``, ``_name`` and ``_parent``, as
    the base class of Model, Spaces and Cells answers them,
    applied to the Reference.
    On this release it forwards them to that class
    (see the known limitation under :ref:`toolapi-detection`).
    ``doc`` is :obj:`None`.
    What the proxy answers for any other name is undocumented.

    >>> proxy = m._get_object("Base.rate", as_proxy=True)

    >>> proxy.name, proxy.parent, proxy._idstr, proxy._get_repr(fullname=True)
    ('rate', <UserSpace Model1.Base>, 'Base.rate', 'Model1.Base.rate')

    .. admonition:: Known limitation

       In an ItemSpace and in the DynamicSpaces in it, a Reference can
       refer to the ItemSpace's own copy of its value, as the note under
       :ref:`reference-proxy-identity` describes
       (``P[1].Child.up`` for ``P.Child.up = P``, for example).
       A proxy for it obtained through the ItemSpace or the DynamicSpace
       stands for the copy, not for the Reference:
       its ``name``, ``fullname``, ``parent``, ``_idstr``, ``_idtuple``
       and ``_evalrepr`` name the copy,
       and ``refmode`` raises :obj:`AttributeError`.
       For ``P.rel = P.Child``, the proxy for ``rel`` in ``P[1]``
       has the ``name`` ``'Child'`` and the ``_idstr``
       ``'P.__Space1.Child'``.
       This is not part of the frozen contract and may change.

.. currentmodule:: modelx.core.model

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Model._get_attrdict
  Model._baseattrs
  Model._get_assoc_values
  Model._get_refs

.. currentmodule:: modelx.core.space

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  UserSpace._get_attrdict
  UserSpace._baseattrs
  ItemSpace._get_attrdict
  ItemSpace._baseattrs
  DynamicSpace._get_attrdict
  DynamicSpace._baseattrs

.. currentmodule:: modelx.core.cells

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Cells._get_attrdict
  Cells._baseattrs

.. currentmodule:: modelx.core.macro

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Macro._get_attrdict
  Macro._baseattrs

.. currentmodule:: modelx.core.reference

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ReferenceProxy._get_attrdict
  ReferenceProxy._baseattrs

.. currentmodule:: modelx.core.views

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  SpaceView._get_attrdict
  SpaceView._baseattrs
  CellsView._get_attrdict
  CellsView._baseattrs
  RefView._get_attrdict
  RefView._baseattrs
  MacroView._get_attrdict
  MacroView._baseattrs

.. currentmodule:: modelx.core.node

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ItemNode._get_attrdict
  ItemNode._baseattrs

.. currentmodule:: modelx.core.reference

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ReferenceNode._get_attrdict
  ReferenceNode._baseattrs

.. currentmodule:: modelx.core.formula

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  Formula._get_attrdict

.. currentmodule:: modelx.io.baseio

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  BaseIOSpec._get_attrdict

.. currentmodule:: modelx.io.pandasio

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  PandasData._get_attrdict

.. currentmodule:: modelx.io.excelio

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ExcelRange._get_attrdict

.. currentmodule:: modelx.io.moduleio

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ModuleData._get_attrdict


.. _toolapi-errors:

Errors and warnings
-------------------

.. module:: modelx.core.errors

The exception and warning classes of modelx live in
:mod:`modelx.core.errors`.
It is a supported import path for tools,
the one module under ``modelx.core`` that is::

    from modelx.core.errors import FormulaError

The classes are not available from the top-level :mod:`modelx` module.
To test whether a class exists, use
``getattr(modelx.core.errors, name, None)``:
no Model can take the place of a name in this module.

This release defines four exception classes there,
each a direct subclass of :obj:`Exception`, and no warning classes.

* :class:`~modelx.core.errors.FormulaError` is raised when an error
  occurs while a formula runs. The original error is returned by
  :func:`~modelx.get_error`.
  After ``use_formula_error(False)``, the original error is raised instead.

  .. admonition:: Known limitation

     When the error occurs in a formula whose
     :attr:`~modelx.core.formula.Formula.source` is :obj:`None`,
     because modelx could not retrieve the source code of its function,
     :obj:`TypeError` is raised instead of FormulaError on this release
     (``can only concatenate str (not "NoneType") to str``),
     also when that formula was called from other formulas.
     :func:`~modelx.get_error` still returns the original error,
     and after ``use_formula_error(False)`` the original error is raised.
     This is not part of the frozen contract and may change.

* :class:`~modelx.core.errors.DeepReferenceError` is the original error
  when a chain of formula calls exceeds the limit.
* :class:`~modelx.core.errors.NoneReturnedError` is the original error
  when a formula returns :obj:`None` and ``allow_none`` is :obj:`False`.
* :class:`~modelx.core.errors.DeletedObjectError` is raised
  when a deleted object is used.

.. currentmodule:: modelx.core.errors

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  FormulaError
  DeepReferenceError
  NoneReturnedError
  DeletedObjectError


.. _toolapi-not:

What is not tool API
--------------------

A tool that relies on any of these can break in any release,
without a deprecation warning:

* The ``_impl`` attribute of an object and the ``_impls`` attribute
  of a view, and everything reached through them.
* The ``_io`` and ``_manager`` attributes of an IOSpec,
  and everything reached through them.
* Imports from the modules of the :mod:`modelx` package other than
  :mod:`modelx.core.errors`, such as ``modelx.core.space``
  and ``modelx.io.excelio``, and so the classes defined there,
  for example in :func:`isinstance` tests.
  This includes the modules that define the classes of
  :ref:`toolapi-kinds`: the names of those classes are tool API,
  and so is the promise that each is defined in a module of
  the :mod:`modelx` package, but not which module.
* Tests of an object's class by its name for a class that
  :ref:`toolapi-kinds` does not list,
  such as ``type(obj).__name__ == "NullFormula"``.
  A test of a listed name is tool API only after the module check
  that :ref:`toolapi-kinds` describes:
  without it, a user's own class of that name passes the test.
  The ``'type'`` key of a dict from ``_get_attrdict`` is a different matter:
  it is part of the snapshot wire.
* Behaviour that this page or the rest of this reference does not describe,
  for example the text of error messages,
  how ``__SpaceN`` names are numbered,
  and what a ReferenceProxy answers for names it is not documented to forward.

Members without an underscore are the public API that the rest of
this reference documents, and tools can use them as users do.
