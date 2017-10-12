from modelx import *


m = new_model()
s = m.new_space()

@defcells
def single_value():
    return 2310

s.single_value()

s.single_value.to_series()

print(s.to_dataframe())