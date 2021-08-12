# Copyright (c) 2017-2021 Fumito Hamamura <fumito.ham@gmail.com>

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

from modelx.core.base import ImplChainMap


class NamespaceServer:

    __cls_stateattrs = [
     "_namespace",
     "observing",
     "is_fresh",
     "_referrers"
    ]

    def __init__(self, namespace: ImplChainMap):
        self._namespace = namespace
        self.is_fresh = True   # dummy
        self.observing = []         # dummy
        self._referrers = []
        self._namespace.append_observer(self)

    def set_refresh(self):
        self.notify_referrers(is_all=True)

    def add_referrer(self, referrer: "BaseNamespaceReferrer"):
        if all(referrer is not other for other in self._referrers):
            self._referrers.append(referrer)

    def remove_referrer(self, referrer: "BaseNamespaceReferrer"):
        self._referrers.remove(referrer)

    def notify_referrers(self, is_all=True, names=None):
        for referrer in self._referrers:
            referrer.on_namespace_change(is_all, names)

    def on_add_item(self, sender, name, value):
        self.notify_referrers(is_all=False, names=[name])

    def on_delete_item(self, sender, name):
        self.notify_referrers(is_all=False, names=[name])

    def on_update(self, method, args):
        if method == "rename":
            # _namespace must be updated directly
            self.notify_referrers(is_all=False, names=args)
        else:
            raise ValueError("invalid method")

    @property
    def namespace(self):
        return self._namespace.fresh


class BaseNamespaceReferrer:
    
    def __init__(self, server: NamespaceServer):
        server.add_referrer(self)

    def on_namespace_change(self, is_all, names):
        raise NotImplementedError



