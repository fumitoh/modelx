from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def Payments():
    params = itertools.product([20, 30], [0.03, 0.04])
    result = []
    for t, r in params:
        result.append(
            {'Term': t,
             'Rate': r,
             'Payment': fixed[t, r].Payment()}
            )
    return result


# ---------------------------------------------------------------------------
# References

fixed = ("Interface", ("..", "Fixed"), "auto")

itertools = ("Module", "itertools")