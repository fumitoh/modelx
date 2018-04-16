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

import sys
import re
import keyword
import importlib
import types
from inspect import getmro

class AutoNamer:

    def __init__(self, basename):

        self.__basename = basename
        self.__last_postfix = 0

    def get_next(self, existing_names, prefix=''):

        self.__last_postfix += 1
        result = prefix + self.__basename + str(self.__last_postfix)

        if result in existing_names:
            # Increment postfix until no name
            # exists with that postfix.
            return self.get_next(existing_names, prefix)
        else:
            return result

    def revert(self):
        self.__last_postfix -= (self.__last_postfix and 1)

    def reset(self):
        self.__last_postfix = 0


_system_defined_names = re.compile(r"^_.*")


def is_valid_name(word):

    if word is None:
        return False

    if word.isidentifier() and not keyword.iskeyword(word):
        check = _system_defined_names.match(word)
        if not check:   # _system_defined_names.match(word):
            return True

    return False


def get_state_attrs(obj):

    mro = list(reversed(getmro(type(obj))))
    mro.remove(object)
    attrs = {}
    for klass in mro:
        klass_attrs = {}
        for attr in klass.state_attrs:
            klass_attrs[attr] = getattr(obj, attr)

        attrs.update(klass_attrs)

    return attrs


def get_module(module_):

    if isinstance(module_, types.ModuleType):
        pass

    elif isinstance(module_, str):
        if module_ not in sys.modules:
            importlib.import_module(module_)

        module_ = sys.modules[module_]

    else:
        raise TypeError("%s is not a module or string." %
                        module_)

    return module_
