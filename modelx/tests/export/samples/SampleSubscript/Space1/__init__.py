from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def foo(x, y, z):
    return bar[x] + baz[x, y] + qux[x, y, z]


def bar(x):
    return x


def baz(x, y):
    return x + y


def qux(x, y, z):
    return x + y + z


