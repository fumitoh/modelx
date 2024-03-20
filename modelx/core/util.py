# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

    def get_next(self, existing_names, prefix=""):

        self.__last_postfix += 1
        result = prefix + self.__basename + str(self.__last_postfix)

        if result in existing_names:
            # Increment postfix until no name
            # exists with that postfix.
            return self.get_next(existing_names, prefix)
        else:
            return result

    def revert(self):
        self.__last_postfix -= self.__last_postfix and 1

    def reset(self):
        self.__last_postfix = 0


_system_defined_names = re.compile(r"^_.*")


def is_valid_name(word):

    if not isinstance(word, str):
        return False

    if word.isidentifier() and not keyword.iskeyword(word):
        check = _system_defined_names.match(word)
        if not check:  # _system_defined_names.match(word):
            return True

    return False


def get_module(module):

    if isinstance(module, types.ModuleType):
        pass

    elif isinstance(module, str):
        if module not in sys.modules:
            importlib.import_module(module)

        module = sys.modules[module]

    else:
        raise TypeError("%s is not a module or string." % module)

    return module


def get_param_func(param_names):

    if param_names:
        sig = "=None, ".join(param_names) + "=None"
    else:
        sig = ""

    return "def _param_func(" + sig + "): pass"


class ReorderableDict(dict):

    def get_index(self, key):
        for i, k in enumerate(self.keys()):
            if key == k:
                return i
        raise ValueError("%s not found" % key)

    def get_key(self, index):
        for i, k in enumerate(self.keys()):
            if i == index:
                return k
        raise IndexError("index out of range")

    def move(self, index_from, index_to, length=1):

        total_len = len(self)

        if index_from < total_len:
            length = min(total_len - index_from, length)
        else:
            raise IndexError("index out of range")

        if total_len - length < index_to:
            raise IndexError("index out of range")

        if index_from == index_to:
            return
        elif index_from > index_to:
            self._move_to_last(index_to, index_from - index_to)
            self._move_to_last(index_to + length, total_len - index_from - length)
        elif index_from < index_to:
            self._move_to_last(index_from, length)
            self._move_to_last(index_to, total_len - length - index_to)

    def _move_to_last(self, index_from, length):
        for _ in range(length):
            key = self.get_key(index_from)
            self[key] = self.pop(key)


def abs_to_rel(target: str, namespace: str):
    """Convert absolute name relative to namespace

    number of dots: nslen - shared + 1
    number of names: tglen - shared

    >>> tg = "aaa.bbb.ddd"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '..ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa.bbb"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '..'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa.bbb.ddd"
    >>> ns = "aaa.bbb"
    >>> abs_to_rel(tg, ns)
    '.ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "eee.fff"
    >>> ns = "aaa"
    >>> abs_to_rel(tg, ns)
    '..eee.fff'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa"
    >>> ns = "aaa.bbb.ccc.ddd"
    >>> abs_to_rel(tg, ns)
    '....'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "ddd"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '....ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True
    """
    tg = target.split(".")
    ns = namespace.split(".")

    tglen = len(tg)
    nslen = len(ns)

    shared = 0
    while (
            shared < min(tglen, nslen)
            and tg[shared] == ns[shared]
    ):
        shared += 1

    dots = nslen - shared + 1
    names = tglen - shared

    return "." * dots + ".".join(tg[tglen - names:])


def abs_to_rel_tuple(target: tuple, namespace: tuple):
    """
    >>> tg = ("aaa", "bbb", "ddd")
    >>> ns = ("aaa", "bbb", "ccc")
    >>> abs_to_rel_tuple(tg, ns)
    ('..', 'ddd')
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True

    >>> tg = ("aaa", "bbb")
    >>> ns = ("aaa", "bbb", "ccc")
    >>> abs_to_rel_tuple(tg, ns)
    ('..',)
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True

    >>> tg = ("aaa", "bbb", "ddd")
    >>> ns = ("aaa", "bbb")
    >>> abs_to_rel_tuple(tg, ns)
    ('.', 'ddd')
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True

    >>> tg = ("eee", "fff")
    >>> ns = ("aaa",)
    >>> abs_to_rel_tuple(tg, ns)
    ('..', 'eee', 'fff')
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True

    >>> tg = ("aaa",)
    >>> ns = ("aaa", "bbb", "ccc", "ddd")
    >>> abs_to_rel_tuple(tg, ns)
    ('....',)
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True

    >>> tg = ("ddd",)
    >>> ns = ("aaa", "bbb", "ccc")
    >>> abs_to_rel_tuple(tg, ns)
    ('....', 'ddd')
    >>> tg == rel_to_abs_tuple(abs_to_rel_tuple(tg, ns), ns)
    True
    """
    tg = target
    ns = namespace

    tglen = len(tg)
    nslen = len(ns)

    shared = 0
    while (
            shared < min(tglen, nslen)
            and tg[shared] == ns[shared]
    ):
        shared += 1

    dots = nslen - shared + 1
    names = tglen - shared

    return ("." * dots,) + tg[tglen - names:]


def rel_to_abs(target: str, namespace: str):
    """Convert name relative to namespace to absolute"""

    # shared = nslen - dots + 1

    ns = namespace.split(".")
    nslen = len(ns)

    dots = 0
    while dots < len(target) and target[dots] == ".":
        dots += 1

    shared = nslen - dots + 1
    tg = target[dots:].split(".") if dots < len(target) else []  # Avoid [""]
    abs = ns[:shared] + tg

    return ".".join(abs)


def rel_to_abs_tuple(target: tuple, namespace: tuple):
    """Convert name relative to namespace to absolute"""

    # shared = nslen - dots + 1

    ns = namespace
    nslen = len(ns)

    dots = 0
    while dots < len(target) and target[dots] == ".":
        dots += 1

    if target[0] == "." * len(target[0]):
        dots = len(target[0])
    else:
        raise ValueError("invalid tuple")

    shared = nslen - dots + 1
    tg = target[1:]
    abs = ns[:shared] + tg

    return abs
