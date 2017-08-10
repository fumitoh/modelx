from modelx.core.api import *

m = create_model()
s = m.create_space()

fibo = lambda x: x if x == 0 or x == 1 else fibo[x - 1] + fibo[x - 2]

fibo = defcells(space=s, name='fibo')(fibo)

print(fibo(10))

fibo2 = """lambda x: x if x == 0 or x == 1 else fibo2[x - 1] + fibo2[x - 2]"""

# fibo2 = \
# """\
# def fibo2(x):
#     if x == 0 or x == 1:
#         return x
#     else:
#         return fibo2(x - 1) + fibo2(x - 2)"""

fibo2 = s.create_cells(name='fibo2', func=fibo2)

print(fibo2(10))