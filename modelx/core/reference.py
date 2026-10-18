# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

import sys
import builtins
import importlib
from types import ModuleType, FunctionType
import functools

from modelx.core.base import (
    Derivable, Impl, Interface, get_mixin_slots)
from modelx.io.baseio import BaseIOSpec
from modelx.core.node import ObjectNode, get_node, OBJ


class ReferenceImpl(Derivable, Impl):

    __slots__ = (
        "container",
        "refmode",
        "is_relative"
    ) + get_mixin_slots(Derivable, Impl)

    def __init__(self, parent, name, value, container, is_derived=False,
                 refmode=None):
        # Side-effect-free: the caller registers self into ``container``
        # (D-11; registration happens in the pipeline's apply stage).
        Impl.__init__(
            self,
            system=parent.system,
            parent=parent,
            name=name,
            interface=value
        )
        Derivable.__init__(self, is_derived)

        self.container = container
        self.refmode = refmode
        if refmode == "absolute":
            self.is_relative = False
        else:   # 'auto' or 'relative'
            self.is_relative = True

    def on_delete(self):
        pass

    def to_node(self):
        return ReferenceNode(get_node(self, None, None))

    def repr_self(self, add_params=True):
        return self.name

    @staticmethod
    def _get_members(other):
        return other.own_refs

    def has_interface(self):
        return (isinstance(self.interface, Interface)
                and self.interface._is_valid())

    def on_inherit(self, updater, bases, txn):
        """Re-derive self from ``bases[0]``.

        The resolution is computed first (so an out-of-scope error
        aborts the edit before any state change), writes are journaled,
        and trace clearing is deferred to the pipeline finalize stage —
        and skipped entirely when the binding is unchanged.

        A value inside a space the edit is deleting still looks alive
        here (deletion is finalized post-commit), but must be treated
        as invalid so the deletion is not aborted by a failing relative
        resolution (pre-pipeline deletion order).
        """
        if bases[0].has_interface() and not txn.is_in_removed_space(
                bases[0].interface._impl):

            if self.refmode == "absolute":
                is_relative = False
                interface = bases[0].interface
            else:
                is_relative, interface = updater.get_relative_interface(
                    self.parent,
                    bases[0])
                if self.refmode == "auto":
                    pass
                elif self.refmode == "relative":
                    if not is_relative:
                        raise ValueError(
                            "Relative reference %s out of scope" %
                            self.get_fullname()
                        )
                else:
                    raise ValueError("must not happen")

            if (interface is not self.interface
                    or is_relative != self.is_relative):
                txn.set_attr(self, "is_relative", is_relative)
                txn.set_attr(self, "interface", interface)
                txn.add_modified(self)
                # Ref values are baked into ns_dict, so a rebind must
                # invalidate the namespaces seeing this ref.
                txn.mark_dirty(self.parent, "own_refs")
        else:
            interface = bases[0].interface
            if interface is not self.interface:
                txn.set_attr(self, "interface", interface)
                txn.add_modified(self)
                txn.mark_dirty(self.parent, "own_refs")


class NameSpaceReferenceImpl(ReferenceImpl):
    __slots__ = ()


