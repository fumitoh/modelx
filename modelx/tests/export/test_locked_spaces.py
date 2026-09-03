"""Tests for exporting Spaces with the model lock (``locked_spaces``).

A locked Space computes each cached Cells value and creates each ItemSpace
at most once when several threads call it, by taking a lock shared by all
the locked Spaces of the model on a cache miss. The tests below check:

* that an export without ``locked_spaces`` is byte-identical to the golden
  output recorded from the exporter before the parameter existed,
* the shape of the generated code of locked and unlocked Spaces,
* the validation of the parameter,
* that the lock really makes every formula run once under threads, and
  that the same test detects the duplicate runs of an unlocked export.
"""
import ast
import importlib
import json
import math
import pathlib
import re
import sys
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

import pytest

import modelx as mx
from modelx.export.exporter import Exporter, LOCK_ATTR, resolve_locked_spaces
from test_slots import (
    BYTE_IDENTICAL_MODELS, walk_spaces, assert_slots_cover_dicts,
    generated_modules)


sample_dir = pathlib.Path(__file__).parent / 'samples'
GOLDEN_FILE = sample_dir / 'golden_exports.json'

# The id() numbers in io_data[...] / pickle_data[...] differ between processes.
ID_EXPR = re.compile(r'\b(io_data|pickle_data)\[\d+\]')

LOCKED = ['Data', 'Table']


def normalise(text):
    return ID_EXPR.sub(r'\1[ID]', text.replace('\r\n', '\n'))


def regenerate_golden():
    """Rewrite the golden file from the current exporter.

    Only meant to be run with an exporter whose default output is known to
    be right; the tests below then hold every later change to it.
    """
    golden = {}
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for name in BYTE_IDENTICAL_MODELS:
            m = mx.read_model(sample_dir / name)
            try:
                for use_slots in (True, False):
                    tag = 'slots' if use_slots else 'noslots'
                    out = tmp / name / tag
                    Exporter(m, out, use_slots=use_slots).export()
                    for path in generated_modules(out):
                        key = '/'.join(
                            [name, tag, path.relative_to(out).as_posix()])
                        golden[key] = normalise(
                            path.read_text(encoding='utf-8'))
            finally:
                m.close()
    GOLDEN_FILE.write_text(json.dumps(golden, indent=1, sort_keys=True) + '\n',
                           encoding='utf-8', newline='\n')


# ---------------------------------------------------------------------------
# Helpers

def import_export(model, root, pkg, **kwargs):
    """Export ``model`` as package ``pkg`` under ``root`` and import it."""
    Exporter(model, root / pkg, **kwargs).export()
    sys.path.insert(0, str(root))
    try:
        for mod in list(sys.modules):
            if mod == pkg or mod.startswith(pkg + '.'):
                del sys.modules[mod]
        return importlib.import_module(pkg)
    finally:
        sys.path.pop(0)


def space_fullname(model_name, root, path, class_name):
    """The fullname of the Space that ``class_name`` in ``path`` stands for."""
    parts = [p[len('_m_'):] for p in path.relative_to(root).parts[:-1]]
    return '.'.join([model_name] + parts + [class_name[len('_c_'):]])


def class_defs(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {node.name: node for node in tree.body
            if isinstance(node, ast.ClassDef)}


def methods(class_node):
    return {node.name: node for node in class_node.body
            if isinstance(node, ast.FunctionDef)}


def lock_withs(func_node):
    """The ``with self._mx_lock:`` statements anywhere in ``func_node``."""
    result = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.With):
            for item in node.items:
                expr = item.context_expr
                if (isinstance(expr, ast.Attribute)
                        and isinstance(expr.value, ast.Name)
                        and expr.value.id == 'self'
                        and expr.attr == LOCK_ATTR):
                    result.append(node)
    return result


def assigned_attrs(func_node):
    """Names assigned as ``self.<name>`` in ``func_node``, in order."""
    names = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == 'self'):
                    names.append(target.attr)
    return names


