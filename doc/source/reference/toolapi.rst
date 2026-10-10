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
:class:`~modelx.core.cells.Cells`, :class:`~modelx.core.macro.Macro`,
:class:`~modelx.core.reference.ReferenceProxy`, the view classes,
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
for such a name, and ``new_cells`` and :func:`~modelx.defcells`
replace it with an automatic name such as ``Cells1``.

Five routes still accept such names:
global References (``model._x = value``, and
:meth:`Model.new_pandas <modelx.core.model.Model.new_pandas>`,
:meth:`~modelx.core.model.Model.new_module` and
:meth:`~modelx.core.model.Model.new_excel_range`),
References created by ``new_space(refs=...)``,
the parameters of a Space formula,
the ``refs`` that a Space formula returns,
and :meth:`UserSpace.rename <modelx.core.space.UserSpace.rename>`,
which checks no name in this release.
An object named this way can have the name of a tool member.
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
The notes marked **Known limitation** below describe behaviour of
this release that a tool should not rely on.

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

No frozen member is deprecated in this release.


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
    instead of a tool member:

    >>> m2 = mx.new_model("Model2")

    >>> s2 = m2.new_space("Space1")

    >>> m2._new_member = 1

    >>> hasattr(m2, "_new_member"), hasattr(s2, "_new_member")
    (True, True)

    >>> getattr(type(m2), "_new_member", None) is None
    True

    >>> m2.close()

    A :class:`~modelx.core.reference.ReferenceProxy` answers some members
    by forwarding them (see :ref:`toolapi-wire`), so they are not attributes
    of its class: ``getattr(type(proxy), "_idstr", None)`` is :obj:`None`
    although ``proxy._idstr`` works.
    Every member that this page lists as forwarded is answered
    on every release that has this page, so a tool does not need to detect it.

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
A ReferenceProxy defines ``_evalrepr``, and answers
``_idstr``, ``_idtuple``, ``_get_repr``, ``_name``, ``_parent``
and ``_is_valid`` by forwarding (see :ref:`toolapi-wire`).

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
    With ``add_params=True`` a Cells shows its parameters
    and an ItemSpace shows its arguments.

    >>> foo._get_repr(), foo._get_repr(fullname=True)
    ('foo(x)', 'Model1.Base.foo(x)')

    >>> foo._get_repr(fullname=True, add_params=False)
    'Model1.Base.foo'

    >>> item._get_repr(), item.bar._get_repr(fullname=True)
    ('Proj[1]', 'Model1.Proj[1].bar()')

    **Known limitation:** for an ItemSpace, ``add_params=False``
    gives its ``__SpaceN`` name, and with ``fullname=True``
    leaves out the name of its Space: ``'Model1.__Space1'`` for ``Proj[1]``.

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
    <Cells Model1.Proj[1].bar()>

    >>> m._get_object("Base.foo.formula")
    lambda x: 2 * x

    >>> mx.get_object("Model1.Base.cells")
    {foo}

    **Known limitation:** with ``as_proxy=True``,
    the parts after a Reference are ignored:
    ``m._get_object("Base.rate.real", as_proxy=True)``
    returns the proxy of ``rate``.

    **Known limitation:** a name that continues past an object
    that is not a modelx object, such as the value of a Reference
    or a leaf attribute, as in ``"Base.rate.real"`` or
    ``"Base.foo.formula.source"``, raises :obj:`AttributeError`
    on this release, because the lookup asks that object for
    its ``_get_object``. Do not rely on the type of this exception.

``Model._get_from_name(name)``
    Finds an object by its ``_idstr``.
    The first part must be a Space of the Model;
    the parts after it can be child Spaces, ItemSpaces by their
    ``__SpaceN`` names, Cells, and References, which give their values.
    For every Space and every Cells,
    ``model._get_from_name(obj._idstr) is obj``.
    It does not find the Model itself (``''``), a global Reference
    or a Macro.
    A first part that is not a Space of the Model raises :obj:`KeyError`.

    >>> m._get_from_name("Proj.__Space1.Child") is item.Child
    True

    **Known limitation:** a later part that is not found,
    and a name that continues past the value of a Reference,
    raise :obj:`AttributeError` on this release, as a side effect
    of the lookup. Do not rely on the type of this exception.

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

    **Known limitation:** a :class:`~modelx.core.macro.Macro` and a
    ReferenceProxy return :obj:`True` even after their Macro or Reference
    has been deleted.

    **Known limitation:** closing a Model does not make the Model
    or its objects invalid on this release.

    **Known limitation:** an ItemSpace that a tool holds after it was
    deleted, and a DynamicSpace in it, become valid again
    when the Space creates the item again with the same arguments,
    because modelx reuses the same objects on this release.
    The ItemSpace's ``_idstr`` then has a new ``__SpaceN`` name.
    The Cells in it are not revived:
    a Cells of the deleted item that a tool holds stays invalid.

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
told apart by ``_is_dynamic()``, not by a derived flag.

