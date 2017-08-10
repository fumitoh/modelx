from modelx import *

create_model().create_space()

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
    print(get_currentspace().lx[10])



