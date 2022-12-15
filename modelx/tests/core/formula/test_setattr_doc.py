from itertools import product
import inspect

import pytest
import modelx as mx
from modelx.core.formula import replace_docstring


def foo(x):
    """single line docstr"""
    return x


def bar(x,
        y):
    """multline doc header

    doc
    string
    """
    return x, y


def baz(x,
        y): """multline

    doc
    string
    """; return x


def qux(x): """single line"""; return x


def quux(x):
    return x


singledocstr = """single line doc"""


multdocstr = \
"""this line
    continues
    here
    """

multdocstr_unindented = \
"""this line
continues
here
"""


@pytest.mark.parametrize(
    "func, docstr",
    product([foo, bar, baz, qux, quux], [singledocstr, multdocstr]))
def test_replace_docstring(func, docstr):
    funcdef = replace_docstring(
        inspect.getsource(func),
        docstr
    )
    ns = {}
    exec(funcdef, ns)

    assert ns[func.__name__].__doc__ == docstr


@pytest.mark.parametrize(
    "func, docstrs",
    product([bar],
            zip([singledocstr, multdocstr_unindented],
                [singledocstr, multdocstr])))
def test_replace_docstring_indent(func, docstrs):

    docstr_unindented, docstr_indented = docstrs

    funcdef = replace_docstring(inspect.getsource(func),
                                docstr_unindented,
                                insert_indents=True)
    ns = {}
    exec(funcdef, ns)

    assert ns[func.__name__].__doc__ == docstr_indented


@pytest.fixture(scope="module")
def testspace():
    m = mx.new_model()
    s = m.new_space()
    mx.defcells(foo, bar, baz, qux, quux)
    yield s
    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize(
    "func, docstr",
    product(["foo", "bar", "baz", "qux", "quux"], [singledocstr, multdocstr]))
def test_set_doc(testspace, func, docstr):
    testspace.cells[func].doc = docstr
    assert testspace.cells[func].doc == docstr


@pytest.mark.parametrize(
    "func, docstrs",
    product(["bar"],
            zip([singledocstr, multdocstr_unindented],
                [singledocstr, multdocstr])))
def test_set_doc_indent(testspace, func, docstrs):

    docstr_unindented, docstr_indented = docstrs
    testspace.cells[func].set_doc(docstr_unindented, insert_indents=True)
    assert testspace.cells[func].doc == docstr_indented


