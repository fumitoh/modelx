# Fast path for argument binding on the cells access hot path

Working instruction for a fresh session. Self-contained.

**Repo:** `C:\Users\fumito\OneDrive\pyproj\modelx` (branch `main`, v0.32.0)
**Python:** `C:/Users/fumito/anaconda3/envs/py313/python.exe`
**Goal:** stop paying a full `inspect.Signature.bind()` + `BoundArguments.apply_defaults()` on
every cells access, including cache hits.
**Expected win:** ~30% of projection wall time on real lifelib workloads (range −20% to −35%).

Branch before committing. Do not commit on `main`.

---

## 1. The problem

`modelx/core/execution/trace.py:91`:

```python
def _bind_args(obj, args, kwargs):
    boundargs = obj.formula.signature.bind(*args, **kwargs)
    boundargs.apply_defaults()
    return tuple(boundargs.arguments.values())
```

`get_node()` calls this to build the trace key, and `executor.eval_node()` consults the cache
**after** the key exists (`executor.py:34`). So a cache hit pays a full `Signature.bind()`.

Measured on `LTC_JP_S` (jplib, 8 model points, ~14 s of projection):

| | |
|---|---:|
| `_bind_args` calls | 2,371,603 |
| formula evaluations | 793,539 |
| cache hits that still bound | 1,578,062 (66.5%) |

`VA_US_S` gives 1,609,960 binds / 633,094 evaluations / 60.7% hits. Across real models the
ratio is **2.5–3.0 cells references per formula evaluation, 61–67% of them cache hits**.

Over a full 28-model sweep of `lifelib-products` (uslib + uklib + jplib, 234 model points):
**15,914,995 bind calls.**

### Where the time actually goes

cProfile says `_bind_args` is 52.1% cumulative — **do not quote that number**. The profiler turns
a 14.2 s run into 38.5 s (2.6×) and the inflation lands precisely on deep stacks of tiny `inspect`
calls. The honest figure from an unprofiled A/B is **~30%**.

## 2. The hot call site is not the obvious one

The chain looks like `Cells.__call__` (`cells.py:193`) → `CellsImpl.get_value` (`cells.py:803`).
Measured by caller frame, that route accounts for **9 calls out of 2,371,603**.

**2,371,586 (99.9993%) enter at `cells.py:808`, inside `CellsImpl.call`**, because
`space.py:1995` does:

```python
for k, v in self.cells.items():
    self._ns_dict[k] = v.call
```

Every cells name in the formula-execution namespace is bound directly to the **bound method
`CellsImpl.call`**. An intra-formula reference like `pols_if(t)` therefore never touches
`Cells.__call__`. A fast path installed there would optimise 9 calls out of 2.4M.

Install it in `get_node`, which every route shares.

Related: 793,527 of 793,541 formula evaluations (99.998%) are `DynamicCellsImpl` — the workload
is almost entirely ItemSpace-dynamic cells, so the fast path must be correct for derived and
dynamic cells above all.

## 3. Correctness envelope

`tuple(sig.bind(*args, **kwargs).apply_defaults().arguments.values())` equals `tuple(args)`
**if and only if** every parameter is `POSITIONAL_ONLY` or `POSITIONAL_OR_KEYWORD`, `kwargs` is
falsy, and `len(args)` equals the parameter count exactly.

Two results that are easy to get backwards:

- **Defaults do NOT need to be excluded from the guard.** A default is only *applied* when the
  call is short; a full-arity all-positional call never touches them. Short calls fail the arity
  test and take the slow path.
- **`POSITIONAL_ONLY` does NOT need to be excluded.** `def f(x, /, y)` called `f(1, 2)` binds to
  `(1, 2)` exactly.

Decision table (every row produced by creating a real Cells, calling it, and reading
`cells._impl.data` keys):

