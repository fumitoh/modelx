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

"""Unified mutation pipeline (CoreRefactorDesign §5.4, Phase 4).

One ``ModelEditor`` entry point runs each ``Edit`` through
validate -> apply -> derive inside a :class:`Transaction`, rolls back on
any exception, and performs all side effects (trace invalidation,
deletions, batched namespace notification, ValueRegistry/IOSpec
bookkeeping, itemspace invalidation) post-commit in ``_finalize``.

Phase 4 covers the reference mutations end-to-end. The ``derive`` stage
is an interim per-Edit hook: Phase 5 replaces it with
``InheritanceSync.derive`` as the single home of derived-member
creation.
"""

from modelx.core.base import Interface
from modelx.core.binding.namespace import NamespaceServer
from modelx.core.reference import ReferenceImpl
from modelx.core.edit.transaction import Transaction, ChangeSet


class Edit:
    """One model mutation.

    ``validate`` performs name/cycle/relref checks without changing any
    state; ``apply`` performs the defined-member structural writes,
    journaled through the transaction; ``derive`` fans the change out to
    derived members in sub spaces (interim home, see module docstring).
    """

    result = None

    def validate(self, model, txn):
        pass

    def apply(self, model, txn):
        raise NotImplementedError

    def derive(self, model, txn):
        pass


class ModelEditor:
    """Runs Edits against a model (CoreRefactorDesign §5.4).

    Stateless: constructed per access by ``ModelImpl.editor`` so that no
    new slot enters pickled model state.
    """

    def __init__(self, model):
        self.model = model

    def execute(self, edit):
        txn = Transaction(self.model)
        try:
            edit.validate(self.model, txn)
            edit.apply(self.model, txn)
            edit.derive(self.model, txn)
        except BaseException:
            txn.rollback()
            raise
        txn.commit()
        self._finalize(txn.changes)
        return edit.result

    def _finalize(self, changes):
        """Post-commit side effects; must not fail the edit."""
        model = self.model

        # 1. Trace invalidation for removed and modified members
        for impl in changes.removed:
            if isinstance(impl, ReferenceImpl):
                model.clear_attr_referrers(impl)
            else:
                model.clear_obj(impl)
        for impl in changes.modified:
            if isinstance(impl, ReferenceImpl):
                model.clear_attr_referrers(impl)
            else:
                model.clear_obj(impl)

        # 2. Finalize deletions
        for impl in changes.removed:
            impl.on_delete()

        # 3. Batched notify: exactly one namespace invalidation per
        #    dirty container. The itemspace-deletion half of
        #    DynamicBase.on_notify is handled by ItemSpaceManager below.
        for parent, attr in changes.dirty_containers:
            container = getattr(parent, attr)
            if parent.is_model():
                for space in parent.yield_spaces():
                    NamespaceServer.on_notify(space, container)
            else:
                NamespaceServer.on_notify(parent, container)

        # 4. ValueRegistry / IOSpec bookkeeping
        for op in changes.registry_ops:
            if op[0] == "register":
                model.valreg.register(op[1])
            elif op[0] == "unregister":
                model.valreg.unregister(op[1])
            elif op[0] == "rebind":
                model.valreg.rebind(op[1], op[2])
            else:
                raise RuntimeError("must not happen")

        # 5. Itemspace invalidation (verbatim pre-pipeline policy)
        model.itemspacemgr.invalidate(changes)


# ----------------------------------------------------------------------
# Space-level reference edits


def _create_ref(txn, space, name, value, is_derived, refmode):
    ref = ReferenceImpl(space, name, value, container=space.own_refs,
                        is_derived=is_derived, refmode=refmode)
    txn.set_item(space.own_refs, name, ref)
    txn.add_created(ref)
    txn.mark_dirty(space, "own_refs")
    return ref


def _replace_ref(txn, space, name, value, is_derived, refmode):
    old = space.own_refs[name]
    txn.del_item(space.own_refs, name)
    txn.add_removed(old)
    new = _create_ref(txn, space, name, value, is_derived, refmode)
    return old, new


class NewRef(Edit):
    """Create a reference in a space and derive it into sub spaces."""

    def __init__(self, space, name, value, refmode, register=False):
        self.space = space
        self.name = name
        self.value = value
        self.refmode = refmode
        self.register = register

    def validate(self, model, txn):
        spmgr = model.spmgr
        other = spmgr._find_name_in_subs(self.space, self.name)
        if other is not None:
            if not isinstance(other, ReferenceImpl):
                raise ValueError("Cannot create reference '%s'" % self.name)
            elif other not in model.global_refs.values():
                raise ValueError("Cannot create reference '%s'" % self.name)

        spmgr._check_subs_relrefs(
            self.space, self.name, self.value, self.refmode)

    def apply(self, model, txn):
        ref = _create_ref(txn, self.space, self.name, self.value,
                          is_derived=False, refmode=self.refmode)
        if self.register:
            txn.changes.registry_ops.append(("register", ref))
        self.result = ref

    def derive(self, model, txn):
        spmgr = model.spmgr
        space, name, refmode = self.space, self.name, self.refmode
        value = self.value

        for subspace in spmgr._get_subs(space):
            is_relative = False
            if name in subspace.own_refs:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = spmgr.get_relative_interface(
                        subspace, space.own_refs[name])
            ref = _create_ref(txn, subspace, name, value,
                              is_derived=True, refmode=refmode)
            ref.is_relative = is_relative


