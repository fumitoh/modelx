from modelx.core.api import *
# from modelx.core.cells import CellPointer

model = create_model()

space = model.create_space()

import pickle

# print(space.__dict__)


@defcells
def foo(x):
    if x == 0:
        return 123
    else:
        return foo(x - 1)


foo[1] == 123

g = model._impl.cellgraph
import networkx as nx

node = nx.nodes(g)[0]
# s = pickle.dumps(node)
# t = pickle.loads(s)

# import pickletools
# pickletools.dis(s)

# s = pickle.dumps(model._impl.cellgraph)
#
# s = pickle.dumps(space)
# t = pickle.loads(s)

# s = pickle.dumps(model)
# t = pickle.loads(s)

#
# @defcells
# def single_value(x):
#     return 5 * x
#
# @defcells
# def mult_single_value(x):
#     return 2 * single_value(x)

model.save('data/pickle_test')
loaded = open_model('data/pickle_test')
# print(loaded.spaces['Space1'].cells['foo'].formula)
# up_foo = loaded.spaces['Space1'].interface.foo
# print(up_foo[13])


# print(space.mult_single_value(5))


# @defcells
# def fibo(x):
#     if x == 0 or x == 1:
#         return x
#     else:
#         return fibo(x - 1) + fibo(x - 2)
#
# space.fibo[1] = 2
#
# print(fibo(4))


# import collections
#
# def recurdive_graph(g):
#
#     for key, value in g.items():
#         if isinstance(value, collections.Mapping):
#             recurdive_graph(value)
#         else:
#             print('Key(%s):' % type(key), key)
#             print('Value(%s):' % type(value), value)
#
#
# recurdive_graph(g.__dict__)