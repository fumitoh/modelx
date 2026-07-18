# modelx Core Refactoring — Target Architecture & Phased Roadmap

- Status: **Implemented — all phases (0–8) merged to main as of 2026-07-17.** Written 2026-07-12 against commit `e71cbd6` (v0.31.1 + a few commits); see revision notes below for as-implemented deltas.
- Revision 2026-07-13: **D-7 reversed — all mixins stay** (no mixin→component conversions). Old Phase 2 (TraceManager component) replaced by the self-observation fix (D-12); old Phase 7 (BaseSpaceImpl decomposition) dropped; selective invalidation is now Phase 7, file split Phase 8.
- Revision 2026-07-15: **serializer compatibility narrowed** (user decision). Serializers 2–3 are being deprecated for *loading* and 2–5 for *writing* (in a separate session, independent of this refactoring). The saved-model compatibility surface for this refactoring is therefore **loading serializer_4–7 only**. (Phase 0 had found the serializer_2/3 readers already broken on master — `UserSpaceImpl.new_cells` gone; deprecation supersedes fixing them.)
- Revision 2026-07-17 (Phase 7 as implemented): five refinements to §5.8. (1) **Granularity is per itemspace**, not per parent: itemspace I is cleared iff `dirty_spaces ∩ closure(I) ≠ ∅` with `closure(I)` = I's recorded tree dynbases + their MRO bases + the parent's nearest static UserSpace. The `*_nukes_at_parent` characterization tests flipped accordingly. (2) **Two dirty buckets**: `ChangeSet.dirty_spaces` (namespace-binding changes; intersected with the full closure) and `ChangeSet.dirty_bases` (formula changes/renames via `txn.mark_dirty_base`; intersected with the recorded dynbases only) — preserving the per-dynbase selectivity that `clear_subs_rootitems` gave formula/rename edits, including for the edited space's own itemspaces built on foreign dynbases. (3) The new `ItemSpaceImpl` slot (`tree_dynbases`) records **impl references, not idstr strings** — idstrs and MRO are resolved at invalidation time, so the closure follows renames of base spaces instead of going stale. (4) `DelSpace` now records the removed spaces in `dirty_spaces` (via `add_removed_space`), fixing an under-clearing hole where itemspaces built on a deleted space survived with a dangling dynbase. (5) **Cross-model invalidation** goes through the dirty spaces' `_dynamic_subs` back-pointers (idstrs are model-relative, so closure intersection is only valid within one model); root itemspaces of other models built on dirty spaces are cleared per root. `ChangeSet.cleared_subs`/`clear_subs_rootitems`/`DynamicBase.on_notify`/`on_namespace_change` are removed (subsumed/dead). Known pre-existing hole left for later: deleting a space does not delete the deleted space's *own* live itemspaces (their trace nodes linger); unchanged from before Phase 7.
- Revision 2026-07-17 (Phase 8 as implemented): `DynamicBase`/`DynamicSpaceImpl`/`ItemSpaceImpl` moved to new `core/dynamic.py`; the `DynamicSpace`/`ItemSpace` *interface* classes stay in `space.py` but are relocated above `UserSpaceImpl`, and `space.py` imports the moved impls mid-module right before `UserSpaceImpl` (which inherits `DynamicBase`) — that import is the permanent pickle alias (`modelx.core.space.ItemSpaceImpl` etc. resolve forever). One mechanical change in the moved code: `DynamicSpaceImpl._init_allargs` looks up `UserSpaceImpl` through the space module object at runtime. Alias retirement: `model.py` keeps `SpaceGraph` and `SpaceManager` only (pickle-relevant — `spmgr` is a slot of every pickled Impl, the graph lives inside it); the eight idstr node-helper aliases, `SharedSpaceOperations`, and `ReferenceManager` (incl. the `refs.py` alias) are deleted. `modelx/managers` deleted together with its only consumer `modelx/tests/managers`; `core/members/` (untracked pycache remnant) deleted; `core/inheritance/__pycache__` contained only current-module caches by this point — nothing stale left to remove.
- Revision 2026-07-17 (follow-up): **space-deletion itemspace hole closed** — the known hole flagged at the end of the Phase 7 note above (pre-existing on master; deliberately kept out of the phase diffs to keep them behavior-parity-focused). Deleting a UserSpace (`DelSpace` in `edit/pipeline.py`) never deleted the deleted space's *own* live itemspaces: `UserSpaceImpl` inherits `BaseSpaceImpl.on_delete`, which clears cells but not itemspaces (unlike `DynamicSpaceImpl.on_delete`), and `ItemSpaceManager.invalidate` enumerates only live spaces (`model.yield_spaces()`) — so the removed space's `param_spaces` entries, their `(parent, key)` nodes in `model.tracegraph`, and their entries in their dynbases' `_dynamic_subs` lists lingered. Fixed in `ModelEditor._finalize`: removed spaces get `del_all_itemspaces()` in the trace-invalidation stage, before any `on_delete`, while the whole removed tree is still alive — the deletion still flows through the frozen `clear_with_descs → on_clear_trace → _del_itemspace` contract. Behavior elsewhere unchanged; regression tests in `tests/core/space/test_delattr.py`.
- Revision 2026-07-18 (post-completion cleanup): **`SharedSpaceOperations` merged into `SpaceManager`** (`core/inheritance/manager.py`). After Phase 6 retired `SpaceUpdater`, the base class had a single subclass and the split was vestigial. Pure mechanical merge (methods verbatim); safe for pickles because pickle records only the concrete class (`SpaceManager`, as `Impl.spmgr`) and base classes are never recorded; nothing imported or isinstance-checked the base class.
- Purpose: self-contained guide for executing the refactoring one phase per session. A session picking up any phase should need only this document plus the source tree.
- Line numbers below refer to the tree as of the commit above; re-verify before editing, but the structural claims were all confirmed against source when this was written.