``Cells._is_derived()``
    :obj:`True` if the Cells was copied from a base Space
    and has not been redefined in its own Space.
    Setting an input value does not change it,
    and assigning a formula makes it :obj:`False`.
    Every Cells in an ItemSpace or a DynamicSpace returns :obj:`True`.

``Cells._is_defined()``
    ``not _is_derived()``.

    >>> sub.foo._is_derived(), foo._is_derived(), item.bar._is_derived()
    (True, False, True)

``ReferenceProxy.is_derived()``
    :obj:`True` if the Reference was copied from a base Space
    into a sub Space and has not been redefined there.
    modelx-bridge 0.10 calls it.
    It has no underscore, and it is the only derived flag for References
    on this release.
    It is :obj:`False` for a Space's own Reference,
    also when it overrides a Reference of a base Space,
    for a global Reference, also through a Space,
    for an argument of an ItemSpace,
    and for a Reference that a Space formula returns.
    Through an ItemSpace, a Reference of its Space
    gives the flag of that Reference.

    >>> sub._get_object("rate", as_proxy=True).is_derived()
    True

    >>> base._get_object("rate", as_proxy=True).is_derived()
    False

    **Known limitation:** seen through an ItemSpace,
    a Reference of its Space whose value is the Space itself,
    or a Cells or a Space inside it, and whose mode is not ``'absolute'``
    (see the note under :ref:`reference-proxy-identity`),
    gives a proxy on which ``is_derived()`` raises :obj:`AttributeError`
    if the value is a Space, and returns :obj:`True` if it is a Cells.

``_is_dynamic()``, ``_is_static()``, ``_is_root()`` (Spaces)
    ``_is_dynamic()`` is :obj:`True` for an ItemSpace and a DynamicSpace,
    and :obj:`False` for a UserSpace.
    ``_is_static()`` is always ``not _is_dynamic()``.
    ``_is_root()`` is :obj:`True` only for an ItemSpace,
    the root of a dynamic tree, including an ItemSpace of a DynamicSpace.
    It is :obj:`False` for a DynamicSpace.

    >>> [(s._is_dynamic(), s._is_static(), s._is_root())
    ...  for s in (proj, item, item.Child)]
    [(False, True, False), (True, False, True), (True, False, False)]

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

    In an ItemSpace, ``_own_refs`` holds only the References
    that the Space formula returns in ``'refs'``.
    It does not hold the arguments, the References of the Space
    that the ItemSpace is an item of, or the global References.
    In a DynamicSpace, it is empty on this release.
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

    **Known limitation:** on an ItemSpace or a DynamicSpace,
    ``_direct_bases`` does not give the bases of that Space,
    and it can name an unrelated Space. Read ``bases`` there.

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

  ReferenceProxy.is_derived

