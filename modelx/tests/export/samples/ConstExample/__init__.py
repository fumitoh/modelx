# modelx: pseudo-python
# This file is part of a modelx model.
# It can be imported as a Python module, but functions defined herein
# are model formulas and may not be executable as standard Python.

from modelx.serialize.jsonvalues import *

_name = "ConstExample"

_allow_none = False

_spaces = [
    "Consts",
    "Foo"
]

# ---------------------------------------------------------------------------
# References

ProductID = ("Interface", (".", "Consts", "ProductID"), "None")