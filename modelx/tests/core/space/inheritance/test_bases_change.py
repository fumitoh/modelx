import pytest
import modelx as mx


@pytest.mark.parametrize("new_member", ["cells", "space"])
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


@pytest.mark.parametrize("new_member", ["cells", "space"])
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


@pytest.mark.parametrize("new_descents", [True, False])
def test_add_remove_bases_lv4ly2(new_descents):
    """
    A <--B
    |    |
    C(*) C
    |    |
    D(*) D
    |    |
    E*   E
    """
    model = mx.new_model()
    B = model.new_space("B")
    E = B.new_space("C").new_space("D").new_space("E")
    A = model.new_space("A")
    if new_descents:
        D = A.new_space("C").new_space("D")
    A.add_bases(B)
    assert "E" in A.spaces["C"].spaces["D"].spaces
    A.remove_bases(B)
    if new_descents:
        assert "E" not in A.spaces["C"].spaces["D"].spaces
    else:
        assert "C" not in A.spaces


@pytest.mark.parametrize("new_descents", [True, False])
def test_new_del_basemember_lv4ly2(new_descents):
    """
    A <--B
    |    |
    C(*) C
    |    |
    D(*) D
    |    |
    E*   E
    """
    model = mx.new_model()
    B = model.new_space("B")
    E = B.new_space("C").new_space("D").new_space("E")
    A = model.new_space("A")
    if new_descents:
        D = A.new_space("C").new_space("D")
    A.add_bases(B)
    assert "E" in A.spaces["C"].spaces["D"].spaces

    del B.spaces["C"].spaces["D"].spaces["E"]
    assert "E" not in A.spaces["C"].spaces["D"].spaces


@pytest.mark.parametrize("new_member", ["cells", "space"])
def test_add_remove_bases(new_member):
    """
        A   B   C
                |
                D
                |
                E

    B.add_bases(C) # Automatic child addition (repetetive)

        A   B <-C
            |   |
            D*  D
            |   |
            E*  E

    A.add_bases(B) # Automatic child addition (repetetive)

        A <-B <-C
        |   |   |
        D*  D*  D
        |   |   |
        E*  E*  E
    """
    new_members = new_member + ("s" if new_member[-1] != "s" else "")
    model = mx.new_model()
    A = model.new_space("A")
    B = model.new_space("B")
    C = model.new_space("C")

    getattr(C.new_space("D"), "new_" + new_member)("E")

    for _ in repr(2):

        B.add_bases(C)
        assert "D" in B.spaces
        assert "E" in getattr(B.spaces["D"], new_members)

        A.add_bases(B)
        assert "D" in A.spaces
        assert "E" in getattr(A.spaces["D"], new_members)

        A.remove_bases(B)
        B.remove_bases(C)
        assert not "D" in A.spaces
        assert not "D" in B.spaces


@pytest.mark.parametrize("new_member", ["cells", "space"])
def test_new_del_basemember_lv3ly3(new_member):

    """
        A <-B <-C

        A <-B <-C
        |   |   |
        D*  D*  D        

    A.add_bases(B) # Automatic child addition (repetetive)

        A <-B <-C
        |   |   |
        D*  D*  D
        |   |   |
        E*  E*  E

    B.del_[item, space](C) # Automatic child deletion

        A <-B <-C
        |   |   |
        D*  D*  D

        A <-B <-C
    """
    new_members = new_member + ("s" if new_member[-1] != "s" else "")

    model = mx.new_model()
    A = model.new_space("A")
    B = model.new_space("B")
    C = model.new_space("C")
    A.add_bases(B)
    B.add_bases(C)

    for _ in range(2):
        D = C.new_space("D")
        assert "D" in B
        assert "D" in A
        E = getattr(D, "new_" + new_member)("E")
        assert "E" in getattr(B.spaces["D"], new_members)
        assert "E" in getattr(A.spaces["D"], new_members)

        del getattr(D, new_members)["E"]
        assert "E" not in getattr(B.spaces["D"], new_members)
        assert "E" not in getattr(A.spaces["D"], new_members)
        del C.spaces["D"]
        assert "D" not in B.spaces
        assert "D" not in A.spaces


@pytest.mark.parametrize("new_member", ["cells", "space"])
def test_new_del_basemember_lv32ly3(new_member):
    """
       G <-F   C <-A
       |   |   |   |
       D*  D <-B   B
       |   |   |   |
       E*  E*  E*  E
    """
    new_members = new_member + ("s" if new_member[-1] != "s" else "")

    model = mx.new_model()
    A = model.new_space("A")
    AB = A.new_space("B")
    C = model.new_space("C")
    CB = C.new_space("B")
    F = model.new_space("F")
    D = F.new_space("D")
    D.add_bases(CB)
    C.add_bases(A)
    G = model.new_space("G")
    G.add_bases(F)

    for _ in range(2):
        getattr(AB, "new_" + new_member)("E")
        assert "E" in getattr(CB, new_members)
        assert "E" in getattr(D, new_members)
        assert "E" in getattr(G.spaces["D"], new_members)
        del getattr(AB, new_members)["E"]
        assert "E" not in getattr(CB, new_members)
        assert "E" not in getattr(D, new_members)
        assert "E" not in getattr(G.spaces["D"], new_members)


def test_base_parent_child():
    """
        C <-----+
          <-B   |
             \  A
              \ |
                D
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
    assert "D" in A.spaces


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
