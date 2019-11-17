def nestedfibo(n):
    if n == 0 or n == 1:
        return n
    else:
        return nestedfibo(n - 1) + nestedfibo(n - 2)
