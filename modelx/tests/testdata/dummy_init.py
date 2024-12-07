"""Sample docstring

"""

import numpy
import pytest


# ---------------------------------------------------------------------------
# Cells


def dyn_lapse_params():
    """Dynamic lapse parameters"""

    # Comment in a block

    return pd.read_excel(
        asmp_file(),
        sheet_name="DynLapse",
        index_col=0)   # Comment on return

    # Indented comment


def claim_pp(t):
# if t == 0:
#     return sum_assured()
    return sum_assured()

def foo():
    return \
        1

_allow_none = False

def bar():
    return 1

# ---------------------------------------------------------------------------
# References

np = (numpy, 'np')