def count_formula_runs(package, sleep=0.0005):
    """Wrap every ``_f_`` method of every Space class of ``package``.

    Returns the list the wrappers append ``(class, cells, id(space), args)``
    to; the id tells the ItemSpaces of one class apart. The sleep releases
    the GIL, so that the duplicate runs of an unlocked export show up on a
    build with the GIL as well.
    """
    runs = []
    guard = threading.Lock()
    root = pathlib.Path(package.__file__).parent

    def make(cls, name, orig):
        def wrapper(self, *args):
            with guard:
                runs.append((cls.__name__, name, id(self), args))
            time.sleep(sleep)
            return orig(self, *args)
        return wrapper

    for path in root.rglob('_mx_classes.py'):
        rel = path.relative_to(root).with_suffix('').as_posix()
        module = sys.modules[package.__name__ + '.' + rel.replace('/', '.')]
        for cls_name, cls in vars(module).items():
            if not (isinstance(cls, type) and cls_name.startswith('_c_')):
                continue
            for name in list(vars(cls)):
                if name.startswith('_f_'):
                    setattr(cls, name, make(cls, name, getattr(cls, name)))
    return runs


def run_threads(nomx, n_threads=8, n_points=64, n_steps=20, timeout=120):
    """Compute ``Projection[i].pv(t)`` over all points, one slice per thread.

    Returns ``(results, itemspace_ids)`` where results maps (i, t) to the
    value and itemspace_ids is the set of ids seen for ``Table['A']``.
    """
    barrier = threading.Barrier(n_threads)
    ids = set()
    ids_guard = threading.Lock()

    def work(k):
        barrier.wait(timeout=timeout)
        out = {}
        for i in range(k, n_points, n_threads):
            for t in range(n_steps):
                out[(i, t)] = nomx.Projection[i].pv(t)
        with ids_guard:
            ids.add(id(nomx.Table['A']))
        return out

    results = {}
    with ThreadPoolExecutor(n_threads) as pool:
        futures = [pool.submit(work, k) for k in range(n_threads)]
        for f in futures:
            results.update(f.result(timeout=timeout))
    return results, ids


# ---------------------------------------------------------------------------
# The model under test

@pytest.fixture(scope='module')
def lock_sample():
    """A model with shared Spaces to lock and a per-thread Space.

    ``Data`` (with a child ``Sub``) and the parameterized ``Table`` (with a
    child ``Child``) are the shared Spaces. ``Helper`` is not locked but is
    called by a locked Cells and calls back into ``Data``. ``Projection[i]``
    is the per-thread Space; its child ``Sub`` sits below an unlocked
    parameterized Space, which the exporter warns about when it is listed.
    """
    m = mx.new_model('LockSample')
    m.GlobalConst = 7

    data = m.new_space('Data')
    sub = data.new_space('Sub')
    helper = m.new_space('Helper')
    table = m.new_space('Table')
    table.parameters = ('key',)
    tchild = table.new_space('Child')
    proj = m.new_space('Projection')
    proj.parameters = ('i',)
    psub = proj.new_space('Sub')

    @mx.defcells(space=data)
    def table_obj():
        return {'a': 1.0, 'b': 2.0}

    @mx.defcells(space=data)
    def scale():
        return 1.5

    @mx.defcells(space=data)
    def rate(t):
        return 0.01 * t + scale()

    @mx.defcells(space=data)
    def lookup(name):
        return table_obj()[name]

    @mx.defcells(space=data)
    def uncached(n):
        return n * scale()

    data.uncached.is_cached = False

    @mx.defcells(space=data)
    def via_helper(n):
        return helper.twice(n)

    @mx.defcells(space=data)
    def flaky():
        if fail_count[0] > 0:
            fail_count[0] -= 1
            raise ValueError('not yet')
        return 42

    @mx.defcells(space=sub)
    def sub_value():
        return data.scale() * 10

    @mx.defcells(space=helper)
    def twice(n):
        return 2 * data.scale() * n

    @mx.defcells(space=table)
    def key_weight():
        return {'A': 1.0, 'B': 2.0}[key]

    @mx.defcells(space=table)
    def rec(x):
        return 1.0 if x == 0 else rec(x - 1) + key_weight()

    @mx.defcells(space=tchild)
    def child_val():
        return tbl.key_weight() * 3

    @mx.defcells(space=proj)
    def pv(t):
        return (data.rate(t) + data.lookup('a') + data.Sub.sub_value()
                + data.via_helper(i) + table['A'].rec(t)
                + table['B'].Child.child_val() + i + GlobalConst)

    @mx.defcells(space=psub)
    def psub_val():
        return i * 2

    # References of the kinds ref_value() handles
    data.ratio = 2.5
    data.label = 'data'
    data.flag = True
    data.nothing = None
    data.math = math
    data.fail_count = [2]           # pickled, shared by every caller
    data.helper = helper
    sub.data = data                 # a child sees its parent through a ref
    tchild.tbl = table              # Table['A'].Child.tbl is Table['A']
    helper.data = data
    proj.data = data
    proj.table = table

    yield m
    m.close()


