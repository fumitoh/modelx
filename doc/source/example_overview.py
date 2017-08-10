from modelx import *

model = create_model('MyModel')
space = model.create_space('MySpace')


@defcells
def fibo(n):

    if n == 0 or n == 1:
        return n
    else:
        return fibo(n - 1) + fibo(n - 2)