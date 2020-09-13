import modelx as mx


def test_serialize_refmode(tmp_path):
    """
        m---A---RefDynCells --(abs)-->B[1, 2].foo
          |   +-RefSpace --(rel)-->B
          |   +-RefCells --(auto)-->B.foo
          |
          +-B[x, y]---foo
    """
    m = mx.new_model()
    A = mx.new_space('A')
    B = mx.new_space('B')
    B.parameters = ('x', 'y')

    @mx.defcells
    def foo(x):
        return x

    A.absref(RefDynCells=B[1, 2].foo)
    A.relref(RefSpace=B)
    A.RefCells = B.foo

    m.write(tmp_path / 'refpickle')
    m2 = mx.read_model(tmp_path / 'refpickle')

    assert m2.A.RefSpace is m2.B
    assert m2.A.RefDynCells is m2.B[1, 2].foo
    assert m2.A.RefCells is m2.B.foo

    assert m2.A._get_object('RefSpace', as_proxy=True).refmode == "relative"
    assert m2.A._get_object('RefDynCells', as_proxy=True).refmode == "absolute"
    assert m2.A._get_object('RefCells', as_proxy=True).refmode == "auto"
