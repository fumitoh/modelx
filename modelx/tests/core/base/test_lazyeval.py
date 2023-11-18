import pytest
from modelx import *
from modelx.core.base import *


data1 = {"A": 1, "B": 2}
data2 = {"C": 3, "D": 4}

check = {"B": 2, "C": 3, "D": 4, "E": 5}
ledict2 = LazyEvalDict("ledict", data2, [])
ledict1 = LazyEvalDict("ledict", data1, [ledict2])


class LazyEvalDict2(LazyEvalDict):
    def __init__(self, source, data, observers):
        self.source = source
        self.org_data = data.copy()
        LazyEvalDict.__init__(self, data, observers)

    def _refresh(self):
        self.clear()
        self.update(self.org_data)
        self.update(self.source)


class SampleLazyEval:
    def __init__(self):
        self._lazy_eval_dict1 = LazyEvalDict("dict1", data1, [])
        self._lazy_eval_dict2 = LazyEvalDict2(self._lazy_eval_dict1, data2, [])
        self._lazy_eval_dict1.append_observer(self._lazy_eval_dict2)
        self._lazy_eval_chmap = LazyEvalChainMap("chmap", [self._lazy_eval_dict2], [])
        # self._lazy_eval_dict2.append_observer(self._lazy_eval_chmap)

    @property
    def lazy_eval_dict1(self):
        return self._lazy_eval_dict1.fresh

    @property
    def lazy_eval_dict2(self):
        return self._lazy_eval_dict2.fresh

    @property
    def lazy_eval_chmap(self):
        return self._lazy_eval_chmap.fresh


def test_lazy_eval_dict():
    sample = SampleLazyEval()
    assert sample.lazy_eval_dict2 == CustomChainMap(data1, data2)


def test_lazy_eval_dict_update():
    sample = SampleLazyEval()
    del sample.lazy_eval_dict1["A"]
    sample.lazy_eval_dict1["E"] = 5
    sample.lazy_eval_dict1.set_refresh()

    assert sample.lazy_eval_dict2 == check


def test_lazy_eval_chmap():
    sample = SampleLazyEval()
    assert sample.lazy_eval_chmap == CustomChainMap(data1, data2)


def test_lazy_eval_chmap_update():

    sample = SampleLazyEval()
    del sample.lazy_eval_dict1["A"]
    sample.lazy_eval_dict1["E"] = 5
    sample.lazy_eval_dict1.set_refresh()

    assert sample.lazy_eval_chmap == check