@pytest.fixture(scope='module')
def exports(lock_sample, tmp_path_factory):
    """``(unlocked, locked with slots, locked without slots)`` packages."""
    root = tmp_path_factory.mktemp('locked')
    unlocked = import_export(lock_sample, root, 'LockSample_unlocked')
    slots = import_export(lock_sample, root, 'LockSample_slots',
                          locked_spaces=LOCKED)
    noslots = import_export(lock_sample, root, 'LockSample_noslots',
                            use_slots=False, locked_spaces=LOCKED)
    return unlocked, slots, noslots


# ---------------------------------------------------------------------------
# The default output is unchanged

@pytest.mark.parametrize('name', BYTE_IDENTICAL_MODELS)
def test_default_output_matches_golden(name, tmp_path):
    """No ``locked_spaces``, ``None`` and ``[]`` all give the recorded output."""
    golden = json.loads(GOLDEN_FILE.read_text(encoding='utf-8'))
    m = mx.read_model(sample_dir / name)
    try:
        for use_slots in (True, False):
            tag = 'slots' if use_slots else 'noslots'
            for n, kwargs in enumerate(
                    ({}, {'locked_spaces': None}, {'locked_spaces': []})):
                out = tmp_path / tag / str(n)
                Exporter(m, out, use_slots=use_slots, **kwargs).export()
                checked = 0
                for path in generated_modules(out):
                    key = '/'.join([name, tag, path.relative_to(out).as_posix()])
                    code = normalise(path.read_text(encoding='utf-8'))
                    assert code == golden[key], key
                    assert LOCK_ATTR not in code
                    assert 'threading' not in code
                    checked += 1
                assert checked
    finally:
        m.close()


def test_mx_sys_is_copied_verbatim(lock_sample, tmp_path):
    from modelx.export import exporter

    source = (pathlib.Path(exporter.__file__).parent / '_mx_sys.py').read_bytes()
    Exporter(lock_sample, tmp_path / 'locked', locked_spaces=LOCKED).export()
    assert (tmp_path / 'locked' / '_mx_sys.py').read_bytes() == source


# ---------------------------------------------------------------------------
# The shape of the generated code

