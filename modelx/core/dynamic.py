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

"""Dynamic (item) space implementation classes.

Moved out of :mod:`modelx.core.space` in Phase 8 of the core
refactoring (CoreRefactorDesign §5.1). :mod:`modelx.core.space`
re-imports these names permanently: runtime pickles of live models
record them under their historical ``modelx.core.space`` paths.

This module is imported by :mod:`modelx.core.space` mid-module, after
``BaseSpaceImpl`` and the ``DynamicSpace``/``ItemSpace`` interfaces are
defined and before ``UserSpaceImpl`` (which inherits ``DynamicBase``).
Names that space.py defines later, such as ``UserSpaceImpl``, must be
looked up through the module object at runtime.
"""

from modelx.core.base import (
    get_interface_list,
    get_mixin_slots,
    Interface,
)
from modelx.core.binding.namespace import NamespaceServer
from modelx.core.chainmap import CustomChainMap
from modelx.core.reference import ReferenceImpl
from modelx.core.cells import DynamicCellsImpl
from modelx.core.util import is_valid_name
from modelx.core import space as _space
from modelx.core.space import BaseSpaceImpl, DynamicSpace, ItemSpace


class DynamicBase(BaseSpaceImpl):
    """A space that dynamic spaces can be based on.

    ``_dynamic_subs`` lists the live dynamic spaces whose ``_dynbase``
    is this space. Itemspace invalidation no longer walks it (Phase 7:
    ``ItemSpaceManager`` intersects each itemspace's recorded closure
    with ``ChangeSet.dirty_spaces`` instead); namespace changes reach
    this class as plain ``NamespaceServer.on_notify`` flag propagation.
    """

    __slots__ = ("_dynamic_subs",) + get_mixin_slots(BaseSpaceImpl)

    def __init__(self):
        self._dynamic_subs = []


