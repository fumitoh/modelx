def foo(n):
    """Return 1 for all n >= 0"""
    if n == 1:
        return n
    else:
        return foo(n - 1)


def bar(n):
    """Return 2 for all n >= 0"""
    if n == 2:
        return n
    else:
        return foo(n)
