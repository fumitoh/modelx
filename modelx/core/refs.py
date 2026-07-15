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

from modelx.core.base import Interface
from modelx.core.space import UserSpaceImpl


class ReferenceManager:

    def __init__(self, model, iomanager):
        self._model = model
        self._manager = iomanager
        self._valid_to_refs = {}         # id(value) -> [refs]

    def _check_sanity(self):

        for refs in self._valid_to_refs.values():
            for r in refs:
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=r.interface)
                if spec is not None:
                    assert r.interface is spec.value
                    spec._check_sanity()

    def has_spec(self, value):
        spec = self._manager.get_spec_from_value(self._model.interface, value)
        return spec is not None

    def get_spec(self, value):
        return self._manager.get_spec_from_value(self._model.interface, value)

    @property
    def values(self):
        return list(ref[0].interface for ref in self._valid_to_refs.values())

    @property
    def specs(self):
        result = []
        for r in self._valid_to_refs.values():
            spec = self.get_spec(r[0].interface)
            if spec is not None:
                result.append(spec)
        return result

    def new_ref(self, impl, name, value, refmode):
        # ModelImpl imported here to avoid a circular import with model.py
        from modelx.core.model import ModelImpl

        if isinstance(impl, ModelImpl):
            ref = impl.new_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            ref = impl.model.spmgr.new_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(value, Interface):
            refs = self._valid_to_refs.setdefault(id(value), [])
            assert all(ref is not r for r in refs)
            refs.append(ref)

    def del_ref(self, impl, name):
        # ModelImpl imported here to avoid a circular import with model.py
        from modelx.core.model import ModelImpl

        refdict = impl.own_refs
        ref = refdict[name]
        valid = id(ref.interface)
        val = ref.interface

        if isinstance(impl, ModelImpl):
            impl.del_ref(name)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.del_ref(impl, name)
        else:
            raise RuntimeError("must not happen")

        if not isinstance(val, Interface):
            refs = self._valid_to_refs.get(valid)
            assert refs
            refs.remove(ref)
            if not refs:
                del self._valid_to_refs[valid]
                spec = self._manager.get_spec_from_value(
                    io_group=self._model.interface,
                    value=val
                )
                if spec:
                    self._manager.del_spec(spec)

    def change_ref(self, impl, name, value, refmode=None):
        # ModelImpl imported here to avoid a circular import with model.py
        from modelx.core.model import ModelImpl

        refdict = impl.own_refs
        prev_ref = refdict[name]
        prev_valid = id(prev_ref.interface)
        prev_val = prev_ref.interface

        if isinstance(impl, ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")

        refs = self._valid_to_refs.get(prev_valid, None)
        if refs is not None:        # None in case prev_ref is derived
            if prev_ref in refs:
                refs.remove(prev_ref)
            if not refs:    # ref is empty
                del self._valid_to_refs[prev_valid]
                spec = self._manager.get_spec_from_value(self._model.interface, prev_val)
                if spec:
                    self._manager.del_spec(spec)

        if not isinstance(value, Interface):
            self._valid_to_refs.setdefault(id(value), []).append(refdict[name])

    def del_all_spec(self):
        specs = self.specs.copy()
        while specs:
            self._manager.del_spec(specs.pop())

    def update_value(self, old_value, new_value=None, **kwargs):

        prev_id = id(old_value)
        refs = self._valid_to_refs.get(prev_id, None)
        spec = self._manager.get_spec_from_value(self._model.interface, old_value)

        if refs is None:
            raise ValueError("value not referenced")

        if new_value is None:
            new_value = old_value

        if spec is not None:
            self._manager.update_spec_value(spec, new_value, kwargs)
            new_value = spec.value

        newrefs = []
        while refs:
            ref = refs.pop()
            impl = ref.parent
            name = ref.name
            refmode = ref.refmode
            value = new_value
            self._impl_change_ref(impl, name, value, refmode)
            newrefs.append(impl.own_refs[name])

        self._valid_to_refs.pop(prev_id)
        self._valid_to_refs[id(new_value)] = newrefs

    @staticmethod
    def _impl_change_ref(impl, name, value, *refmode):
        # ModelImpl imported here to avoid a circular import with model.py
        from modelx.core.model import ModelImpl

        if isinstance(impl, ModelImpl):
            impl.model.change_ref(name, value)
        elif isinstance(impl, UserSpaceImpl):
            impl.model.spmgr.change_ref(impl, name, value, refmode)
        else:
            raise RuntimeError("must not happen")