class ReferenceProxy:
    """Proxy to interface to References

    *Reference* objects are not exposed to the user,
    thus ReferenceProxy objects are used to interface to References.
    A proxy object to a Reference can be created and returned by
    the :func:`~modelx.get_object` function, by passing
    the full dotted name of the Reference to ``name``,
    and :obj:`True` to ``as_proxy``::

    >>> mx.get_object("Model1.Space1.foo", as_proxy=True)

    Reference shares its ultimate base class with Model, Space and
    Cells classes, and below are attributes common among those
    classes.

    Attributes:

        name (str): The name of the Reference.

        fullname (str): The dotted name of the object.

        parent: The parent of the Reference.

        model: The Model that the Reference belongs to.

    .. seealso::

        :func:`~modelx.get_object`, :class:`~ReferenceNode`

    """

    __slots__ = ("_impl",)

    def __new__(cls, impl=None):
        """Make a :class:`DynamicReferenceProxy` for a dynamic Reference.

        ``ReferenceProxy(impl)`` gives a DynamicReferenceProxy when the
        Reference's parent is an ItemSpace or a DynamicSpace in one: an
        argument of an ItemSpace, a ref that its Space formula returns,
        and the ``_self``, ``_space`` and ``_model`` of either Space.
        Every site that makes a proxy calls ``ReferenceProxy(impl)``, so
        the rule is here.

        A Reference that an ItemSpace shares with its Space, as
        ``P[1].k`` is ``P.k``, keeps its Space as parent, so its proxy is
        a ReferenceProxy. So is that of a slot of an ItemSpace holding
        the ItemSpace's copy of a Space or a Cells, which is not a
        Reference itself on this release: without the ``isinstance``
        test the class would follow the parent of what the slot holds,
        and a slot holding None would raise.

        ``impl`` defaults to None because :func:`copy.copy` calls
        ``cls.__new__(cls)`` with no argument; with ``impl`` required,
        copying any proxy raised TypeError. The rule applies only when
        ``cls`` is ReferenceProxy itself, so a copy keeps its class.
        """
        if (cls is ReferenceProxy and isinstance(impl, ReferenceImpl)
                and not impl.parent.is_model()
                and impl.parent.is_dynamic()):
            cls = DynamicReferenceProxy
        return object.__new__(cls)

    def __init__(self, impl):
        self._impl = impl

    # Explicit, so a copy and a pickle get the impl back on every Python.
    # From 3.11 object.__getstate__ is found first and gives the slots,
    # (None, {'_impl': impl}), while __getattr__ forwards __setstate__ to
    # Interface's, which takes the impl: on 3.11.15 copy.copy gave a proxy
    # whose _impl was that tuple, and whose .value raised AttributeError.
    def __getstate__(self):
        return self._impl

    def __setstate__(self, state):
        self._impl = state

    def __getattr__(self, name):
        item = getattr(Interface, name)
        if isinstance(item, property):
            return item.fget(self)
        elif isinstance(item, FunctionType):
            return functools.partial(item, self)

    @property
    def value(self):
        """Returns referenced object"""
        return self._impl.interface

    @property
    def refmode(self):
        """Returns reference mode

        Returns a string representing the reference mode,
        or :obj:`None` or :obj:`False` for some References.

        Returns:
            str, None or bool: "auto", "absolute" or "relative" for
            most References.
            :obj:`None` for a global Reference and for an argument of
            an :class:`~modelx.core.space.ItemSpace`.
            **Known limitation:** :obj:`False` for a Reference that
            ``new_pandas``, ``new_module`` or ``new_excel_range``
            creates in a :class:`~modelx.core.space.UserSpace`.
            This is not part of the frozen contract and may change.

        Raises:
            AttributeError: On this release, on a proxy got through an
                :class:`~modelx.core.space.ItemSpace` for a Reference of
                its Space that is not ``'absolute'`` and whose value is
                the Space itself, or a Cells or a Space inside it,
                because such a proxy stands for the ItemSpace's copy of
                the value (see :ref:`reference-proxy-identity`); and on
                a proxy got through an ItemSpace for a Reference to a
                Space whose name begins with the name of the Space, such
                as ``PX`` for ``P`` (see :ref:`the note on such
                References <toolapi-prefix-ref>`).
                These are known limitations, not part of the frozen
                contract, and may change.

        .. seealso::

            :meth:`~modelx.core.space.UserSpace.set_ref`,
            :meth:`~modelx.core.space.UserSpace.absref`,
            :meth:`~modelx.core.space.UserSpace.relref`

        """
        return self._impl.refmode

    def _is_derived(self):
        """Whether the Reference is a copy, not defined in its own Space.

        :obj:`True` if the Reference was copied from a base Space
        into a sub Space and has not been redefined there.
        :obj:`False` for a Space's own Reference, also when it
        overrides a Reference of a base Space,
        for a global Reference, also through a Space,
        for an argument of an :class:`~modelx.core.space.ItemSpace`,
        for a Reference that a Space formula returns,
        and for the ``_self``, ``_space`` and ``_model`` of a Space.
        Through an ItemSpace, a Reference of its Space
        gives the flag of that Reference.

        :obj:`None` when the proxy does not stand for a Reference,
        so a tool that asks every proxy in a model gets an answer
        from each, and no exception.

        On this release that is the case for a proxy got through an
        ItemSpace for a Reference of its Space that is not
        ``'absolute'`` and whose value is the Space itself, or a Cells
        or a Space inside it, because such a proxy stands for the
        ItemSpace's copy of the value (see
        :ref:`reference-proxy-identity`), and for a proxy got through an
        ItemSpace for a Reference to a Space whose name begins with the
        name of the Space, such as ``PX`` for ``P`` (see
        :ref:`the note on such References <toolapi-prefix-ref>`).
        Which proxies these are is a known limitation, not part of the
        frozen contract, and may change.

        Returns:
            bool or None: :obj:`True` for a derived Reference,
            :obj:`False` for any other Reference, :obj:`None` for a
            proxy that does not stand for a Reference.

        .. versionadded:: 0.34.0
        """
        impl = self._impl
        # An isinstance test, not a try. On this release a proxy's impl can
        # be an item's DynamicSpaceImpl, ItemSpaceImpl or DynamicCellsImpl,
        # or None (see the docstring). Without the test, a whole-model
        # _get_attrdict(['_is_derived']) raised
        # "AttributeError: 'DynamicSpaceImpl' object has no attribute
        # 'is_derived'". A try would not do: a DynamicCellsImpl has
        # is_derived(), and gave its Cells' flag, True, for the proxy.
        if isinstance(impl, ReferenceImpl):
            return impl.is_derived()
        return None

    def is_derived(self):
        """The same as :meth:`_is_derived`, kept for modelx-bridge 0.10.

        It has no underscore. modelx-bridge 0.10 calls it, so it stays,
        with no deprecation. New code calls :meth:`_is_derived`.

        .. versionchanged:: 0.34.0
            It calls :meth:`_is_derived`, so it returns :obj:`None` for a
            proxy that does not stand for a Reference. On 0.33 it raised
            :obj:`AttributeError` there, or returned :obj:`True` when the
            proxy stood for an ItemSpace's copy of a Cells.
        """
        return self._is_derived()

    @property
    def _baseattrs(self):
        """The older form of :meth:`_get_attrdict`, kept for existing tools.

        Returns:
            dict: The same keys as :meth:`_get_attrdict` called without
            ``extattrs``.
        """
        result = Interface._baseattrs.fget(self)
        result["type"] = "Reference"
        result["value_type"] = type(self.value).__name__
        return result

    def _get_attrdict(self, extattrs=None, recursive=True):
        """A dict that describes the Reference.

        The names in ``extattrs`` are added as the snapshot wire
        describes (see :ref:`toolapi-wire`), and ``recursive`` is
        passed on with them.

        Returns:
            dict: ``'type'``, which is ``'Reference'``;
            ``'id'``, ``'name'``, ``'fullname'``, ``'repr'`` and
            ``'namedid'``, as in the dict of a Model, a Space or a Cells;
            and ``'value_type'``, the class name of the value.
        """
        result = Interface._get_attrdict(self, extattrs, recursive)
        result["type"] = "Reference"
        result["value_type"] = type(self.value).__name__
        if extattrs:
            Interface._get_attrdict_extra(self, result, extattrs, recursive)

        return result

    @property
    def _evalrepr(self):
        """The full name of the Reference in call syntax.

        It is the full name of the Reference's parent in call syntax,
        followed by the name of the Reference. A global Reference has
        the name of its Model before its name, from whichever Space
        the proxy was obtained.
        A proxy that stands for an ItemSpace's copy of a Reference's
        value names the copy instead, a known limitation described
        under "ReferenceProxy forwarding" in :ref:`toolapi-wire`.

        Returns:
            str: Such as ``'Model1.Base.rate'``, ``'Model1.scale'``
            for a global Reference, or ``'Model1.Proj(1).i'`` for an
            argument of an ItemSpace.
        """
        return Interface._evalrepr.fget(self)

    def __repr__(self):
        return Interface.__repr__(self)


