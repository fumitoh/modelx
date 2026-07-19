# Dependent Packages: spymx-kernels and modelx-cython

Two packages maintained in sibling repositories depend on modelx. They use the
public modelx API and, in several places, reach into modelx implementation
details. This document catalogs those dependencies so that future changes to
the modelx specification (public API, private helpers, the export/"nomx"
format, and the serializer) can be checked against them.

The catalog was produced by a full audit of both repositories on 2026-07-19,
with every referenced modelx symbol verified to exist (or not) in the modelx
working copy at the snapshot commit below. Line numbers cited here refer to the
snapshot commits and will drift over time.

## Snapshot

| Repository | Local path | Version | Commit (HEAD, main) | Commit date | Remote |
|---|---|---|---|---|---|
| modelx (reference) | `../modelx` | 0.31.1 + 15 commits (`v0.31.1-15-gc2e9a1b`) | `c2e9a1b47282fbecb36ac427fdf869379dbdd847` | 2026-07-19 | https://github.com/fumitoh/modelx |
| spymx-kernels | `../spymx-kernels` | 0.3.0 (tag `v0.3.0` = HEAD) | `a59b8a256ba8438555ed04b5120a24accc24f33e` | 2026-07-03 | https://github.com/fumitoh/spymx-kernels |
| modelx-cython | `../modelx-cython` | 0.0.8 + 4 commits (`v0.0.8-4-gfaa65e2`) | `faa65e29768f7d795146a7fa01b1e71b52d3bb08` | 2025-12-13 | https://github.com/fumitoh/modelx-cython |

Risk ratings used below:

- **low** — public, documented API; normal deprecation policy applies.
- **medium** — semi-public: stable in practice, or documented class on an
  internal import path, or a surface deliberately maintained for a dependent
  (e.g. `_get_attrdict` for spyder-modelx) but without a formal guarantee.
- **high** — private implementation detail or codegen convention with no
  contract; a rename or restructure in modelx breaks the dependent silently.

---

## 1. spymx-kernels

Provides the Jupyter/Spyder kernels used by the spyder-modelx plugin.

**How it depends on modelx:**

- modelx is **not declared** in `setup.py` (`install_requires` lists only
  `spyder-kernels>=1.8.1`). It is a runtime-only dependency: every `mx_*` comm
  handler does `import modelx` lazily inside the function body, so the kernel
  starts without modelx and each handler raises `ImportError` if it is absent.
- There are **two parallel kernel implementations** with the same modelx
  surface: `spymx_kernels/console/kernel.py` (current, comm_handler-based, for
  spyder-kernels 3.x) and `spymx_kernels/console/kernel_5.py` (legacy, for
  Spyder 4/5-era frontends, wired live via `start_kernel.py:79`). **Any
  modelx-side change must be propagated to both files**, or Spyder 5 users
  break silently. Line numbers below cite kernel.py; kernel_5.py has the same
  code at shifted lines.
- The repo has no test suite, so breakage from modelx changes will not be
  caught by spymx-kernels CI.

### 1.1 Public API used (risk: low)

All verified present at the snapshot commit.

| modelx symbol | Representative use (kernel.py) | Usage |
|---|---|---|
| `modelx.new_model` | :92 | create model (also `_get_or_create_model` :253) |
| `modelx.read_model` | :99 | load model from frontend-supplied path |
| `modelx.write_model` | :109 | save model; `backup` passed **positionally** (3rd arg) |
| `modelx.zip_model` | :107 | save as zip; 3 positional args |
| `modelx.get_models` | :107 | name→Model dict lookup (6 sites) |
| `modelx.cur_model` | :253 | default/fallback model (4 sites) |
| `modelx.get_object` (incl. `as_proxy=True`) | :118 | resolve dotted fullnames from the frontend (13 sites); the proxy form returns `ReferenceProxy` — a documented contract |
| `Model.new_space` / `UserSpace.new_space(name=, bases=)` | :130 | create space |
| `UserSpace.new_cells(name=, formula=)` | :227 | create cells from formula string |
| `Cells.set_formula` / `UserSpace.set_formula` | :240 | assign new formula |
| `Model.close` | :142 | delete model |
| `Model.cur_space` | :219 | default parent for new cells |
| `Model.__delattr__` / `UserSpace.__delattr__` | :137 | child deletion via `obj.__delattr__(name)` (equivalent to `del parent.name`) |
| `Cells.node` / `BaseSpace.node` (NodeFactory) | :341 | build Node for MxAnalyzer; also eval'd as text `'{expr}.node{argstr}'` (:523) |
| `Node.preds` / `Node.succs` | :361 | fetched via `getattr(node, adjacency_string)` for the dependency tracer |
| `BaseSpace.spaces` / `.cells` / `.refs` | :187 | iterate children in `mx_import_names` |
| `Cells.__contains__` / `Cells.__call__` | :474 | `args in obj` cache check, then `obj(*args)` |
| `Interface.name` / `Interface.parent` | :146, :177 | variable naming; walking out of ItemSpaces |