## 1. Scope and ground rules

The refactoring covers five concern areas of `modelx/core`:

1. Component & inheritance management (create/delete/rename/copy of spaces/cells/refs; base-space relationships)
2. Namespace management (per-space namespaces in which formulas evaluate)
3. Formula evaluation & calculation tracing
4. Reference management (external-value identity tracking, IO specs)
5. Dynamic (item) space management

Ground rules (user-confirmed):

- **Public Python API preserved.** `modelx.*` functions and the Model/Space/Cells/ReferenceProxy interfaces keep working as documented. One approved spec change: **selective ItemSpace invalidation** (§5.8, Phase 7) — ItemSpaces survive edits to unrelated spaces.
- **Saved-model compatibility.** Models written by `serializer_4`–`serializer_7` must still load (2–3 deprecated for loading, 2–5 for writing — revision 2026-07-15). Note: serializers never write Impl classes by module path (`Interface.__reduce__` reduces to an idtuple during serialization, `base.py:557`), so *moving classes between modules is safe for saved models*. Runtime pickling of live models does record module paths, so `model.py` must keep import aliases for every moved class (pickle-relevant aliases are permanent).
- **External-tool compatibility.** `modelx/export` and spyder-modelx internal touchpoints keep working or get an explicit migration step. See §3 for the exact compatibility surface.
- Each roadmap phase is independently executable and leaves `pytest modelx/tests` green.

Ignore `modelx/managers` (unused sketch) — it is *not* the starting point for any of this; it should eventually be deleted. The `modelx/core/inheritance/` and `modelx/core/members/` directories exist but contain only stale `__pycache__` remnants of an earlier attempt; `inheritance/` is reused by this design, `members/` gets deleted (Phase 8).

## 2. Current architecture (with evidence)

### 2.1 Components & inheritance

- `ModelImpl` (`model.py:1164`) = `TraceManager + EditableParentImpl + Impl` mixins. Owns `spmgr` (SpaceManager), `refmgr` (ReferenceManager), `_global_refs`, `named_spaces`. The `updater` property creates a **new `SpaceUpdater` per access**, each copying the full inheritance graph (`model.py:1259–1261`).
- `SpaceManager` (`model.py:1708–1945`): mutations that do not touch the inheritance graph (rename, new/del cells, new/change/del ref, copy_cells, sort_cells). Owns `_graph` = `SpaceGraph`, a `networkx.DiGraph` subclass: nodes keyed by space idstr (dotted path), edges base→derived with an `index` attribute for base ordering, C3 linearization via `get_mro`, relative-path resolution via `get_relative` (`model.py:1451–1569`).
- `SpaceUpdater` (`model.py:1947–2238`): graph-touching mutations (`new_space`, `add_bases`, `remove_bases`, `del_defined_space`, `copy_space`). Pattern: copy `manager._graph` → mutate the copy → queue `Instruction` objects in an `InstructionList` → execute → `_update_manager()` swaps the graph back.
- `SharedSpaceOperations` (`model.py:1607–1706`): shared base of both; `get_deriv_bases` resolves bases of cells/refs by walking the parent space's MRO and matching member names.
- `Derivable` mixin (`base.py:264`) on CellsImpl/ReferenceImpl: `_is_derived` flag; `bases` computed on demand via `spmgr.get_deriv_bases` (`base.py:286`).
- Inheritance sync via `on_inherit` callbacks: `UserSpaceImpl.on_inherit` (`space.py:2413–2459`) reconciles `cells`/`own_refs` against a `CustomChainMap` of the bases' dicts; `CellsImpl.on_inherit` (`cells.py:753`) copies formula/allow_none/is_cached from `bases[0]`; `ReferenceImpl.on_inherit` (`reference.py:80`) recomputes relative/absolute values. `update_subs` broadcasts `on_inherit` to all descendants per mutation, unbatched.

**Load-bearing subtlety — two-phase inheritance order.** `InstructionList.execute` (`model.py:1596–1604`) iterates a plain list while `_update_derived_space` (`model.py:1960–1966`) *appends* `_update_derived_refs` instructions mid-iteration. The emergent effect: all `cells` syncs across the affected subgraph run before all `own_refs` syncs. Relative-reference resolution depends on target spaces already existing when refs are derived. Any replacement pipeline must preserve this ordering **explicitly**.

### 2.2 Namespaces & binding

- `NamespaceServer` (`core/binding/namespace.py:31–83`): mixin on `BaseSpaceImpl`; lazily rebuilds `_ns_dict` via `on_update_ns` (`space.py:2007–2018`: spaces→namespace objects, refs→interfaces, cells→bound `call` methods); `_is_ns_updated` cache flag.
- `Subject`/`Observer` (`base.py:703–746`). `AlteredFunction` (`core/binding/boundfunc.py:47–123`) rebinds formula code objects to `ns_dict` as `FunctionType` globals, lazily; extracts `LOAD_GLOBAL` names from bytecode. Mixed into **both** `BaseSpaceImpl` (observing itself — see the identity dispatch in `BaseSpaceImpl.on_notify`, `space.py:2000–2005`) and `CellsImpl` (observing its parent space).
- Invalidation is **manual**: every mutation site must call `space.on_notify(<dict>)` explicitly (`space.py:2465/2517/2524`, `cells.py:696`, …). Missing a call silently leaves stale namespaces.
- `ModelImpl` has no NamespaceServer; it uses `CustomChainMap(named_spaces, _global_refs)` (`model.py:1204`).