```
    signature            call            key            fast?  why
 1  def f()              f()             ()             YES
 2  def f(x)             f(1)            (1,)           YES
 3  def f(x)             f(x=1)          (1,)           no     kwargs
 4  def f(x,y,z)         f(1,2,3)        (1,2,3)        YES
 5  def f(x,y,z)         f(z=3,x=1,y=2)  (1,2,3)        no     out-of-order kwargs still bind
                                                               to declaration order
 6  def f(x,y,z)         f(1,2,z=3)      (1,2,3)        no     mixed
 7  def f(x,y=10,z=20)   f(1)            (1,10,20)      no     arity 3 != 1
 8  def f(x,y=10,z=20)   f(1,2,3)        (1,2,3)        YES    defaults never applied
 9  def f(x,/,y)         f(1,2)          (1,2)          YES    POSITIONAL_ONLY is safe
10  def f(*,x)           f(1)            TypeError      --     must NOT be swallowed
11  def f(*args)         f(1,2)          ((1,2),)       --     note the nested tuple
```

### Why the naive guard is wrong

A check of the form `if len(args) == len(parameters) and not kwargs: return args` was fuzzed with
each kind-exclusion removed. All three exclusions are load-bearing:

**Dropping `VAR_POSITIONAL` — silent wrong keys, nothing raises.** This is the dangerous one:

```
sig=(*p0)       f(1)      truth=((1,),)     fast=(1,)      <- wrong key
sig=(*p0)       f((1,2))  truth=(((1,2),),) fast=((1,2),)  <- wrong key
```

On a real cells `def vp(*args)`: `vp(1,2)` through the slow path keys as `((1,2),)`, and
`vp((1,2))` through the naive fast path *also* keys as `((1,2),)`. **Two logically distinct calls
alias onto one cache entry** and the second silently returns the first's value.

**Dropping `KEYWORD_ONLY` — swallowed `TypeError`.** On `def ko(x, *, y=5)`, `formula.parameters`
is `('x','y')`, length 2, so `ko(1, 2)` passes an arity check while `sig.bind(1, 2)` raises
`TypeError: too many positional arguments`. An invalid call becomes a valid cache entry.

**Dropping `VAR_KEYWORD` — swallowed `TypeError`**, same shape.

### The guard

Computed once per Formula, O(1) per call. Python's grammar and `inspect.Signature` both enforce
the kind ordering `PO < POK < VAR_POSITIONAL < KEYWORD_ONLY < VAR_KEYWORD`, so checking kinds at
Formula-construction time is enough; per call it is an integer comparison.

Fuzzed to **zero mismatches over 149 distinct signature shapes × 6006 call shapes**.

### How often it engages

Instrumented across all 28 models in the three lifelib-products libraries:

| library | models | bind sites | fast path | hit rate | rejected by guard | by kwargs | by arity |
|---|---:|---:|---:|---:|---:|---:|---:|
| uslib | 12 | 8,400,622 | 8,319,969 | 99.04% | 0 | 0 | 80,653 |
| uklib | 7 | 1,486,414 | 1,470,722 | 98.94% | 0 | 0 | 15,692 |
| jplib | 9 | 6,027,959 | 5,999,730 | 99.53% | 0 | 0 | 28,229 |
| **total** | **28** | **15,914,995** | **15,790,421** | **99.22%** | **0** | **0** | **124,574** |

**Every miss is a default-reliant short call; not one is caused by the signature guard.** The
complete list of non-fast-path shapes across all 28 models is three entries:

```
116,474  (t, kind=None)                                                    called with 1 arg
  4,500  (seg_bal_init, seg_deductions, index_return, conv=None, cap=None)  called with 3 args
  3,600  (index_return, cap=None)                                           called with 1 arg
```

`kwargs`-carrying calls never occur at all in these workloads.

## 4. The patch

### 4.1 `modelx/core/formula.py`

Add `Parameter` to the existing `inspect` import (line 20).

Extend `__slots__` (line 268):

```python
    __slots__ = (
        "func", "signature", "source", "module", "_is_lambda",
        "_bind_tails", "_parameters")
```

Add a single assignment funnel next to `_copy_other`:

