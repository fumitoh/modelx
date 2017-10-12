from modelx import *


space = new_model().new_space(
    paramfunc=lambda int_rate: {'bases': get_self()})


@defcells
def discfac():
    return 1 / (1 + int_rate) ** term


@defcells
def mv():
    return face_amount * discfac

space.term = 10
# space.int_rate = 0.014 / 100
space.face_amount = 100

# subspace = space[0.014]
# print(space[0.014].mv())

int_rate_range = [i / 10000 for i in range(-200, 200, 10)]

import time

start_time = time.time()

mvs = [space[int_rate].mv() for int_rate in int_rate_range]

duration = time.time() -start_time

print(duration)

print(mvs)