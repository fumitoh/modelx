from modelx import *

# ---------------------------------------------------------------------
# line:6-21

model, life = new_model(), new_space('Life')

def l(x):
    if x == x0:
        return 100000
    else:
        return l(x - 1) - d(x - 1)

def d(x):
    return l(x) * q

def q():
    return 0.003

l, d, q = defcells(l, d, q)
life.x0 = 50
# ---------------------------------------------------------------------
# line:25-41

term_life = model.new_space(name='TermLife', bases=life)

@defcells
def benefits(x):
    if x < x0 + n:
        return d(x) / l(x0)
    if x <= x0 + n:
        return 0

@defcells
def pv_benefits(x):
    if x < x0:
        return 0
    elif x <= x0 + n:
        return benefits(x) + pv_benefits(x + 1) / (1 + disc_rate)
    else:
        return 0

# ---------------------------------------------------------------------
# line:46-47
#term_life.x0 = 50
term_life.n = 10
term_life.disc_rate = 0

# ---------------------------------------------------------------------
# line:53-62


endowment = model.new_space(name='Endowment', bases=term_life)

@defcells
def benefits(x):
    if x < x0 + n:
        return d(x) / l(x0)
    elif x == x0 + n:
        return l(x) / l(x0)
    else:
        return 0

# ---------------------------------------------------------------------
# line:67

data = [[1, 50, 10], [2, 60, 15], [3, 70, 5]]

# ---------------------------------------------------------------------
# line:72-86

def params(policy_id):
    return {'name': 'Policy%s' % policy_id,
            'bases': _self}

policy = model.new_space(name='Policy', bases=term_life, formula=params)

policy.data = data

@defcells
def x0():
    return data[policy_id - 1][1]

@defcells
def n():
    return data[policy_id - 1][2]

# ---------------------------------------------------------------------
# line:xx-yy

# def params(policy_id):
#     return {'name': 'Policy%s' % policy_id,
#             'bases': [_self,
#                       Endowment if data[policy_id - 1][0] == 2
#                       else TermLife]}
#
# policy = model.new_space(name='ThePolicy', formula=params)
#
# policy.data = data
# policy.Endowment = endowment
# policy.TermLife = term_life
#
# @defcells
# def x0():
#     return data[policy_id - 1][1]
#
# @defcells
# def n():
#     return data[policy_id - 1][2]

