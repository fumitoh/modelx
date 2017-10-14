from modelx import *

model, life = new_model(), new_space('Life')

def l(x):
    if x == 50:
        return 100000
    else:
        return l(x - 1) - d(x - 1)

def d(x):
    return l(x) * q


def q():
    return 0.003

l, d, x = defcells(l, d, q)

term_life = model.new_space(name='TermLife', bases=life)

@defcells
def benefits(x):
    if x < x_issue + n:
        return d(x) / l(x_issue)
    if x <= x_issue + n:
        return 0

@defcells
def pv_benefits(x):
    if x < x_issue:
        return 0
    elif x <= x_issue + n:
        return benefits(x) + pv_benefits(x + 1) / (1 + disc_rate)
    else:
        return 0


term_life.x_issue = 50
term_life.n = 10
term_life.disc_rate = 0

endowment = model.new_space(name='Endowment', bases=term_life)

@defcells
def benefits(x):
    if x < x_issue + n:
        return d(x) / l(x_issue)
    elif x == x_issue + n:
        return l(x) / l(x_issue)
    else:
        return 0

term_life.benefits.can_return_none = False
print(term_life.pv_benefits(50))
print(endowment.pv_benefits(50))