class DynamicSpaceImpl(BaseSpaceImpl):
    """The implementation of Dynamic Space class."""

    interface_cls = DynamicSpace

    __slots__ = (
        "_dynbase",
        "_allargs",
        "rootspace",
        "_dynbase_refs"
    ) + get_mixin_slots(BaseSpaceImpl)

    def __init__(
        self,
        parent,
        name,
        container,
        base,
        refs=None,
        arguments=None,
        cache=None
    ):
        self._dynbase = base
        base._dynamic_subs.append(self)
        self._init_root(parent)
        if cache:
            cache._impl = self
            self.interface = cache # must be set before Impl.__init__
        BaseSpaceImpl.__init__(
            self,
            parent,
            name,
            base.formula,
            arguments,
            base.doc
        )

        container[name] = self

        if refs is not None:
            for key, value in refs.items():
                self.own_refs[key] = ReferenceImpl(
                    self, key, value, container=self.own_refs,
                    refmode="auto")

        self._init_cells()

    def _init_root(self, parent):
        self.rootspace = parent.rootspace

    def _init_cells(self):
        for base in self._dynbase.cells.values():
            cells = DynamicCellsImpl(space=self, base=base, is_derived=True)
            self.cells[cells.name] = cells
            self.on_notify(self.cells)

    def _init_refs(self, arguments=None):
        self._allargs = self._init_allargs()
        self._dynbase_refs = {}
        self.refs = CustomChainMap(
                *self._allargs.maps,     # underlying parent's _allargs
                self.own_refs,
                self.sys_refs,
                self._dynbase_refs,
                self.model._global_refs)

        self.refs_outer = CustomChainMap(
                *self._allargs.maps,     # underlying parent's _allargs
                self.own_refs,
                self._dynbase_refs,
                self.model._global_refs)

    def _init_dynbaserefs(self):
        # Populate _dynbase_refs creating relative reference within
        # the dynamic space tree.
        # Called from ItemSpaceParent.__init__ at last.
        #
        # A Reference re-pointed at the tree's own copy of its value (a
        # resolved slot, ToolAPIDesign T5, decision 7) gets a ReferenceImpl
        # of its own here, a derived copy of the binding with this Space as
        # parent and _dynbase_refs as container, like an argument has in
        # _arguments. Before 0.34 the slot held the copy's impl itself, so
        # its proxy had the copy's name and _idstr ('Child',
        # 'P.__Space1.Child' for P[1].rel with P.rel = P.Child), its
        # refmode and is_derived() raised AttributeError, it never went
        # stale, and _space.rel in a formula of P[1] failed the assert in
        # Namespace.__getattr__. on_update_ns gives formulas the same object
        # as before for such a slot.
        slots = self._dynbase_refs
        for name, ref in self._dynbase.own_refs.items():
            impl = self.wrap_impl(ref)
            if not isinstance(impl, ReferenceImpl):
                impl = ReferenceImpl(
                    self, name, impl.interface, container=slots,
                    is_derived=True, refmode=ref.refmode)
            slots[name] = impl

        for space in self.named_spaces.values():
            space._init_dynbaserefs()

    def on_update_ns(self):
        BaseSpaceImpl.on_update_ns(self)
        # A resolved slot whose value is a Space of the tree gives formulas
        # that Space's namespace, as the slot holding the Space's impl did
        # before 0.34, not the interface the loop above puts there for a
        # Reference. With the interface, recomputing P[1].h(), which reads
        # rel.w(), cost 10.48-10.88 us against 9.35-9.95 us (min of 7 x
        # 20,000, 3 processes each); with the namespace every ns_dict entry
        # of the dynamic Spaces of a synthetic model and of simplelife's
        # items, 402 in all, was the same object as on 1d92c67.
        # A slot whose value is a Cells already gives the Cells, as before.
        # An argument or a formula ref of the same name hides the slot, and
        # a Cells of the same name wins over it, as the loop above runs the
        # Cells last: add_bases lets S have both, a Cells c inherited from B
        # and S.c = S.Child. Without the Cells test, c() in a formula of
        # S[1] raised FormulaError, as c was S[1].Child's namespace, where
        # S's formulas and S[1]'s on 1d92c67 called the Cells.
        slots = self._dynbase_refs
        refs = self.refs
        cells = self.cells
        ns_dict = self._ns_dict
        for name, ref in slots.items():
            if (ref.container is slots and refs[name] is ref
                    and name not in cells):
                target = ref.interface._impl
                if isinstance(target, NamespaceServer):
                    ns_dict[name] = target._namespace

    def wrap_impl(self, value):

        assert isinstance(value, ReferenceImpl)

        if isinstance(value.interface, Interface) and value.interface._is_valid():

            if value.is_relative:   # value.is_relative is set to True
                                    # When value.is_defined and
                                    # value.refmode == "relative"

                impl = value.interface._impl.idstr
                root = self.rootspace._dynbase.idstr

                if root == impl:
                    return self.rootspace
                elif impl.startswith(root + "."):
                    # A dot boundary: before 0.34 the test was
                    # root == impl[:len(root)], so for P.r = PX, a sibling
                    # whose name starts with 'P', the slot held None: every
                    # formula of P[1] raised AttributeError ('NoneType'
                    # object has no attribute 'interface'), and so did the
                    # dicts of P[1], of its refs view and of the Model
                    # ('... no attribute 'name'') (fix-reference-identity/
                    # g06). With 'relative', P[1] is now refused as for any
                    # other sibling: "'PX' referred as 'P.r' is out of 'P'".
                    copy = self.rootspace.get_impl_from_name(
                        impl[len(root) + 1:])   # +1 to remove preceding dot
                    if copy is not None:
                        return copy
                    # The tree has no copy of the value, such as for
                    # P.r = P.Child[3], an ItemSpace, which no item copies:
                    # before 0.34 the slot held None, with the failures
                    # above. The item sees what its Space sees, as for a
                    # value outside the tree.
                    return value
                else:
                    if value.refmode == "auto":
                        # The binding, also when it is derived: its value
                        # is already the one its Space sees. Before 0.34 a
                        # derived binding went to value.direct_bases[0],
                        # which a ReferenceImpl does not have, so making the
                        # ItemSpace raised AttributeError, as for Y.P[1]
                        # with Y.P(X.P) and X.P.r = X.Other relative to
                        # Y.Other.
                        return value

                    elif value.refmode == "relative":
                        raise ValueError(
                            "'%s' referred as '%s' is out of '%s'" %
                            (impl, value.idstr, root)
                        )
                    else:
                        raise RuntimeError("must not happen")

            else:   # absolute
                return value
        else:
            return value


    def _init_allargs(self):
        if isinstance(self.parent, _space.UserSpaceImpl):
            allargs = [self._arguments]
        elif isinstance(self, ItemSpaceImpl):
            allargs = [self._arguments, *self.parent._allargs.maps]
        else:
            allargs = [*self.parent._allargs.maps]

        return CustomChainMap(*allargs)

    def on_delete(self):
        for space in list(self.named_spaces.values()):
            space.on_delete()
            del self.named_spaces[space.name]
        self.del_all_itemspaces()
        self._dynbase._dynamic_subs.remove(self)
        super().on_delete()

    @property
    def arguments(self):
        return self._arguments

    def is_dynamic(self):
        return True

    @property
    def dynamic_key(self):
        # Non-ItemSpace
        return self.parent.dynamic_key + (self.name,)

    @property
    def bases(self):
        if self._dynbase:
            return [self._dynbase]
        else:
            return []

    @property
    def direct_bases(self):
        # A dynamic space has no node in the inheritance graph, so the
        # graph's preds of its idstr named bases of unrelated spaces:
        # P[1].Child gave the bases of P (F6). Its only base is _dynbase.
        return self.bases


