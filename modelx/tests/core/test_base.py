import pytest
from modelx import *
from modelx.core.base import *


data1 = {'A': 1, 'B': 2}
data2 = {'C': 3, 'D': 4}

check = {'B': 2, 'C': 3, 'D': 4, 'E': 5}
ledict2 = LazyEvalDict(data2, [])
ledict1 = LazyEvalDict(data1, [ledict2])


class LazyEvalDict2(LazyEvalDict):

    def __init__(self, source, data, observers):
        self.source = source
        self.org_data = data.copy()
        LazyEvalDict.__init__(self, data, observers)

    def _update_data(self):
        self.data.clear()
        self.data.update(self.org_data)
        self.data.update(self.source)


class SampleLazyEval:
    def __init__(self):
        self._lazy_eval_dict1 = LazyEvalDict(data1, [])
        self._lazy_eval_dict2 = LazyEvalDict2(self._lazy_eval_dict1, data2, [])
        self._lazy_eval_dict1.append_observer(self._lazy_eval_dict2)
        self._lazy_eval_chmap = LazyEvalChainMap([self._lazy_eval_dict2], [])
        # self._lazy_eval_dict2.append_observer(self._lazy_eval_chmap)

    @property
    def lazy_eval_dict1(self):
        return self._lazy_eval_dict1.get_updated()

    @property
    def lazy_eval_dict2(self):
        return self._lazy_eval_dict2.get_updated()

    @property
    def lazy_eval_chmap(self):
        return self._lazy_eval_chmap.get_updated()


def test_lazy_eval_dict():
    sample = SampleLazyEval()
    assert sample.lazy_eval_dict2 == ChainMap(data1, data2)


def test_lazy_eval_dict_update():
    sample = SampleLazyEval()
    del sample.lazy_eval_dict1['A']
    sample.lazy_eval_dict1['E'] = 5
    sample.lazy_eval_dict1.set_update()

    assert sample.lazy_eval_dict2 == check


def test_lazy_eval_chmap():
    sample = SampleLazyEval()
    assert sample.lazy_eval_chmap == ChainMap(data1, data2)


def test_lazy_eval_chmap_update():

    sample = SampleLazyEval()
    del sample.lazy_eval_dict1['A']
    sample.lazy_eval_dict1['E'] = 5
    sample.lazy_eval_dict1.set_update()

    assert sample.lazy_eval_chmap == check


# --------------------------------------------------------------------------
# Test Interface.__repr__

@pytest.fixture
def repr_test():

    model, space = new_model('ReprModel'), new_space('ReprSpace')

    @defcells
    def Foo(x, y):
        return x * y

    child = space.new_space('ReprChild')

    @defcells
    def Bar(x, y):
        return x * y

    def params(m, n):
        return {'bases': _self}

    model.new_space('DynSpace', bases=space, formula=params)

    return model

def test_repr_model(repr_test):
    assert repr(repr_test) == "<Model ReprModel>"

def test_repr_space(repr_test):
    assert repr(repr_test.ReprSpace) == "<Space ReprSpace in ReprModel>"

def test_repr_suspace(repr_test):
    assert repr(repr_test.ReprSpace.ReprChild) \
        == "<Space ReprChild in ReprModel.ReprSpace>"

def test_repr_cells(repr_test):
    cells = repr_test.ReprSpace.Foo
    assert repr(cells) == "<Cells Foo(x, y) in ReprModel.ReprSpace>"

def test_repr_cells_in_child(repr_test):
    cells = repr_test.ReprSpace.ReprChild.Bar
    repr_ = "<Cells Bar(x, y) in ReprModel.ReprSpace.ReprChild>"
    assert repr(cells) == repr_

def test_repr_dynspace(repr_test):
    space = repr_test.DynSpace(1, 2)
    assert repr(space) == "<Space DynSpace[1, 2] in ReprModel>"

def test_repr_cells_in_dynspace(repr_test):
    cells = repr_test.DynSpace(1, 2).Foo
    assert repr(cells) == "<Cells Foo(x, y) in ReprModel.DynSpace[1, 2]>"