### 2.3 Execution & tracing

- `TraceManager` (`core/execution/trace.py:175–286`): mixin on ModelImpl; owns `tracegraph` (nodes are `(traceobj, key)` tuples) and `refgraph`. API: `clear_with_descs`, `clear_obj`, `clear_attr_referrers`. Clearing calls `node[OBJ].on_clear_trace(key)` in postorder — this callback contract with CellsImpl and ItemSpaceParent is **frozen**.
- Executor (`core/execution/executor.py`): `NonThreadedExecutor`/`ThreadedExecutor` lives on `System` (`system.py:75`); `CallStack.pop()` writes tracegraph/refgraph edges; the executor *borrows* `model.tracegraph`/`refgraph` only during `_start_exec`.
- `CellsImpl.on_eval_formula` uses `altfunc`; cached values in `CellsImpl.data`, user inputs tracked in `input_keys`.

### 2.4 References & IO

- `ReferenceImpl` (`reference.py:27–108`): `refmode` absolute/auto/relative; `is_relative` flag.
- `ReferenceManager` (`model.py:2240–2389`): `_valid_to_refs`: `id(value) → [ReferenceImpl]`. Its `new_ref`/`del_ref`/`change_ref` isinstance-dispatch **back into** `spmgr` or `ModelImpl` (`model.py:2278–2344`) — circular. Manages IOSpec lifecycle against `System.iomanager` (`io/baseio.py:140`; `BaseIOSpec` hooks `_on_serialize`/`_on_unserialize`/…). Registry-update calls are scattered: `model.py:1296–1315`, `reference.py:82`, `space.py:2506/2521`.

### 2.5 Dynamic spaces

- `ItemSpaceParent` mixin (`space.py:1706–1876`): `_named_itemspaces`, `param_spaces`, `dynamic_cache` (WeakValueDictionary), param `formula`; `get_itemspace` → `executor.eval_node` → `on_eval_formula` creates `ItemSpaceImpl`; `on_clear_trace` → `_del_itemspace`.
- `DynamicSpaceImpl` (`space.py:2576–2725`): `_dynbase`, `_allargs`, `rootspace`, `_dynbase_refs`; `wrap_impl` (`space.py:2649–2686`) re-resolves relative refs inside the dynamic subtree (multi-branch refmode logic). Namespace = `CustomChainMap(*_allargs.maps, own_refs, sys_refs, _dynbase_refs, model._global_refs)`.
- `ItemSpaceImpl` (`space.py:2786–2843`): binds args, recursively builds dynamic children.
- `DynamicBase.on_notify` (`space.py:2140–2145`): on **any** namespace change, deletes **all** itemspaces of every dynamic sub's root. ItemSpace deletion flows through the trace graph: `clear_with_descs` → `on_clear_trace` → `_del_itemspace` → `on_delete`.

## 3. Compatibility surface (verified by grep — do not break)

**Serializers** (`modelx/serialize/serializer_*.py`) read/write, at Impl or interface level:
`space._named_itemspaces` (interface property, `space.py:317`), `cells._impl.input_keys`, `cells._impl.data`, `cells._impl.set_value`, `cells._impl.source`, `obj._impl.has_node`, `parent._impl.refs[key].is_derived()`, `parent._impl.is_model()`, `ModelImpl._global_refs`, `BaseSpaceImpl.own_refs`. These names must keep working as attributes or properties.

**Export** (`modelx/export/exporter.py`) reads only interface-level `spaces`/`cells`/`refs`, `Formula.source`, and `_named_itemspaces` naming in generated code — no deeper impl coupling.

**spyder-modelx** surface: `Interface._baseattrs`, `_get_attrdict` (incl. `extattrs=["get_referents", ...]`), `_get_object`, `_evalrepr`, `_impl.system`, `system.callstack` (including `TraceableCallStack` swapping), `Model.tracegraph` (interface property, `model.py:582`). Tests also poke `model._impl.tracegraph` (`tests/core/model/test_model.py:85`).

**Frozen contracts:** `on_clear_trace(key)` postorder callback; trace-node identity `(impl_obj, key)` where the OBJ for itemspace nodes is the space impl itself.

**Direct internal call sites worth knowing:** `parent.py:832` calls `space.spmgr.new_cells` directly; `parent.py:119`, `model.py:1309`, `space.py:2352` use `model.updater`.

## 4. Verified problem inventory

