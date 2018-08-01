"""Sample script showing how dynamic reference feature works.


    SpaceB      SpaceA
      |           |
    SpaceB[n]   SpaceA[n]


"""
from modelx import *

model = new_model()

def formula(n):
    names = {'SpaceA': SpaceA[n]}
    return {'refs': names}

space_a = model.new_space(name='SpaceA', formula=lambda n: None)
space_b = model.new_space(name='SpaceB', formula=formula)
space_b.SpaceA = space_a

space_a[1].NameA = 10
space_a[2].NameA = 20

assert space_b[1].SpaceA is space_a[1]
assert space_b[2].SpaceA is space_a[2]

print(space_b[1].SpaceA.NameA,
      space_b[2].SpaceA.NameA)

# should print "10, 20"