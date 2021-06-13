import modelx as mx
from modelx import new_model, defcells

import pytest


@pytest.fixture
def sample_space():

    space = new_model(name="samplemodel").new_space(name="samplespace")

    funcdef = """def func(x): return 2 * x"""

    space.new_cells(formula=funcdef)

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo[x - 2]

    @defcells
    def double(x):
        double[x] = 2 * x

    @defcells
    def return_last(x):
        return return_last(x - 1)

    def func1(x):
        return 5 * x

    def func2(y):
        return 6 * y

    func1, func2 = defcells(func1, func2)

    @defcells
    def no_param():
        return 5

    @defcells
    def matchtest(x, y, z):
        return None

    matchtest.allow_none = True

    matchtest[1, 2, 3] = 123
    matchtest[1, 2, None] = 120
    matchtest[1, None, 3] = 103
    matchtest[None, 2, 3] = 23
    matchtest[1, None, None] = 100
    matchtest[None, 2, None] = 20
    matchtest[None, None, 3] = 3
    matchtest[None, None, None] = 0

    return space


@pytest.fixture
def sample_for_rename_and_formula():
    """Test model for rename and set_formula

        model-----Parent---Child1---Foo # rename to Baz
               |         |
               |         +-Child2---Bar
               |
               +--Sub1 <- Parent
               |
               +--Sub2[a] <- {1:Child1, *:Child2}

    """
    model = mx.new_model()
    parent = model.new_space('Parent')
    child1 = parent.new_space('Child1')
    child2 = parent.new_space('Child2')
    foo = child1.new_cells('Foo', formula=lambda x: x)
    bar = child2.new_cells('Bar', formula=lambda x: x)
    sub1 = model.new_space('Sub1', bases=parent)

    def _param(a):
        b = Parent.Child1 if a == 1 else Parent.Child2
        return {'bases': b}

    sub2 = model.new_space('Sub2', formula=_param)
    sub2.Parent = parent
    foo(1)
    bar(1)
    sub2[1].Foo(1)
    sub2[2].Bar(1)
    model.Sub1.Child1.Foo(1)

    assert tuple(sub1.Child1.cells) == ("Foo",)
    assert len(sub1.Child1.Foo) == 1
    assert tuple(sub2.itemspaces) == (1, 2)

    return model