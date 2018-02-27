from textwrap import dedent

import pytest

from modelx import *



def test_cells_mutual():

    space = new_model().new_space()

    func1 = dedent("""\
    def single_value(x):
        return 5 * x
    """)

    func2 = dedent("""\
    def mult_single_value(x):
        return 2 * single_value(x)
    """)

    f1 = space.new_cells(formula=func1)
    f2 = space.new_cells(formula=func2)

    assert f2(5) == 50
