# Task: Serializer v8 — write IOSpecs as literal tuples instead of pickling them

Repo: the modelx repository (branch off `main`, at or after `a79b7b2`).
Run tests with `python -m pytest`.

## Goal

Add a new serializer version (8) whose writer declares every
`BaseIOSpec` and its parameters as **literal tuples in a central text
file** (e.g. `_data/iospecs.py`) instead of pickling spec objects into
`_data/iospecs.pickle`. Ref sites keep a compact `("IOSpec", …)`
reference and additionally carry the user-supplied constructor
parameters **as a trailing comment** for readability. No spec objects
are pickled; the only pickle left in a saved model is
`_data/data.pickle` (user data values), whose spec-related content is
limited to small `("DataValue", n)` / `("BaseIOSpec", n)` persistent-id
stubs — the same shape v7 emits today.

Motivation: `iospecs.pickle` is the one binary blob in an otherwise
text-first, diffable format; pickled spec metadata has repeatedly
broken (pandas 3 removed `pc.load_reduce` → the tolerant_pickle work;
`BaseIOSpec` renamed twice → compat shims in unpicklers; import paths
are load-bearing). Spec metadata is ~5 literal-friendly fields — pickle
is pure downside for it.

## Current mechanism (v7 = HIGHEST_VERSION), all on main a79b7b2

Version dispatch: `modelx/serialize/__init__.py:14-24`
(`_MX_TO_FORMAT`, `HIGHEST_VERSION`).

Writer (`modelx/serialize/serializer_6.py`, inherited by v7):
- `:368` `iospec_by_value` — `{id(value): spec}` built from
  `model.iospecs`.
