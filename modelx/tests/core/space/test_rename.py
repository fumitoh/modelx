import modelx as mx
from modelx.core.errors import FormulaError
import pytest


def test_rename():
    """

    Before:

        A---B--C--Cells1
               |
               +-Cells2

        D<--B

    After:

         Foo---Bar--Baz--Cells1
               |
               +-Cells2

        Qux<--Bar

    """
    m = mx.new_model()
    s1 = m.new_space('A')
    s2 = s1.new_space('B')
    s3 = s2.new_space('C')
    c1 = s3.new_cells('Cells1', formula=lambda: 1)
    c2 = s1.new_cells('Cells2', formula=lambda: B.C.Cells1())
    s4 = m.new_space('D', bases=s2)

    assert c2() == 1  # Calculate c1 and c2

    s1.rename('Foo')
    s3.rename('Baz')

    assert s1.name == 'Foo'
    assert s3.name == 'Baz'

    with pytest.raises(FormulaError):
        c2()

    c2.formula = lambda:B.Baz.Cells1()
    assert c2() == 1
    # assert s4.Baz.Cells1() == 1

    s2.rename('Bar')
    s4.rename('Qux')

    assert s2.name == 'Bar'
    assert s4.name == 'Qux'

    with pytest.raises(FormulaError):
        c2()

    c2.formula = lambda:Bar.Baz.Cells1()
    assert c2() == 1

    m._impl._check_sanity()