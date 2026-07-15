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