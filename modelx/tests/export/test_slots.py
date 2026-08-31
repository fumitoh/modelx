"""Tests for exporting Space classes that declare ``__slots__``.

The exporter emits one ``__slots__`` entry per attribute the generated code
assigns on a Space instance. A name left out of ``__slots__`` is not a
compile-time error but an ``AttributeError`` the first time the exported model
runs, so the tests below check the two in both directions:

* every attribute a ``use_slots=False`` export assigns at run time is declared
  by the matching ``use_slots=True`` class, and
* the ``use_slots=False`` output is exactly the ``use_slots=True`` output with
  the ``__slots__`` declarations taken out.
"""
import ast
import importlib
import math
import pathlib
import re
import sys
import types

import pandas as pd
import pytest

import modelx as mx
from modelx.export.exporter import Exporter


sample_dir = pathlib.Path(__file__).parent / 'samples'

# A whole ``__slots__`` declaration together with the blank line the
# class_template reserves for it. Anchored on the class statement so that a
# Cells docstring holding a line that looks like one cannot match.
SLOTS_BLOCK = re.compile(
    r"(?m)^(class _c_\w+\(_mx_sys\.BaseSpace\):\n)\n"
    r"    __slots__ = \(\n(?:[^\n]*\n)*?    \)\n")

ARGVALS = (1, 2)


# ---------------------------------------------------------------------------
# Helpers

def export_both(model, tmp_path, name='Sample'):
    """Export ``model`` with and without ``__slots__``.

    Returns ``(no_slots_package, slots_package)``, both imported.
    """
    result = []
    for use_slots in (False, True):
        pkg = name + ('_slots' if use_slots else '_noslots')
        root = tmp_path / pkg
        Exporter(model, root, use_slots=use_slots).export()
        sys.path.insert(0, str(tmp_path))
        try:
            for mod in list(sys.modules):
                if mod == pkg or mod.startswith(pkg + '.'):
                    del sys.modules[mod]
            result.append(importlib.import_module(pkg))
        finally:
            sys.path.pop(0)

    return tuple(result)


def walk_spaces(parent):
    """Yield every Space below ``parent``, ItemSpaces included."""
    for space in parent._mx_walk(skip_self=True):
        yield space
        for item in list(getattr(space, '_mx_itemspaces', {}).values()):
            yield from walk_spaces(item)
            yield item


def space_key(space, pkg_name):
    """A key identifying a Space class across two parallel exports."""
    module = type(space).__module__
    return module[len(pkg_name):] + '.' + type(space).__name__


def declared_slots(cls):
    """Names of the slot descriptors cls and its bases really have.

    Not the __slots__ tuples themselves: CPython mangles a private name
    in __slots__ with the class that declares it.
    """
    names = set()
    for klass in cls.__mro__:
        names.update(name for name, value in vars(klass).items()
                     if isinstance(value, types.MemberDescriptorType))
    return names


def exercise(space, depth=0, max_depth=3):
    """Call every Cells and create ItemSpaces, recursively.

    Cells that need arguments the caller cannot guess simply raise; the point
    is to assign as many attributes as possible, not to get right answers.
    """
    for sp in space._mx_walk():
        module = sys.modules[type(sp).__module__]
        for name in getattr(module, '_v_cells_names_' + sp._name, []):
            cells = getattr(sp, name)
            for args in ((), (ARGVALS[0],), ARGVALS):
                try:
                    cells(*args)
                except Exception:
                    continue
                break
        params = getattr(module, '_v_space_params_' + sp._name, [])
        if params and depth < max_depth:
            for val in ARGVALS:
                try:
                    item = sp(*([val] * len(params)))
                except Exception:
                    continue
                exercise(item, depth + 1, max_depth)


def generated_modules(root):
    return sorted(root.rglob('_mx_classes.py')) + [root / '_mx_model.py']


# ---------------------------------------------------------------------------
# The model under test