### 1.2 Private / implementation-detail surface

This is the load-bearing part. The `_get_attrdict` family plus
`Model._get_from_name` / `Model._get_assoc_values` are effectively a **wire
format consumed by spyder-modelx** — the dict schemas they return are parsed
by the frontend in a separate process.

| modelx symbol | Defined at (modelx, snapshot) | Use (kernel.py) | Risk | Notes |
|---|---|---|---|---|
| `modelx.core.mxsys` (system singleton) | `core/system.py:403`, re-exported `core/__init__.py:15` | :86 (`get_modelx()` returns it to callers) | high | private module-level singleton |
| `Interface._get_attrdict(extattrs=, recursive=)` | `core/base.py:683` | :269 (10 call sites) | medium | the core serialization channel to Spyder; underscore-private but deliberately maintained for spyder-modelx (release notes v0.13.1, v0.16.1, v0.30.1) |
| `BaseNode._get_attrdict` | `core/node.py:92` | :342, :362, :384, :525 | medium | kernel consumes the top-level `'value'` key; `extattrs` is ignored at top level (only nested in `'obj'`) |
| `BaseIOSpec._get_attrdict` | `io/baseio.py:462` (overrides in `io/pandasio.py:273`, `io/excelio.py:570`) | :407 | medium | kernel rewrites its `'value'` key |
| `ReferenceProxy._get_attrdict` | `core/reference.py:209` | :411 | medium | adds `'type'`/`'value_type'` |
| **attrdict dict-schema contract** (keys `'value'`, `'formula'`, `'spec'`, `'refs'`, `'valid'` …) | spread across the above | :315-316, :343, :366, :388, :405-411, :527-528 | **high** | undocumented dict schema used as a wire format; has changed before (`'valid'` added v0.30.1, `'refs'` shape changed v0.16.1); only additive discipline keeps it compatible |
| `Model._get_from_name` | `core/model.py:631` | :126, :217 | high | resolves names relative to a model |
| `Model._get_assoc_values` | `core/model.py:663` | :397 (consumes keys `'value'`, `'spec'`, `'refs'` at :405-411) | high | private method **and** private dict schema built from `_impl.valreg` internals |
| `modelx.core.reference.ReferenceProxy` (class import) | `core/reference.py:132` | :170, :333, :466, :496 (isinstance) | medium | class is autoclass-documented, import path is internal |
| `ReferenceProxy.value`; `.name` via `__getattr__` delegation | `core/reference.py:176-179`, `:169-174` | :180-181 | medium | `.name` only works because `__getattr__` forwards Interface properties |
| `modelx.core.base.Interface` (class import) | `core/base.py:347` | :285 etc. (6 imports; only :467, :497 load-bearing) | medium | isinstance dispatch |
| `modelx.core.cells.Interface` (re-export path) | `core/cells.py:19` (incidental import from base) | :419 | high | works only because cells.py happens to import Interface; **any import cleanup in cells.py silently breaks it** — spymx-kernels should import from `modelx.core.base` |
| `modelx.core.space.ItemSpace` | `core/space.py:2158` | :164 import; attribute-chain `mx.core.space.ItemSpace` isinstance at :176 | medium | interface class stayed in space.py after the Phase-8 refactor (import documented as permanent for pickle compat at space.py:2217-2226); the `mx.core.space` attribute chain must keep working |
| `modelx.core.space.BaseSpace` | `core/space.py:71` | :169 import, :190 isinstance | medium | undocumented base class |
| `modelx.core.parent.BaseParent` | `core/parent.py:23` | :166 import (live branch for modelx > 0.19), :186 isinstance | medium | undocumented base class |
| `modelx.io.baseio.BaseIOSpec` | `io/baseio.py:289` | :426 (live branch for modelx >= 0.20) | medium | this class has been renamed twice already (BaseDataClient → BaseDataSpec → BaseIOSpec), demonstrating the path's volatility |
| `Interface.__repr__` / `BaseIOSpec.__repr__` output | `core/base.py:569` | :429 (`_to_sendval` returns `repr(value)`) | medium | repr string is displayed verbatim in Spyder's MxDataViewer; format changes are user-visible |
| pickling protocol: `Interface.__reduce__` / `__getstate__` / `__setstate__` outside serialization | `core/base.py:580-594` | :482, :501-512 (`cloudpickle.dumps` of values that may contain Interface objects, unpickled in the Spyder frontend process) | **high** | `__getstate__` returns `self._impl`, so the **whole `*Impl` object graph must remain cloudpicklable outside a serialization context** |

