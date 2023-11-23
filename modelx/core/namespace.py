# Copyright (c) 2017-2023 Fumito Hamamura <fumito.ham@gmail.com>

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

from modelx.core.base import ImplChainMap, ChainObserver, get_mixin_slots


class NamespaceServer:

    __slots__ = ()
    __mixin_slots = ("_namespace",)

    def __init__(self, namespace: ImplChainMap):
        self._namespace = namespace

    @property
    def namespace(self):
        return self._namespace.fresh


class BaseNamespaceReferrer(ChainObserver):

    __slots__ = ()
    __mixin_slots = ()

    def __init__(self, namespace):
        ChainObserver.__init__(self)
        self.observe(namespace, notify=False)

    def notify(self):
        self.on_namespace_change()

    def on_namespace_change(self):
        raise NotImplementedError