def test_generated_code_shape(lock_sample, exports):
    _, slots, noslots = exports
    expected = resolve_locked_spaces(lock_sample, LOCKED)

    for pkg in (slots, noslots):
        root = pathlib.Path(pkg.__file__).parent
        checked_locked = checked_unlocked = 0
        for path in root.rglob('_mx_classes.py'):
            module = ast.parse(path.read_text(encoding='utf-8'))
            names = {node.targets[0].id: node.value for node in module.body
                     if isinstance(node, ast.Assign)
                     and isinstance(node.targets[0], ast.Name)}
            for cls_name, cls in class_defs(path).items():
                fullname = space_fullname(lock_sample.name, root, path, cls_name)
                meths = methods(cls)
                cells = [c.value for c in names['_v_cells_names_' + cls_name[3:]].elts]
                cached = [c for c in cells if '_f_' + c in meths]
                if fullname in expected:
                    checked_locked += 1
                    init = assigned_attrs(meths['__init__'])
                    assert LOCK_ATTR in init
                    # the lock sits above the cache variables
                    assert init.index(LOCK_ATTR) < min(
                        (init.index(n) for n in init
                         if n.startswith(('_v_', '_has_'))), default=len(init))
                    if pkg is slots:
                        slots_node = next(
                            node for node in cls.body if isinstance(node, ast.Assign)
                            and node.targets[0].id == '__slots__')
                        assert LOCK_ATTR in [e.value for e in slots_node.value.elts]
                    for name in cached:
                        withs = lock_withs(meths[name])
                        assert len(withs) == 1, (fullname, name)
                        # the unlocked cache-hit check comes first
                        assert isinstance(meths[name].body[0], ast.If)
                        assert meths[name].body[1] is withs[0]
                        names_in_with = assigned_attrs(withs[0])
                        if '_has_' + name in names_in_with:
                            assert (names_in_with.index('_v_' + name)
                                    < names_in_with.index('_has_' + name))
                    for name in set(cells) - set(cached):
                        assert not lock_withs(meths[name]), (fullname, name)
                    if '__call__' in meths:
                        assert len(lock_withs(meths['__call__'])) == 1
                        assert '.get(' in ast.unparse(meths['__call__'])
                        assert not lock_withs(meths['__delitem__'])
                else:
                    checked_unlocked += 1
                    src = ast.unparse(cls)
                    assert LOCK_ATTR not in src, fullname
        assert checked_locked == 4      # Data, Data.Sub, Table, Table.Child
        assert checked_unlocked == 3    # Helper, Projection, Projection.Sub


def test_model_module(exports):
    _, slots, _ = exports
    code = (pathlib.Path(slots.__file__).parent / '_mx_model.py').read_text(
        encoding='utf-8')
    assert 'import threading' in code
    assert code.index('self._mx_lock = threading.RLock()') < code.index('# Space assignments')


def test_lock_is_shared(exports):
    _, slots, noslots = exports
    for pkg in (slots, noslots):
        nomx = pkg.mx_model
        nomx.Projection[1].pv(3)        # creates the ItemSpaces
        assert isinstance(nomx._mx_lock, type(threading.RLock()))
        seen = 0
        for space in walk_spaces(nomx):
            name = type(space).__name__
            if name in ('_c_Data', '_c_Table', '_c_Child') or (
                    name == '_c_Sub' and space._parent._name == 'Data'):
                assert space._mx_lock is nomx._mx_lock
                seen += 1
            else:
                assert not hasattr(space, LOCK_ATTR), name
        assert seen >= 6    # Data, Data.Sub, Table, Table.Child, Table['A'], Table['B'](.Child)


def test_slots_cover_assigned_attributes(exports):
    _, slots, noslots = exports
    for pkg in (slots, noslots):
        nomx = pkg.mx_model
        nomx.Projection[2].pv(1)
        nomx.Data.uncached(3)
    assert_slots_cover_dicts(noslots, slots)


def test_values_identical(lock_sample, exports):
    m = lock_sample
    for pkg in exports:
        nomx = pkg.mx_model
        for i in range(3):
            for t in range(4):
                assert nomx.Projection[i].pv(t) == m.Projection[i].pv(t)
        assert nomx.Data.uncached(3) == m.Data.uncached(3)
        assert nomx.Table['B'].rec(5) == m.Table['B'].rec(5)
        assert nomx.Data.math is math
        assert nomx.Data.helper is nomx.Helper


# ---------------------------------------------------------------------------
# The parameter

