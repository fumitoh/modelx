"""Base space"""

from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = [
    "Child"
]

# ---------------------------------------------------------------------------
# Cells

def foo(x):
    if x == 0:
        return 0
    return foo(x - 1) + m


bar = lambda x: x * m

# ---------------------------------------------------------------------------
# References

m = 3

self_space = ("Interface", (".",), "auto")

the_model = ("Interface", ("..",), "auto")

the_cells = ("Interface", (".", "foo"), "auto")

s = "abc"

lst = ("Pickle", 2400958695424)

dct = ("Pickle", 2400957345280)

tpl = ("Pickle", 2400957197248)