class ItemSpaceImpl(DynamicSpaceImpl):

    interface_cls = ItemSpace

    __slots__ = (
        "_arguments",
        "argvalues",
        "argvalues_if",
        "tree_dynbases"
    ) + get_mixin_slots(DynamicSpaceImpl)

    def __init__(
        self,
        parent,
        base,
        name,
        refs,
        arguments,
        cache
    ):
        if name is None:
            name = parent.itemspacenamer.get_next(base.named_itemspaces)
        elif (is_valid_name(name)
              and name not in parent.namespace
              and name not in parent.named_itemspaces):
            pass
        else:
            raise ValueError("invalid name")

        DynamicSpaceImpl.__init__(
            self, parent, name, parent._named_itemspaces, base, refs, arguments, cache
        )
        self._bind_args(self.arguments)
        self._init_child_spaces(self)
        self._init_dynbaserefs()
        self.tree_dynbases = tuple(self._iter_tree_dynbases(self))

    def _init_root(self, parent):
        self.rootspace = self

    def _init_child_spaces(self, space):
        for name, base in space._dynbase.named_spaces.items():
            dkey = space.dynamic_key + (name,)
            cache = self.dynamic_cache.get(dkey, None)
            child = DynamicSpaceImpl(space, name, space.named_spaces, base, cache=cache)
            self._init_child_spaces(child)
            self.parent.dynamic_cache[dkey] = child.interface

    # ----------------------------------------------------------------------
    # Selective invalidation closure (CoreRefactorDesign §5.8, Phase 7)

    @classmethod
    def _iter_tree_dynbases(cls, space):
        """Yield the ``_dynbase`` of each node of this itemspace's
        dynamic tree (the root plus the ``_init_child_spaces``
        recursion; nested itemspaces record their own trees)."""
        yield space._dynbase
        for child in space.named_spaces.values():
            yield from cls._iter_tree_dynbases(child)

    def get_tree_dynbases(self):
        """The dynbases of this itemspace's tree, recorded at creation.

        The impls are recorded rather than their idstrs so that the
        closure follows renames of (and survives deletions of) the base
        spaces; ``ItemSpaceManager`` resolves idstrs at invalidation
        time. ``None`` marks a pre-Phase-7 pickle; the tree is immutable
        after creation, so recording lazily gives the same result.
        """
        if self.tree_dynbases is None:
            self.tree_dynbases = tuple(self._iter_tree_dynbases(self))
        return self.tree_dynbases

    def __setstate__(self, state):
        super().__setstate__(state)
        if "tree_dynbases" not in state:    # pre-Phase-7 pickle
            self.tree_dynbases = None

    def _init_refs(self, arguments=None):
        args = {}
        for k, v in arguments.items():
            args[k] = ReferenceImpl(self, k, v, container=args)
        self._arguments = args
        DynamicSpaceImpl._init_refs(self)


    def _bind_args(self, args):
        boundargs = self.parent.formula.signature.bind(**args)
        self.argvalues = tuple(boundargs.arguments.values())
        self.argvalues_if = tuple(get_interface_list(self.argvalues))

    # ----------------------------------------------------------------------
    # repr methods

    def repr_parent(self):
        return self.parent.repr_parent()

    def repr_self(self, add_params=True):
        # The argument form whatever add_params is, so that
        # get_repr(fullname=True, add_params=False) is the display name
        # of every object (F1), and an item of an item is labelled by
        # its parent's argument form, recursively. On 0.33 P[1][5]
        # displayed as 'Syn.__Space1[5]', and with add_params=False as
        # 'Syn.__Space2', which left out P[1] altogether; P[1] gave
        # 'Syn.__Space1' and P[1].Child[2] 'Syn.P[1].__Space1'.
        args = [repr(arg) for arg in get_interface_list(self.argvalues)]
        if isinstance(self.parent, ItemSpaceImpl):
            label = self.parent.repr_self()
        else:
            label = self.parent.name
        return "%s[%s]" % (label, ", ".join(args))

    @property
    def evalrepr(self):
        """TraceObject repr"""
        args = [repr(arg) for arg in get_interface_list(self.argvalues)]
        param = ", ".join(args)
        return "%s(%s)" % (self.parent.evalrepr, param)

    @property
    def dynamic_key(self):
        if self.parent.is_dynamic():
            return self.parent.dynamic_key + (self.argvalues_if,)
        else:
            return (self.argvalues_if,)
