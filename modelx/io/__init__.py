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

"""Catalog of the IO spec classes shipped with modelx.

Saved models (serializer 8 and later) identify IO specs by bare class
name; the serializers resolve those names through this catalog, never
by import path, so the saved format is decoupled from the module
layout. Modules are imported lazily so optional dependencies (pandas,
openpyxl) are required only when a model actually uses them.

A spec class must be listed here to be writable: the version-8 writer
rejects specs whose type does not resolve through this catalog, keeping
the write and read sides symmetric.
"""

import importlib

SPEC_CLASSES = {
    "PandasData": "modelx.io.pandasio",
    "ExcelRange": "modelx.io.excelio",
    "ModuleData": "modelx.io.moduleio",
}


def get_spec_class(name):
    """Return the IO spec class registered under ``name``."""
    if name not in SPEC_CLASSES:
        raise ValueError("unknown IO spec type: %r" % name)
    return getattr(importlib.import_module(SPEC_CLASSES[name]), name)
