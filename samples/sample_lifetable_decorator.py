from modelx import *

new_model().new_space()

@defcells
def lx(x):
    if x == 0:
        return 100000
    else:
        return lx[x - 1] - dx[x - 1]


@defcells
def dx(x):
    return lx[x] * qx


@defcells
def qx():
    return 0.01


if __name__ == "__main__":
    print(cur_space().lx[10])



