def modfibo(n):
    if n == 0 or n == 1:
        return n
    else:
        return modfibo(n - 1) + modfibo(n - 2)
