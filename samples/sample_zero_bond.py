"""
================
Zero-coupon bond
================
Calculate present values of zero-coupon bonds of various interest rates.

This example demonstrate dynamic spaces.
"""
from modelx import *

space = new_model().new_space(
    paramfunc=lambda int_rate: {'bases': _self})

@defcells
def discfac():
    return 1 / (1 + int_rate) ** term

@defcells
def mv():
    return face_amount * discfac

space.term = 10
space.face_amount = 100

int_rate_range = [i / 10000 for i in range(-200, 200, 10)]
mvs = [space[int_rate].mv() for int_rate in int_rate_range]
print(mvs)