1. **Fragile transactions.** Only `new_space` attempts rollback, and it is partial: `del parent.named_spaces[name]` (`model.py:2078–2082`) while orphan graph nodes and partially-created members survive. `add_bases`/`remove_bases`/`del_defined_space` have **no** rollback. Additionally, `remove_bases` and `del_defined_space` iterate descendants from the **old** graph (`self.manager._graph`, `model.py:2156, 2177`) while mutating the copied graph — a latent inconsistency.
2. **Unclear state ownership.** Component dicts are mutated by managers, by `on_inherit`, *and* by constructors: `container[name] = self` in `BaseSpaceImpl.__init__` (`space.py:1989`), refs created inside the same constructor (`space.py:1994–1997`), `space.cells[name] = self` in `CellsImpl.__init__` (`cells.py:695`), `ReferenceImpl(set_item=True)`. Graph ownership is split between SpaceManager and per-operation SpaceUpdater copies.
3. **No unified mutation pipeline.** `on_notify` / refmgr updates / `clear_attr_referrers` / `del_all_itemspaces` / `update_subs` are hand-sprinkled per mutation site. Notification cost is O(members × descendants) per edit, unbatched.
4. **Mixin entanglement.** `BaseSpaceImpl(NamespaceServer, ItemSpaceParent, BaseParentImpl, Impl)` plus `AlteredFunction`; identity dispatch in `on_notify`; `AlteredFunction` duplicated on spaces and cells; `TraceManager` state on ModelImpl but populated by System's executor.
5. **Circular managers.** ReferenceManager dispatches back into spmgr/ModelImpl.
6. **Over-broad invalidation.** Any namespace change nukes all itemspaces (`space.py:2140`); every mutation broadcasts `on_inherit` to all descendants.
7. **Duplicated derived-member creation.** `SpaceManager.new_cells` fan-out (`model.py:1765–1786`, incl. the subtle `cells_after` reorder) vs `UserSpaceImpl.on_inherit` reconcile (`space.py:2413–2459`).
8. **id()-keyed ref registry** relies implicitly on refs keeping values alive; sanity depends on an unstated invariant.

## 5. Target architecture

### 5.1 Package layout (`modelx/core/`)

```
base.py                 # Impl, Interface, Derivable, Subject/Observer (unchanged home)
model.py                # Model interface + ModelImpl ONLY (~600 lines after split);
                        # import aliases for every moved class (pickle compat)
space.py                # Space interfaces + BaseSpaceImpl/UserSpaceImpl
dynamic.py       (new)  # DynamicSpaceImpl, ItemSpaceImpl, DynamicBase (Phase 8, optional)
cells.py                # Cells interface + CellsImpl
reference.py            # ReferenceImpl, ReferenceProxy
parent.py               # BaseParent(Impl), EditableParent(Impl)
inheritance/            # inheritance domain (dir exists as pycache remnant — clean & reuse)
    graph.py            # SpaceGraph (nx.DiGraph subclass), C3 MRO, get_relative,
                        # ALL idstr node-string helpers (split_node, has_parent, trim_*)
    manager.py          # InheritanceManager: owns THE graph; query API
    sync.py             # InheritanceSync: the ONLY place derived members are
                        # created/updated/removed
edit/            (new)  # unified mutation pipeline
    pipeline.py         # ModelEditor, Edit command classes, ChangeSet
    transaction.py      # Transaction (undo journal + shadow-graph commit)
refs.py          (new)  # ValueRegistry (ReferenceManager successor) + IOSpec hooks
itemspaces.py    (new)  # ItemSpaceManager (per-model itemspace invalidation policy)
binding/                # namespace.py (NamespaceServer),
                        # boundfunc.py (AlteredFunction mixin — unchanged home)
execution/              # trace.py (TraceManager mixin — unchanged home),
                        # executor.py (unchanged; stays on System)
```

### 5.2 State ownership map

| State | Current owner / mutators | Target owner | Mutated only by |
|---|---|---|---|
| Inheritance graph | `SpaceManager._graph` + throwaway per-op copies | `InheritanceManager.graph` (one instance, `model.inheritance`) | `Transaction.commit()` (shadow-copy swap); reads via query API |
| Component dicts (`named_spaces`, `cells`, `own_refs`) | Spaces, but mutated by managers, `on_inherit`, constructors | **Stay on spaces** (dict identity preserved — serializers, pickling, and ChainMaps hold these dicts) | Pipeline apply/derive stages; constructors become side-effect-free |
| Trace graphs | ModelImpl via TraceManager mixin | Unchanged (TraceManager mixin on ModelImpl) | Executor (borrowed during eval), pipeline finalize |
| Ref value registry | ReferenceManager, updated from 3 scattered paths | `model.valreg` = ValueRegistry; entries hold `(value, [refs])` **strongly** | Pipeline bookkeeping stage only |
| IOSpec lifecycle | ReferenceManager ↔ System.iomanager | ValueRegistry emits register/unregister; IOManager unchanged | Pipeline bookkeeping stage |
| Itemspace containers | ItemSpaceParent mixin state per space | Unchanged (ItemSpaceParent mixin state; attribute names untouched); the invalidation *policy* moves to `ItemSpaceManager` per model | Executor (creation), TraceManager (`on_clear_trace` deletion), pipeline finalize |
| ns_dict / bound-formula caches | NamespaceServer + AlteredFunction mixins, hand-invalidated | Unchanged mixins; space self-observation replaced by a direct hook (D-12, §5.9) | Flag-flip via the direct hook + Subject/Observer edges, driven by the pipeline notify stage |

### 5.3 Mixins retained (revised decision, 2026-07-13)

**All existing mixins stay mixins** — including `TraceManager`, `ItemSpaceParent`, and `AlteredFunction`, which an earlier draft converted to components. Reasons:

- **Dynamic-path cost.** Every cells — including every `DynamicCellsImpl` created per itemspace — carries `AlteredFunction` state. As a separate component object that is a ~64-byte GC-tracked allocation per cells (tens of MB and on the order of 10^6 extra objects at lifelib scale) plus one extra pointer hop on the hottest read in the system (`altfunc`, read on every formula call). Inline mixin slots avoid both.
- **Pickle/slots stability.** No `__getstate__`/`__setstate__`/`get_mixin_slots` churn; pickled-state key names untouched. This removes what was the riskiest part of the old decomposition phase.
- **One idiom.** The codebase keeps a single structural pattern (`__slots__` + `get_mixin_slots`) instead of half mixins, half components.

