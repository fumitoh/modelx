from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def result():
    params = itertools.product([100, 110], [0.2, 0.3])
    return [{'K': k, 'sigma': s, 'price': bs[k, s].call_opt()} for k, s in params]


# ---------------------------------------------------------------------------
# References

itertools = ("Module", "itertools")

bs = ("Interface", ("..", "BlackScholes"), "auto")