```python
    _SIMPLE_KINDS = (
        Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)

    def _set_signature(self, sig):
        """Assign ``signature`` and everything derived from it.

        ``_bind_tails[n]`` is the tuple of default values to append to ``n``
        positional arguments to obtain the trace key, or None when ``n``
        arguments would be a TypeError.  It is None as a whole when the
        signature has any parameter kind the shortcut cannot canonicalise the
        same way ``bind`` does (VAR_POSITIONAL, VAR_KEYWORD, KEYWORD_ONLY).

        Every assignment to ``signature`` must go through here: a stale
        ``_bind_tails`` is a silent wrong-cache-key bug, not a crash.
        """
        self.signature = sig
        params = tuple(sig.parameters.values())
        self._parameters = tuple(sig.parameters)

        for param in params:
            if param.kind not in self._SIMPLE_KINDS:
                self._bind_tails = None
                return

        nparams = len(params)
        nrequired = nparams
        for i, param in enumerate(params):
            if param.default is not Parameter.empty:
                nrequired = i   # defaults are always a trailing run
                break

        self._bind_tails = tuple(
            tuple(p.default for p in params[i:]) if i >= nrequired else None
            for i in range(nparams + 1)
        )
```

Route **all three** `self.signature = signature(...)` assignments through it — line 292 (the
`except OSError:` branch of `__init__`), line 350 (`_init_from_funcdef`), line 367
(`_init_from_lambda`):

```python
        self._set_signature(signature(self.func))
```

`_reload()` (line 392) is **not** a fourth site: it calls `self.__init__(func=...)` and so
re-enters the three above. Verify that still holds if you touch it.

Replace the recomputing property (line 378):

```python
    @property
    def parameters(self):
        return self._parameters
```

### 4.2 `modelx/core/execution/trace.py`

Put the guard inline in `get_node` and leave `_bind_args` **byte-identical** as the slow path, so
"the slow path is unchanged" is assertable by inspection:

```python
def get_node(obj: TraceObject, args, kwargs) -> TraceNode:
    """Create a node from arguments and return it"""

    if args is None and kwargs is None:
        return (obj,)

    # Fast path for the all-positional call, which is >99% of calls in
    # practice.  It must produce the key ``_bind_args`` would produce, or
    # values silently alias in ``obj.data``; ``Formula._bind_tails`` is
    # None for every signature where that is not simply args + defaults.
    if not kwargs and args.__class__ is tuple:
        formula = obj.formula
        if formula is not None:
            tails = formula._bind_tails
            if tails is not None:
                nargs = len(args)
                if nargs < len(tails):
                    tail = tails[nargs]
                    if tail is not None:
                        return obj, args + tail

    if kwargs is None:
        kwargs = {}
    return obj, _bind_args(obj, args, kwargs)
```

Every clause earns its place:

- `not kwargs` covers both `None` (from `CellsImpl.get_value(args, kwargs=None)`) and `{}`
  (`CellsImpl.set_value` passes `{}` explicitly at `cells.py:836`).
- **`args.__class__ is tuple` is not a micro-optimisation — it is a correctness guard.** See §5.
- `formula is not None` preserves today's error text for a formula-less Space: `S[1]` currently
  raises `AttributeError: 'NoneType' object has no attribute 'signature'`. Costs ~15 ns × 15.9M
  ≈ 0.24 s against ~48 s saved. Keep it.
- `nargs < len(tails)` rejects too-many-args; `tail is not None` rejects too-few. Both fall
  through to `_bind_args`, which raises the **same** `TypeError` with the **same** message.
- `args + tail` returns `args` itself when `tail` is `()`, which is >99% of calls.

### 4.3 Leave `node_get_args` alone

A fast path there is possible but pointless: it ran **234 times against 15,914,995 `_bind_args`
calls** in the same sweep — once per ItemSpace creation, from `space.py:1852`.

## 5. Two traps that measurement will not catch

Both were found only by adversarial review; the 15.9M-call workload exercises neither.

