from modelx.serialize.jsonvalues import *

_formula = lambda K, sigma: None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def call_opt():
    d1 = (math.log(S0 / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S0 * stats.norm.cdf(d1) - K * math.exp(-r * T) * stats.norm.cdf(d2)


# ---------------------------------------------------------------------------
# References

math = ("Module", "math")

stats = ("Module", "scipy.stats")

S0 = 100

T = 3

K = 110

r = 0.05

sigma = 0.2