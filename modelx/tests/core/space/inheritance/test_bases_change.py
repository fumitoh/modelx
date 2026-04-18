import pytest
import modelx as mx


@pytest.mark.parametrize("new_member", ["cells"])
def test_add_remove_bases_lv2ly2(new_member):
    """
    Pattern #1: 2 levels, 2 layers

    C:Item, Space

        A   B
            |
            C

    A.add_bases(B) # Automatic child addition

        A <-B
        |   |
        C*  C

    A.remove_bases(B) # Automatic child removal

        A   B
            |
            C
    """
    model = mx.new_model()
    A = model.new_space("A")
    B = model.new_space("B")
    C = getattr(B, "new_" + new_member)("C")

    for _ in range(2):
        A.add_bases(B)
        assert "C" in A
        A.remove_bases(B)
        assert "C" in B
        assert "C" not in A

    model._impl._check_sanity()
    model.close()


@pytest.mark.parametrize("new_member", ["cells"])
def test_new_del_basemember_lv2ly2(new_member):
    """
        A <-B

    A.add_bases(B) # Automatic child addition (repetetive)

        A <-B
        |   |
        C*  C

    B.del_[item, space](C) # Automatic child deletion

        A <-B
    """
    new_members = new_member + ("s" if new_member[-1] != "s" else "")
    model = mx.new_model()
    A = model.new_space("A")
    B = model.new_space("B")
    A.add_bases(B)

    for _ in range(2):
        C = getattr(B, "new_" + new_member)("C")
        assert "C" in B
        assert "C" in A
        del getattr(B, new_members)["C"]
        assert "C" not in B
        assert "C" not in A

    model._impl._check_sanity()
    model.close()

def test_base_parent_child():
    """
        C <-----+
          <-B   |
            |   A
            |   |
            +---D
    """
    model = mx.new_model()
    A = model.new_space("A")
    D = A.new_space("D")
    B = model.new_space("B")
    C = model.new_space("C")
    C.add_bases(B)
    C.add_bases(A)
    B.add_bases(D)
    assert C.bases == [B, D, A]

    model._impl._check_sanity()
    model.close()

def test_sub_parent_child():
    """
        A <-B <-C
        |       |
        D <-----+
    """
    model = mx.new_model()
    A = model.new_space("A")
    D = A.new_space("D")
    B = model.new_space("B")
    C = model.new_space("C")
    A.add_bases(B)
    B.add_bases(C)
    D.add_bases(C)
    assert D.bases == [C]

    model._impl._check_sanity()
    model.close()

def test_pararell_inheritance():
    """
        A <-B
        |   |
        C <-D
    """
    model = mx.new_model()
    A = model.new_space("A")
    B = model.new_space("B")
    C = A.new_space("C")
    D = B.new_space("D")
    A.add_bases(B)
    C.add_bases(D)
    assert "C" in A.spaces
    # assert "D" in A.spaces
    B.new_cells('E')
    assert "E" in A.cells
    D.new_cells('E')
    assert "E" in C.cells

    model._impl._check_sanity()
    model.close()

def test_circler_nonerror():
    """
            C
            |-+
        A <-D |
        |     |
        B --->E

    """
    model = mx.new_model()
    A = model.new_space("A")
    B = A.new_space("B")
    C = model.new_space("C")
    D = C.new_space("D")
    E = C.new_space("E")

    A.add_bases(D)
    E.add_bases(B)

    assert A.bases == [D]
    assert E.bases == [B]

    model._impl._check_sanity()
    model.close()

def test_add_bases_to_defined():
    """
       A     B
       |     |
       foo   foo

       A <---B
       |     |
       foo   foo
    """

    def foo_base():
        return "base"

    def foo_sub():
        return "sub"

    m = mx.new_model()

    A = m.new_space("A")
    A.new_cells(name="foo", formula=foo_sub)

    B = m.new_space("B")
    B.new_cells(name="foo", formula=foo_base)

    B.add_bases(A)
    assert B.foo() == "base"
    assert A.foo() == "sub"

    m._impl._check_sanity()
    m.close()


def test_update_base_cells():

    m = mx.new_model()
    base = m.new_space('Base')

    @mx.defcells(base)
    def foo():
        return 1

    sub = m.new_space(bases=base)
    assert sub.foo._is_derived()

    def foo2():
        return 2

    base.foo.formula = foo2

    assert sub.foo() == 2
    assert sub.foo._is_derived()

    m._impl._check_sanity()
    m.close()