import itertools

import modelx as mx
import pytest


def parent_param(x):

    if x == 0:
        base = Base1
    else:
        base = Base2

    return {"base": base}


def child_param(y):
    return {"base": ChildBase}


def cells1(i):
    return 100 * i


def cells2(i):
    return 200 * i


def cells3(i):
    return 300 * x * y * i


def cells4(i):
    return 400 * x * y * i


@pytest.fixture
def build_sample_dynamic_model():
    """2 level multi-base dynamic space model

    Base1       Base2                Parent[x]
      |           |------+            |--------+
      |           |      |            |        |
    cells1      cells2  Child[y]     Base1    Base2
                         |
                         |------------+-------------+
                         |            |             |
                        ChildBase1   ChildBase2    ChildBase
                         |            |
                        cells3       cells4
    """

    model = mx.new_model(name="sample_dynamic_model")

    base1 = model.new_space(name="Base1")
    base2 = model.new_space(name="Base2")

    base1.new_cells(formula=cells1)
    base2.new_cells(formula=cells2)

    parent = model.new_space(name="Parent", formula=parent_param)
    child = base2.new_space(name="Child", formula=child_param)

    child.new_space(name="ChildBase1").new_cells(formula=cells3)
    child.new_space(name="ChildBase2").new_cells(formula=cells4)
    child.new_space(name="ChildBase",
                    bases=[child.ChildBase1, child.ChildBase2])

    parent.Base1 = base1
    parent.Base2 = base2

    return model


@pytest.fixture(params=[False, True])
def sample_dynamic_model(request, build_sample_dynamic_model, tmpdir_factory):

    model = build_sample_dynamic_model
    if request.param:
        file = str(tmpdir_factory.mktemp("data").join(model.name + ".mx"))
        model.write(file)
        model.close()
        model = mx.read_model(file)

    yield model
    model._impl._check_sanity()
    model.close()


def test_shared_dynamic_bases(sample_dynamic_model):
    """Test if dynamic spaces have the same shared bases.

    Dynamic spaces: Parent[x].Child[y] where x > 0
    Shared bases: [__Space1, ChildBase1, ChildBase2]
    """

    parent = sample_dynamic_model.Parent
    p1 = parent[1]
    ci = p1.Child._impl
    c0 = p1.Child[0]
    shared_bases = c0.bases

    for i, j in itertools.product(range(1, 4), range(3)):
        assert parent[i].Child[j].bases == shared_bases


def test_dynamic_index(sample_dynamic_model):

    parent = sample_dynamic_model.Parent
    for x, y, i in itertools.product(range(1, 4), range(3), (1, 2)):
        assert parent[x].Child[y].cells3(i) == 300 * x * y * i
        assert parent[x].Child[y].cells4(i) == 400 * x * y * i