### 1.3 Version gates and dead code paths

spymx-kernels branches on the modelx version in two places; the legacy
branches reference symbols that no longer exist in current modelx (harmless
because the gates keep them from executing, but they constrain the version
attributes themselves):

- `mx.VERSION > (0, 19)` (kernel.py:165) selects `modelx.core.parent.BaseParent`;
  the else-branch imports `modelx.core.spacecontainer.BaseSpaceContainer`,
  a module **removed** from current modelx. Requires `VERSION` to stay a
  numeric 3-tuple (`modelx/__init__.py:23`).
- `modelx.__version__` parsed as `int` triples (kernel.py:417-426) selects
  `BaseDataClient` (< 0.18, **gone**) / `BaseDataSpec` (< 0.20, **gone**) /
  `BaseIOSpec` (>= 0.20, live). Requires the first three dot-separated
  components of `__version__` to stay numeric (no `0.32.0rc1`-style segment).

### 1.4 File formats

None directly. Model paths from the frontend are passed straight to
`read_model` / `write_model` / `zip_model`; spymx-kernels never parses
`_system.json`, model directories, or exported packages itself.

---

## 2. modelx-cython

The `mx2cy` toolchain: exports a model with `Model.export()`, traces it,
rewrites the generated sources, and compiles them with Cython.

**How it depends on modelx:**

- Declared in `pyproject.toml` `[project].dependencies` as `"modelx"` —
  **unpinned**, no version bounds. README.md:84 documents "modelx v0.23.0+"
  but that floor is not encoded in package metadata. Since almost all coupling
  below targets the exporter's generated code, any modelx release that changes
  the export layout breaks fresh modelx-cython installs immediately.
- The runtime package (`modelx_cython/*.py`) contains **zero
  `import modelx` statements** — modelx is imported only in tests. All runtime
  coupling is **structural**, against the code that `Model.export()`
  (`modelx/export/exporter.py` + `modelx/export/_mx_sys.py`) generates:
  file names, identifier prefixes, generated method names/signatures, module
  globals, and runtime object internals.
- No version checks or fallback code paths exist anywhere in the package —
  it tracks exactly one exporter output shape.

### 2.1 Public API used (tests only; risk: low)

| modelx symbol | Use | Notes |
|---|---|---|
| `modelx.read_model` | `tests/test_samples.py:27, :59`; every sample `assert_cy.py` | |
| `Model.export` | `tests/test_samples.py:27, :59` | documented (versionadded 0.22.0) but docstring flags the feature **experimental**, so output-format churn is nominally fair game — in practice constrained by everything in 2.2 |
| `modelx.get_models` | `tests/test_samples.py:60` | ⚠ the test does `del mx.get_models()[model]` intending to unload the model — but `get_models()` returns a **fresh dict** each call (`core/api.py`, `get_interface_dict` at `core/base.py:21-22`), so the deletion is a silent no-op. Bug on the modelx-cython side; do not "fix" it from the modelx side by making the dict live. |
| `Space.__getitem__` (itemspaces), `Cells.__call__` | sample `assert_cy.py` files | result comparison against compiled models |
| exported top-level names `mx_model` and `<ModelName>` | sample scripts (`benchmark.py`, `sample.py`) | the one **documented** export-layout promise (`export_model` docstring) |

### 2.2 Export/"nomx" format couplings (the core of the dependency)

These are all conventions of the code generated by
`modelx/export/exporter.py` and the runtime support module
`modelx/export/_mx_sys.py`. None have a compatibility contract; modelx-cython
mirrors them as string constants and templates. **Treat every item here as a
compatibility checklist when touching `modelx/export/`.**

