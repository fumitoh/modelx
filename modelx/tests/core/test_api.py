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
