import modelx as mx
from modelx.core.errors import FormulaError
import pytest


def test_rename():
    """

    Before:

        Space1---Space2--Space3--Cells1
               |
               +-Cells2

        Space4<--Space2

    After:

         Foo---Bar--Baz--Cells1
               |
               +-Cells2

        Qux<--Bar

    """
    m = mx.new_model()
    s1 = m.new_space('Space1')
    s2 = s1.new_space('Space2')
    s3 = s2.new_space('Space3')
    c1 = s3.new_cells('Cells1', formula=lambda:1)
    c2 = s1.new_cells('Cells2', formula=lambda:Space2.Space3.Cells1())
    s4 = m.new_space('Space4', bases=s2)

    assert c2() == 1  # Calculate c1 and c2

    s1.rename('Foo')
    s3.rename('Baz')

    assert s1.name == 'Foo'
    assert s3.name == 'Baz'

    with pytest.raises(FormulaError):
        c2()

    c2.formula = lambda:Space2.Baz.Cells1()
    assert c2() == 1
    assert s4.Baz.Cells1() == 1

    s2.rename('Bar')
    s4.rename('Qux')

    assert s2.name == 'Bar'
    assert s4.name == 'Qux'

    with pytest.raises(FormulaError):
        c2()

    c2.formula = lambda:Bar.Baz.Cells1()
    assert c2() == 1

    m._impl._check_sanity()