**`find_match` passes a LIST, not a tuple.** `modelx/core/cells.py:825-828`:

```python
        masked = [None] * keylen
        for idx in idxs:
            masked[idx] = key[idx]
        value = self.get_value(masked)          # args is a list
```

`keylen == nparams`, so the arity test passes and the guard fires. Returning `args` unchanged
yields a **list cache key**, which blows up as `TypeError: unhashable type: 'list'` at
`obj.data[key]`. Reproduced: stock `Cells.match(1,2,4)` returns
`ArgsValuePair(args=(1,2,None), value=120)`; without the tuple guard it raises. This breaks the
existing 8-case parametrized `modelx/tests/core/cells/test_cells.py::test_match`.

The `args.__class__ is tuple` clause in §4.2 is what prevents it. **Do not "simplify" it away**,
and do not replace `args + tail` with anything that assumes a sized, re-iterable input. Measured
container types over a real run: `{'tuple': 26, 'list': 3}`.

**`ParamFunc.__slots__ = ()` shadows `Formula.__slots__`.** `modelx/core/space.py:66`:

```python
class ParamFunc(Formula):
    __slots__ = ()
```

and `Formula._copy_other` does `for attr in self.__slots__: setattr(self, attr, getattr(other, attr))`.
For a `ParamFunc` instance `self.__slots__` is `()`, so `_copy_other` copies **nothing**.
`UserSpaceImpl.set_formula` (`space.py:1751`) constructs `ParamFunc(formula, name="_formula")`,
and `Formula.__init__` routes a `NullFormula` argument to `_copy_other`. So
`S._impl.set_formula(NULL_FORMULA)` already yields a `ParamFunc` with no attributes:

```
today:   AttributeError: 'ParamFunc' object has no attribute 'signature'
patched: AttributeError: 'ParamFunc' object has no attribute '_bind_tails'
```

Same exception type, different message, private API only, and the object was already broken.
Not a regression — but it violates the design's own invariant ("every assignment to `signature`
goes through `_set_signature`"). Decide deliberately: either fix `_copy_other` to iterate
`Formula.__slots__` explicitly, or document the exception. Do not leave it undiscovered.

## 6. Ruled out — do not spend time on these

- **Caching `Formula.parameters` for speed.** It is read **zero times** during a projection sweep.
  Fold it into `_set_signature` for tidiness as shown, but claim no speedup.
- **`functools.lru_cache` on `_bind_args`** — the key includes unhashable and unbounded argument
  values.
- **Caching bound keys per `(args, kwargs)`** — same problem, plus unbounded growth.
- **Consulting `obj.data` before building the key** — there is no key to look up yet; this is the
  ordering the patch works around rather than changes.
- **Putting the guard inside `_bind_args`** — works identically, but costs one extra Python call
  (~40 ns × 15.9M ≈ 0.6 s) and makes "the slow path is untouched" harder to assert.

## 7. Verification

### 7.1 Correctness

Baseline, already captured on a clean tree — **1218 passed, 6 skipped, 100.93 s**, zero failures:

```
C:/Users/fumito/anaconda3/envs/py313/python.exe -m pytest modelx/tests -q -p no:randomly
```

Any failure after the patch is yours. Pay particular attention to
`modelx/tests/core/cells/test_signature.py` (no_param / single_param / single_param_with_default /
mult_params / mult_params_with_default, plus `TypeError` on too-many and too-few args) and
`modelx/tests/core/cells/test_cells.py::test_match`.

Add a new test module — suggest `modelx/tests/core/cells/test_bind_fastpath.py` — covering, for
each row of the §3 decision table, **both the returned value and the resulting cache key**
(`cells._impl.data` keys, and node identity via `get_node`). It must include:

- all-positional at exact arity, for 0/1/3 parameters
- keyword calls, out-of-order keyword calls, mixed positional+keyword
- defaults called short and called full
- `POSITIONAL_ONLY` (`def f(x, /, y)`)
- `KEYWORD_ONLY` (`def f(*, x)`, `def f(x, *, y)`) — assert `TypeError` still raised
- `VAR_POSITIONAL` (`def f(*args)`) — assert the key is `((1,2),)` and that `f(1,2)` and
  `f((1,2))` do **not** alias
