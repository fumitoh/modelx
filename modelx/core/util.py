import re
import keyword
from inspect import getmro

class AutoNamer:

    def __init__(self, basename):

        self.__basename = basename
        self.__last_postfix = 0

    def get_next(self, existing_names):

        self.__last_postfix += 1
        result = self.__basename + str(self.__last_postfix)

        if result in existing_names:
            # Increment postfix until no name
            # exists with that postfix.
            return self.get_next(existing_names)
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
