from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def bar():
    return 'Hello! World.'


# ---------------------------------------------------------------------------
# References

sibling = ("Interface", ("..", "Parent"), "auto")