| Exporter convention (modelx side, snapshot location) | modelx-cython side | Risk |
|---|---|---|
| Module file names `_mx_model.py`, `_mx_classes.py`, `_mx_sys.py` (exporter.py:43-45, :75) | `consts.py:26-28` (`MX_MODEL_MOD`/`MX_SPACE_MOD`/`MX_SYS_MOD`), ~15 use sites in cli/tracer/transformer | medium |
| Name prefixes `_mx_` / `_m_` / `_c_` / `_f_` / `_v_` / `_has_` (exporter.py:42-48; transformer.py:153) | `consts.py:17-23`; every parser/transformer/config decision keys off these strings; also user-facing spec-file resolution (`config.py:53-72`) | **high** |
| Generated names `_mx_assign_refs`, `_mx_copy_refs`, `BaseModel`, `_v_space_params_<Space>` (exporter.py:323, :383, :387, :361; _mx_sys.py:41) | `consts.py:30-33`; tracing (`tracer.py:344, :419, :437`) and codegen | **high** |
| `_mx_sys.py` class/attribute layout: `BaseMxObject`/`BaseParent`/`BaseModel`/`BaseSpace` with attrs `_mx_spaces`, `_parent`, `_model`, `_name`, `_mx_is_cells_set`, `_mx_cells`, plus exporter-assigned `_space`, `_mx_itemspaces`, `_mx_roots` (_mx_sys.py:14-107; exporter.py:369, :379, :539) | **`modelx_cython/_mx_sys.pxd`** — a hand-written cdef mirror shipped into every compiled model (`cli.py:90-91`). **The single tightest coupling in either repo**: any attribute added/renamed in modelx's `_mx_sys.py` *or* the exporter's `__init__` templates silently desynchronizes compiled models; no automated check exists on either side | **high** |
| `BaseModel._mx_spaces` dict; `_mx_walk()` generator; `BaseSpace._mx_itemspaces` dict (only initialized when the space has a formula, exporter.py:538-539) | `tracer.py:423, :427, :439` walk the exported model tree | high |
| `_mx_model` module contains exactly one `BaseModel` subclass and one singleton (`mx_model = {name} = _c_{name}()`, exporter.py:299-306) | `tracer.py:418-421` discovers the model class/instance by scanning the module `__dict__` | high |
| Formulas renamed `_f_*`; per-class `_mx_assign_refs`; generated `__call__(self, {params})` for parametrized spaces (transformer.py:153; exporter.py:432) | `tracer.py:334-349` (`MxCodeFilter` profiles by filename suffix + name prefix); `transformer.py:548` | high |
| Refs assigned as plain `self.<ref> = <value>` statements inside `_mx_assign_refs`, nothing else non-underscore assigned there (exporter.py:216-230) | `tracer.py:376-379` treats every non-underscore `__dict__` entry of the traced instance as a ref; `parser.py:144-170` parses the method body lexically | high |
| In a generated space `__init__`, the **only** non-underscore `self.<name> = ...` assignments are child-space instantiations (exporter.py:358-381, :587-597) | `parser.py:139-142` infers child spaces from that pattern (TODO at parser.py:140 asks modelx.export to emit an authoritative child-space list instead) | high |
| Cache-priming assignments `self._v_<cells> = {}` / `= None` + `self._has_<cells> = False` in space `__init__` (exporter.py:519-531) | `transformer.py:411-437` (`remove_cache_assigns`) deletes exactly those | high |
| `_mx_copy_refs(self, base, base_root)` — exact parameter names and arity; class header `_c_{name}(_mx_sys.BaseSpace)` (exporter.py:364, :387) | `transformer.py:62-68` (pxd template), `:472-479` (renames the literal name `base`), `:531-534` (typed cast) | high |
| Child-space path `_m_<Parent>._mx_classes._c_<Child>`; package-dir naming `_m_<Space>` derived from class `_c_<Space>` (exporter.py:47, :94-95, :591-593) | `transformer.py:170-175, :374-380`; `builder.py:327-332` | high |
| `_mx_sys.py` copied verbatim to the exported package root (exporter.py:75) | `cli.py:105` makes `<model>/_mx_sys.py` the first Cython compilation unit | medium |
| Every space subpackage contains `_mx_classes.py` and its `__init__.py` imports it (exporter.py:92) | `cli.py:125` writes `__init__.pxd` with `from . cimport _mx_classes` | medium |
| Traced modules end in `_mx_model` or `_mx_classes` **only** | `cli.py:109` asserts this | high — see the `_mx_macros` gap below |

