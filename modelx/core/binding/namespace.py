# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

import logging
from modelx.core.base import Observer, Subject

logger = logging.getLogger(__name__)


class BaseNamespace:

    __slots__ = ('_impl',)

    _impl: 'NamespaceServer'

    def __init__(self, impl: 'NamespaceServer'):
        self._impl = impl


class NamespaceServer(Subject):

    __slots__ = ()
    __mixin_slots = (
        "_namespace",
        "_ns_dict",
        "_is_ns_updated"
    )
    _ns_class = BaseNamespace
    _namespace: BaseNamespace
    _ns_dict: dict
    _is_ns_updated: bool

    def __init__(self):
        """
        Initialize NamespaceServer.
        subjects: a sequence of name-object mappings (e.g., ImplChainMap, NamespaceServer, dict, etc.)
        subjects must be in a reverse order of name resolution priority.
        The last subject has the highest priority in name resolution.
        """
        Subject.__init__(self)
        self._namespace = self._ns_class(self)
        self._is_ns_updated = False

    def on_notify(self, subject: Subject) -> None:
        self._is_ns_updated = False
        self.notify()   # notify observers

    @property
    def namespace(self):
        if self._is_ns_updated:
            return self._namespace
        else:
            return self._update_ns()
    
    @property
    def ns_dict(self):
        if self._is_ns_updated:
            return self._ns_dict
        else:
            self._update_ns()
            return self._ns_dict

    def _update_ns(self) -> BaseNamespace:  # TODO: Refactor.
        self._ns_dict = {}
        self.on_update_ns()
        self._is_ns_updated = True
        return self._namespace

    def on_update_ns(self):
        """Called when namespace is updated."""
        raise NotImplementedError


class BaseNamespaceReferrer(Observer):

    __slots__ = ()
    __mixin_slots = ('ns_server',)
    
    ns_server: NamespaceServer

    def __init__(self, server: NamespaceServer):
        Observer.__init__(self, (server,))
        self.ns_server = server

    def on_notify(self, namspace: NamespaceServer):
        raise NotImplementedError

    def call(self, *args, **kwargs):    # Used in server._uspdate_ns() to indicate cells
        raise NotImplementedError



