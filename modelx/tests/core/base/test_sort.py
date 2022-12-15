import pytest
import modelx as mx
from modelx.core.base import _sort_partial, _sort_all


def test_sort_all():
    d = {'a': 1, 'bb': 2, 'aa': 3, 'cc': 4, 'b': 5}
    _sort_all(d)
    assert d == {'a': 1, 'aa': 3, 'b': 5, 'bb': 2, 'cc': 4}
    assert list(d) == list({'a': 1, 'aa': 3, 'b': 5, 'bb': 2, 'cc': 4})


@pytest.mark.parametrize("sorted_keys, result", [
    [['aa', 'bb', 'cc'], {'a': 1, 'aa': 3, 'bb': 2, 'cc': 4, 'b': 5}],
    [['a', 'aa', 'bb'], {'a': 1, 'aa': 3, 'bb': 2, 'cc': 4, 'b': 5}],
    [['b', 'cc'], {'a': 1, 'bb': 2, 'aa': 3, 'b': 5, 'cc': 4}],
    [[], {'a': 1, 'bb': 2, 'aa': 3, 'cc': 4, 'b': 5}]
])
def test_sort_partial(sorted_keys, result):
    d = {'a': 1, 'bb': 2, 'aa': 3, 'cc': 4, 'b': 5}
    _sort_partial(d, sorted_keys)
    assert d == result
    assert list(d) == list(result)


def test_sort():
    """Test a new cells in base sapce is inserted in subspace
    before the cells defined in sub cells.
    """

    m = mx.new_model()

    s1 = m.new_space()
    s1.new_cells('bbb')
    s1.new_cells('aaa')
    s1.new_cells('ccc')

    s2 = m.new_space()
    s2.new_cells('fff')
    s2.new_cells('ddd')
    s2.new_cells('eee')

    s2.add_bases(s1)


    s1.sort_cells()
    assert list(s1.cells) == ['aaa', 'bbb', 'ccc']
    assert list(s2.cells) == ['aaa', 'bbb', 'ccc', 'fff', 'ddd', 'eee']

    s2.sort_cells()
    assert list(s2.cells) == ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']

    m._impl._check_sanity()
    m.close()