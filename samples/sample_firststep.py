"""
==========
First step
==========
"""

from modelx import *

# Create a model and space to work on.
model, space = new_model(), new_space()

# Below is an example to show cells name ('bar') can be set different from its
# defining function name ('fibo').
@defcells(name='bar')
def fibo(x):
    if x == 0 or x == 1:
        return x
    else:
        return bar[x - 1] + bar[x - 2]  # Refer by cells not by function


# Should print 55
print(fibo(10))

# Cells is iterable.
for i in fibo:
    print(i)

# repr(fibo)
print(fibo)


# Below is an example how to specify the space to create a cells in.
@defcells(space=space)
def distance(x, y):
    return (x ** 2 + y ** 2) ** 0.5

# Should [print the square root of 2, 5]
print([space.distance(x, y) for x, y in zip([1, 3], [1, 4])])


# Constant cells
@defcells
def single_value():
    return 2310

# Scalar cells are coerced in arithmetic operations
# Should print 3333
print(single_value + 1023)

# Conversion to Pandas DataFrame and Series
print(fibo.series)
print(space.distance.series)
print(space.single_value.series)
print(space.frame)
