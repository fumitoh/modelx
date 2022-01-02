# Copyright (c) 2017-2022 Fumito Hamamura <fumito.ham@gmail.com>

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

from textwrap import dedent
from modelx.core.node import get_node_repr

"""
modelx errors & warnings
"""


class FormulaError(Exception):
    """Formula execution error

    By default, FormulaError is raised when any error is raised during
    formula execution. The original errors are obtained by calling
    :func:`modelx.get_error` function. This behaviour can be altered
    by passing ``False`` to :func:`modelx.use_formula_error` function,
    in which case the original errors are raised.
    """


class DeepReferenceError(Exception):
    """
    Error raised when the chain of formula reference exceeds the limit
    specified by the user.
    """


class NoneReturnedError(Exception):
    """
    Error raised when a cells return None while its allow_none
    attribute is set to False.
    """


class DeletedObjectError(Exception):
    """Error raised when a deleted object is accessed."""
