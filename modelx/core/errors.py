# Copyright (c) 2017 Fumito Hamamura <fumito.ham@gmail.com>

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
"""
modelx errors & warnings
"""


class DeepReferenceError(RuntimeError):
    """
    Error raised when the chain of formula reference exceeds the limit
    specified by the user.
    """
    message_template = dedent("""
        Formula chain exceeded the {0} limit.
        Call stack traceback:
        {1}""")

    def __init__(self, max_depth, trace_msg):
        msg = self.message_template.format(max_depth, trace_msg)
        RuntimeError.__init__(self, msg)


class NoneReturnedError(ValueError):
    """
    Error raised when a cells return None while its can_have_none
    attribute is set to False.
    """
    message_template = dedent("""
        None returned from {0}.
        Call stack traceback:
        {1}""")

    def __init__(self, last_call, trace_msg):
        msg = self.message_template.format(last_call, trace_msg)
        ValueError.__init__(self, msg)