@pytest.fixture(scope='module')
def kitchen_sink(tmp_path_factory):
    """A model exercising every category of exported Space attribute.

    ``Parent`` is parameterized, so its parameter is assigned on ``Child`` and
    ``GrandChild`` too, and ``Child``'s parameters are assigned on
    ``GrandChild``. That propagation is what makes ``__slots__`` easy to get
    wrong, and no on-disk sample covers it together with the other kinds.
    """
    m = mx.new_model('SlotsSample')

    # Model-level (global) Reference
    m.GlobalConst = 7

    other = m.new_space('Other')
    other.tag = 'other'

    parent = m.new_space('Parent')
    child = parent.new_space('Child')
    grandchild = child.new_space('GrandChild')

    parent.parameters = ('x',)
    child.parameters = ('y', 'z')

    @mx.defcells(space=parent)
    def parent_total():
        return x + GlobalConst

    @mx.defcells(space=child)
    def child_sum():
        return x + y + z

    @mx.defcells(space=child)
    def scaled(n):
        return n * ratio

    @mx.defcells(space=child)
    def uncached(n):
        return n + x

    child.uncached.is_cached = False

    @mx.defcells(space=grandchild)
    def deepest():
        return x * y * z

    # References of every kind ref_value() handles
    child.ratio = 2.5                       # literal float
    child.label = 'child'                   # literal str
    child.flag = True                       # literal bool
    child.nothing = None                    # literal None
    child.math = math                       # module
    child.pickled = [1, 2, 3]               # pickled
    child.set_ref('sibling', other, refmode='absolute')      # Interface
    child.set_ref('up', parent, refmode='auto')              # Interface

    grandchild.new_pandas(
        'table', 'table.csv',
        pd.DataFrame({'a': [1, 2, 3], 'b': [4.0, 5.0, 6.0]}),
        file_type='csv')

    @mx.defmacro
    def sample_macro(a):
        return a + mx_model.GlobalConst

    yield m
    m.close()


@pytest.fixture(scope='module')
def kitchen_sink_exports(kitchen_sink, tmp_path_factory):
    path = tmp_path_factory.mktemp('slots')
    no_slots, slots = export_both(kitchen_sink, path, 'SlotsSample')
    exercise(no_slots.mx_model)
    exercise(slots.mx_model)
    return no_slots, slots


# ---------------------------------------------------------------------------
# The equivalence test: __slots__ must cover everything actually assigned

SAMPLE_MODELS = [
    'ConstExample', 'FixedMortgage', 'ModelPath', 'NestedParams',
    'NestedSpace', 'Options', 'PandasData', 'Params', 'RelativeRefs',
    'RelativeRefs2', 'SampleSubscript',
]

# EmptyModel has no Space at all, so it has nothing to declare slots for.
BYTE_IDENTICAL_MODELS = SAMPLE_MODELS + ['EmptyModel']


def assert_slots_cover_dicts(no_slots, slots):
    """Every attribute the no-slots export assigns must have a slot."""
    used = {}
    for space in walk_spaces(no_slots.mx_model):
        key = space_key(space, no_slots.__name__)
        used.setdefault(key, set()).update(vars(space))

    available = {}
    for space in walk_spaces(slots.mx_model):
        available[space_key(space, slots.__name__)] = declared_slots(type(space))

    assert used, 'the model under test has no Spaces'
    for key, names in sorted(used.items()):
        assert key in available
        assert not (names - available[key]), (
            '%s assigns %s but does not declare it in __slots__'
            % (key, sorted(names - available[key])))


@pytest.mark.parametrize('name', SAMPLE_MODELS)
def test_slots_cover_assigned_attributes(name, tmp_path):
    m = mx.read_model(sample_dir / name)
    try:
        no_slots, slots = export_both(m, tmp_path, name)
        exercise(no_slots.mx_model)
        exercise(slots.mx_model)
        assert_slots_cover_dicts(no_slots, slots)
    finally:
        m.close()


def test_slots_cover_assigned_attributes_kitchen_sink(kitchen_sink_exports):
    assert_slots_cover_dicts(*kitchen_sink_exports)


