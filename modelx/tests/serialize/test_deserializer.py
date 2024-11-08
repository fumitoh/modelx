import os
import pathlib
import asttokens
import pytest
import modelx as mx
import modelx.tests.testdata
from modelx.serialize import deserializer

datadir = pathlib.Path(os.path.dirname(mx.tests.testdata.__file__))


def get_statmetns_atok(path):
    txt = pathlib.Path(path).read_text(encoding='utf-8')
    atok = asttokens.ASTTokens(txt, parse=True)
    return list(atok.get_text(stmt) for stmt in atok.tree.body)


def test_compare_statements():
    path_ = datadir / 'dummy_init.py'
    for t, a in zip(deserializer.get_statements(path_), get_statmetns_atok(path_)):
        assert t == a
