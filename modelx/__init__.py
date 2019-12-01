# Copyright (c) 2017-2019 Fumito Hamamura <fumito.ham@gmail.com>

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

"""Attributes defined in the top level module.

Attributes:
    models (dict): Alias for :func:`get_models`.
        Available for Python 3.7 or newer

"""

VERSION = (0, 1, 1, "dev")
__version__ = ".".join([str(x) for x in VERSION])
from modelx.core.api import *  # must come after __version__ assignment.
try:
    from modelx.core.api import __getattr__, __dir__
except ImportError:
    pass
from modelx.qtgui.api import *
