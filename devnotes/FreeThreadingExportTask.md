# Export models for free-threaded Python: `locked_spaces`

Working notes for the feature implemented on branch `enh/export-locked-spaces`
(modelx) and `enh/free-threading` (modelx-cython), 2026-09-03. Self-contained.

**Repos:** `C:\Users\fumito\OneDrive\pyproj\modelx` (v0.32.0 + slots, v0.33.0 unreleased),
`C:\Users\fumito\OneDrive\pyproj\modelx-cython` (v0.0.9)
**Interpreters:** `py313` = `C:/Users/fumito/anaconda3/envs/py313/python.exe` (3.13.9, GIL,
Cython 3.2.4), `py314t` = `C:/Users/fumito/anaconda3/envs/py314t/python.exe` (3.14.7
free-threaded, Cython 3.3.0, editable modelx and lifelib; modelx-cython via `PYTHONPATH`).
**Origin:** fumitoh/modelx discussion #192, comment 14652162.

---

## 1. Why

On a free-threaded build the exported `BasicTerm_S` already scales (18.4 s single-threaded,
11.3 s with two threads in the #192 experiment) because it has one Space and each thread owns
its `Projection[i]`. `TradLife_A` does not: every `Projection[i]` shares `InputData`,
`Economic`, `Assumptions`, `PolicyAttrs` and `CommTable` (`_mx_copy_refs` copies a ref to a
Space outside the ItemSpace root as the same object), and the generated cache methods have no
synchronisation. Two threads missing at once both run the formula; for `InputData` that means
two threads inside one openpyxl workbook, whose worksheets mutate their cell dicts on access.
`CommTable.__call__` races on `_mx_itemspaces` too: every model point of a product asks for the
same key.

## 2. Design (decisions confirmed with the maintainer)

| Decision | Choice |
| --- | --- |
| API | `locked_spaces=None` on `export_model`, `Model.export`, `Exporter.__init__` |
| Lock | one `threading.RLock` per exported model, created by the generated model class |
| When taken | only on a cache miss (double-checked locking); the hit path is byte-identical to today |
| Scope of an entry | the listed Space plus all its descendants; ItemSpaces share the class, so they are covered |
| Default output | byte-identical to today when the parameter is absent, `None` or empty; `_mx_sys.py` untouched |
| modelx-cython | recognises a locked class by the `self._mx_lock = self._model._mx_lock` line in `__init__`; `_has_` flags go through acquire/release atomics; `freethreading_compatible` always; `Cython>=3.2` |

Rejected: `cython.critical_section` around whole bodies (CPython suspends a critical section
whenever the thread blocks or enters one on another object, so nested cells calls let a second
thread run the same formula; and it does nothing for the pure-Python export), `cython.pymutex`
(not reentrant), always taking the RLock (25 to 99 ns per warm call single-threaded, 93 to
1,478 ns with 8 threads on one object), per-Space locks (deadlock on cyclic space-level call
graphs; a possible later option with a static cycle check), a locked `__delitem__` (the
`__call__` hit path never takes the lock, so it protects nothing).

## 3. Where the code is

modelx, `modelx/export/exporter.py`:

| item | what |
| --- | --- |
| `LOCK_ATTR = '_mx_lock'` | the attribute name, also the marker modelx-cython reads |
| `resolve_locked_spaces(model, spec)` / `_resolve_space` | validation and expansion to descendants; warns when a listed Space is below an unlocked parameterized Space |
| `Exporter.__init__` | `self.locked_spaces` (frozenset of fullnames), computed before anything is written |
| `ParentTranslator.threading_import` | `''`, set by `ModelTranslator` to `'\nimport threading'`; glued to the `_mx_sys` import line of the template |
| `ModelTranslator.lock_init`, `use_lock` | `self._mx_lock = threading.RLock()` prepended to the Space assignments |
| `SpaceTranslator.cache_method_noparam_locked`, `cache_method_locked`, `itemspace_methods_locked`, `lock_assign` | the locked templates; the first statements are today's hit path |
| `SpaceTranslator._get_class_def` | `locked = space.fullname in self.locked_spaces`; template choice; the two lock lines inserted at index 0 of `cache_vars` after the `# Cache variables` header, with `slot_names.append(LOCK_ATTR)` on the same line; the guard against a Space parameter named `_mx_lock` |

`modelx/core/api.py` (`export_model`, the `**Free threading**` docstring section) and
`modelx/core/model.py` (`Model.export`) forward the parameter.

modelx-cython, `modelx_cython/`:

| file | what |
| --- | --- |
| `_mx_sys.pxd` | the verbatim C shim `_mx_load_flag` / `_mx_store_flag` (`_Py_atomic_load_int_acquire` / `_Py_atomic_store_int_release` under `Py_GIL_DISABLED`, plain access otherwise) and `cdef public object _mx_lock` on `BaseParent` |
| `consts.py` | `MX_LOCK` |
| `parser.py` | `ModuleVisitor.locked_classes`, filled in `collect_space_info` |
| `builder.py` | `ClassInfo.is_locked`, `CombinedCellsInfo.is_locked`, `uses_dict_cache` |
| `transformer.py` | `remove_cache_assigns` keeps `self._v_x = {}` for dict caches of locked classes; `update_method` regenerates no-arg and arrayable bodies through `_locked_body`, keeps dict-cached bodies without `_add_dict_assign` |
| `cli.py` | `create_setup` emits `compiler_directives={"freethreading_compatible": True}`; INFO log per locked class |

## 4. The generated code

Locked no-arg cells (the parameterized one is analogous with `key in dict`):

```python
def name(self):
    if self._has_name:
        return self._v_name
    with self._mx_lock:
        if self._has_name:
            return self._v_name
        val = self._v_name = self._f_name()
        self._has_name = True
        return val
```

Locked `__call__` uses a single `self._mx_itemspaces.get(_mx_key)` on the hit path (a
concurrent `del` cannot turn `in` + `[]` into a `KeyError`) and publishes the root last.

Compiled no-arg cells of a locked class (arrayable cells the same, per element):

```python
@_mx_cy.ccall
def name(self) -> _mx_cy.double:
    if _mx_sys._mx_load_flag(_mx_cy.address(self._has_name)):
        return self._v_name
    with self._mx_lock:
        if self._has_name:
            return self._v_name
        val = self._f_name()
        self._v_name = val
        _mx_sys._mx_store_flag(_mx_cy.address(self._has_name), True)
        return val
```

## 5. Why the unlocked hit path is safe

CPython 3.13/3.14 (`Python/structmember.c`, `bytecodes.c`): a `__slots__` or instance-dict
store is `FT_ATOMIC_STORE_PTR_RELEASE` under the object's critical section; a load is an
atomic (seq-cst or acquire) load plus `_Py_TryIncrefCompare`. Dict insert is a release store
under the dict lock; `in` / `[]` / `.get` are lock-free acquire reads with retry. The template
stores `_v_` before `_has_`, so a reader that sees the flag sees the value. Keep that order.

In the compiled model the flags are C fields, whose plain accesses carry no ordering, hence the
shim. `Python.h` includes `pyatomic.h` on 3.13 and 3.14, GIL and free-threaded builds; MSVC x64
implements the two functions as volatile accesses, ARM64 as `stlr` / `ldar`. `bint` is C `int`.

## 6. Traps met on the way

- Do NOT add `_mx_lock` to `class_names` in `_get_class_def`: `slots_decl` rejects every slot
  name found there, so the lock's own slot would raise. A Space parameter named `_mx_lock`
  (modelx allows leading-underscore parameters, `test_slots.py` uses `_cells`) is guarded
  separately, for both `use_slots` settings, because `_mx_assign_params` would assign over the
  lock.
- In the pxd the lock must be on `BaseParent`. A compiled Space reads `self._model._mx_lock`
  through the `BaseModel`-typed `_model` field and `self._mx_lock` through its own type;
  declared on `BaseModel` alone, the Space classes have no field and Cython silently compiles
  a generic setattr that raises at model construction.
- No-arg cells of a locked class need the regenerated body too, not only arrayable cells: the
  transformer used to keep the exported body for every no-arg cells, which in a cclass is a
  plain C load and store.
- A child Space does not see its parent's Cells by name in modelx; the test model uses refs.
- `MonkeyType` is a live dependency of modelx-cython (`monkeytype_tracing.py` imports
  `monkeytype.compat/typing/util`).
- Cython builds must run from PowerShell on this machine: Git Bash drops the
  `ProgramFiles(x86)` variable setuptools needs to find `vswhere`.
- A translated module needs both `from cython.cimports.<pkg> import _mx_sys` and the Python
  `from . import _mx_sys`; the cimported name alone has no `import_module`.
- The tracer is installed with `sys.setprofile`, per thread: `sample.py` must stay
  single-threaded.

## 7. Verification

- modelx: `pytest modelx/tests/export` green on py313 (134 tests) and the new
  `test_locked_spaces.py` (41 tests) green on py314t, including the exactly-once stress test
  (8 threads, sleeping formulas) and its control that shows duplicates on the unlocked export
  on both builds; `test_annuallife_threaded` (TradLife_A, 4 threads) green on both builds.
- Golden byte-identity: `modelx/tests/export/samples/golden_exports.json` records the
  `_mx_classes.py` / `_mx_model.py` of the twelve sample models from `main` (f63ffc8), both
  `use_slots` settings; `test_default_output_matches_golden` compares the parameter-absent,
  `None` and `[]` exports to it. Regenerate with `regenerate_golden()` in the test module only
  when the default output is meant to change.
- modelx-cython: unlocked translations of the twelve self-contained samples are byte-identical
  between `main` (5516053) and the branch (only `setup.py` and `_mx_sys.pxd` differ), checked
  with a git worktree; `test_locked_spaces` (translate-only assertions, compile, 8 threads)
  green on py313 and py314t; `test_mx2cy_with_annuallife[tradlife_a-TradLife_A-True]`
  (locked export, compile, 4 threads) green on py313; full suite on py313 (see below).
- Free-threading check: on py314t `sys._is_gil_enabled()` stays False after importing the
  compiled packages (the `freethreading_compatible` directive).

## 8. Measurements

Micro (py314t, GIL disabled): warm hit paths 25 ns (slot) / 52 ns (dict) with the old and the
new templates alike; `with rlock: pass` 74 ns uncontended, ~250 ns with 2 threads, ~8 µs with
8 threads contending. Cost model to document: a miss is cheap uncontended and expensive under
contention, so lock Spaces with bounded key spaces; `CommTable.AnnDuenx/Axn` in TradLife_A
miss ~50 times per model point after warm-up and bound the scaling.

TradLife_A end to end, py314t (3.14.7 free-threaded, GIL disabled), Windows 11, quiet
machine. The five shared Spaces locked; the shared caches warmed by one model point per product
single-threaded first; then the 30 model points that `sample.py` traces (`range(0, 300, 10)`,
the compiled caches are sized for them) split round-robin across the threads, each thread
deleting and recomputing its `Projection[i]` ItemSpaces `reps` times so that the timed work is
the projection itself. Points per second of `pv_net_cf(0)`:

| model | threads | unlocked | locked |
| --- | ---: | ---: | ---: |
| exported (pure Python), 20 reps | 1 | 1,785 | 1,853 |
| | 2 | | 2,609 |
| | 4 | | 3,879 |
| | 8 | | 4,097 |
| compiled (mx2cy), 200 reps | 1 | 5,834 | 5,771 |
| | 2 | | 10,331 |
| | 4 | | 16,599 |
| | 8 | | 18,984 |

The lock costs nothing measurable single-threaded (the two 1-thread columns differ by 1 to 4%,
within run-to-run noise). The pure-Python model scales to 2.2x with 8 threads, the compiled
model to 3.3x; the ceiling is the `CommTable.AnnDuenx/Axn` misses that every model point makes
under the one lock, plus the refcount contention on the shared numpy arrays and Series that the
`Projection` formulas read. Script: `scratchpad/bench/bench_tradlife.py` of the session
(export locked and unlocked, `mx2cy` both, then `bench_tradlife.py <package> 300 <reps> 1 2 4 8`).

## 9. Follow-ups

- Per-Space lock granularity as an option, with a static cycle check over refs.
- Reduce per-model-point misses in lifelib `TradLife_A.CommTable`.
- Lock `BaseSpace._cells` population (benign race); a `lock_timeout` debug aid.
- Vendor the three `monkeytype` helpers so modelx-cython can drop the dependency.
- lifelib: a threaded `TradLife_A` driver script.