**Known gap — `_mx_macros`:** modelx commit `e01c237` added a new exported
module kind, `_mx_macros.py` (exporter.py:46, :79-81), imported from the
package `__init__`. modelx-cython predates it and does not know about it. The
`cli.py:109` assert does not fire today only because `MxCodeFilter` never
traces that filename, and the compiled copy carries `_mx_macros` as an
uncompiled plain module — mx2cy with macro-bearing models is untested
territory. Any further new module kinds in the exporter should be checked
against modelx-cython.

### 2.3 Serializer-format couplings (test fixtures)

- Eleven sample model directories under `modelx_cython/tests/samples/`
  (ref_space, array_size, deep_recursion, duplicated_params, index_range,
  nested_params, no_spec, size_spec_change, various_types,
  varying_integral_types_of_args, varying_types_of_args) are committed
  **modelx-serialized models**: `__init__.py` starts
  `from modelx.serialize.jsonvalues import *`, and `_system.json` pins
  `{"modelx_version": [0,27,0] or [0,28,0], "serializer_version": 6}`.
  Every test calls `mx.read_model` on them, so **dropping serializer-v6 read
  support or changing `modelx.serialize.jsonvalues` breaks the entire
  modelx-cython test suite.** (Per the current deprecation plan, loading
  v4-v7 remains supported; only v2-v3 loading is slated for removal.)
- `test_mx2cy_with_lifelib` (`tests/test_samples.py:26-27`) loads models
  created by `lifelib.create('basiclife', ...)` — i.e., models serialized by
  whatever modelx version the installed lifelib release used. This couples the
  test to modelx's backward serializer-read window covering lifelib's
  published models, independent of any symbol usage.

---

## 3. Checklist for future modelx changes

When changing any of the following in modelx, check the listed dependents:

| If you change… | Check… |
|---|---|
| `Interface._get_attrdict` / `BaseNode._get_attrdict` / `BaseIOSpec._get_attrdict` / `ReferenceProxy._get_attrdict`, or any key in the dicts they return | spymx-kernels **and** the spyder-modelx frontend (wire format). Keep changes additive. Both `kernel.py` and `kernel_5.py`. |
| `Model._get_from_name`, `Model._get_assoc_values` (incl. returned dict keys `value`/`spec`/`refs`) | spymx-kernels (both kernel files) |
| `modelx.core.mxsys` name/location; `modelx.core.{base,cells,space,parent,reference}` module layout; class names `Interface`, `BaseSpace`, `BaseParent`, `ItemSpace`, `ReferenceProxy`; `modelx.io.baseio.BaseIOSpec` | spymx-kernels imports these by internal path (isinstance dispatch). Note `modelx.core.cells.Interface` is reached via an incidental import in cells.py. |
| `Interface.__repr__` format; pickling behavior of Interface/`*Impl` objects outside serialization (`Interface.__reduce__`/`__getstate__`) | spymx-kernels (values are cloudpickled to the Spyder frontend; repr strings shown in MxDataViewer) |
| `VERSION` tuple shape or `__version__` string scheme | spymx-kernels version gates (numeric 3-tuple / numeric first three dot-components) |
| **Anything in `modelx/export/`** — file names, `_mx_*`/`_m_`/`_c_`/`_f_`/`_v_`/`_has_` prefixes, `_mx_sys.py` class/attribute layout, generated method names/signatures/bodies, module globals, new module kinds | modelx-cython (`consts.py`, `_mx_sys.pxd`, tracer/parser/transformer/builder/cli). The hand-maintained `_mx_sys.pxd` mirror is the most fragile artifact. |
| Serializer read-compat window (`serializer_version` dispatch), `modelx.serialize.jsonvalues` | modelx-cython test fixtures (v6) and the lifelib-based test |

**Improvement opportunities noted during the audit** (changes on the
dependents' side, recorded here so they are not lost):

- spymx-kernels: import `Interface` from `modelx.core.base` instead of
  `modelx.core.cells`; modelx should not be left undeclared in `setup.py`.
- modelx-cython: `del mx.get_models()[model]` in `test_samples.py:60` is a
  no-op (should use `Model.close()`); the `modelx` dependency in
  `pyproject.toml` should carry version bounds; `parser.py:140` TODO asks
  modelx.export to emit an authoritative child-space list, which would remove
  the most fragile parsing heuristic.