@pytest.mark.parametrize('api', ['function', 'method', 'exporter'])
def test_locked_spaces_keyword(lock_sample, tmp_path, api):
    out = tmp_path / api
    if api == 'function':
        mx.export_model(lock_sample, out, locked_spaces=['Data'])
    elif api == 'method':
        lock_sample.export(out, locked_spaces=['Data'])
    else:
        Exporter(lock_sample, out, locked_spaces=['Data']).export()
    assert LOCK_ATTR in (out / '_mx_classes.py').read_text(encoding='utf-8')


def test_resolution(lock_sample):
    m = lock_sample
    assert resolve_locked_spaces(m, None) == frozenset()
    assert resolve_locked_spaces(m, []) == frozenset()
    assert resolve_locked_spaces(m, ['Data']) == {
        'LockSample.Data', 'LockSample.Data.Sub'}
    assert resolve_locked_spaces(m, ['Data.Sub']) == {'LockSample.Data.Sub'}
    assert resolve_locked_spaces(m, [m.Table]) == {
        'LockSample.Table', 'LockSample.Table.Child'}
    assert (resolve_locked_spaces(m, ['Data', 'Data', m.Data.Sub])
            == resolve_locked_spaces(m, ('Data',)))


@pytest.mark.parametrize('spec, error, text', [
    ('Data', TypeError, 'iterable'),
    (42, TypeError, 'iterable'),
    ([42], TypeError, '42'),
    (['Nope'], ValueError, "'Nope'"),
    (['Data.rate'], ValueError, "'Data.rate'"),      # a Cells, not a Space
    (['Data.ratio'], ValueError, "'Data.ratio'"),    # a Reference
])
def test_invalid_specs(lock_sample, spec, error, text):
    with pytest.raises(error) as excinfo:
        resolve_locked_spaces(lock_sample, spec)
    assert text in str(excinfo.value)
    if error is ValueError:
        assert lock_sample.name in str(excinfo.value)


def test_bare_space_is_rejected(lock_sample):
    with pytest.raises(TypeError):
        resolve_locked_spaces(lock_sample, lock_sample.Data)


def test_itemspace_is_rejected(lock_sample):
    with pytest.raises(ValueError) as excinfo:
        resolve_locked_spaces(lock_sample, [lock_sample.Table['A']])
    assert 'ItemSpace' in str(excinfo.value)


def test_space_of_another_model_is_rejected(lock_sample):
    other = mx.new_model('OtherModel')
    try:
        other.new_space('Data')
        with pytest.raises(ValueError) as excinfo:
            resolve_locked_spaces(lock_sample, [other.Data])
        assert 'LockSample' in str(excinfo.value)
    finally:
        other.close()


def test_validation_happens_before_writing(lock_sample, tmp_path):
    with pytest.raises(ValueError):
        Exporter(lock_sample, tmp_path / 'never', locked_spaces=['Nope'])
    assert not (tmp_path / 'never').exists()


def test_warns_below_unlocked_parameterized_space(lock_sample):
    with pytest.warns(UserWarning, match="'LockSample.Projection'"):
        resolve_locked_spaces(lock_sample, ['Projection.Sub'])
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        resolve_locked_spaces(lock_sample, ['Projection', 'Projection.Sub'])
        resolve_locked_spaces(lock_sample, ['Data', 'Table', 'Table.Child'])


@pytest.mark.parametrize('use_slots', [True, False])
def test_parameter_named_after_the_lock_is_rejected(tmp_path, use_slots):
    m = mx.new_model('LockParam')
    try:
        parent = m.new_space('Parent')
        parent.new_space('Child')
        parent.parameters = (LOCK_ATTR,)

        for locked in (['Parent'], ['Parent.Child']):
            with pytest.raises(ValueError) as excinfo:
                m.export(tmp_path / 'clash', use_slots=use_slots,
                         locked_spaces=locked)
            assert LOCK_ATTR in str(excinfo.value)

        m.export(tmp_path / 'ok', use_slots=use_slots)     # unlocked is fine
    finally:
        m.close()