def test_slots_cover_class_body_assignments(kitchen_sink_exports):
    """Static counterpart of the run-time check above.

    Reads the generated source instead of running it, so a Space whose Cells
    the run-time check could not call is still covered.
    """
    _, slots = kitchen_sink_exports
    root = pathlib.Path(slots.__file__).parent
    checked = 0
    for path in root.rglob('_mx_classes.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            declared = set()
            assigned = set()
            for sub in ast.walk(node):
                if not isinstance(sub, (ast.Assign, ast.AugAssign)):
                    continue
                targets = (sub.targets if isinstance(sub, ast.Assign)
                           else [sub.target])
                for target in targets:
                    if (isinstance(target, ast.Name)
                            and target.id == '__slots__'):
                        declared = {elt.value for elt in sub.value.elts}
                    elif (isinstance(target, ast.Attribute)
                          and isinstance(target.value, ast.Name)
                          and target.value.id in
                          ('self', '_mx_space', 'other')):
                        assigned.add(target.attr)
            assert declared, '%s declares no __slots__' % node.name
            assert not (assigned - declared), (
                '%s assigns %s but does not declare it in __slots__'
                % (node.name, sorted(assigned - declared)))
            checked += 1

    assert checked == 4    # Other, Parent, Child, GrandChild


def test_inherited_parameters_are_declared(kitchen_sink_exports):
    """The parameters of every parameterized ancestor need a slot.

    ``__call__`` assigns them through ``_mx_assign_params`` and
    ``_mx_copy_params`` on every Space in the subtree, not just on the Space
    that owns the formula.
    """
    _, slots = kitchen_sink_exports
    child = type(slots.mx_model.Parent.Child)
    grandchild = type(slots.mx_model.Parent.Child.GrandChild)

    assert 'x' in child.__slots__
    assert set(('x', 'y', 'z')) <= set(grandchild.__slots__)


def test_nested_parameters_run(tmp_path):
    """The values of test_itemspace_nested_params, under both settings."""
    m = mx.read_model(sample_dir / 'NestedParams')
    try:
        for nomx in export_both(m, tmp_path, 'NestedParams'):
            model = nomx.mx_model
            assert model.Parent[1].x == 1
            assert model.Parent[1].Child.x == 1
            assert model.Parent[1].Child[2].x == 1
            assert model.Parent[1].Child[2].y == 2
            assert model.Parent[2].Child[3].x == 2
            assert model.Parent[2].Child[3].y == 3
            assert model.Parent[2].Child[3].SubChild.baz == 1
    finally:
        m.close()


# ---------------------------------------------------------------------------
# use_slots=False must reproduce the previous output exactly

def strip_slots(code):
    return SLOTS_BLOCK.sub(r'\1', code)


@pytest.mark.parametrize('name', BYTE_IDENTICAL_MODELS)
def test_use_slots_false_output_unchanged(name, tmp_path):
    """``use_slots=False`` output is the slots output minus the declarations.

    The declarations are the only difference the flag is allowed to make, so
    the two exports must match once they are removed.
    """
    m = mx.read_model(sample_dir / name)
    try:
        no_slots_dir = tmp_path / 'noslots'
        slots_dir = tmp_path / 'slots'
        Exporter(m, no_slots_dir, use_slots=False).export()
        Exporter(m, slots_dir, use_slots=True).export()

        checked = 0
        for plain in generated_modules(no_slots_dir):
            slotted = slots_dir / plain.relative_to(no_slots_dir)
            assert slotted.exists()
            plain_code = plain.read_text(encoding='utf-8')
            slotted_code = slotted.read_text(encoding='utf-8')
            if '(_mx_sys.BaseSpace):' in slotted_code:
                assert '__slots__' in slotted_code
            assert strip_slots(slotted_code) == plain_code
            checked += 1

        assert checked
    finally:
        m.close()


def test_mx_sys_is_copied_verbatim(tmp_path):
    """_mx_sys.py is a static template and does not depend on the flag."""
    from modelx.export import exporter

    m = mx.read_model(sample_dir / 'Options')
    try:
        source = (pathlib.Path(exporter.__file__).parent
                  / '_mx_sys.py').read_bytes()
        for use_slots in (False, True):
            out = tmp_path / str(use_slots)
            Exporter(m, out, use_slots=use_slots).export()
            assert (out / '_mx_sys.py').read_bytes() == source
    finally:
        m.close()


# ---------------------------------------------------------------------------
# Instance layout

def test_spaces_have_no_dict_under_slots(kitchen_sink_exports):
    no_slots, slots = kitchen_sink_exports

    for space in walk_spaces(slots.mx_model):
        assert not hasattr(space, '__dict__'), type(space).__name__

    # The Model class is deliberately left alone.
    assert hasattr(slots.mx_model, '__dict__')

    # Adding __slots__ to the _mx_sys base classes does not take the __dict__
    # away from classes that declare none of their own.
    for space in walk_spaces(no_slots.mx_model):
        assert hasattr(space, '__dict__'), type(space).__name__


def test_weakref_unsupported_under_slots(kitchen_sink_exports):
    """Documented consequence: no __weakref__ slot is declared."""
    import weakref

    no_slots, slots = kitchen_sink_exports
    weakref.ref(no_slots.mx_model.Parent)       # unchanged
    with pytest.raises(TypeError):
        weakref.ref(slots.mx_model.Parent)


# ---------------------------------------------------------------------------
# Results are the same either way

def test_values_identical(kitchen_sink_exports, kitchen_sink):
    no_slots, slots = kitchen_sink_exports
    m = kitchen_sink

    for pkg in (no_slots, slots):
        nomx = pkg.mx_model
        assert nomx.Parent[3].parent_total() == m.Parent[3].parent_total()
        assert (nomx.Parent[3].Child[4, 5].child_sum()
                == m.Parent[3].Child[4, 5].child_sum())
        assert (nomx.Parent[3].Child[4, 5].scaled(2)
                == m.Parent[3].Child[4, 5].scaled(2))
        assert (nomx.Parent[3].Child[4, 5].uncached(2)
                == m.Parent[3].Child[4, 5].uncached(2))
        assert (nomx.Parent[3].Child[4, 5].GrandChild.deepest()
                == m.Parent[3].Child[4, 5].GrandChild.deepest())
        assert nomx.Parent.Child.sibling is nomx.Other
        assert nomx.Parent.Child.up is nomx.Parent
        assert nomx.Parent.Child.math is math
        assert nomx.Parent.Child.pickled == [1, 2, 3]
        assert pkg.sample_macro(1) == m.sample_macro(1)
        pd.testing.assert_frame_equal(
            nomx.Parent.Child.GrandChild.table,
            m.Parent.Child.GrandChild.table)


# ---------------------------------------------------------------------------
# The API

@pytest.mark.parametrize('api', ['function', 'method', 'exporter'])
def test_use_slots_keyword(api, tmp_path):
    m = mx.read_model(sample_dir / 'Options')
    try:
        for use_slots in (False, True):
            out = tmp_path / (api + str(use_slots))
            if api == 'function':
                mx.export_model(m, out, use_slots=use_slots)
            elif api == 'method':
                m.export(out, use_slots=use_slots)
            else:
                Exporter(m, out, use_slots=use_slots).export()

            code = (out / '_mx_classes.py').read_text(encoding='utf-8')
            assert ('__slots__' in code) is use_slots
    finally:
        m.close()


def test_slots_default_is_on(tmp_path):
    m = mx.read_model(sample_dir / 'Options')
    try:
        mx.export_model(m, tmp_path / 'default')
        code = (tmp_path / 'default' / '_mx_classes.py').read_text(
            encoding='utf-8')
        assert '__slots__' in code
    finally:
        m.close()


# ---------------------------------------------------------------------------
# Name clashes

def test_parameter_clashing_with_cells_is_rejected(tmp_path):
    """A slot may not repeat a name bound in the class body.

    A Cells named after a parameter of an enclosing Space is already broken in
    the exported model - the parameter assignment shadows the method - but
    under use_slots=True it would fail at class creation with a message
    pointing at the generated file, so the exporter rejects it up front.
    """
    m = mx.new_model('SlotsClash')
    try:
        parent = m.new_space('Parent')
        child = parent.new_space('Child')
        parent.parameters = ('t',)

        @mx.defcells(space=child)
        def t():
            return 99

        with pytest.raises(ValueError) as excinfo:
            m.export(tmp_path / 'clash')

        message = str(excinfo.value)
        assert 'SlotsClash.Parent.Child' in message
        assert "'t'" in message
        assert 'use_slots=False' in message

        # The previous behaviour stays available.
        m.export(tmp_path / 'noclash', use_slots=False)
        assert (tmp_path / 'noclash' / '_m_Parent' / '_mx_classes.py').exists()
    finally:
        m.close()


@pytest.mark.parametrize('param', ['_cells', '_mx_walk'])
def test_parameter_clashing_with_inherited_member_is_rejected(param, tmp_path):
    """A slot may not repeat a member of the _mx_sys base classes either.

    CPython raises nothing for these: the slot silently shadows the member,
    which kills the ``_cells`` property and ``_mx_walk``. Every inherited
    member starts with an underscore, and a Space parameter is the only slot
    name that can: modelx rejects a leading underscore in the name of a
    Reference or a Space, and renames such a Cells, whose name in any case
    only reaches ``__slots__`` behind a ``_v_`` or ``_has_`` prefix.
    """
    m = mx.new_model('SlotsInherited')
    try:
        space = m.new_space('Space1')
        space.parameters = (param,)

        with pytest.raises(ValueError) as excinfo:
            m.export(tmp_path / 'clash')

        assert repr(param) in str(excinfo.value)
        m.export(tmp_path / 'noclash', use_slots=False)
    finally:
        m.close()


def test_private_parameter_name_is_mangled(tmp_path):
    """A private parameter is written under the owning class's mangled name.

    ``_mx_assign_params`` is compiled in the body of the Space that owns the
    parameter, so ``__x`` reaches a descendant as ``_c_<Owner>__x``. A
    ``__slots__`` string is mangled with the class that declares it, so the
    descendant has to name the owner's form.
    """
    m = mx.new_model('SlotsPrivate')
    try:
        parent = m.new_space('Parent')
        parent.new_space('Child')
        parent.parameters = ('__x',)

        no_slots, slots = export_both(m, tmp_path, 'SlotsPrivate')
        assert '_c_Parent__x' in type(slots.mx_model.Parent.Child).__slots__

        for nomx in (no_slots.mx_model, slots.mx_model):
            assert nomx.Parent[5].Child is not None
        assert_slots_cover_dicts(no_slots, slots)
    finally:
        m.close()


def test_macro_cannot_create_a_reference_under_slots(tmp_path):
    """The attributes of a Space class are fixed when the model is exported.

    A macro that assigns a Reference the model does not already have works on
    the live model and in a use_slots=False export. It cannot work under
    __slots__, because the name is unknown when the class is generated. The
    failure is loud and names the attribute, which is why it is documented
    rather than guarded against.
    """
    m = mx.new_model('SlotsMacro')
    try:
        m.new_space('Space1')

        @mx.defmacro
        def add_ref():
            mx_model.Space1.added = 123
            return mx_model.Space1.added

        no_slots, slots = export_both(m, tmp_path, 'SlotsMacro')
        assert no_slots.add_ref() == 123
        with pytest.raises(AttributeError) as excinfo:
            slots.add_ref()
        assert 'added' in str(excinfo.value)
    finally:
        m.close()


def test_non_normalised_names_are_declared_as_stored(tmp_path):
    """Python normalises identifiers to NFKC; a ``__slots__`` string is not.

    A fullwidth letter is what a name pasted out of a spreadsheet carries, and
    :meth:`str.isidentifier` accepts it, so modelx keeps it verbatim. The
    generated ``self.<name> = ...`` compiles to the normalised name, so the
    slot has to carry the normalised name too or the exported package does not
    even import.
    """
    ref_name = chr(0xFF32) + 'ate'      # FULLWIDTH LATIN CAPITAL LETTER R
    param_name = chr(0xFF54)            # FULLWIDTH LATIN SMALL LETTER T

    m = mx.new_model('SlotsUnicode')
    try:
        parent = m.new_space('Parent')
        child = parent.new_space('Child')
        setattr(child, ref_name, 0.03)
        parent.parameters = (param_name,)

        no_slots, slots = export_both(m, tmp_path, 'SlotsUnicode')
        declared = declared_slots(type(slots.mx_model.Parent.Child))
        assert 'Rate' in declared
        assert 't' in declared

        for nomx in (no_slots.mx_model, slots.mx_model):
            assert nomx.Parent.Child.Rate == 0.03
            assert nomx.Parent[9].Child.t == 9
        assert_slots_cover_dicts(no_slots, slots)
    finally:
        m.close()


def test_reference_named_after_a_cells_is_rejected(tmp_path):
    """The guard covers References, not only parameters.

    ``space.refs`` includes the model-level globals, so a global sharing its
    name with a Cells of the Space is assigned over the Cells method. modelx
    v0.32.0 exports the alias case below correctly, because ``self.rate =
    self.rate`` resolves to the same bound method, but ``__slots__`` cannot
    declare the name at all while the class body defines the method.
    """
    m = mx.new_model('SlotsGlobalRef')
    try:
        space = m.new_space('Space1')

        @mx.defcells(space=space)
        def rate(x):
            return 2 * x

        m.rate = space.rate     # a model-level alias for the Cells

        with pytest.raises(ValueError) as excinfo:
            m.export(tmp_path / 'clash')
        assert "'rate'" in str(excinfo.value)
        assert 'SlotsGlobalRef.Space1' in str(excinfo.value)

        m.export(tmp_path / 'noclash', use_slots=False)
    finally:
        m.close()