.. currentmodule:: modelx.core.space

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  UserSpace._is_dynamic
  UserSpace._is_static
  UserSpace._is_root
  UserSpace._is_base
  UserSpace._is_sub
  UserSpace._own_refs
  UserSpace._direct_bases
  ItemSpace._is_dynamic
  ItemSpace._is_static
  ItemSpace._is_root
  ItemSpace._is_base
  ItemSpace._is_sub
  ItemSpace._own_refs
  ItemSpace._direct_bases
  DynamicSpace._is_dynamic
  DynamicSpace._is_static
  DynamicSpace._is_root
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
         - ``'type'``: the class name; ``'id'``: the :func:`id` of
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
           ``'Reference'``, and ``'value_type'``:
           the class name of the value.
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
           ``'predslen'``, ``'succslen'``, ``'precedentslen'``,
           ``'repr_parent'`` and ``'repr'``.
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
    With ``recursive=False``, ``'refs'`` lists every name,
    ``__builtins__`` and names that start with an underscore included.

    **Known limitation:** for an ItemNode with no stored value,
    ``_get_attrdict`` and ``_baseattrs`` raise :obj:`ValueError`
    on this release.
    Check ``has_value()`` before asking a node of a Cells for its dict.

    **Known limitation:** an ItemSpace's dict can hold two records
    with the same ``'id'`` and ``'namedid'``.
    A Reference of the Space whose value is the Space itself,
    or a Cells or a Space inside it, and whose mode is not
    ``'absolute'``, is seen in an ItemSpace as the ItemSpace's copy of
    the value, as the note under :ref:`reference-proxy-identity` describes.
    Its record in the ItemSpace's ``'refs'`` has the ``'type'``
    ``'Reference'``, but its ``'id'``, ``'namedid'``, ``'name'`` and
    ``'fullname'`` are those of the copy, the same as in the copy's
    own record.
    So do not key records by ``'id'`` or ``'namedid'`` alone.

    ``extattrs`` is a list of further names to add to the dicts.
    It is passed down to every object that the walk reaches.
    A Macro, a Formula and an IOSpec ignore it.
    A view passes it to its members and adds nothing to its own dict.
    A node passes it to its object, so the names are added to
    the node's ``'obj'``, not to the node's own dict:
    ask for ``formula`` and read ``record['obj']['formula']``.
    For each name that is not already a key, modelx reads the attribute
    of that name from the object,
    and skips the name if :func:`hasattr` is :obj:`False`.
    A value that has its own ``_get_attrdict`` is replaced by its dict,
    a callable value is called with no arguments
    and replaced by its result,
    and any other value is added as it is.

    >>> foo._get_attrdict(["_is_derived", "_evalrepr"], recursive=False)["_evalrepr"]
    'Model1.Base.foo'

    The attribute is read from the instance.
    So on a Model or a Space, a name that its class does not define
    reaches a member of that name, if there is one:
    a Reference's value is added, and called if it is callable,
    and a Cells or a Space is added as its dict.
    A Cells skips a name that its class does not define.
    A ReferenceProxy skips a name that neither its class nor
    the base class of Model, Spaces and Cells defines.
    What it adds for a name that only that base class defines,
    other than the names it forwards (see ReferenceProxy forwarding below),
    is undocumented.
    So request only names that the classes of the objects concerned define,
    and expect the key to be missing where a class does not define it.
    A name that only some classes define, such as ``_is_derived``,
    which only Cells defines,
    is safe on those classes but can reach a user's object on the others.
    A name whose value is a list of modelx objects, such as
    ``_direct_bases``, puts the objects themselves into the dict.

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
    ``_baseattrs`` and ``is_derived()`` itself.
    It answers ``name``, ``fullname``, ``parent``, ``model``,
    ``doc``, ``allow_none``, ``_idtuple``, ``_idstr``, ``_get_repr``,
    ``_is_valid``, ``_name`` and ``_parent`` by forwarding them to
    the base class of Model, Spaces and Cells, applied to the Reference.
    ``doc`` is :obj:`None`.
    What the proxy answers for any other name is undocumented.

    >>> proxy = m._get_object("Base.rate", as_proxy=True)

    >>> proxy.name, proxy.parent, proxy._idstr, proxy._get_repr(fullname=True)
    ('rate', <UserSpace Model1.Base>, 'Base.rate', 'Model1.Base.rate')

    **Known limitation:** a Reference of a Space whose value is
    the Space itself, or a Cells or a Space inside it, and whose mode
    is not ``'absolute'``, is seen in an ItemSpace as the ItemSpace's copy
    of the value (see the note under :ref:`reference-proxy-identity`).
    A proxy for it obtained through the ItemSpace stands for the copy,
    not for the Reference:
    its ``name``, ``fullname``, ``parent``, ``_idstr`` and ``_idtuple``
    name the copy, and ``refmode`` raises :obj:`AttributeError`.
    For ``P.rel = P.Child``, the proxy for ``rel`` in ``P[1]``
    has the ``name`` ``'Child'`` and the ``_idstr`` ``'P.__Space1.Child'``.

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
* Imports from ``modelx.core`` and its submodules other than
  :mod:`modelx.core.errors`, and so the classes defined there,
  for example in :func:`isinstance` tests.
* Tests of an object's class by its name,
  such as ``type(obj).__name__ == "ItemSpace"``.
  The ``'type'`` key of a dict from ``_get_attrdict`` is a different matter:
  it is part of the snapshot wire.
* Behaviour that this page or the rest of this reference does not describe,
  for example the text of error messages,
  how ``__SpaceN`` names are numbered,
  and what a ReferenceProxy answers for names it is not documented to forward.

Members without an underscore are the public API that the rest of
this reference documents, and tools can use them as users do.
