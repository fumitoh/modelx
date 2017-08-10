from modelx import *


def Dx(x):
    return lx[x] * disc ** x


def Cx(x):
    return dx[x] * disc ** (x + 1 / 2)


def Nx(x):
    if x == 110:
        Nx[x] = Dx[x]
    else:
        Nx[x] = Nx[x + 1] + Dx[x]


def Mx(x):
    if x == 110:
        Mx[x] = Dx[x]
    else:
        Mx[x] = Mx[x + 1] + Cx[x]


def int_rate():
    return 1.5 / 100


def disc():
    return 1 / (1 + int_rate)


def Abarx(x, n):
    return (Mx[x] - Mx[x + n]) / Dx[x]


def Ex(x, n):
    return Dx[x + n] / Dx[x]


def AnnDue(x, n):
    return (Nx[x] - Nx[x + n]) / Dx[x]


def netprem(x, n):
    return Abarx[x, n] / AnnDue[x, n]