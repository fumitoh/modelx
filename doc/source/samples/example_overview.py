import modelx as mx

model, space = mx.new_model(), mx.new_space()

@mx.defcells
def fibo(n):
    if n == 0 or n == 1:
        return n
    else:
        return fibo(n - 1) + fibo(n - 2)

