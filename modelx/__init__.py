# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

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

import warnings

VERSION = (0, 0, 8, 'dev')
__version__ = '.'.join([str(x) for x in VERSION])
from modelx.core.api import *  # must come after __version__ assignment.

try:
    from modelx.qtgui import *
except ImportError:
    warnings.warn("QtPy package not found."
                  "GUI will not be available.", ImportWarning)

del warnings
