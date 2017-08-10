from modelx.core.api import *

model = create_model()
A = model.create_space(name='A')


@defcells
def fibo(x):
    if x == 0 or x == 1:
        return x
    else:
        return fibo[x - 1] + fibo[x - 2]


B = model.create_space(name='B', bases=A)


print(A._impl._self_members.observers)


print(B.fibo(10))


@defcells(space=A)
def fibo(x):
    if x == 1 or x == 2:
        return x
    else:
        return fibo[x - 1] + fibo[x - 2]


print(B.fibo(10))


