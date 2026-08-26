import sys
import os
import pathlib
from inspect import getsource
from textwrap import dedent

import pandas as pd
import modelx as mx
import pytest
from modelx.export.exporter import Exporter


sample_dir = pathlib.Path(__file__).parent / 'samples'


def test_check_contents(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'Options')
    mx.export_model(m, nomx_path / 'Options')
    assert set(os.listdir(nomx_path / 'Options')) == {
        '__init__.py', '_mx_sys.py', '_mx_classes.py', '_mx_model.py'}
    m.close()


@pytest.fixture(scope='module')
def empty_model():
    m = mx.read_model(sample_dir / 'EmptyModel')
    yield m
    m.close()


@pytest.mark.parametrize("api", ['function', 'method'])
def test_api(empty_model, tmp_path, api):
    nomx_path = tmp_path / 'model'

    try:
        sys.path.insert(0, str(nomx_path))

        if api == 'function':
            mx.export_model(empty_model , nomx_path / 'nomx_model')
        elif api == 'method':
            empty_model.export(nomx_path / 'nomx_model')
        else:
            raise RuntimeError

        from nomx_model import mx_model
        from nomx_model import EmptyModel
        assert mx_model is EmptyModel
    finally:
        sys.path.pop(0)


def test_nested_space_ref(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'NestedSpace')
    Exporter(m, nomx_path / 'NestedSpace').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from NestedSpace import mx_model
        assert mx_model.Pibling.sibling.Child.GrandChild.foo() == 'Hello!'
        assert mx_model.Parent.Child.GrandChild.grandpibling.bar() == 'Hello! World.'
    finally:
        sys.path.pop(0)


def test_pandasio(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'PandasData')
    Exporter(m, nomx_path / 'PandasData').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from PandasData import mx_model
        pd.testing.assert_frame_equal(mx_model.Foo.df, m.Foo.df)
    finally:
        sys.path.pop(0)
        m.close()


def test_pickle(tmp_path):

    m = mx.new_model('PickleSample')
    s = m.new_space('Space1')

    s.df = pd.DataFrame({
        'Name': ['John', 'Anna', 'Peter', 'Linda'],
        'Age': [28, 22, 35, 58],
        'City': ['New York', 'Los Angeles', 'Berlin', 'London']
    })

    nomx_path = tmp_path / 'model'
    Exporter(m, nomx_path / 'PickleSample').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from PickleSample import mx_model
        pd.testing.assert_frame_equal(mx_model.Space1.df, m.Space1.df)
    finally:
        sys.path.pop(0)
        m.close()


def test_subscript(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'SampleSubscript')
    Exporter(m, nomx_path / 'SampleSubscript').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from SampleSubscript import mx_model
        assert mx_model.Space1.foo(1, 2, 3) == 10
    finally:
        sys.path.pop(0)
        m.close()


@pytest.fixture(scope="module")
def mortgage_model(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "FixedMortgage")
    Exporter(m, nomx_path / 'FixedMortgage').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from FixedMortgage import mx_model
        yield m, mx_model
    finally:
        sys.path.pop(0)
        m._impl._check_sanity()
        m.close()


def test_literal_ref(mortgage_model):
    source, target = mortgage_model
    assert source.Fixed.Principal == target.Fixed.Principal == 100_000
    assert source.Fixed.Term == target.Fixed.Term == 30
    assert source.Fixed.Rate == target.Fixed.Rate == 0.03
    assert source.Fixed.SampleString == target.Fixed.SampleString


def test_module_ref(mortgage_model):
    source, target = mortgage_model
    assert source.Summary.itertools is sys.modules['itertools']


def test_itemspace(mortgage_model):
    source, target = mortgage_model
    assert source.Summary.Payments() == target.Summary.Payments()


@pytest.fixture(scope="session")
def sample_params(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "Params")
    m.export(nomx_path / 'Params_nomx')

    sys.path.insert(0, str(nomx_path))
    from Params_nomx import mx_model
    yield m, mx_model
    sys.path.pop(0)
    m.close()


