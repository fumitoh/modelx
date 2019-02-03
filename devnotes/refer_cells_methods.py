# Sample script of dependency tracking not working when a cells method is
# referenced.

import modelx as mx
from modelx import defcells

m, s = mx.new_model(), mx.new_space()


@defcells
def triple(x):
    return 3 * x


@defcells
def refertriple(x):
    return x in list(triple.keys())


[triple(x) for x in range(10)]

assert refertriple(3)

triple.clear()

assert not refertriple(3)
