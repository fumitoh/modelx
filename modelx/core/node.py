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

from collections import Sequence

OBJ = 0
KEY = 1

# class HasFormula:
#
#     self.data
#     self.formula
#
#     @property
#     def is_scalar(self):
#         return len(self.parameters) == 0
#
#     @property
#     def parameters(self):
#         return self.signature.paramters
#
#     @property
#     def signature(self):
#         return self.formula.signature
#

def node_has_key(node):
    return len(node) > 1


def get_node(obj, args, kwargs):
    """Create a node from arguments and return it"""

    if args is None and kwargs is None:
        return (obj,)

    if kwargs is None:
        kwargs = {}
    return obj, _bind_args(obj, args, kwargs)


def node_get_args(node):
    """Return an ordered mapping from params to args"""
    obj = node[OBJ]
    key = node[KEY]
    boundargs = obj.formula.signature.bind(*key)
    boundargs.apply_defaults()
    return boundargs.arguments


def tuplize_key(obj, key, remove_extra=False):
    """Args"""

    paramlen = len(obj.formula.parameters)

    if isinstance(key, str):
        key = (key,)
    elif not isinstance(key, Sequence):
        key = (key,)

    if not remove_extra:
        return key
    else:
        arglen = len(key)
        if arglen:
            return key[:min(arglen, paramlen)]
        else:
            return key


def _bind_args(obj, args, kwargs):
    boundargs = obj.formula.signature.bind(*args, **kwargs)
    boundargs.apply_defaults()
    return tuple(boundargs.arguments.values())


def get_node_repr(node):

    obj = node[OBJ]
    key = node[KEY]

    name = obj.get_repr(fullname=True, add_params=False)
    params = obj.formula.parameters

    arglist = ', '.join('%s=%s' % (param, arg) for param, arg
                        in zip(params, key))

    if key in obj.data:
        return name + '(' + arglist + ')' + '=' + str(obj.data[key])
    else:
        return name + '(' + arglist + ')'