class ChangeRef(Edit):
    """Assign a new value to an existing reference in a space."""

    def __init__(self, space, name, value, refmode, rebind=False):
        self.space = space
        self.name = name
        self.value = value
        self.refmode = refmode
        self.rebind = rebind

    def validate(self, model, txn):
        model.spmgr._check_subs_relrefs(
            self.space, self.name, self.value, self.refmode)

    def apply(self, model, txn):
        old, new = _replace_ref(txn, self.space, self.name, self.value,
                                is_derived=False, refmode=self.refmode)
        if self.rebind:
            txn.changes.registry_ops.append(("rebind", old, new))

    def derive(self, model, txn):
        spmgr = model.spmgr
        space, name, refmode = self.space, self.name, self.refmode
        value = self.value

        for subspace in spmgr._get_subs(space):
            is_relative = False
            subref = subspace.own_refs[name]
            if subref.is_defined():
                break
            elif subref.defined_bases[0] is not space.own_refs[name]:
                break
            if isinstance(value, Interface) and value._is_valid():
                if refmode == "auto" or refmode == "relative":
                    is_relative, value = spmgr.get_relative_interface(
                        subspace, space.own_refs[name])
            old, _ = _replace_ref(txn, subspace, name, value,
                                  is_derived=True, refmode=refmode)
            # Preserved pre-pipeline behavior: SpaceManager.change_ref
            # assigned the resolved is_relative to the object returned by
            # on_change_ref, which was the replaced (old) ref; the new
            # derived ref keeps the flag its constructor derives from
            # refmode.
            txn.set_attr(old, "is_relative", is_relative)


class DelRef(Edit):
    """Delete a reference from a space and re-derive its sub spaces."""

    def __init__(self, space, name, unregister=False):
        self.space = space
        self.name = name
        self.unregister = unregister

    def apply(self, model, txn):
        ref = self.space.own_refs[self.name]
        txn.del_item(self.space.own_refs, self.name)
        txn.add_removed(ref)
        txn.mark_dirty(self.space, "own_refs")
        if self.unregister:
            txn.changes.registry_ops.append(("unregister", ref))

    def derive(self, model, txn):
        # Mirrors SharedSpaceOperations.update_subs(space, skip_self=False):
        # reconcile 'cells' across all affected spaces before 'own_refs'
        # (the two-phase inheritance order, CoreRefactorDesign §2.1).
        spmgr = model.spmgr
        for attr in ("cells", "own_refs"):
            for s in spmgr._get_subs(self.space, skip_self=False):
                bases = spmgr._get_space_bases(s)
                s.on_inherit(spmgr, bases, attr, txn=txn)


# ----------------------------------------------------------------------
# Model-global reference edits


class NewGlobalRef(Edit):
    """Create a global reference on the model."""

    def __init__(self, model, name, value, register=False):
        self.name = name
        self.value = value
        self.register = register

    def apply(self, model, txn):
        ref = ReferenceImpl(model, name=self.name, value=self.value,
                            container=model._global_refs)
        txn.set_item(model._global_refs, self.name, ref)
        txn.add_created(ref)
        txn.mark_dirty(model, "global_refs")
        if self.register:
            txn.changes.registry_ops.append(("register", ref))
        self.result = ref


class DelGlobalRef(Edit):
    """Delete a global reference from the model."""

    def __init__(self, model, name, unregister=False):
        self.name = name
        self.unregister = unregister

    def apply(self, model, txn):
        ref = model.global_refs[self.name]
        txn.del_item(model._global_refs, self.name)
        txn.add_removed(ref)
        txn.mark_dirty(model, "global_refs")
        if self.unregister:
            txn.changes.registry_ops.append(("unregister", ref))


class ChangeGlobalRef(Edit):
    """Assign a new value to an existing global reference."""

    def __init__(self, model, name, value, rebind=False):
        self.name = name
        self.value = value
        self.rebind = rebind

    def apply(self, model, txn):
        old = model.global_refs[self.name]
        txn.del_item(model._global_refs, self.name)
        txn.add_removed(old)
        new = ReferenceImpl(model, name=self.name, value=self.value,
                            container=model._global_refs)
        txn.set_item(model._global_refs, self.name, new)
        txn.add_created(new)
        txn.mark_dirty(model, "global_refs")
        if self.rebind:
            txn.changes.registry_ops.append(("rebind", old, new))
        self.result = new