What replaces the benefits composition was buying:

- **Ownership discipline comes from the pipeline, not from object boundaries.** After migration, mixin state (trace graphs, itemspace containers, namespace/altfunc caches) is mutated only by the executor (during eval) and the pipeline stages (§5.4). The grep-able rule in §5.4 is the enforcement mechanism.
- **The self-observation wart is fixed directly** (D-12, §5.9, Phase 2): `BaseSpaceImpl` no longer registers itself in its own observer list; `NamespaceServer.on_notify` invokes a direct same-object hook instead. The identity dispatch at `space.py:2000–2005` disappears without any component.

The only new manager-like object is `ItemSpaceManager` (per-model invalidation *policy*, §5.8) — new state with a new owner, not a conversion of existing mixin state.

### 5.4 Unified mutation pipeline

One long-lived `ModelEditor` on ModelImpl replaces the SpaceManager-dispatch / per-op SpaceUpdater / ReferenceManager-dispatch triangle.

```python
# modelx/core/edit/pipeline.py
class ChangeSet:
    created:  list[Impl]          # new cells/refs/spaces (incl. derived)
    removed:  list[Impl]          # impls taken out of containers (not yet finalized)
    modified: list[Impl]          # formula changed, ref rebound, ...
    dirty_containers: set[tuple[parent_impl, str]]   # ('cells'|'own_refs'|'named_spaces'|'global_refs')
    dirty_spaces: set[str]        # idstrs of mutated spaces + inheritance closure

class Edit:                        # one subclass per mutation
    def validate(self, model, txn): ...   # name/cycle/MRO/relref checks; NO state change
    def apply(self, model, txn): ...      # structural writes, journaled via txn
    # derive/notify/invalidate are generic pipeline stages, not per-Edit

class ModelEditor:
    def execute(self, edit):
        txn = Transaction(self.model.inheritance)   # lazy shadow graph + undo journal
        try:
            edit.validate(self.model, txn)
            edit.apply(self.model, txn)             # dict writes via txn.set_item/del_item (auto-journal)
            self.model.inheritance.sync.derive(txn) # phase A: 'cells' over affected subs (topo order)
                                                    # phase B: 'own_refs' over affected subs
        except BaseException:
            txn.rollback()                          # reverse-replay journal; drop shadow graph
            raise                                   # model is bit-identical to before the edit
        txn.commit()                                # swap shadow graph in; freeze ChangeSet
        self._finalize(txn.changes)                 # post-commit; cannot fail the edit
        return edit.result

    def _finalize(self, ch):
        # 1. trace invalidation: clear_obj / clear_attr_referrers for removed+modified
        # 2. finalize deletions: impl.on_delete() (NullImpl) for removed
        # 3. batched notify: exactly ONE on_notify per dirty container
        # 4. ValueRegistry / IOSpec bookkeeping (register/unregister/rebind, spec GC)
        # 5. ItemSpaceManager.invalidate(ch)        # pluggable policy (see §5.8)
```

Design commitments:

