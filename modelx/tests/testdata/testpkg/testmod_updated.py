

# modfibo(10) == 144


def modfibo(n):
    if n == 0 or n == 1:
        return n + 1
    else:
        return modfibo(n - 1) + modfibo(n - 2)

# modbar(2) == 6

def modbar(n):
    return baz * n


baz = 3
