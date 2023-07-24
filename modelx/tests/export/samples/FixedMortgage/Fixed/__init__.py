from modelx.serialize.jsonvalues import *

_formula = lambda Term, Rate: None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def Payment():
    return Principal * Rate * (1+Rate)**Term / ((1+Rate)**Term - 1)


def Balance(t):

    if t > 0:
        return Balance(t-1) * (1+Rate) - Payment()
    else:
        return Principal


# ---------------------------------------------------------------------------
# References

Principal = 100000

Term = 30

Rate = 0.03