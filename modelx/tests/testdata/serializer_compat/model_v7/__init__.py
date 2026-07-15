# modelx: pseudo-python
# This file is part of a modelx model.
# It can be imported as a Python module, but functions defined herein
# are model formulas and may not be executable as standard Python.

"""Fixture model for serializer compatibility gates"""

from modelx.serialize.jsonvalues import *

_name = "SerializerCompat"

_allow_none = False

_spaces = [
    "Base",
    "Sub",
    "Params"
]

# ---------------------------------------------------------------------------
# References

gref = 12