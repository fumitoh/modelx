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
        for name, ref in self._dynbase.own_refs.items():
            self._dynbase_refs[name] = self.wrap_impl(ref)

        for space in self.named_spaces.values():
            space._init_dynbaserefs()

    def wrap_impl(self, value):

        assert isinstance(value, ReferenceImpl)

        if isinstance(value.interface, Interface) and value.interface._is_valid():

            if value.is_relative:   # value.is_relative is set to True
                                    # When value.is_defined and
                                    # value.refmode == "relative"

                impl = value.interface._impl.idstr
                root = self.rootspace._dynbase.idstr
                rootlen = len(root)

                if root == impl:
                    return self.rootspace
                elif root == impl[:rootlen]:
                    return self.rootspace.get_impl_from_name(
                        impl[rootlen+1:]) # +1 to remove preceding dot
                else:
                    if value.refmode == "auto":
                        if value.is_defined():
                            return value
                        else:
                            return value.direct_bases[0]

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

        if add_params:
            args = [repr(arg) for arg in get_interface_list(self.argvalues)]
            param = ", ".join(args)
            return "%s[%s]" % (self.parent.name, param)
        else:
            return self.name

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
