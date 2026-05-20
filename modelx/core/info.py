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
"""Informational reprs for Interface objects.

This module defines lightweight wrappers returned by the
:attr:`~modelx.core.base.Interface.info` property. The wrappers carry no
new state of their own; they format a human-readable snapshot of the
underlying Cells or Space when ``repr()`` is called on them.
"""

_INDENT = "    "
_MAX_ITEMS = 5


def _format_key(key):
    """Render a cells data key. Single-argument tuples are unwrapped."""
    if isinstance(key, tuple) and len(key) == 1:
        return repr(key[0])
    return repr(key)


def _format_kv_items(items, indent=_INDENT, max_items=_MAX_ITEMS):
    """Format key-value items as indented lines, truncating long lists."""
    items = list(items)
    lines = []
    if len(items) <= max_items:
        for key, value in items:
            lines.append(indent + _format_key(key) + ": " + repr(value))
    else:
        head = max_items - 1
        for key, value in items[:head]:
            lines.append(indent + _format_key(key) + ": " + repr(value))
        lines.append(indent + "...")
    return lines


def _format_keys_list(keys, max_items=_MAX_ITEMS):
    """Format ``keys`` as a single-line abbreviated list literal."""
    keys = list(keys)
    if len(keys) <= max_items:
        return "[" + ", ".join(repr(k) for k in keys) + "]"
    head = max_items - 1
    return "[" + ", ".join(repr(k) for k in keys[:head]) + ", ...]"


def _signature_str(formula):
    """Return ``formula``'s signature without the outer parentheses."""
    s = str(formula.signature)
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    return s


class _InterfaceInfo:
    """Base class for objects returned by ``Interface.info``."""

    __slots__ = ("_interface",)

    def __init__(self, interface):
        self._interface = interface

    def _class_name(self):
        return type(self._interface).__name__

    def _header(self):
        return self._interface._get_repr(fullname=True, add_params=True)

    def _body_lines(self):
        return []

    def __repr__(self):
        lines = ["%s: %s" % (self._class_name(), self._header())]
        lines.extend(self._body_lines())
        return "\n".join(lines)


class CellsInfo(_InterfaceInfo):
    """Informational repr for :class:`~modelx.core.cells.Cells`."""

    __slots__ = ()

    def _header(self):
        impl = self._interface._impl
        parent_repr = impl.repr_parent()
        sig = str(impl.formula.signature)
        if parent_repr:
            return parent_repr + "." + impl.name + sig
        return impl.name + sig

    def _body_lines(self):
        cells = self._interface
        impl = cells._impl
        lines = []
        lines.append("is_derived: " + repr(cells._is_derived()))
        lines.append("is_cached: " + repr(cells.is_cached))
        lines.append("allow_none: " + repr(cells.allow_none))

        source = impl.formula.source
        lines.append("formula:")
        if source:
            for line in source.rstrip("\n").splitlines():
                lines.append(_INDENT + line)
        else:
            lines.append(_INDENT + "(source not available)")

        data = impl.data
        input_keys = impl.input_keys
        cached_items = [(k, v) for k, v in data.items() if k not in input_keys]
        input_items = [(k, v) for k, v in data.items() if k in input_keys]

        lines.append("cached values: " + str(len(cached_items)))
        lines.extend(_format_kv_items(cached_items))

        if input_items:
            lines.append("input values: " + str(len(input_items)))
            lines.extend(_format_kv_items(input_items))

        return lines


class SpaceInfo(_InterfaceInfo):
    """Informational repr for spaces (UserSpace, ItemSpace, DynamicSpace)."""

    __slots__ = ()

    def _body_lines(self):
        space = self._interface
        lines = []

        base_names = [b.fullname for b in space.bases]
        lines.append("bases: [" + ", ".join(base_names) + "]")

        formula = getattr(space._impl, "formula", None)
        if formula is not None:
            lines.append("parameters: " + _signature_str(formula))

        itemspaces = dict(space.itemspaces)
        lines.append("itemspaces: " + str(len(itemspaces)))
        if itemspaces:
            lines.append(_INDENT + _format_keys_list(itemspaces.keys()))
        return lines


class ModelInfo(_InterfaceInfo):
    """Informational repr for :class:`~modelx.core.model.Model`."""

    __slots__ = ()

    def _header(self):
        return self._interface.name

    def _body_lines(self):
        spaces = dict(self._interface.spaces)
        lines = ["spaces: " + str(len(spaces))]
        if spaces:
            lines.append(_INDENT + _format_keys_list(spaces.keys()))
        return lines


def build_info(interface):
    """Return an info wrapper appropriate for ``interface``.

    Imports are deferred so this module does not need to be imported
    at package load time.
    """
    from modelx.core.cells import Cells
    from modelx.core.space import BaseSpace
    from modelx.core.model import Model

    if isinstance(interface, Cells):
        return CellsInfo(interface)
    if isinstance(interface, BaseSpace):
        return SpaceInfo(interface)
    if isinstance(interface, Model):
        return ModelInfo(interface)
    return _InterfaceInfo(interface)