- `VAR_KEYWORD` (`def f(**kw)`)
- too-few and too-many args: same exception type **and message** as before the patch
- `find_match` / `Cells.match` with a masked list
- a Space with `formula is None`, asserting the `AttributeError` text is unchanged

An invariant test is worth more than any of the above: for a set of formulas and calls, assert
`get_node(obj, args, kwargs) == (obj, _bind_args(obj, args, kwargs))` — the fast path must never
disagree with the slow path it is bypassing.

### 7.2 Performance

Prototype A/B over all 28 lifelib-products models (234 model points, 15.9M binds), interleaved
BASE/FAST with the order flipped each rep, hashing every `result_cf()` frame:

**median 170.7 s → 123.0 s, byte-identical SHA-256 digests across all six runs.**

Read the honest caveats before quoting a number:

- **The variance lives in the code being removed.** FAST arms are tight (88.2 / 113.1 / 115.9);
  BASE arms swing 136.7–185.3 (36% spread). The BASE median is the least stable quantity in the
  experiment, so a four-significant-figure percentage is unwarranted. **Quote −20% to −35%, best
  estimate ≈ −30%**, or the drift-immune absolute: ~48–71 s of bind time per 28-model sweep.
- **Per-model percentages below ~3 s are noise.** Do not report `Term_US_A` (2 model points) or
  `IP_UK_S` as signal.
- The prototype parked its analysis on `formula.func.__dict__` because `Formula` is `__slots__`-ed
  and a monkeypatch cannot add a slot. The real patch reads `obj.formula._bind_tails` directly and
  should be ~0.5 s better still.
- **Measure back-to-back in one quiet session.** This machine produced 1.3–2.2× wall-clock
  inflation while sibling work was running. Load-independent operation counts (binds, evals, cache
  hits) are the only figures that survive contention — anchor on those and re-measure timings
  before quoting.

There is a benchmark harness at `C:\Users\fumito\OneDrive\pyproj\modelx-bench`
(`scripts/run_benchmark.py`, `results/`, `docs/`) and pytest-benchmark artefacts under
`modelx/tests/.benchmarks`. Use them for the recorded result.

### 7.3 CI

`.github/workflows/python-package.yml` runs `pytest modelx/tests/` across
**Python 3.9/3.10/3.11/3.12/3.13/3.14 × ubuntu/macos/windows**, with networkx pinned per row
(3.9→2.6, 3.10→2.7, 3.11→2.8, 3.12→3.2, 3.13→3.4, 3.14→3.5). `setup.py` declares
`python_requires='>=3.7'` and classifiers back to 3.7, so the patch must not use syntax newer than
3.7. `Parameter.POSITIONAL_ONLY` exists across all of these; `BoundArguments.arguments` is an
`OrderedDict` on older versions and a `dict` on newer, but `tuple(...values())` is order-correct
either way and the fast path does not touch it.

## 8. Definition of done

- [ ] `_set_signature` added; all three assignment sites routed through it; `_reload` confirmed to
      re-enter `__init__`.
- [ ] `__slots__` extended; `_copy_other` / `ParamFunc` interaction decided deliberately (§5).
- [ ] `get_node` fast path added with all five guard clauses; `_bind_args` byte-identical.
- [ ] `Formula.parameters` reads the cached tuple; no speedup claimed for it.
- [ ] `node_get_args` untouched.
- [ ] New `test_bind_fastpath.py` covering the full decision table plus the
      `get_node == (obj, _bind_args(...))` invariant.
- [ ] `modelx/tests` green at 1218 passed / 6 skipped; `test_match` and `test_signature.py`
      specifically confirmed.
- [ ] A/B re-measured back-to-back in a quiet session; result digests identical; speedup quoted as
      a range.
- [ ] Committed on a topic branch, not `main`.
