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

    _refmodes = ("auto", "absolute", "relative")
    """The reference modes, as :meth:`~modelx.core.space.UserSpace.set_ref`
    takes them and :attr:`~ReferenceProxy.refmode` gives them.

    ``set_ref`` raises :obj:`ValueError` for a mode not in it.

    .. versionadded:: 0.34.0
    """

    def __new__(cls, impl=None):
        """Make a :class:`DynamicReferenceProxy` for a dynamic Reference.

        ``ReferenceProxy(impl)`` gives a DynamicReferenceProxy when the
        Reference's parent is an ItemSpace or a DynamicSpace in one: an
        argument of an ItemSpace, a ref that its Space formula returns,
        the ``_self``, ``_space`` and ``_model`` of either Space, and a
        Reference of its Space that refers to the ItemSpace's own copy
        of its value, such as ``P[1].rel`` for ``P.rel = P.Child``
        (:ref:`reference-proxy-identity`), which is the ItemSpace's copy
        of the Reference.
        Every site that makes a proxy calls ``ReferenceProxy(impl)``, so
        the rule is here.

        A Reference that an ItemSpace shares with its Space, as
        ``P[1].k`` is ``P.k``, keeps its Space as parent, so its proxy is
        a ReferenceProxy. So is a proxy made over an object that is not
        a Reference: without the ``isinstance`` test the class would
        follow that object's parent, and None would raise. Before 0.34
        a slot of an ItemSpace that referred to the ItemSpace's copy of
        its value held the copy itself, or None for ``P.r = PX``, and
        modelx made such proxies.

        ``impl`` defaults to None because :func:`copy.copy` calls
        ``cls.__new__(cls)`` with no argument; with ``impl`` required,
        copying any proxy raised TypeError. A copy keeps its class
        because it passes no impl, so the rule never reaches it.
        The rule applies only when ``cls`` is ReferenceProxy itself, so
        a class that a subclass or a caller names is kept: without that
        test, a subclass made over an argument of an ItemSpace came back
        a DynamicReferenceProxy.
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

    def __eq__(self, other):
        """Whether ``other`` is a proxy to the same Reference.

        Two proxies are equal when they stand for the same Reference,
        however each was obtained, and of either class: a proxy
        from :func:`~modelx.get_object` with ``as_proxy=True``, one from
        a Space's ``_get_object`` and one from a
        :class:`ReferenceNode`'s ``obj`` are equal, and so is a
        :func:`copy.copy` of any of them. A Reference that an ItemSpace
        shares with its Space, as ``P[1].k`` is ``P.k``, is one
        Reference, so its proxy obtained through the ItemSpace is equal
        to its proxy obtained through the Space.
        A proxy is never equal to an object that is not a proxy,
        such as the value of its Reference.

        .. versionchanged:: 0.34.0
            Proxies are equal by the Reference they stand for. Before,
            each proxy was equal only to itself, so two proxies to one
            Reference made a set of 2.
        """
        # False, not NotImplemented, for an object that is not a proxy.
        # With NotImplemented (object.__eq__, before 0.34) Python then asks
        # the other operand: proxy == P.h raised TypeError from
        # Cells.__eq__ for a Cells with parameters, and proxy == P.sc ran
        # the formula of a scalar Cells (len(tracegraph) 1 -> 2), so a
        # comparison could evaluate the model.
        if isinstance(other, ReferenceProxy):
            return other._impl is self._impl
        return False

    def __hash__(self):
        """The hash of the Reference, so equal proxies hash equally.

        .. versionchanged:: 0.34.0
            Before, the hash was that of the proxy object.
        """
        return hash(id(self._impl))

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

        One of :attr:`_refmodes`, ``'auto'``, ``'absolute'`` or
        ``'relative'``, for a Reference of a UserSpace, its copies, and a
        ref that a Space formula returns, or :obj:`None` for the other
        References, which have no mode.

        * A Reference of a :class:`~modelx.core.space.UserSpace` has the
          mode it was set with: ``'auto'`` when it is set by assignment
          or by the ``refs`` of ``new_space``, and the mode given to
          :meth:`~modelx.core.space.UserSpace.set_ref`,
          ``'absolute'`` by :meth:`~modelx.core.space.UserSpace.absref`
          and ``'relative'`` by
          :meth:`~modelx.core.space.UserSpace.relref`.
          Its copies in sub Spaces have the same mode, and so does the
          Reference seen through an ItemSpace, or a DynamicSpace in one,
          that shares it, as ``P[1].k`` is ``P.k``, or that is the
          ItemSpace's copy of it, as ``P[1].rel`` is for
          ``P.rel = P.Child`` (see :ref:`reference-proxy-identity`).
        * A ref that the formula of a Space returns in ``'refs'`` is
          ``'auto'``.
        * A global Reference, also through a Space or an ItemSpace,
          an argument of an :class:`~modelx.core.space.ItemSpace`, and
          the ``_self``, ``_space`` and ``_model`` of a Space have no
          mode: :obj:`None`.

        Returns:
            str or None: One of :attr:`_refmodes`, or :obj:`None`.

            **Known limitation:** some References give a value that is
            neither: :obj:`False` for a Reference that ``new_pandas``,
            ``new_module`` or ``new_excel_range`` creates in a
            :class:`~modelx.core.space.UserSpace`, and for its copies
            in sub Spaces; and, after :func:`~modelx.read_model`, the
            value the model file holds: an int for a Reference of a
            UserSpace whose value is that of an IOSpec, in a model
            saved in serializer version 7 or earlier, the default format
            before modelx 0.32, and a mode outside :attr:`_refmodes`
            that ``set_ref`` accepted before 0.34, as a str, such as
            ``'sideways'``, or ``'None'`` for :obj:`None`.
            This is not part of the frozen contract and may change.

        .. versionchanged:: 0.34.0
            A Reference seen through an ItemSpace, or a DynamicSpace in
            one, that refers to the ItemSpace's own copy of its value,
            such as ``P[1].rel`` for ``P.rel = P.Child``, has the mode of
            the Reference it copies. Before, its proxy stood for the
            copy, and ``refmode`` raised :obj:`AttributeError`; so it did
            for a Reference to a Space whose name begins with the name of
            the Space, such as ``P.r = PX``.

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
        gives the flag of that Reference. The exception is a Reference
        that refers to the ItemSpace's own copy of its value, such as
        ``P[1].rel`` for ``P.rel = P.Child`` or ``P[1].Child.up`` for
        ``P.Child.up = P`` (see :ref:`reference-proxy-identity`, which
        gives the condition): the ItemSpace has a copy of that Reference,
        a resolved slot (:ref:`toolapi-resolved-slots`), which gives
        :obj:`True`, as ``P[1].h`` does.

        :obj:`None` when the proxy does not stand for a Reference,
        so a tool that asks every proxy in a model gets an answer
        from each, and no exception. modelx makes no such proxy.

        Returns:
            bool or None: :obj:`True` for a derived Reference,
            :obj:`False` for any other Reference, :obj:`None` for a
            proxy that does not stand for a Reference.

        .. versionadded:: 0.34.0
        """
        impl = self._impl
        # An isinstance test, not a try. Before resolved slots, a proxy's
        # impl could be an item's DynamicSpaceImpl, ItemSpaceImpl or
        # DynamicCellsImpl, or None, and a whole-model
        # _get_attrdict(['_is_derived']) raised
        # "AttributeError: 'DynamicSpaceImpl' object has no attribute
        # 'is_derived'". modelx no longer makes such proxies; the test stays
        # so a walk never raises on one made by hand. A try would not do: a
        # DynamicCellsImpl has is_derived(), and gave its Cells' flag.
        if isinstance(impl, ReferenceImpl):
            return impl.is_derived()
        return None

    def is_derived(self):
        """The same as :meth:`~ReferenceProxy._is_derived`, kept for
        modelx-bridge 0.10.

        It has no underscore. modelx-bridge 0.10 calls it, so it stays,
        with no deprecation. New code calls :meth:`_is_derived`.

        .. versionchanged:: 0.34.0
            It calls :meth:`_is_derived`, so it returns :obj:`None` for a
            proxy that does not stand for a Reference. On 0.33 a proxy
            got through an ItemSpace for a Reference that refers to the
            ItemSpace's own copy of its value stood for the copy, and
            ``is_derived()`` raised :obj:`AttributeError` when the copy
            was a Space and returned the copy's flag, :obj:`True`, when
            it was a Cells. From 0.34 such a proxy stands for the
            ItemSpace's copy of the Reference, which is derived.
        """
        return self._is_derived()

    @property
    def _baseattrs(self):
        """The older form of :meth:`~ReferenceProxy._get_attrdict`, kept
        for existing tools.

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

        Returns:
            str: Such as ``'Model1.Base.rate'``, ``'Model1.scale'``
            for a global Reference, ``'Model1.Proj(1).i'`` for an
            argument of an ItemSpace, or ``'Model1.Proj(1).rel'`` for
            ``Proj.rel = Proj.Child`` seen through ``Proj[1]``, which is
            the ItemSpace's copy of the Reference
            (:ref:`reference-proxy-identity`).

        .. versionchanged:: 0.34.0
            For a Reference seen through an ItemSpace that refers to the
            ItemSpace's own copy of its value, the name of the Reference
            after the ItemSpace's, ``'Model1.Proj(1).rel'``. Before, the
            proxy stood for the copy, so it gave the copy's,
            ``'Model1.Proj(1).Child'``.
        """
        return Interface._evalrepr.fget(self)

    @property
    def _idstr(self):
        """The dotted name of the Reference without the name of its
        Model.

        It is the ``_idstr`` of the Reference's parent followed by the
        name of the Reference, or the name alone for a global Reference,
        from whichever Space the proxy was obtained. An ItemSpace
        appears in it under its ``__SpaceN`` name, so an ``_idstr`` that
        contains one is valid only while that ItemSpace lives.

        Returns:
            str: Such as ``'Base.rate'``, ``'scale'`` for a global
            Reference, ``'Proj.__Space1.i'`` for an argument of an
            ItemSpace, or ``'Proj.__Space1.rel'`` for
            ``Proj.rel = Proj.Child`` seen through ``Proj[1]``, which is
            the ItemSpace's copy of the Reference
            (:ref:`reference-proxy-identity`).

        .. versionchanged:: 0.34.0
            Defined on the class, so ``getattr(type(proxy), '_idstr')``
            finds it. Before, the proxy answered it by forwarding it to
            the base class of Model, Spaces and Cells, with the same
            value, except for a Reference seen through an ItemSpace that
            refers to the ItemSpace's own copy of its value: its proxy
            stood for the copy, so it gave the copy's,
            ``'Proj.__Space1.Child'``.
        """
        return Interface._idstr.fget(self)

    def _get_repr(self, fullname=False, add_params=True):
        """The display string of the Reference.

        It is the name of the Reference. With ``fullname=True`` it is
        the display name of the Reference's parent, as the parent's
        ``_get_repr(fullname=True, add_params=False)`` gives it, followed
        by the name, so it starts with the name of the Model.
        ``add_params`` changes nothing for a Reference.

        Returns:
            str: Such as ``'rate'``, or ``'Model1.Base.rate'`` and
            ``'Model1.Proj[1].i'`` with ``fullname=True``.

        .. versionchanged:: 0.34.0
            Defined on the class, so ``getattr(type(proxy),
            '_get_repr')`` finds it. Before, the proxy answered it by
            forwarding it to the base class of Model, Spaces and Cells,
            with the same value, except for a Reference seen through an
            ItemSpace that refers to the ItemSpace's own copy of its
            value (:ref:`reference-proxy-identity`): its proxy stood for
            the copy, so it gave the copy's string, ``'Child'`` where it
            now gives ``'rel'``.
        """
        return Interface._get_repr(self, fullname, add_params)

    def _is_valid(self):
        """Whether the Reference that the proxy stands for is still
        bound.

        :obj:`True` while the Space or the Model that holds the
        Reference holds it under its name. :obj:`False` once the
        Reference is deleted or bound again, as by ``space.x = 2``,
        and once the Space that holds it is deleted.
        Binding a Reference of a base Space again makes a new copy of it
        in each sub Space, so a proxy to a copy turns :obj:`False` then.
        An argument of an ItemSpace, a ref that its Space formula
        returns, the ``_self``, ``_space`` and ``_model`` of an
        ItemSpace or a DynamicSpace in it, and the ItemSpace's copy of a
        Reference that refers to the ItemSpace's own copy of its value
        (``P[1].rel`` for ``P.rel = P.Child``, see
        :ref:`reference-proxy-identity`) turn :obj:`False` when the
        ItemSpace is deleted, by ``del``, by ``clear_items()``, or by an
        edit that deletes the ItemSpaces of its Space. They stay
        :obj:`False` when an ItemSpace with the same arguments is made
        again, because the new ItemSpace has References of its own.
        The References of a closed Model stay valid, as the closed
        Model's own ``_is_valid()`` does.

        ``repr()`` of a proxy whose Reference is no longer bound shows a
        null object, as for a deleted Cells:
        ``<ReferenceProxy null object>``, or
        ``<DynamicReferenceProxy null object>``.

        Returns:
            bool: :obj:`True` while the Reference is bound, :obj:`False`
            after.

        .. versionchanged:: 0.34.0
            :obj:`False` once the Reference is no longer bound. Before,
            the proxy forwarded it to the base class of Model, Spaces and
            Cells, which gave :obj:`True` for every proxy, also after its
            Reference was deleted or bound again, and after the ItemSpace
            that made it was deleted. ``repr()`` of such a proxy showed
            the Reference.
        """
        impl = self._impl
        if not isinstance(impl, ReferenceImpl):
            # Not a Reference. modelx makes no such proxy since resolved
            # slots; before them a slot of an ItemSpace held the item's copy
            # of a value, or None for P.r = PX. The answer Interface gives,
            # and never a raise.
            return Interface._is_valid(self)
        # Two tests, both on impls. The container test alone is not enough:
        # a deleted ItemSpace keeps its dicts, so an argument or a formula
        # ref of a cleared ItemSpace passed it (fix-used-by/u04). The parent
        # test must not ask the parent's interface for _is_valid(): an
        # ItemSpace made again with the same arguments re-uses the old
        # interface objects, and with that test a kept argument or formula
        # ref proxy answered True again after del P[3]; P[3], after
        # P.clear_items(); P[3] and after a rebind of P.rel and P[3]
        # (refute2/r08b; fix-final/e03, both re-run on this code).
        parent = impl.parent
        return (parent.interface._impl is parent
                and impl.container.get(impl.name) is impl)

    def __repr__(self):
        return Interface.__repr__(self)


class DynamicReferenceProxy(ReferenceProxy):
    """A proxy to a Reference that an ItemSpace makes.

    ``ReferenceProxy(impl)``, and every call that gets a proxy, such as
    :func:`~modelx.get_object` with ``as_proxy=True``, gives a
    DynamicReferenceProxy for a Reference whose parent is an
    :class:`~modelx.core.space.ItemSpace` or a
    :class:`~modelx.core.space.DynamicSpace` in one: an argument of an
    ItemSpace, a ref that the Space formula returns, the ``_self``,
    ``_space`` and ``_model`` of either Space, and the ItemSpace's copy of
    a Reference of its Space that refers to the ItemSpace's own copy of
    its value, as ``P[1].rel`` is for ``P.rel = P.Child``
    (:ref:`reference-proxy-identity`), which tools call a resolved slot
    (:ref:`toolapi-resolved-slots`). Any other Reference of a Space seen
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
