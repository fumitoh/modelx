from modelx import *

model, space = new_model(), new_space()

@defcells
def fibo(n):
    if n == 0 or n == 1:
        return n
    else:
        return fibo(n - 1) + fibo(n - 2)

