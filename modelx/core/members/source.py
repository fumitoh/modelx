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


class NamespaceComposer(Observer):
    """Observes its sources; rebuilds ns_dict in priority order.

    Intended to back ``NamespaceServer.on_update_ns`` so that file no longer
    knows the namespace is "spaces + refs + cells". Sources are supplied
    lowest-priority first; later sources override earlier names.
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

    def build(self) -> dict:
        """Replacement body for BaseSpaceImpl.on_update_ns()."""
        ns_dict = {}
        for source in self._sources:
            source.contribute(ns_dict)
        return ns_dict
