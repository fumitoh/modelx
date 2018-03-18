
def foo(n):
    """Return 0 for all n >= 0"""
    if n == 0:
        return n
    else:
        return foo(n - 1)


def baz(n):
    """Return True"""
    return True