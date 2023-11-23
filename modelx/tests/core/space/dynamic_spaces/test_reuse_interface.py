import modelx as mx

def test_reuse_interface():
    m = mx.new_model()
    A = m.new_space('A', formula=lambda i: None)
    B = A.new_space('B', formula=lambda j: None)
    C = B.new_space('C')

    @mx.defcells(A)
    def foo():
        return i

    A1 = A[1]
    A1B2 = A1.B[2]
    A1B2C = A[1].B[2].C

    A.clear_all()

    assert A1 is A[1]
    assert A1B2 is A[1].B[2]
    assert A1B2C is A[1].B[2].C

    m._impl._check_sanity()
    m.close()