- `:380` `assign_id` — deterministic sequential ids (PR #265); ids are
  opaque tokens to readers; first-encounter (traversal) order.
- `:472` `_reorder_io_specs` — puts each model-owned shared IO's
  `_specs` registry in assigned-id order before `write_ios` so
  multi-sheet Excel order survives reloads.
- `:499` `write_pickledata` — dumps `{assigned_id: spec}` to
  `_data/iospecs.pickle` via `IOSpecPickler`, then `pickledata` to
  `_data/data.pickle` via `DeterministicModelPickler`.
- `:884` `IOSpecEncoder` — emits `("IOSpec", value_id, spec_id)`
  literals into `__init__.py` ref sites; puts the value into
  `pickledata`.

Pickle layer (`modelx/serialize/custom_pickle.py`):
- `:10` `IOSpecPickler` — spec objects pickled BY VALUE (class by
  import path, state via `BaseIOSpec.__getstate__` →
  `_on_serialize`).
- `:86/:92/:132` `spec_id` / `data_value_id` hooks +
  `DeterministicModelPickler` — emit `("BaseIOSpec", spec_id)` and
  `("DataValue", spec_id)` persistent ids inside `data.pickle`, where
  `spec_id = assign_id(spec)`, so a DataFrame that is also a cells
  input is stored once and identity survives reload.
- `:164` `ModelUnpickler._find_iospec` — resolves those pids against
  `reader.iospecs` (`{spec_id: spec}`).
- KEY POINT for v8: these pid shapes and hooks can be reused
  UNCHANGED — only where `reader.iospecs` comes from changes (parsed
  literals instead of unpickling).

Reader (`serializer_6.py`):
- `:1119` `read_pickledata` — loads iospecs.pickle FIRST, then
  data.pickle; this order is load-bearing (DataValue pids resolve
  during data.pickle unpickling). v8 replaces only the first half:
  build `{spec_id: spec}` by parsing the literal file — a drop-in
  phase replacement, no pipeline change.
- `:1402` `RefAssignParser.set_instruction` — ref decoders are
  constructed at parse time; `restore()` runs in the
  `__setattr__`/`set_ref` instruction batch.
- `:1767` `IOSpecDecoder` — resolves `("IOSpec", value_id, …)` via
  `find_pickledata`.
- `tolerant_pickle.py` — iospecs-specific salvage paths (unnecessary
  for the v8 format; literal parsing fails per-line and cleanly).

Read pipeline order (`_read_model_inner`, serializer_7.py:287): parse
→ formula/cells batches → `add_bases` → `read_pickledata` →
`load_pickledata` batch → `__setattr__`/`set_ref` batch →
`_set_dynamic_inputs`.

Spec state, per subclass (`_on_serialize` adds to the base state):
- `PandasData` (`modelx/io/pandasio.py:45`, `_on_serialize:183`):
  `read_args`, `squeeze`, `name`, `sheet`; IO carries `path` +
  `persistent_args = {"file_type": …}`. `read_args`/`squeeze`/`name`
  are DERIVED by `_init_spec()` from the live data — see the
  params-schema open decision.
- `ExcelRange` (`modelx/io/excelio.py:253`, `_on_serialize:329`):
  `range`, `sheet`, `keyids`; IO carries `path`.
- `ModuleData` (`modelx/io/moduleio.py:66`, `_on_serialize:111`): no
  extra state; IO carries `path`.
- Base state also has legacy `is_hidden` (v4-era hidden specs) —
  see decision 9.

## Settled design decisions (do not relitigate)

1. **New version 8; v6/v7 untouched.** New module `serializer_8.py`
   subclassing serializer_7/6 machinery. Register in `_MX_TO_FORMAT`
   under the next mx version. Do not modify serializer_1–7 behavior;
   all existing fixtures (v4–v7) must keep loading.

2. **Central literal file, one declaration per spec.** A text file
   under `_data/` (e.g. `_data/iospecs.py`; exact name/grammar open)
   with one `ast.literal_eval`-able tuple per line, e.g.
   `(key, "ClassName", io_params, spec_params)`, written via `ziputil`
   (dir/zip parity for free, like `_dynamic_inputs`). Keys are the
   writer-assigned spec ids — the same `assign_id(spec)` ints that key
   `iospecs.pickle` today — and lines are emitted sorted by key, so
   the file is canonical. Declaring ALL of `model.iospecs` here
   (regardless of ref visibility) means every spec survives the round
   trip, including legacy hidden-ref specs. IO paths are encoded as
   posix strings following the existing `BaseSharedIO` persistent-id
   convention (relative paths relative to the model folder, absolute
   paths as-is).

3. **Ref sites: `("IOSpec", spec_id)` + readability comment.** The
   `value_id` of the v7 shape is DROPPED: a ref site emits exactly
   `("IOSpec", <spec key>)`, and the v8 decoder's `restore()` returns
   the spec's `.value` directly from `reader.iospecs`, so the value no
   longer enters `pickledata` through the ref path at all (values
   referenced from pickled data are still covered by the DataValue
   pids, decision 6). A size-2 tuple rides the same `__setattr__`
   routing as existing `("Pickle", n)` refs — see the size-based
   dispatch in `RefAssignParser.set_instruction`
   (serializer_6.py:1421) — so no new instruction plumbing is needed;
   verify rather than re-derive. Each reference is followed by a
   trailing comment carrying the user-supplied constructor params,
   e.g.
   `pdref = ("IOSpec", 2)  # PandasData path='files/data.csv' file_type='csv' sheet='SheetA'`.
   The comment is writer-generated documentation ONLY: never parsed on
   read, regenerated deterministically on every save (derived from
   spec state in a fixed field order), and must round-trip
   byte-identically. Verify early that `get_statement_tokens` /
   `RefAssignParser` tolerate trailing comments on REFDEFS assignment
   lines (v7 relaxed top-of-file header comments; trailing comments on
   statements need checking — if the tokenizer chokes, fixing that is
   in scope for the v8 parser subclasses only).

4. **Spec classes resolved via a name→class registry** (e.g.
   `"PandasData"` → `modelx.io.pandasio.PandasData`), never by import
   path in the file. Decouples the format from module layout.

5. **Persist constructor params plus load-essential metadata;
   recompute everything else.** Parameters must be
   literal-representable (str/int/float/bool/None/tuple/list/dict) — a
   permanent contract for future spec types. The writer emits params
   in a FIXED field order per class so the text is canonical. See the
   params-schema open decision for the per-class audit method.

6. **Pickle layer reused unchanged.** `data.pickle` keeps v7's pid
   shapes — `("DataValue", spec_id)` / `("BaseIOSpec", spec_id)` with
   `spec_id = assign_id(spec)` — so `DeterministicModelPickler`'s
   hooks and `ModelUnpickler._find_iospec` are inherited as-is. The v8
   `read_pickledata` override builds `reader.iospecs = {key: spec}` by
   parsing the literal file (registry class +
   `IOManager.get_or_create_io` + `_on_unserialize`-style init, which
   loads the value), then loads data.pickle exactly as today. No
   parse-time side channels, no ordinal invariants, no content-dedup —
   keys make spec identity explicit, so two refs sharing one spec
   trivially resolve to the same object.

7. **Journal and tolerant obligations carry over.** Set
   `reader.io_journal_mark` before constructing specs (mirroring
   `IOSpecUnpickler.__init__`) so a failed load rolls back registered
   IOs/specs (PR #256/#257 error-path behavior). A missing or
   unloadable IO file → `UserWarning`, ref restored as None, key
   recorded as lost so `_find_iospec` degrades too, no orphan
   IOs/specs (match `test_tolerant_unpickle.py` /
   `test_read_error_cleanup.py` expectations). A malformed literal
   line fails cleanly per-line.

8. **Determinism is a hard requirement.** v8 must pass the
   byte-identical no-op save→load→save contract, including the
   ref-site comments. Reuse `assign_id` / `iospec_by_value`; emit the
   literal file sorted by key. Extend
   `modelx/tests/serialize/test_deterministic_output.py`
   parametrization to version 8.

9. **`_reorder_io_specs` stays** (or an equivalent): a v8 reload
   registers specs in literal-file key order, while a building session
   registers them in creation order, so multi-sheet books still need
   the writer-side reorder. Hidden-ref legacy specs survive via the
   central file (decision 2), but the `is_hidden` flag itself is
   DROPPED: v8 files carry no such field, and a formerly hidden spec
   reloads as an ordinary one (`_is_hidden` False; the v4-era
   `_mx_dataclient` attachment in `_read_pandas` no longer triggers).

10. **Dependent packages**: consult `devnotes/DependentPackages.md`
    before finalizing. modelx-cython's exporter calls `_on_serialize`
    directly — keep that hook working (or coordinate an exporter
    change). spyder-modelx uses runtime paths (`_get_attrdict`,
    runtime pickling via `_on_pickle`) — must remain untouched.

## Open decisions (settle during design, document the choice)

- **Ref-site comment format** (fixed field order per class; keep it
  stable across releases since comments participate in byte
  identity).
- **Params schema per class** — the audit method: classify every field
  of the current pickled state as (a) user-supplied constructor param
  → persist; (b) derived and recomputable from the IO file → omit;
  (c) derived at save time but load-essential and NOT recoverable from
  the file → persist in a version-independent form. Category (c) is
  the crux for `PandasData`: `read_args`/`squeeze`/series-`name` are
  needed to parse the file before the data exists (a one-column
  DataFrame and a Series produce identical CSV). Recommended: persist
  shape metadata (`index_nlevels`, `columns_nlevels`, `is_series`,
  series `name`) and recompute `read_args` from it on load the way
  `_init_spec()` does (engine from path suffix, sheet_name from
  `sheet`), rather than persisting the raw pandas-API dict. Expected
  outcome: PandasData io_params `{path, file_type}` / spec_params
  `{sheet + shape metadata}`; ExcelRange `{path}` /
  `{range, sheet, keyids}`; ModuleData `{path}` / `{}`. NOTE:
  `PandasData.name` is the pandas Series name, not the ref name from
  `new_pandas(name=...)` — the ref name lives at the ref site and must
  not be duplicated.
- **Exact file name and line grammar** of the central literal file.

## Constraints

- No changes to serializer_1–5, and no behavior changes to v6/v7
  writers/readers. All existing fixtures (v4–v7) must still load;
  full suite must pass.
- v8 files will not load on older releases (expected — version
  dispatch). Verify the failure on an unknown version is a clean
  error, not a stack-trace surprise (see `_get_serializer`).
- Follow conda-only package rules in the global CLAUDE.md if anything
  needs installing.

## Suggested approach

1. Write the literal-file grammar, the registry, and the comment
   format into the `serializer_8.py` module docstring first.
2. Writer: subclass v7 `ModelWriter`; override `write_pickledata` to
   write the literal file (sorted by `assign_id(spec)`) instead of
   iospecs.pickle; replace `IOSpecEncoder` with one emitting the
   compact reference + params comment. The pickler hooks are inherited
   unchanged.
3. Reader: subclass v7 `ModelReader`; override `read_pickledata` to
   build `reader.iospecs` from the literal file (journal mark,
   per-line tolerant handling) before loading data.pickle; new
   `IOSpecDecoder` for the ref-site shape; make the v8 parser
   subclasses tolerate trailing comments if the shared tokenizer does
   not already.
4. Wire version 8 into `modelx/serialize/__init__.py`.
5. Tests (beyond the determinism rows): round-trip equivalence for all
   three spec types (pandas csv + multi-sheet excel, ExcelRange,
   ModuleData); TWO refs sharing one spec's value — identity preserved
   after reload; an iospec value that is also a cells input (DataValue
   path); a hidden-ref spec surviving the round trip as an ordinary
   spec (is_hidden dropped per decision 9); missing IO file
   and malformed literal line (warning + None + no orphans); ref-site
   comments identical across a no-op round trip; a v8 fixture in the
   `serializer_compat` pattern; full suite green.
6. Adversarially review before finalizing (comment tolerance in the
   parser, tolerant paths, dependent-package hooks, determinism).

## Out of scope

- Removing or deprecating v6/v7 writers, migrating existing models
  (they load via old readers and resave as v8 naturally),
  write-if-identical/mtime optimizations, spyder-modelx/modelx-cython
  changes.

## Deliverable

A feature branch with serializer_8 + tests, PR-ready against `main`,
with the literal grammar and comment format documented in the module
docstring and a summary of the design decisions taken on the open
points above.
