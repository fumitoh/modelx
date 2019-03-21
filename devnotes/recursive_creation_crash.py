# Python crashes due to recursive creation of s[1]

import modelx as mx

m, s = mx.new_model(), mx.new_space()

def param(i):
    refs = {'s1': s[i]}
    return {'refs': refs}

s.s = s
s.formula = param

s[1]