class DynamicReferenceProxy(ReferenceProxy):
    """A proxy to a Reference that an ItemSpace makes.

    ``ReferenceProxy(impl)``, and every call that gets a proxy, such as
    :func:`~modelx.get_object` with ``as_proxy=True``, gives a
    DynamicReferenceProxy for a Reference whose parent is an
    :class:`~modelx.core.space.ItemSpace` or a
    :class:`~modelx.core.space.DynamicSpace` in one: an argument of an
    ItemSpace, a ref that the Space formula returns, and the ``_self``,
    ``_space`` and ``_model`` of either Space. A Reference of a Space seen
    through one of its ItemSpaces, as ``P[1].k`` is ``P.k``, and a global
    Reference keep a :class:`ReferenceProxy`.

    A DynamicReferenceProxy is a ReferenceProxy, so ``isinstance`` against
    ReferenceProxy is :obj:`True` for it. A tool tells it apart by the
    name of its class, ``'DynamicReferenceProxy'``, after checking that
    the class is defined in a module of the ``modelx`` package (see
    :ref:`toolapi-kinds`). ``repr()`` shows that name. The ``'type'`` of
    its :meth:`~ReferenceProxy._get_attrdict` and ``_baseattrs`` is
    ``'Reference'``, as for any proxy.

    .. versionadded:: 0.34.0
    """

    __slots__ = ()


class ReferenceNode(ObjectNode):

    @property
    def obj(self):
        """Return the ReferenceProxy object"""
        return ReferenceProxy(self._impl[OBJ])

    def has_value(self):
        """Always returns :obj:`True` as Reference has value"""
        return True

    @property
    def value(self):
        return self._impl[OBJ].interface
