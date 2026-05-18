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

"""Step B enabler: the namespace source list.

``NamespaceServer.__init__`` already documents (but does not implement) a
design where the namespace is built from "subjects ... in reverse order of
name-resolution priority". This module realizes that: a ``NamespaceSource``
is an ordered, observable name->value provider, and ``NamespaceComposer``
folds a priority-ordered list of them into ``_ns_dict``.

This moves the content rule out of ``BaseSpaceImpl.on_update_ns`` (which
hardcodes "namespace = named_spaces u refs u cells" and the per-kind value
projection) and into a list the server iterates. Dynamic spaces, whose
``refs`` is a 5-layer ``CustomChainMap`` (parent args / own / sys / wrapped
base / global), express that as multiple sources in the list rather than a
special case in the server.
"""

from typing import Callable

from modelx.core.base import Observer, get_mixin_slots
from modelx.core.binding.namespace import BaseNamespace, NamespaceServer
from modelx.core.members.container import MemberContainer


class NamespaceSource:
    """A priority-ranked, observable name->namespace-value provider.

    ``project`` maps a member impl to its namespace value, replacing the
    per-kind branching in on_update_ns:
      cells  -> member.call
      ref    -> member.interface (or nested namespace for space-like refs)
      space  -> member._namespace
    """

    __slots__ = ("subject", "_members", "_project")

    def __init__(self, subject, members, project: Callable):
        self.subject = subject          # the Subject to observe (a container)
        self._members = members         # name->member mapping (dict / chainmap)
        self._project = project

    def contribute(self, ns_dict: dict) -> None:
        for name, member in self._members.items():
            ns_dict[name] = self._project(member)


def container_source(container: MemberContainer,
                     project: Callable) -> NamespaceSource:
    """Adapt a single MemberContainer as a namespace source."""
    return NamespaceSource(container, container, project)


def layered_sources(chainmap, project: Callable) -> list:
    """Explode a CustomChainMap into one source per layer, lowest priority
    first. This is how DynamicSpaceImpl's multi-layer ``refs`` enters the
    namespace without the server knowing about chainmaps."""
    # chainmap.maps is highest-priority-first; reverse for contribute order.
    return [NamespaceSource(m, m, project) for m in reversed(chainmap.maps)]


# -- per-kind projections (the value rule extracted from on_update_ns) ----

def project_space(member):
    return member._namespace


def project_cells(member):
    return member.call


def project_ref(member):
    # Byte-for-byte the isinstance ladder from BaseSpaceImpl.on_update_ns.
    if isinstance(member, BaseNamespace):
        return member
    elif isinstance(member, NamespaceServer):
        return member._namespace
    else:
        return member.interface


def space_namespace_sources(space) -> list:
    """Ordered (lowest priority first) source list for a space namespace.

    Reproduces exactly the three-phase assembly previously hardcoded in
    ``BaseSpaceImpl.on_update_ns``: named_spaces, then the (collapsed) refs
    chainmap, then cells -- cells override refs override spaces. The refs
    chainmap's own ``.items()`` already collapses its layers by priority
    (own > sys > base/global, and the dynamic-space arg layers), so passing
    it directly is identical to the old ``for k, v in self.refs.items()``.
    """
    return [
        container_source(space.named_spaces, project_space),
        NamespaceSource(space.refs, space.refs, project_ref),
        container_source(space.cells, project_cells),
    ]


def fill_space_namespace(space, ns_dict: dict) -> None:
    """Drop-in replacement body for ``BaseSpaceImpl.on_update_ns``.

    Step B keeps the existing invalidation path (the explicit
    ``on_notify`` calls drive ``_is_ns_updated = False``); only the content
    rule moves here. Sources are assembled per call -- the persistent
    composer/observer wiring belongs to step C, once container mutations
    notify through ``MemberContainer.set``/``remove``.
    """
    for source in space_namespace_sources(space):
        source.contribute(ns_dict)


class NamespaceComposer(Observer):
    """Observes its sources; rebuilds ns_dict in priority order.

    Reserved for step C: once container mutations notify, the space holds a
    persistent composer that observes its sources instead of reassembling
    the source list on every ``on_update_ns`` call.
    """

    __slots__ = ("_sources", "_server") + get_mixin_slots(Observer)

    def __init__(self, server, sources):
        self._server = server          # the NamespaceServer to invalidate
        self._sources = list(sources)  # lowest priority first
        Observer.__init__(self, [s.subject for s in self._sources])

    def on_notify(self, subject) -> None:
        # Any source changed -> let the server lazily recompute.
        self._server._is_ns_updated = False
        self._server.notify()

    def build_into(self, ns_dict: dict) -> None:
        for source in self._sources:
            source.contribute(ns_dict)

    def build(self) -> dict:
        ns_dict = {}
        self.build_into(ns_dict)
        return ns_dict