def test_itemspace_params(sample_params):
    _, nomx = sample_params
    assert nomx.SingleParam(1).foo() == 1
    assert nomx.SingleParam[2].foo() == 2
    assert nomx.MultipleParams(3, 4).bar() == 7
    assert nomx.MultipleParams[5, 6].bar() == 11
    assert nomx.MultParamWithDefault(2).baz() == 4
    assert nomx.MultParamWithDefault[2].baz() == 4
    assert nomx.MultParamWithDefault(3, 4).baz() == 7
    assert nomx.MultParamWithDefault[3, 4].baz() == 7


def test_itemspace_delitem(sample_params):

    _, nomx = sample_params
    assert nomx.SingleParam(1).foo() == 1
    assert nomx.SingleParam[2].foo() == 2
    assert nomx.MultipleParams(3, 4).bar() == 7
    assert nomx.MultipleParams[5, 6].bar() == 11
    assert nomx.MultParamWithDefault(2).baz() == 4
    assert nomx.MultParamWithDefault[2].baz() == 4
    assert nomx.MultParamWithDefault(3, 4).baz() == 7
    assert nomx.MultParamWithDefault[3, 4].baz() == 7

    assert len(nomx.SingleParam._mx_itemspaces) == 2
    assert len(nomx.MultipleParams._mx_itemspaces) == 2
    assert len(nomx.MultParamWithDefault._mx_itemspaces) == 2

    del nomx.SingleParam[2]
    del nomx.MultipleParams[5, 6]
    del nomx.MultParamWithDefault[3, 4]

    assert len(nomx.SingleParam._mx_itemspaces) == 1
    assert len(nomx.MultipleParams._mx_itemspaces) == 1
    assert len(nomx.MultParamWithDefault._mx_itemspaces) == 1


