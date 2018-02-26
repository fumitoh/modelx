"""Sample script showing how dynamic reference feature works."""
from modelx import *

model = new_model()

def paramfunc(n):
    names = {'SpaceA': SpaceA[n]}
    return {'bases': _self,
            'refs': names}

space_a = model.new_space(name='SpaceA', paramfunc=lambda n: None)
space_b = model.new_space(name='SpaceB', paramfunc=paramfunc)
space_b.SpaceA = space_a

space_a[1].NameA = 10
space_a[2].NameA = 20

print(space_b[1].SpaceA.NameA,
      space_b[2].SpaceA.NameA)

# should print "10, 20"