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

"""Step C4: explicit trace-invalidation port.

The inheritance/composition layer must drop cached values when it removes
or rewires members. It used to do this by reaching directly into the
execution layer's ``TraceManager`` -- ``self.model.clear_obj(...)`` /
``self.model.clear_attr_referrers(...)`` -- so space.py / cells.py /
reference.py were coupled to the TraceManager's method names.

These functions invert that dependency: the inheritance/composition hooks
now depend on this execution-owned port, and the knowledge of *how* trace
invalidation maps onto TraceManager calls lives here, in the execution
package (mirroring how ``members.fill_space_namespace`` owns the namespace
rule). Dispatch is synchronous and the underlying calls and their timing
are byte-for-byte what the direct calls did -- only the direction of the
dependency changes. (An asynchronous publish/subscribe variant would move
*when* invalidation happens relative to member detachment, risking
silently stale dependency graphs, so it is intentionally not done here.)

``model`` is the TraceManager-bearing ModelImpl; these helpers take no
modelx imports, keeping the port a dependency-free leaf.
"""


def invalidate_object(model, obj):
    """Clear cached values/nodes of ``obj`` and their dependants.

    Replaces direct ``model.clear_obj(obj)`` calls in inheritance/
    composition hooks (on_del_cells, on_sort_cells, on_rename,
    CellsImpl.on_inherit).
    """
    model.clear_obj(obj)


def invalidate_attr_referrers(model, ref):
    """Clear values that depend on reference ``ref``.

    Replaces direct ``model.clear_attr_referrers(ref)`` calls in
    inheritance hooks (on_change_ref, on_del_ref, ReferenceImpl.on_inherit).
    """
    model.clear_attr_referrers(ref)