def test_itemspace_nested_params(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "NestedParams")
    m.export(nomx_path / 'NestedParams_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from NestedParams_nomx import mx_model
        assert mx_model.Parent[1].x == 1
        assert mx_model.Parent[1].Child.x == 1
        assert mx_model.Parent[1].Child[2].x == 1
        assert mx_model.Parent[1].Child[2].y == 2
        assert mx_model.Parent[2].Child[3].x == 2
        assert mx_model.Parent[2].Child[3].y == 3
        assert mx_model.Parent[2].Child[3].SubChild.baz == 1

    finally:
        sys.path.pop(0)
        m.close()


def test_relative_refs(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "RelativeRefs")
    m.export(nomx_path / 'RelativeRefs_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from RelativeRefs_nomx import mx_model
        assert mx_model.Parent[1].Child2.c1 is mx_model.Parent[1].Child1
        assert mx_model.Parent[2].Child2.foo() == 2
        assert mx_model.Parent[3].Child2.c1abs is mx_model.Parent.Child1

    finally:
        sys.path.pop(0)
        m.close()


def test_relative_refs2(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "RelativeRefs2")
    m.export(nomx_path / 'RelativeRefs2_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from RelativeRefs2_nomx import mx_model
        assert mx_model.Parent.Child.foo_ref() == 0
        assert mx_model.Parent[1].Child.foo_ref() == 1
        assert mx_model.Parent.Child[2].foo_ref() == 0
        assert mx_model.Parent[1].Child[2].foo_ref() == 1
        assert mx_model.Parent[1].Child[2].foo_ref.__self__ is mx_model.Parent[1].foo.__self__

    finally:
        sys.path.pop(0)
        m.close()


def test_model_path(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "ModelPath")
    m.export(nomx_path / 'ModelPath_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from ModelPath_nomx import mx_model
        assert mx_model.Space1.foo() == nomx_path / 'ModelPath_nomx'

    finally:
        sys.path.pop(0)
        m.close()


def test_parent(tmp_path_factory):
    """Test if _parent is available both in the mx and nomx model

    Code modified from: https://github.com/fumitoh/modelx/discussions/129
    """

    m = mx.new_model()
    RA = m.new_space("RA")

    # Parameterize Space RA with `calc_loop`.
    # This means RA creates exact copies of itself parameterized by calc_loop on the fly,
    # such as RA[0], RA[1], RA[2], etc.
    # They are dynamic child spaces of RA.
    RA.parameters = ("calc_loop",)
    RA.calc_loop = 0    # In RA

    # Define BEL_LAPSE in RA. In the formula, calc_loop is the value given to the parameter of RA[calc_loop].
    # For example, calc_loop == 0 in RA[0].BEL_LAPSE(), calc_loop == 1 in RA[1].BEL_LAPSE(), and so on.
    # In the formula, `_space` is a special name that represents the parent space of the Cells.
    # For example, _space is RA[2] in RA[2].BEL_LAPSE(). _space.parent represents the parent space of RA[2], which is RA.
    # So, _space.parent[1].BEL_LAPSE() means RA[1].BEL_LAPSE()

    @mx.defcells(space=RA)
    def BEL_LAPSE():
        if calc_loop == 0:
            return 0
        elif calc_loop == 1:
            return 120
        else:
            return _space._parent[1].BEL_LAPSE()

    assert RA.BEL_LAPSE() == 0
    assert RA[0].BEL_LAPSE() == 0

    for i in range(1, 5):
        RA[i].BEL_LAPSE() == 120

    nomx_path = tmp_path_factory.mktemp('model')
    m.export(nomx_path / 'Parent_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from Parent_nomx import mx_model as nomx

        assert nomx.RA.BEL_LAPSE() == 0
        assert nomx.RA[0].BEL_LAPSE() == 0
        for i in range(1, 5):
            nomx.RA[i].BEL_LAPSE() == 120

    finally:
        sys.path.pop(0)
        m.close()


def test_space_properties(tmp_path_factory):
    """ Test _space._parent, _space._name, _cells

        m----Space1[i, j]------Space2
               +--get_parent    +--get_parent
               +--get_name
    """

    m = mx.new_model()
    s1 = m.new_space("Space1")
    s2 = s1.new_space("Space2")
    s1.parameters = ('i', 'j')

    @mx.defcells(space=s1)
    def get_parent():
        return _space._parent

    @mx.defcells(space=s2)
    def get_parent():
        return _space._parent

    @mx.defcells(space=s1)
    def get_name():
        return _space._name

    nomx_path = tmp_path_factory.mktemp('model')
    m.export(nomx_path / 'TestSpaceProperties_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from TestSpaceProperties_nomx import mx_model as nomx
        from TestSpaceProperties_nomx._mx_classes import _v_space_params_Space1

        assert nomx.Space1.get_parent() is nomx
        assert nomx.Space1.Space2.get_parent() is nomx.Space1
        assert nomx.Space1.get_name() == "Space1"
        assert _v_space_params_Space1 == ['i', 'j']

        for name in ['get_parent', 'get_name']:
            assert name == nomx.Space1._cells[name].__name__   # method

    finally:
        sys.path.pop(0)


def test_model_level_ref(tmp_path):
    """Model-level (global) references have refmode=None.

    Regression test: Exporter.ref_copies must accept refmode=None for refs
    owned by the Model when the space inherits them as global refs.
    """
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'ConstExample')
    try:
        m.export(nomx_path / 'ConstExample_nomx')

        sys.path.insert(0, str(nomx_path))
        from ConstExample_nomx import mx_model as nomx

        assert nomx.Foo.foo('TERM') == 1
        assert nomx.Foo.foo('WL') == 2
        assert nomx.Foo.foo('ENDW') == 3
        assert nomx.ProductID is nomx.Consts.ProductID
        assert nomx.Foo.ProductID is nomx.Consts.ProductID
    finally:
        sys.path.pop(0)
        m.close()


@pytest.fixture(scope="module")
def comprehension_scopes(tmp_path_factory):
    """A Space whose formulas mix comprehensions with the scopes around them.

    Since PEP 709 (Python 3.12), list, dict and set comprehensions are inlined into
    the enclosing scope and no longer produce a symtable of their own, so the
    exporter has to find the enclosing scope of such a comprehension lexically.
    A generator expression, a lambda and a nested def each still own a symtable,
    and a comprehension that follows one of them used to be resolved against that
    scope's symtable instead of the formula's.

    That symtable cannot answer whether a name is the comprehension's own target
    either, because PEP 709 isolates the target and leaves it indistinguishable
    from a global of the same name.

    ``a``, ``b``, ``c`` and ``d`` are Cells, so every reference to them must be
    exported as ``self.a``, ``self.b``, ``self.c`` and ``self.d``, except where the
    name is bound by the comprehension itself.
    """
    m = mx.new_model()
    s = m.new_space("Space1")

    @mx.defcells(space=s)
    def a(x):
        return x

    @mx.defcells(space=s)
    def b(x):
        return x

    @mx.defcells(space=s)
    def c(x):
        return 10 * x

    @mx.defcells(space=s)
    def d(x):
        return 100 * x

    @mx.defcells(space=s)
    def after_genexp():
        ys = [1, 2]
        return [sum(b(t) for t in range(y)) for y in ys], [c(y) for y in ys]

    @mx.defcells(space=s)
    def after_lambda():
        ys = [1, 2]
        f = lambda t: b(t)
        return f(1), [c(y) for y in ys]

    @mx.defcells(space=s)
    def after_nested_def():
        ys = [1, 2]
        def g(t):
            return b(t)
        return g(1), [c(y) for y in ys]

    @mx.defcells(space=s)
    def before_genexp():
        ys = [1, 2]
        return [c(y) for y in ys], [sum(b(t) for t in range(y)) for y in ys]

    @mx.defcells(space=s)
    def bare_after_genexp():
        ys = [1, 2]
        return [sum(b(t) for t in range(y)) for y in ys], c(1)

    @mx.defcells(space=s)
    def shadowing_loop_var():
        ys = [1, 2]
        f = lambda t: a(t)
        return f(1), [a for a in ys]

    @mx.defcells(space=s)
    def nested_comp_after_genexp():
        ys = [1, 2]
        return [sum(b(t) for t in range(y)) for y in ys], [[c(v) for v in [y]] for y in ys]

    @mx.defcells(space=s)
    def outer_binds_inner_reads():
        ys = [1, 2]
        return c(1), [[c for v in [0]] for c in ys]

    @mx.defcells(space=s)
    def loop_var_also_read():
        ys = [1, 2]
        return d(1), [d for d in ys]

    @mx.defcells(space=s)
    def loop_var_also_read_after_lambda():
        ys = [1, 2]
        h = lambda t: b(t)
        return d(1), h(1), [d for d in ys]

    @mx.defcells(space=s)
    def comp_in_default(t, u=sum([i for i in range(3)])):
        return t + u

    nomx_path = tmp_path_factory.mktemp('model')
    m.export(nomx_path / 'CompScope_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from CompScope_nomx import mx_model as nomx
        yield m, nomx
    finally:
        sys.path.pop(0)
        m.close()


def _formula_source(nomx, name):
    """The source of the method generated for the Cells named ``name``"""
    return dedent(getsource(getattr(nomx.Space1, '_f_' + name)))


def test_comprehension_after_genexp(comprehension_scopes):
    """A generator expression owns a symtable; the comprehension after it does not"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'after_genexp') == dedent("""\
    def _f_after_genexp(self):
        ys = [1, 2]
        return [sum(self.b(t) for t in range(y)) for y in ys], [self.c(y) for y in ys]
    """)
    assert nomx.Space1.after_genexp() == m.Space1.after_genexp()


def test_comprehension_after_lambda(comprehension_scopes):
    """A lambda owns a symtable; the comprehension after it does not"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'after_lambda') == dedent("""\
    def _f_after_lambda(self):
        ys = [1, 2]
        f = lambda t: self.b(t)
        return f(1), [self.c(y) for y in ys]
    """)
    assert nomx.Space1.after_lambda() == m.Space1.after_lambda()


def test_comprehension_after_nested_def(comprehension_scopes):
    """A nested def owns a symtable; the comprehension after it does not"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'after_nested_def') == dedent("""\
    def _f_after_nested_def(self):
        ys = [1, 2]
        def g(t):
            return self.b(t)
        return g(1), [self.c(y) for y in ys]
    """)
    assert nomx.Space1.after_nested_def() == m.Space1.after_nested_def()


def test_comprehension_loop_var_not_qualified(comprehension_scopes):
    """A loop variable shadowing a Cells name must not be prefixed with ``self.``

    ``for self.a in ys`` is valid Python, so this mode of the defect produces code
    that imports and runs, silently rebinding the ``a`` Cells on the Space instance.
    """
    m, nomx = comprehension_scopes

    source = _formula_source(nomx, 'shadowing_loop_var')
    assert 'for self.' not in source
    assert source == dedent("""\
    def _f_shadowing_loop_var(self):
        ys = [1, 2]
        f = lambda t: self.a(t)
        return f(1), [a for a in ys]
    """)

    assert nomx.Space1.a(3) == 3
    assert nomx.Space1.shadowing_loop_var() == m.Space1.shadowing_loop_var()
    assert nomx.Space1.a(3) == 3    # 'a' would be an int here if it had been rebound


def test_nested_comprehension_after_genexp(comprehension_scopes):
    """The lexical walk crosses more than one comprehension without a symtable"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'nested_comp_after_genexp') == dedent("""\
    def _f_nested_comp_after_genexp(self):
        ys = [1, 2]
        return [sum(self.b(t) for t in range(y)) for y in ys], [[self.c(v) for v in [y]] for y in ys]
    """)
    assert (nomx.Space1.nested_comp_after_genexp()
            == m.Space1.nested_comp_after_genexp())


def test_loop_var_read_in_nested_comprehension(comprehension_scopes):
    """A name bound by an outer comprehension stays bare where an inner one reads it"""
    m, nomx = comprehension_scopes

    source = _formula_source(nomx, 'outer_binds_inner_reads')
    assert 'for self.' not in source
    assert source == dedent("""\
    def _f_outer_binds_inner_reads(self):
        ys = [1, 2]
        return self.c(1), [[c for v in [0]] for c in ys]
    """)

    assert nomx.Space1.c(3) == 30
    assert (nomx.Space1.outer_binds_inner_reads()
            == m.Space1.outer_binds_inner_reads())
    assert nomx.Space1.c(3) == 30


@pytest.mark.parametrize("name", ['loop_var_also_read',
                                  'loop_var_also_read_after_lambda'])
def test_comprehension_loop_var_also_read(comprehension_scopes, name):
    """A loop variable is not qualified even where the Cells is also read by name

    PEP 709 isolates the target of an inlined comprehension, so where the same name
    is also read as a global in the formula, the symtable of the enclosing scope
    reports the name as a global and cannot tell the two apart. libCST records the
    binding in the comprehension's own scope, which can.
    """
    m, nomx = comprehension_scopes

    source = _formula_source(nomx, name)
    assert 'for self.' not in source
    assert 'self.d(1)' in source

    assert nomx.Space1.d(3) == 300
    assert getattr(nomx.Space1, name)() == getattr(m.Space1, name)()
    assert nomx.Space1.d(3) == 300


def test_comprehension_in_default_value(comprehension_scopes):
    """A comprehension in a default value is evaluated where ``self`` does not exist

    The default values of the generated method are evaluated while the body of the
    generated class is executed, so a ``self.`` there raises ``NameError`` on import
    of the exported package. A default value cannot refer to a Space member anyway.
    """
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'comp_in_default') == dedent("""\
    def _f_comp_in_default(self, t, u=sum([i for i in range(3)])):
        return t + u
    """)
    assert nomx.Space1.comp_in_default(1) == m.Space1.comp_in_default(1) == 4


def test_comprehension_before_genexp(comprehension_scopes):
    """A comprehension preceding any generator expression stays correct"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'before_genexp') == dedent("""\
    def _f_before_genexp(self):
        ys = [1, 2]
        return [self.c(y) for y in ys], [sum(self.b(t) for t in range(y)) for y in ys]
    """)
    assert nomx.Space1.before_genexp() == m.Space1.before_genexp()


def test_plain_name_after_genexp(comprehension_scopes):
    """A reference outside any comprehension stays correct after a generator expression"""
    m, nomx = comprehension_scopes

    assert _formula_source(nomx, 'bare_after_genexp') == dedent("""\
    def _f_bare_after_genexp(self):
        ys = [1, 2]
        return [sum(self.b(t) for t in range(y)) for y in ys], self.c(1)
    """)
    assert nomx.Space1.bare_after_genexp() == m.Space1.bare_after_genexp()