- **Ordering preserved.** `derive` keeps the two-phase order (all `cells` before all `own_refs` across the affected subgraph) that today emerges implicitly from the self-appending InstructionList.
- **Batched notification.** One `on_notify` per dirty container replaces per-member-per-space notification storms; the existing lazy `_is_ns_updated`/`is_altfunc_updated` flags do the rest.
- **Validation is pure.** All `_can_add`, cycle, MRO-feasibility, name-conflict, and `_check_subs_relrefs` checks run against the shadow graph *before* any dict write.
- **Rollback is real.** The Transaction journals every container write (`set_item`/`del_item`/`move_item`) and impl-attribute change routed through it (e.g. `ReferenceImpl.on_inherit`'s interface rebinding becomes `txn.set_attr(ref, 'interface', v)`). On exception: reverse-replay; no notify/trace/registry actions have run.
- **Grep-able rule after migration:** no `on_notify` calls outside `edit/pipeline.py` and `Subject.notify`.

### 5.5 Facades (permanent compatibility)

- `ModelImpl.spmgr` remains: a query facade over `InheritanceManager` plus thin `new_cells/new_ref/...` methods that construct Edits and call `editor.execute`. (Every Impl carries `spmgr`; `Derivable.bases` calls `spmgr.get_deriv_bases`, `base.py:286`; `parent.py:832` calls `spmgr.new_cells`.)
- `model.updater` becomes a property returning the same facade (exposing `new_space/add_bases/remove_bases/del_defined_space/copy_space`).
- `model.refmgr` aliases `model.valreg`.
- `ModelImpl.tracegraph/refgraph/clear_*` unchanged (TraceManager mixin members); `Model.tracegraph` interface property untouched.
- Impl attrs `_named_itemspaces`, `param_spaces`, `named_itemspaces`, `dynamic_cache`, `formula`, `altfunc`, `global_names`, `input_keys`, `data`, `own_refs`, `_global_refs` unchanged (mixins retained — no property shims needed).

### 5.6 Inheritance subsystem

- `inheritance/graph.py`: `SpaceGraph` unchanged algorithmically (C3 MRO, `get_relative`, `visit_tree`), plus **all** idstr node-string helpers so no other module does node-string surgery. Nodes stay idstr-keyed (D-6); rename fragility is contained in `rename_node_tree`.
- `inheritance/manager.py` (`InheritanceManager`): owns the single graph; query API = `get_mro`, `get_space_bases`, `get_deriv_bases`, `get_direct_bases`, `get_subs`, `get_relative_interface`, `rename_node_tree`; hosts `_check_sanity`.
- `inheritance/sync.py` (`InheritanceSync`): absorbs (a) `UserSpaceImpl.on_inherit`'s reconcile loop, (b) the duplicated derived-cells fan-out in `SpaceManager.new_cells` (including the `cells_after` reorder dance — one tested home), (c) the derived-ref fan-outs in `new_ref`/`change_ref` (`model.py:1887–1928`). Member-level `CellsImpl.on_inherit`/`ReferenceImpl.on_inherit` remain as callbacks invoked by the sync, with container writes routed through the transaction.

### 5.7 Execution/trace placement

- **Executor stays on `System`** — per-process infrastructure (call stack, thread stack sizing, error policy) shared across models; per-model executors would break cross-model formula calls and `mx.setmaxdepth`.
- **TraceManager stays a mixin on ModelImpl** (revised decision, §5.3); the trace graphs remain per-model state. The executor's borrow pattern (`_start_exec` reads `node[OBJ].model.tracegraph`) is untouched.
- The pipeline never touches graphs directly; finalize calls `model.clear_obj/clear_attr_referrers/clear_with_descs` (TraceManager mixin methods), preserving the `on_clear_trace(key)` postorder contract. ItemSpace deletion continues to flow `clear_with_descs → on_clear_trace → _del_itemspace`.

### 5.8 References, IO, and itemspaces

- `refs.py::ValueRegistry` replaces ReferenceManager's bookkeeping half. The dispatching half (isinstance branches delegating back into spmgr/ModelImpl) is **deleted** — dispatch belongs to Edit commands, killing the circularity.
- **Keying:** keep `id(value)` keys (values are arbitrary/unhashable — pandas objects), but store `(value, [refs])` so the registry itself strongly holds the value. This makes id reuse impossible *by construction* while registered, instead of by the implicit "some ref holds it" argument.
- `update_value` (backing `mx.update_pandas` etc.) is reimplemented as an Edit so recalculation targeting and registry moves happen in one transaction.
- Itemspace containers (`_named_itemspaces`, `param_spaces`, `dynamic_cache`, AutoNamer) remain `ItemSpaceParent` mixin state on each space (revised decision, §5.3).
- `ItemSpaceManager` (per model): the invalidation policy. The current policy (nuke-all, `DynamicBase.on_notify`) moves here **verbatim first** (Phase 4), then becomes selective (Phase 7):

**Selective invalidation (approved spec change).** For an ItemSpaceParent P with live itemspaces, define `closure(P)` = the set of UserSpace idstrs consisting of: the `_dynbase` of each node of each itemspace's dynamic tree (root + `_init_child_spaces` recursion, recorded on the itemspace at creation — a new `ItemSpaceImpl` slot), each such dynbase's MRO bases, and P's own parent chain up to the nearest UserSpace. On finalize, invalidate P's itemspaces iff `ChangeSet.dirty_spaces ∩ closure(P) ≠ ∅`. Global-ref changes (`model.new_ref/del_ref/change_ref`) conservatively keep nuke-all in v1; per-name refinement via `AlteredFunction`'s `global_names` is a later optimization. `clear_subs_rootitems` (formula/cells changes on a dynbase) is subsumed by the same mechanism. Over-approximating the closure degrades to "clears too much", never "too little" — correctness is preserved by construction; the trace-graph deletion path is untouched.

### 5.9 Namespace binding

Mechanism unchanged (lazy `_ns_dict` rebuild; `AlteredFunction` rebinding code objects). Two changes: (1) invalidation *initiation* moves exclusively to the pipeline notify stage; (2) the self-observation is removed (D-12, Phase 2): `BaseSpaceImpl` stops registering itself in its own observer list (today via `AlteredFunction.__init__(self, self)`, `space.py:1987`); instead `NamespaceServer.on_notify`, after invalidating `_is_ns_updated`, calls a direct hook `self.on_ns_invalidated()` implemented by the `AlteredFunction` mixin on the same object. Cells — which are separate objects — remain ordinary observers. The identity dispatch at `space.py:2000–2005` is deleted.

## 6. Decision log

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D-1 | networkx dependency | **Keep** | Edit-time only, not hot; C3/DAG code battle-tested; replacement is pure risk. |
| D-2 | Observer vs event bus | **Hybrid** | Keep Subject/Observer for O(1) lazy cache-flag fan-out; add ChangeSet-driven batched notify in the pipeline to fix the scattered-call-sites problem without rewiring consumers. |
| D-3 | SpaceUpdater + InstructionList | **Retire** → ModelEditor + Transaction | Keeps the one sound idea (mutate a graph copy, swap on success) and adds the missing half (journaled component-dict undo). |
| D-4 | id()-keyed ref registry | **Keep id keys; hold values strongly** | Values unhashable/arbitrary → identity is the only key; strong-holding removes the id-reuse hazard by construction. |
| D-5 | Itemspace nuke-on-any-change | **Selective, closure-based** (Phase 7); conservative fallback for global refs | Approved spec change; the big practical win for lifelib-scale models; over-approximation keeps correctness. |
| D-6 | Graph node keys | **Keep idstr strings**; centralize node-string math in `graph.py` | `get_relative` is inherently path-string logic; object keying = rewrite for zero behavior gain. |
| D-7 | Mixin→composition scope | **Keep ALL mixins** (revised 2026-07-13; earlier draft converted TraceManager, ItemSpaceParent, AlteredFunction) | A component per cells costs memory and a hot-path pointer hop at lifelib scale; keeping mixins avoids pickle/slots churn and preserves one idiom. Ownership discipline is enforced by the pipeline (§5.4), not by object boundaries. |
| D-8 | Derived-member creation | **Single `InheritanceSync.make_derived`** | One code path for creation/reordering; `on_inherit` callbacks stay member-level. |
| D-9 | Executor location | **System**; trace graphs stay per-model on ModelImpl (TraceManager mixin) | Call stack/thread machinery is process-global; graphs are model state. |
| D-10 | `updater`/`spmgr`/`refmgr` names | **Keep as facades indefinitely** | Zero cost; protects spyder-modelx `_impl` pokes and user scripts. |
| D-11 | Constructor self-registration | **Remove; registration only in pipeline apply** | Prerequisite for meaningful rollback; state-mutating constructors are the root of the ownership problem. |
| D-12 | Space self-observation (space in its own observer list) | **Remove; direct hook** — `NamespaceServer.on_notify` calls `self.on_ns_invalidated()` on the same object (implemented by the `AlteredFunction` mixin); the space leaves its own observer list | Kills the identity dispatch (`space.py:2000–2005`) without composition; cells remain ordinary observers. |

## 7. Phased roadmap

Each phase: one working session, dependency-ordered, full suite green at the end (`pytest modelx/tests`).

### Phase 0 — Characterization tests for untested invariants (risk: none)
Tests only, no production code. Under `modelx/tests/core/{space/inheritance,reference,execution}/`:
- `get_relative` resolution matrix: nested shared parents; refmode auto/relative/absolute; out-of-scope relative errors.
- Failed-mutation atomicity: `new_space` with a base whose ref-inherit raises midway; `add_bases` raising on name conflict after partial `on_inherit`. Assert state via `_check_sanity()` + full member-dict snapshots. Mark current corruption cases `xfail(strict=True)` — they become Phase 6 acceptance tests.
- Itemspace lifecycle: creation/deletion via trace clearing; `dynamic_cache` interface reuse; `clear_subs_rootitems` triggers.
- Notification: cells recalc after a ref change in a base propagates to subs (guards the batching change).
- Two-phase inherit order: a ref in a sub resolving against a derived space created in the same edit.
- IOSpec refcount GC: deleting one of two refs to the same PandasData keeps the spec; deleting the last drops it.
- Save fixture models with serializer_4–7 into `tests/testdata` as load-compat gates (4–5 written from historic modelx source, since master's old writers are rotted; 6–7 from current master).

### Phase 1 — Mechanical split of `model.py` (risk: low)
Move, logic unchanged: `SpaceGraph` + node-string helpers → `inheritance/graph.py`; `SharedSpaceOperations`/`SpaceManager`/`SpaceUpdater` → `inheritance/manager.py` (temporary home); `ReferenceManager` → `refs.py`; `Instruction`/`InstructionList` → `edit/transaction.py` (temporary). `model.py` keeps import aliases for **all** moved names (runtime-pickle compat; pickle-relevant aliases permanent). Run `tests/core/model/test_model_pickle.py` specifically.

### Phase 2 — Remove namespace self-observation (D-12; risk: low)
`NamespaceServer.on_notify` (`binding/namespace.py:55–57`): after setting `_is_ns_updated = False`, call a new hook `self.on_ns_invalidated()` before `self.notify()`. `AlteredFunction` implements `on_ns_invalidated` (sets `is_altfunc_updated = False`, `_is_global_updated = False`). `BaseSpaceImpl.__init__` stops registering the space as its own observer (`AlteredFunction.__init__(self, self)` at `space.py:1987` — split state initialization from observer registration, e.g. an `observe=False` path). Delete the identity dispatch in `BaseSpaceImpl.on_notify` (`space.py:2000–2005`); the method may reduce to the inherited `NamespaceServer.on_notify` (the `DynamicBase.on_notify` override is untouched until Phase 4). Cells' observer registration is unchanged. Behavior identical; one less re-entrant notification edge before the pipeline phases build on notification. Tests: `tests/core/binding/test_namespace.py`, `tests/core/reference/test_recalc*.py`, and `tests/performance/**` (the invalidation flags sit next to the eval hot path).

### Phase 3 — ValueRegistry; break refmgr↔spmgr circularity (risk: medium)
`refs.py::ValueRegistry`: `register(ref)`, `unregister(ref)`, `rebind(old_ref, new_ref)`, `values`, `specs`, `update_value`, `_check_sanity`; entries hold `(value, refs)` strongly. Dispatch inversion: `ModelImpl.set_attr`/`UserSpaceImpl.set_attr`/`del_attr` call `spmgr`/ModelImpl mutators directly, then registry hooks — the isinstance-dispatch blocks in refmgr are deleted. `model.refmgr` alias retained. IOSpec deletion ordering must match exactly (spec GC when refcount hits zero). Tests: `tests/core/reference/**`, `tests/serialize/refmode/**`, `tests/io/**`, Phase 0 sanity tests.

### Phase 4 — Pipeline skeleton + reference mutations end-to-end (template phase; high care, small surface)
Create `edit/pipeline.py` + `edit/transaction.py` for real: ModelEditor, Edit, ChangeSet, Transaction (journal over container writes; shadow graph unused yet). Edits: `NewRef`, `ChangeRef`, `DelRef` (space-level and model-global). Finalize implements: batched notify (replacing `on_notify` at `space.py:2517/2524` and the `yield_spaces` loops at `model.py:1268–1281`), trace invalidation, registry/IOSpec bookkeeping, itemspace invalidation with **verbatim current policy** (lifted from `DynamicBase.on_notify`). `ReferenceImpl` loses `set_item` self-registration on these paths. `SpaceManager.new_ref/change_ref/del_ref` and `ModelImpl.new_ref/change_ref/del_ref` become facades constructing Edits (signatures unchanged). Tests: full suite; `tests/core/reference/test_recalc*.py`, `test_dyn_base_ref.py`, `tests/core/binding/test_namespace.py`; the Phase 0 notify-batching test.

### Phase 5 — Cells + non-graph space ops; dedupe derived creation (risk: high)
Edits: `NewCells`, `DelCells`, `RenameCells`, `SetCellsProperty` (formula/cache), `SortCells`, `CopyCells`, `RenameSpace`. Introduce `inheritance/sync.py::InheritanceSync`; route both the `new_cells` fan-out and `UserSpaceImpl.on_inherit` reconciliation through it (fixes problem 7; the `cells_after` reorder gets one tested home). `CellsImpl.__init__` loses `add_to_space`. `clear_subs_rootitems`/`clear_obj` calls move into finalize. `spmgr.new_cells(...)` signature preserved (`parent.py:832` calls it directly). Tests: `tests/core/space/**` (esp. `test_new_cells.py`, `test_del_cells.py`, `test_rename.py`, `inheritance/`), `tests/core/cells/**`, `tests/export/**` (cells ordering affects generated code), `test_ref_order.py`.

### Phase 6 — Graph mutations under transactions; retire SpaceUpdater (risk: high — the heart, deliberately after P4/P5 prove the template)
Edits: `NewSpace`, `AddBases`, `RemoveBases`, `DelSpace`, `CopySpace`. Shadow-graph mechanics move into Transaction (lazy copy on first graph write; commit = swap, like today's `_update_manager` but with journaled dict rollback). Fix the old-vs-copied-graph descendant iteration (`model.py:2156/2177`). `UserSpaceImpl.__init__` loses `container[name] = self` (moves to `NewSpace.apply`); initial-refs creation in the constructor moves likewise. Delete `SpaceUpdater` + `InstructionList`; `model.updater` returns the facade. Flip Phase 0 `xfail` rollback tests to passing. Tests: `tests/core/space/inheritance/**`, `test_new_space.py`, `test_copy.py`, `test_delattr.py`, `tests/core/model/test_new_space_from_model.py`, serialize round-trips (deserializers drive `new_space` heavily).

### Phase 7 — Selective itemspace invalidation (risk: medium; the approved spec change)
`ItemSpaceManager` with the closure policy (§5.8). Record each itemspace's dynbase idstr set at creation (new `ItemSpaceImpl` slot, enumerated in its pickling state). `DynamicBase.on_notify` slims to flag propagation. Global-ref edits keep nuke-all. New tests: itemspaces survive unrelated-space cell/ref edits; itemspaces cleared when a base-of-dynbase changes, when a ref used via `_dynbase_refs` changes, and when the parent's formula changes. Update `tests/core/reference/test_clear_itemspaces.py` for the new semantics with an explicit expected-diff list in the PR. Release-note the semantic change (and `spec.rst` if applicable). Integration: full `tests/lifelib/**` and `tests/export/**`.

### Phase 8 (optional) — File split & shim retirement (risk: low)
Move `DynamicSpaceImpl`/`ItemSpaceImpl`/`DynamicBase` → `dynamic.py` (with `space.py` aliases). Delete aliases past their grace period **except pickle-relevant ones** (any class instances of which can appear in runtime pickles — e.g. `SpaceGraph` inside a pickled spmgr — keep their aliases permanently). Remove stale `core/members/` and `core/inheritance/__pycache__` remnants; delete `modelx/managers`.

## 8. Verification strategy

**Per phase:** full `pytest modelx/tests`; sensitive suites called out per phase above. `modelx/tests/lifelib/**` (real actuarial models) is the best regression net for inheritance + itemspace semantics; `modelx/tests/performance/**` guards the executor hot path (run for Phase 2, which touches invalidation flags read on every call, and Phase 7, which changes itemspace lifecycle). Use `modelx/testing/testutil.py` model-comparison utilities in every new round-trip test.

**Sanity invariants:** `ModelImpl._check_sanity` (`model.py:1250`) already chains refmgr and spmgr checks. Extend with: (a) every derived member's `bases[0]` reachable via MRO; (b) ValueRegistry entry values identical to their refs' interfaces; (c) no observer lists containing NullImpl-backed impls. Run `_check_sanity()` in fixture teardown for all new tests (pattern already used in `test_model_pickle.py`).

**Behavior preservation for the risky phases (4–6) — golden snapshots:** scripted edit sequences, serialized with serializer_7 after each step, diffed against checked-in golden trees. The serialized form is a complete, stable observable of component dicts, ordering, refmodes, and input values. (Running old-vs-new modelx side by side in one env is impractical; snapshots recorded from current master serve as the oracle.)

**Compatibility gates:** (1) load the Phase 0 fixture models saved by serializer_4–7; (2) export round-trip: export → import generated package → compare numbers (existing export tests do this); (3) spyder surface: snapshot tests on `_baseattrs` / `_get_attrdict(extattrs=["get_referents", ...])` output for a representative model.
