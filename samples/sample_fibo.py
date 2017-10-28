from modelx.core.api import *
from modelx.core.cells import CellArgs

m = new_model()
s = m.new_space()


@defcells(name="bar")
def fibo(x):
    if x == 0 or x == 1:
        return x
    else:
        return bar[x - 1] + bar[x - 2]

cur_model()

print(fibo(10) == 55)

for i in fibo:
    print(i)


# @defcells
# def single_value(): return 5


@defcells(space=s)
def distance(x, y):
    return (x ** 2 + y ** 2) ** 0.5

# print(single_value())

# for i in single_value:
#     print(i)

model = cur_model()
graph = model.cellgraph



# print(ptr in graph)
for i in range(11):
    ptr = CellArgs(fibo._impl, i)
    print(ptr, graph.predecessors(ptr), graph.successors(ptr))

print(fibo)

import pandas as pd

[s.distance(x, y) for x, y in zip([1 ,2, 3], [4, 5.0, 6])]

# srs = pd.Series(s.distance._impl.data)

x = fibo.to_series()
y = s.distance.to_series()

print(x)
print(y)

print(s.to_frame())