# ---------------------------------------------------------------------------
# Exactly once under threads

def is_free_threaded():
    return not getattr(sys, '_is_gil_enabled', lambda: True)()


@pytest.mark.parametrize('use_slots', [True, False])
def test_formulas_run_once_under_threads(lock_sample, tmp_path, use_slots):
    pkg = import_export(lock_sample, tmp_path, 'LockSample_once_%s' % use_slots,
                        use_slots=use_slots, locked_spaces=LOCKED)
    nomx = pkg.mx_model
    runs = count_formula_runs(pkg)
    switch = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        results, ids = run_threads(nomx)
    finally:
        sys.setswitchinterval(switch)

    locked_classes = {'_c_Data', '_c_Table', '_c_Child'}
    locked_runs = [r for r in runs if r[0] in locked_classes
                   or (r[0] == '_c_Sub' and r[1] == '_f_sub_value')]
    assert locked_runs
    duplicates = [r for r in set(locked_runs) if locked_runs.count(r) > 1]
    assert not duplicates
    assert len(ids) == 1
    for (i, t), value in results.items():
        assert value == lock_sample.Projection[i].pv(t)


def test_unlocked_export_runs_formulas_twice(lock_sample, tmp_path):
    """The control: without the lock the same test sees duplicate runs.

    Proves that the previous test can fail. The values are still right, as
    the formulas are pure.
    """
    pkg = import_export(lock_sample, tmp_path, 'LockSample_control')
    nomx = pkg.mx_model
    runs = count_formula_runs(pkg)
    switch = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        results, _ = run_threads(nomx)
    finally:
        sys.setswitchinterval(switch)

    shared = [r for r in runs if r[0] in ('_c_Data', '_c_Table', '_c_Child')]
    assert len(shared) > len(set(shared))
    for (i, t), value in results.items():
        assert value == lock_sample.Projection[i].pv(t)


def test_recursion_and_reentrancy_from_threads(lock_sample, tmp_path):
    """Locked -> unlocked -> locked chains and deep recursion do not deadlock."""
    nomx = import_export(lock_sample, tmp_path, 'LockSample_reentrant',
                         locked_spaces=LOCKED).mx_model

    def work(k):
        return (nomx.Data.via_helper(k), nomx.Table['A'].rec(110),
                nomx.Table['B'].Child.child_val())

    with ThreadPoolExecutor(4) as pool:
        futures = [pool.submit(work, k) for k in range(8)]
        values = [f.result(timeout=60) for f in futures]

    m = lock_sample
    assert values == [(m.Data.via_helper(k), m.Table['A'].rec(110),
                       m.Table['B'].Child.child_val()) for k in range(8)]


def test_raising_formula_is_retried(lock_sample, tmp_path):
    """A formula that raises caches nothing; the next caller runs it again."""
    pkg = import_export(lock_sample, tmp_path, 'LockSample_flaky',
                        locked_spaces=LOCKED)
    nomx = pkg.mx_model
    runs = count_formula_runs(pkg, sleep=0)
    barrier = threading.Barrier(4)

    def work(k):
        barrier.wait(timeout=60)
        try:
            return nomx.Data.flaky()
        except ValueError as e:
            return str(e)

    with ThreadPoolExecutor(4) as pool:
        values = [f.result(timeout=60)
                  for f in [pool.submit(work, k) for k in range(4)]]

    flaky_runs = lambda: [r for r in runs if r[:2] == ('_c_Data', '_f_flaky')]
    assert sorted(values, key=str) == [42, 42, 'not yet', 'not yet']
    assert len(flaky_runs()) == 3
    assert nomx.Data.flaky() == 42
    assert len(flaky_runs()) == 3


@pytest.mark.skipif(not is_free_threaded(), reason='needs a free-threaded build')
def test_gil_stays_disabled(exports):
    assert not sys._is_gil_enabled()
