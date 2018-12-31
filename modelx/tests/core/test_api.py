import pytest
import modelx as mx

@pytest.fixture
def testmodel():

    model, space = mx.new_model(name='testmodel'), \
                   mx.new_space(name='testspace')

    @mx.defcells(space)
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    space.bar = 3

    @mx.defcells(space)
    def baz(y, z):
        return y + z

    return model


def test_get_object(testmodel):

    assert mx.get_object('testmodel') is testmodel
    assert mx.get_object('testmodel.testspace') is testmodel.testspace
    assert mx.get_object('testmodel.testspace.foo') is testmodel.testspace.foo
    assert mx.get_object('testmodel.testspace.bar') == 3

    objs = [testmodel, testmodel.testspace, testmodel.testspace.foo]

    for obj in objs:
        assert mx.get_object(obj.fullname) is obj

    attrs = ['spaces', 'cells', 'formula']

    for obj, attr in zip(objs, attrs):
        assert mx.get_object(obj.fullname + '.' + attr) is getattr(obj, attr)


@pytest.mark.parametrize('name, argstr, args', [
    ['testmodel.testspace.foo', '3', (3,)],
    ['testmodel.testspace.foo', '3,', (3,)],
    ['testmodel.testspace.baz', '3, 4', (3, 4)],
])
def test_get_node(testmodel, name, argstr, args):
    from modelx.core.api import _get_node
    assert _get_node(name, argstr).args == args
