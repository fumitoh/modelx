_spaces = ['testmod', 'nestedpkg']

def pkgfibo(n):
    if n == 0 or n == 1:
        return n
    else:
        return pkgfibo(n - 1) + pkgfibo(n - 2)

