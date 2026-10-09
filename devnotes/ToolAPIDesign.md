# modelx tool API additions for 0.34: design for approval

**Status:** for the owner of modelx to approve or amend before implementation. 2026-10-07.
**Decided by the owner:** decision 3, where the new exceptions live, and decision 4, that Spaces have no "derived" (both 2026-10-09).
**Scope:** the introspection work in lifelib-app PLAN.md §3.2. It unblocks the two features PLAN §5a records as blocked on modelx (PLAN.md:424-429).
**Basis:** this document builds on Design A ("minimal additions"). Judge 1 picked A, and A had the highest combined score over the two judges: A 98, C 96, B 82. Both judges recommended adding pieces of B and C to it. Those pieces are included here, and §3.0 records where each element came from. Where the judges disagreed, the choice is put to you in §2.
**Review:** two verifiers checked the first draft and raised 28 findings (5 major). Six fixers and an integrator resolved all 28, each by probe; two fresh verifiers then raised 19 more (6 major), which a final pass resolved. Nothing has re-checked the document since that final pass.

**Conventions**
- *Tool API* means the owner's definition. Underscore members of Model, Spaces, Cells, ReferenceProxy and the Node and view objects are public. They are meant for other software, not for end users.
- modelx citations are `file:line` in modelx 0.33.0 (commit 4fa720f). Bridge and mcp citations are relative to `lifelib-app/python/`. spyder citations are relative to `fumitoh/spyder-modelx/`. spymx-kernels citations are taken from the inventory, because that package is not in this checkout.
- **Measured** facts name their probe. **Inferred** facts say so.
- Probes are named by folder and script (for example `fix-final/e04`). They are the scripts the design and review agents ran in the session that wrote this document, and they are **not in this repository**. §9 restates each measured number with what it was measured on, and §6 turns the ones the design relies on into tests.
  - `final/f01`–`f04` were written and run for this document, on CPython 3.11.15 with modelx 0.33.0 from GitHub. `f03` also ran on CPython 3.10.20, 3.12.3, 3.13.14 and 3.14.8.
  - Figures attributed to other probes come from their recorded outputs and were not re-run: `minimal/` (Design A), `design_objmodel/` (B), `tool_contract/` (C), `judge_opus/`, and the inventory folders.

---

## 1. Summary

**What.** modelx 0.34 gains:
- fourteen tool-API elements, T1–T14 in §3:
  - eleven sets of underscore members on Model, Spaces, Cells, Macro, ReferenceProxy, IOSpecs and nodes;
  - new exception and warning classes in `modelx.core.errors`, which becomes a supported import path for tools; they are not re-exported at the top level (decision 3);
  - two groups of top-level names: a name check with a model-file reader, and a provisional calculation hook;
- eleven fixes to existing members, F1–F11;
- a written contract for the existing underscore members that modelx-bridge, modelx-mcp and spyder-modelx already call. Every underscore member of an object users hold stays tool API, as the owner defines it; the contract *freezes* the ones it lists (§5). It is a reference page, a test that pins signatures, and a CI job that runs the released bridge and mcp test suites before every modelx release.

**Why.** Of the 62 needs in the inventory:
- 23 are already served by the tool API;
- 27 reach INTERNAL code: `_impl`, `modelx.core.*` other than `modelx.core.errors`, class-name checks, or undocumented behaviour;
- 12 are UNMET.

That is why modelx-bridge pins `modelx>=0.33.0,<0.34` (modelx-bridge/pyproject.toml:54).

**What it unblocks.**
- The two features PLAN §5a lists as blocked: the `overrides` badge for Cells and References (T4; it turned out to be computable on 0.33 too, from `Cells._is_derived()` and the public `bases`), and a Reference's "used by" links, including the readers in sub Spaces (T10). The other half of the first, dimming an "inherited Space", is withdrawn: a Space is never inherited (decision 4). The Studio and modelx-mcp see only the bridge's wire, so they get them through a new bridge method, `links.used_by` (§7).
- A change signal and a model-level dirty flag that see all 46 measured edit-by-state cases and 70 more calls, 61 of which change the saved model (T8). The bridge's current detectors miss 23 of the 46.
- ItemSpace addresses by argument that never print `__SpaceN` (T6), and an id of its own for a relative Reference that an ItemSpace re-points into its tree (T5).
- A snapshot walk that never reads or calls a user's member (F11). spyder's walk calls user code on 0.33.
- Typed errors, and a name check on every route that makes a binding (decision 9). On 0.33 a global Reference or a `new_space(refs=)` name is never checked, and some such names give a model that writes but cannot be read back.
- Widening the bridge pin to `<0.36`.

## 2. Decisions for the owner

1. **How the contract is written down.** Recommended:
   - a new page, `doc/source/reference/toolapi.rst` ("API for tools");
   - `test_tool_api_surface.py`, which pins every listed name and its `inspect.signature` against a golden file;
   - the downstream CI job in §8.

   The page does not reclassify anything. By the owner's rule every underscore member of an object users hold is tool API. The page and the golden *freeze* the members listed on it; the others stay tool API without that promise (§5's two tiers). The classes users hold define 55 non-dunder underscore members on 0.33, most of the unlisted ones Formula and IOSpec hooks (measured critic2/k03, re-run in fix-final).

   Rejected: Design C's runtime registry of all 81 underscore members, which would freeze every one of them, hooks included, and a `TOOL_API_LEVEL` integer. Use `modelx.VERSION` plus class-level detection instead (§5).
2. **Deprecation signal.** Recommended: add `ToolAPIDeprecationWarning(UserWarning)` to `modelx.core.errors` (decision 3). It keeps the house style, because it is still a UserWarning, and it lets CI find exactly these warnings: the downstream job records every one, in every interpreter the suites start, and fails (§8). A warning filter cannot do this. Each suite runs in its own interpreter, so a filter set in the runner left the bridge suites at 831 passed, exit 0, while a deprecated member was in use, and `PYTHONWARNINGS` cannot name the category (measured fix-bridge-adoption/b06, b06b, b06d). The subclass is still what makes the audit's `issubclass` test exact. A tool-API member is removed only after both:
   - two minor releases of warning;
   - the downstream job being green against the latest released bridge and mcp.
3. **Where the new names live.** Decided by the owner on 2026-10-09:
   - **Exception and warning classes stay in `modelx.core.errors`**, where `FormulaError` already is, and are **not** re-exported at the top level: `ObjectNotFoundError`, `FormulaDefinitionError`, `DynamicObjectError`, `ToolAPIDeprecationWarning` and `CalculationCancelled`. `modelx.core.errors` is a supported import path for tools, and toolapi.rst lists it.
     - It is already where errors come from: modelx's own tests import them from there (tests/core/cells/test_error.py:5, tests/core/cells/test_rename.py:4), tracebacks name `modelx.core.errors.FormulaError`, and `modelx.FormulaError` does not exist on 0.33.
     - Adding no top-level name means none of these classes can hide a model of the same name from `mx.<name>`, and `from modelx import *` gains none of them.
     - The bridge's `from modelx.core.errors import FormulaError` (#20) is therefore tool API, not INTERNAL. The rule that a `modelx.core.*` import is INTERNAL now has this one exception.

   Still recommended, for the owner to confirm: the functions go in `api.py`, beside `get_object`: `is_valid_name`, `get_model_info`, `set_calc_hook`, `clear_calc_hook`, and a new keyword on an existing function, `read_model(..., if_exists=)`. The cost: each new name hides a model of the same name from `mx.<name>`, because models are found only on a miss (api.py:614-620). No `get_kind()` function is added; `getattr(type(v), '_kind', None)` covers it.
4. **Spaces have no "derived".** Decided by the owner on 2026-10-09:
   - Space classes have no "derived" concept. Since 0.24 a base Space's child Spaces are not copied into a sub Space (relnotes_v0_24_0.rst:20-58), so no Space is ever inherited. Only Cells and References are, and only they have `_is_derived()` (T3). There is no `BaseSpace._is_derived()` and no `Model._is_derived()`.
   - A dynamic copy, an ItemSpace or a DynamicSpace, is told by `_is_dynamic()` (T2), never by a derived flag.
   - For a Cells or a Reference, "inherited" in a UI means `_is_derived() and not _is_dynamic()`, and "overrides" comes from T4's `state`.
   - The two needs that asked a Space for a derived flag are not applicable: #10 (the bridge's `_derived()` on a Space) and the Space part of #47 (spyder's "Is Derived" column). spyder already leaves a Space row's cell blank when the key is absent (mxtreemodel.py:121-124), which is the right answer.
   - An earlier draft proposed `BaseSpace._is_derived()` returning `_is_dynamic()`, for uniformity across kinds. It was dropped: it would only repeat `_is_dynamic()` under a name that suggests inheritance.
5. **Address grammar.** Recommended:
   - The canonical form is call syntax, `'Projection(1).claims'`. That is `_evalrepr` without the model name.
   - The resolver also accepts subscript syntax, `'Projection[1].claims'`, which matches display strings, plus `[]` for no arguments (`'Z[].c'`). As in Python, `'T[(1, 2)]'` means two arguments, so the display of a single tuple-valued argument misses; its address `'T((1, 2))'` resolves (g02).
   - There is one resolver: the existing `Model._get_from_name`, extended. It has no `create=` flag; creating an ItemSpace stays a call to the Space.
   - It refuses only `__builtins__`, `_self`, `_space` and `_model` among `_` names. Until 0.36 the public `refs` views list user `_` globals, `_` Space References made by `new_space(refs=)`, `_` arguments and `_` formula refs (C2(2)), so the resolver must find them for their ids to round-trip (T6; measured fix-integrate/i03).
6. **Lookup misses.** Recommended: every tool-API resolver and `mx.get_object` raise `ObjectNotFoundError(NameError, KeyError)` on a miss. `get_object` also stops two bad behaviours:
   - dropping trailing segments after a Reference when `as_proxy=True`;
   - leaking a raw `AttributeError` when it traverses through a value.

   `get_object` stays getattr-based in 0.34. Only `_get_from_name` resolves members first, which avoids shadowing by class attributes. Making `get_object` member-first is a user-visible change; it is better left for later.
7. **A relative Reference inside an ItemSpace** (`P[1].rel`, where `P.rel = P.Child`). Today the slot holds `P[1].Child`'s impl. Its proxy therefore has the target's name and id (`'Child'`, `'P.__Space1.Child'`), and `is_derived()` and `refmode` raise (measured f01, g01). Recommended: give the slot a ReferenceImpl of its own in the dynamic Space (T5).
   - Its proxy is then a Reference like an argument: `_idstr` `'P.__Space1.rel'`, `_address` `'P(1).rel'`, and `.value` `P[1].Child`, which is what a formula in `P[1]` sees.
   - It round-trips through both ids, and `_is_dynamic()` and `_is_derived()` are True. Its binding `P.rel` is `r.parent.bases[0]._get_object('rel', as_proxy=True)`.
   - It needs a one-line fix to `wrap_impl`'s in-tree test (T5, g06).
   - Measured: 75 of 75 proxies on a synthetic model and 72 of 72 on lifelib's simplelife round-trip. The previous recommendation scored 56 and 58 (g02, g03).

   Rejected: a proxy over the dynbase binding that carries the in-tree value. It splits identity from value: its id resolves to `P.Child`, `P[1].rel == P[2].rel` while their values differ, and it stays valid after `del P[1]`. The other alternative is B's plain dynbase proxy. It is consistent, but its value is `P.Child`, not what the formula sees.
8. **What 0.34 includes.** Recommended:
   - The calculation hook ships **provisional**.
   - The edit-impact preview is **deferred**. It needs the UserSpace formula setters routed through ModelEditor and declarative `finalize_ops`; without them it predicts 0 nodes where 260 are cleared (depgraph/d08).
   - Per-object revisions and a per-object `_uid` are **left out**. Both need new state in every object, either an Impl slot or a System dict on every clear path. `Model._get_serial()` covers model identity.
   - T8 returns a third stamp, `saved`, so dirty is a fact about the model (`rev[0] != rev[2]`), not about a host's baseline. It costs one int per model and two stores. It is the only way a save from the Console, spyder or modelx-mcp's `run_python` makes the model clean for every host (measured fix-revision-counter/p04). The alternative is a 2-tuple, with each host keeping its own baseline; a model saved elsewhere then keeps showing dirty.
9. **When the tightened validation takes effect.** Recommended:
   - `set_ref` refuses an invalid refmode immediately (ValueError). Its docstring already promises this (space.py:1533), and an invalid mode already breaks later with "must not happen" (dynamic.py:172).
   - Four routes make a binding without checking `is_valid_name` today. Every other route refuses an invalid name (measured refute2/r06; fix-final/e04):
     - a global Reference: `setattr(m, n, v)` reaches `ModelImpl.set_attr` → `new_ref` → `NewGlobalRef` (model.py:1319-1321, 1335-1343; edit/pipeline.py:711-727), and none of them checks the name;
     - `new_space(refs=)` on a Model or a Space, which calls `create_ref` for each name (edit/pipeline.py:572-574);
     - a Space-formula parameter;
     - a ref a Space formula returns (dynamic.py:97-101).
   - Refused at once in 0.34 (ValueError), because no saved model can hold them or because they break the Space's own formulas:
     - a global or `new_space(refs=)` name that is not an identifier, and a `new_space(refs=)` name that is a keyword. Such a model writes but cannot be read back. A global `'a-b'`, `'1x'` or `'a b'` makes `read_model` raise `TypeError: 'NoneType' object is not callable`, a global `''` makes `write_model` raise IndexError (serializer_8.py:277), a `new_space(refs=)` name `'a-b'` fails the read with that TypeError, and `'class'` or `'None'` with `ValueError: Invalid name` (measured refute2/r06, r07; fix-final/e04);
     - `__builtins__` as a global, which is modelx's own binding (model.py:1220-1222);
     - `_self`, `_space`, `_model` and `__builtins__` as a `new_space(refs=)` name or a Space-formula parameter. Each replaces a system binding for that Space's formulas, or its items' (measured fix-final/e04; refute2/r07): `_space.y` raised `AttributeError: 'int' object has no attribute 'y'`, and `len` raised NameError or TypeError.
   - Six cases warn in 0.34 and become errors in 0.36:
     - other global Reference names that fail `is_valid_name`: `_` names and keywords. `setattr(m, 'class', 7)` is accepted today, and a keyword global survives a write and a read (measured fix-final/k01). A `_` global does not: the writer skips `_` names (serializer_8.py:277), so it is missing from the model `read_model` returns (e04);
     - other `_` names in `new_space(refs=)`. The writer drops them too (serializer_8.py:277; refute2/r07, e04);
     - Space-formula parameter names that fail `is_valid_name` (r12: `lambda _is_dynamic: None` was accepted);
     - ref names returned by a Space formula that fail `is_valid_name` (r12: refs `_is_derived`/`_kind` were accepted). That includes a name that is not a str: `is_valid_name(1)` is False. No formula can read such a ref, and until F11's RefView change it stops the snapshot walk (fix-final/e05; F11);
     - formula text silently cut down to its first lambda;
     - `new_cells` silently renaming an invalid name.
   - Where the checks go. A saved model that holds such a name must keep reading in 0.36, so no check that can fail runs inside `read_model`:
     - global names in `ModelImpl.set_attr` (model.py:1335-1343), skipped while `System.serializing` is set. The reader sets every global through `Model.__setattr__`, which calls `set_attr`, and every v4–v8 reader sets `serializing` for the whole read (serializer_6.py:984; serializer_4.py:1075). Measured e04: the reader's `set_attr` calls ran with it set, and a user's call after the read ran with it `None`;
     - `new_space(refs=)` names and Space-formula parameters in `NewSpace.validate` (edit/pipeline.py:514), and parameters also in the six UserSpace formula members (space.py:1581-1662), for a formula set later. `new_space(formula=)` on a Model and on a Space, and `copy`, all pass `NewSpace.validate`, and none of them passes the six members (critic2/k04; fix-final/e04). The reader passes `NewSpace` with neither formula nor refs and sets Space formulas through the impl (serializer_6.py:1028-1035, 1343-1352), so it passes no check (e04). Never in `ItemSpaceParent.set_formula`, which runs on every ItemSpace build (T8);
     - the returned-ref check where formula refs are made (dynamic.py:97-101). That code runs whenever an ItemSpace is built, and a read builds the ItemSpaces that hold saved inputs (`_dynamic_inputs`, serializer_6.py:685-736). So in 0.36 this check also stays a warning while `System.serializing` is set, or a saved model with such a formula and inputs in its items stops reading (inferred).
   - Clashes inside an ItemSpace warn in 0.34 and stay warnings (T6, T13): a Space-formula parameter or a returned ref with the name of a Cells or child Space of its Space, and the reverse, `new_cells` or `new_space` taking a parameter's name. Such a binding has the same `_idstr` as the member (refute2/r11). No lifelib model has one: 0 of 9 (refute2/r12).
   - A reserved name (T13: the container's class has an attribute of that name) warns in 0.34 when `new_cells`, `new_space`, `Cells.rename`, `new_macro` or a Space-formula parameter takes it. In a Space with a formula, the ItemSpace class counts too, which adds `argvalues` (refute2/r09). It stays a warning, because `read_model` builds Cells through the same `SpaceManager.new_cells`. No lifelib model is affected: 0 of 5,347 member names collide (measured fix-validation-and-fixes/v01, v02).
   - Two clashes are refused at once in 0.34 (F10). `set_ref` on a name held by a Cells or a Space raises AttributeError, as its docstring says. A Model-level `new_space` refuses a macro's name, as `new_macro` already refuses a Space's. That needs no warning window: such a model writes on 0.33 but cannot be read back, `ValueError: Name 'mac' already used` (measured fix-integrate/i01).
10. **Persisting "no formula" and Reference docstrings.** Recommended: defer both.
    - `_has_formula()` (T11) reports the in-memory state. A Cells without a formula is written as `c = lambda: None` and reads back as a plain Formula (measured f04). The obvious encoder fix, writing `c = None`, makes 0.33's `read_model` raise `TypeError: 'NoneType' object is not callable` (measured f04). So the fix needs a reader change and a forward-compatibility decision.
    - `ReferenceProxy.doc` is documented as always `None` for now.
11. **Small compatibility choices.** Recommended:
    - Keep `ReferenceProxy.is_derived()` permanently as an alias of `_is_derived()`, and remove its TODO. The 0.33 bridge calls it. It is in the signature golden, and toolapi.rst lists it only as "kept for modelx-bridge 0.10; use `_is_derived()`" (§3.4).
    - Keep `ItemSpace.argvalues` as it is, but do not put it on the snapshot wire. The raw tuple can hold a Space or an unpicklable object, and then cloudpickle fails on spyder's whole tree (fix-spyder-snapshot/s04). Requested as an extattr, it reaches members named `argvalues` on other kinds (c01, s02). spyder reads the arguments from `_evalrepr`, which it already requests (C3; s05: 1,060 of 1,060 rows). No display-string member is added.
12. **Bridge pin and release gate.** Recommended:
    - After 0.34 ships with the downstream job green, the bridge widens to `modelx>=0.33.0,<0.36`, matching the two-minor deprecation window, and raises the cap one minor at a time.
    - The downstream job hard-blocks `python-publish.yml`'s `deploy`. The override for a deliberate break is to ship a bridge release first.
13. **Extattrs resolve on the class only (F11).** Recommended: `_get_attrdict_extra` (base.py:698-708) looks each requested name up on `type(self)`. A ReferenceProxy also looks on Interface, for properties and functions only, as reference.py:163-168 already does. It never reaches `Model.__getattr__` or `BaseSpace.__getattr__`.
    - On 0.33, spyder's own list called user functions 28 times in one walk, and the prototype 0 times (fix-spyder-snapshot/s02).
    - Output was identical on five lifelib models (53,526 objects), and the spyder gate passes (s03).

    Rejected: leaving it alone. Then spyder's walk keeps calling `_`-named global References and Space-formula refs until decision 9's errors arrive in 0.36. Its Properties list keeps calling global References named `formula` or `parameters` for good, because those names are valid and stay valid (s02).

## 2a. Classification

TOOL_API means an underscore member on an object users hold, or behaviour such a member documents. INTERNAL means access through `_impl`, a `modelx.core.*` import other than `modelx.core.errors` (decision 3), a type-name check, or undocumented behaviour of a call. UNMET means there is no way to get the fact today. N/A means the need asks for something modelx has no concept of (decision 4). B = modelx-bridge/mcp; S = spyder-modelx/spymx-kernels.

**Totals: TOOL_API 23, INTERNAL 27, UNMET 11, N/A 1.** By consumer: B 4/20/8 and 1 N/A, S 19/7/3.

| # | need | by | class | access used today |
|---|---|---|---|---|
| 1 | object-id-string | B | INTERNAL | `obj._idstr` (base.py:724-726) is tool API on Model, Spaces, Cells and macros. A ReferenceProxy defines neither `_idstr` nor `_get_repr`; both answer only through undocumented `__getattr__` forwarding (reference.py:163-168; measured fix-final/k07). The bridge reads them on every Reference: `_objid` (methods.py:2745-2749) and `_display` (methods.py:2829-2848). The bridge's `namedid` fallback is dead (methods.py:2745-2749). |
| 2 | resolve-id-to-object | B | TOOL_API | `Model._get_from_name` (model.py:646-648); `_get_object(name, as_proxy=True)` (space.py:89-105, model.py:650-657); methods.py:2752-2778. |
| 3 | reference-as-object | B | INTERNAL | `_get_object(as_proxy=True)` is tool API, and `name`/`parent` are documented in the class docstring (reference.py:143-150). `doc` is reached only by undocumented `__getattr__` forwarding (methods.py:530-537). |
| 4 | display-name | B | INTERNAL | `obj._impl.repr_parent()` (methods.py:2834). |
| 5 | valid-name-rule | B | INTERNAL | The undocumented rule in util.py:51-61 (methods.py:2365-2406). |
| 6 | object-kind | B | INTERNAL | `type(x).__name__` (methods.py:2681-2686; codec.py:71), and instance-level capability probes that resolve a Model's global References or a Space's members: `hasattr(parent, 'set_ref')` (methods.py:778, 847), `getattr(target, 'formula', None)` (491), `obj.parameters` (2819), `getattr(target, 'node', None)` (2852), `getattr(space, 'cells', None)` (1032), `getattr(obj, 'is_derived', None)` (2731): seven sites (fix-bridge-adoption/b03). |
| 7 | is-modelx-object | B | INTERNAL | `modelx.core.base.Interface` and `modelx.core.reference.ReferenceProxy` imports (codec.py:63-77). |
| 8 | is-dynamic | B | INTERNAL | `type(obj._impl).__name__` (methods.py:2617-2627). |
| 9 | derived-flag-cells-refs | B | INTERNAL | `Cells._is_derived()` (cells.py:582-583) is tool API. The Reference half calls `ReferenceProxy.is_derived()` (reference.py:193), which has no underscore, is not in reference.rst (doc/source/reference/reference.rst:80-81 list only `value` and `refmode`), and carries your TODO to rename it: reliance on an undocumented call. |
| 10 | derived-flag-space | B | N/A | A Space has no derived concept (decision 4). UserSpaceImpl is not Derivable (space.py:2223-2228; base.py:296-329), and since 0.24 no Space is inherited. The bridge's `_derived()` asks a Space anyway (methods.py:2726-2738). |
| 11 | space-ref-membership | B | INTERNAL | Undocumented contents of `space.refs` (`__builtins__`, globals, inherited; model.py:1220-1222), plus a `'_'` filter (methods.py:2741-2742). |
| 12 | computed-node-count | B | INTERNAL | `len(model._impl.tracegraph)` (methods.py:2459-2460, 2582-2614). |
| 13 | reference-edge-count | B | INTERNAL | `len(model._impl.refgraph)` (methods.py:2459-2460). |
| 14 | model-change-signal | B | UNMET | None; approximated by heuristics (methods.py:2441-2524). |
| 15 | model-registry-events | B | UNMET | None; name diffing and a `_BAK` regex (methods.py:353-362, 1504-1521, 2310). |
| 16 | itemspace-enumeration | B | TOOL_API | `_named_itemspaces` (space.py:314-317), `item._get_repr()`. |
| 17 | itemspace-addressing | B | UNMET | None; only session-scoped `__SpaceN` ids. mcp maps `Space[k]` by hand (tools.py:396-470). |
| 18 | formula-source (B) | B | INTERNAL | `type(formula).__name__ == "NullFormula"` (methods.py:2689-2700); the Formula class is undocumented (formula.py:267). |
| 19 | formula-set-refusals | B | INTERNAL | Matching ValueError text (methods.py:2630-2678). |
| 20 | formula-error-class | B | TOOL_API | `from modelx.core.errors import FormulaError` (methods.py:2185-2187). `modelx.core.errors` is a supported import path (decision 3). |
| 21 | formula-error-text-format | B | INTERNAL | Parsing `str(FormulaError)` (tools.py:2338-2392). |
| 22 | reference-value-type (B) | B | TOOL_API | `proxy._get_attrdict()['value_type']` (reference.py:203-210). |
| 23 | cached-values-nonevaluating | B | INTERNAL | An undocumented guarantee that `len` and `series` do not evaluate (methods.py:1174-1189). |
| 24 | ref-used-by | B | UNMET | None; a per-Space ast scan (methods.py:995-1078). |
| 25 | formula-static-reads | B | UNMET | None; the same scan. |
| 26 | edit-impact-preview | B | UNMET | None; reported only after the fact. |
| 27 | trace-graph-enumeration | B | INTERNAL | `_impl.tracegraph` node tuples (tests only). |
| 28 | model-file-format | B | INTERNAL | The serializer layout (files.py:400-473). |
| 29 | backup-rotation | B | INTERNAL | `from modelx.serialize import DEFAULT_MAX_BACKUPS` (files.py:248) and the `_BAK<n>` naming. |
| 30 | read-model-failure-cleanup | B | INTERNAL | Undocumented failure behaviour (samples.py:617-643). |
| 31 | refmode-values | B | UNMET | None. modelx stores any string (measured `'sideways'`, f01). |
| 32 | reference-doc | B | INTERNAL | Forwarded `proxy.doc` (reference.py:163-168). |
| 33 | calc-progress-cancel | B | UNMET | None. |
| 34 | model-tree-snapshot | S | TOOL_API | `model._get_attrdict([...], recursive=True)` (model.py:659-671, space.py:704-726). |
| 35 | object-identity | S | TOOL_API | attrdict `'id'` = `id(impl)` (base.py:661, 690). |
| 36 | named-id | S | TOOL_API | attrdict `'namedid'`, `_get_from_name`. |
| 37 | eval-repr | S | TOOL_API | `_evalrepr` (base.py:713-715; reference.py:212-214). |
| 38 | display-repr | S | TOOL_API | attrdict `'repr'` = `_get_repr()` (base.py:710-711). |
| 39 | repr-parent | S | TOOL_API | Node attrdict `'repr_parent'` (node.py:103). |
| 40 | itemspace-address | S | UNMET | None. A `__SpaceN` fullname goes stale (mxexplorer_6.py:141-144). |
| 41 | get-object-leaf-path | S | TOOL_API | `mx.get_object(fullname + '.cells')`. `get_object` only delegates to `Model._get_object` (system.py:242-254), whose docstring states the leaf traversal for spyder-modelx (base.py:376-379). |
| 42 | lookup-miss-exception | S | INTERNAL | `except NameError`, while the docs say AttributeError (api.py:650-651 against base.py:385-386). |
| 43 | kind-type-name | S | TOOL_API | attrdict `'type'` (base.py:660, 690; reference.py:199, 205). |
| 44 | value-kind-tests | S | INTERNAL | isinstance against `modelx.core.base.Interface`, `modelx.core.reference.ReferenceProxy` and `modelx.io.baseio.BaseIOSpec`, plus parsing the version. |
| 45 | container-capabilities | S | INTERNAL | isinstance against `modelx.core.parent.BaseParent` and `modelx.core.space.BaseSpace`/`ItemSpace`. |
| 46 | user-visible-members | S | INTERNAL | The implicit `'_'` filter in RefView (views.py:261), against the unfiltered public `refs`. |
| 47 | is-derived | S | UNMET | No member exists for References, so the key is absent from their rows. The Cells key is TOOL_API. For Spaces the key is absent and N/A (decision 4). |
| 48 | space-bases-names | S | TOOL_API | attrdict `'bases'` (space.py:720), which is the MRO, not the direct bases the need asks for; spyder shows the MRO today (mxproperty.py:161-162). `_direct_bases` (space.py:146-151) is tool API but returns objects. |
| 49 | node-record | S | TOOL_API | `node._get_attrdict(...)` (node.py:92-106). |
| 50 | node-adjacent-counts | S | TOOL_API | `predslen`, `succslen`, `precedentslen` (node.py:100-102). |
| 51 | change-detection-full-diff | S | UNMET | None; re-reads everything and deep-compares. |
| 52 | value-identity-valid | S | TOOL_API | `'valid'` = `id(value)` (node.py:99). |
| 53 | cached-count | S | TOOL_API | `'__len__'` extattr (base.py:698-708). |
| 54 | formula-source (S) | S | TOOL_API | `Formula._get_attrdict()` (formula.py:480-481). |
| 55 | set-formula-from-source | S | INTERNAL | A string passed to the deprecated `Cells.set_formula` (cells.py:460-464). |
| 56 | value-cached-check | S | INTERNAL | `args in obj`. Cells apply no defaults (cells.py:187-188); Spaces test member names (space.py:1332). |
| 57 | reference-value-type (S) | S | TOOL_API | attrdict `'value_type'`. |
| 58 | value-registry-refs | S | TOOL_API | `_get_assoc_values()`, `_get_refs()` (model.py:673-691). |
| 59 | iospec-attributes | S | TOOL_API | `spec._get_attrdict()` (io/baseio.py:562-570). |
| 60 | named-itemspaces | S | TOOL_API | `_named_itemspaces` (space.py:314-317, 708-717). |
| 61 | itemspace-argvalues | S | TOOL_API | Reachable today as extattr `'argvalues'` (measured `(1,)`, f01), but never requested; the column reads an absent key (mxtreemodel.py:244-252). Requesting it is unsafe (C3): it reaches members named `argvalues` on other kinds (c01), and a Space-valued argument breaks spyder's transport (s04). |
| 62 | modelx-system-handle | S | INTERNAL | `from modelx.core import mxsys`, in dead code. |

Some rows were judgement calls:
- **#1 object-id-string:** INTERNAL, for its Reference half. `_idstr` is tool API, but a proxy answers it only by the same undocumented forwarding that makes #3 and #32 INTERNAL. T5 defines `_idstr` and `_get_repr` on ReferenceProxy explicitly.
- **#3 reference-as-object:** INTERNAL, because `doc` is undocumented forwarding.
- **#9 derived-flag-cells-refs:** INTERNAL. The Cells half is tool API, but the Reference half calls `is_derived()`, which has no underscore and is undocumented. T3's explicit `ReferenceProxy._is_derived()` covers it.
- **#41 get-object-leaf-path:** TOOL_API. The public `get_object` only delegates to `Model._get_object`, and that tool-API member documents the leaf traversal for spyder-modelx. C2(6) also states it on `get_object`.
- **#47 is-derived:** UNMET for its Reference rows, which have no member. Its Space rows are N/A: a Space has no derived concept (decision 4).

---

## 3. The API

### 3.0 Rules and overview

**Placement**
- Each fact goes on the object it describes, as an underscore member. `is_valid_name` rejects a leading `_` (util.py:48-61), so in a static Space a new member cannot shadow a user's Cells, Space, or a Reference made by `set_ref` or by assignment (r03, r03b). A non-underscore name would make saved models holding a Reference of that name unloadable (inventory risk 1b), and it would hide a user's member of that name (T13).
- Four paths still take `_` names: global References (r03), `new_space(refs=)` on a Model or a Space (refute2/r07), Space-formula parameter names, and refs a Space formula returns (r12). Decision 9 refuses `_self`, `_space`, `_model` and `__builtins__` at once in `new_space(refs=)` and as parameters, and `__builtins__` as a global, and deprecates the other `_` names on all four routes. Until 0.36, a new class-level member hides such a name from attribute access outside formulas. With `ItemSpace._kind` set, `R[7]._kind` gives `'ItemSpace'` where it gave 7, while a formula in `R[7]` still reads 7 (fix-spyder-snapshot/s05). The same holds in a static Space: `new_space('S', refs={'_kind': 'user-kind'})` makes `S._kind` return `'user-kind'` today (refute2/r07). Tools are not affected: F11 (C3) reads only class members, and T6 resolves members first.
- Once Model defines a member, `EditableParent.__setattr__` (parent.py:87-98) refuses a global Reference of that name. Today `m._get_revision = 1` is accepted as a global Reference (measured f01).
- Facts that have no object go into `api.py` next to `get_object` (api.py:629).

**State**
- There is no new Impl slot. `Impl.__setstate__` raises on unknown slots (base.py:163-180), and `UserSpaceImpl.__getstate__` enumerates every slot (space.py:1999-2003).
- New state lives on System.

**Return values** are Interfaces, ReferenceProxies, the public Node classes, literals, and plain tuples or dicts. Never an Impl.

**Hot paths.** Nothing is added to:
- `eval_node`'s cached branch (execution/executor.py:29-49);
- `CallStack.append`/`pop` (executor.py:245-290);
- `get_node` (execution/trace.py:52).

T8 adds one node-count check to the top-level miss branch (`_start_exec`, executor.py:67-118). Read through networkx's node dicts, it adds +0.21–0.25 µs (+13–15%, minimum) to an uncached top-level call, and +0.33–0.64 µs at the minimum, +0.18–0.44 µs at the median (+4–15%), to a cached top-level miss. Through `len()` it adds +0.62–0.65 µs to an uncached call (fix-revision-counter/p05; refute2/r02, r03; fix-final/r03, two runs).

**Imports.** Only the stdlib, networkx and asttokens, which keeps the code Pyodide-safe. libcst and `modelx.export` stay out.

**ReferenceProxy.**
- Every new member that also applies to References is **defined on ReferenceProxy explicitly**.
- The blind `__getattr__` forwarding (reference.py:163-168) is **kept as it is**. Narrowing it drops `allow_none`, which spyder requests on Reference rows at mxshell_6.py:235 (judge_opus/j02). `allow_none`, `_idtuple`, `_idstr` and `_get_repr` are answered only by forwarding today (measured f01: `'allow_none' in vars(ReferenceProxy)` is False; critic2/k07). T5 defines `_idstr` and `_get_repr` explicitly, because the bridge reads them on every Reference.

| ID | Element | Kind | Origin |
|---|---|---|---|
| T1 | `_kind` class attribute | new | A N1 |
| T2 | `_is_dynamic()` on every kind | new (Space: existing) | B/C, judge 1 graft 8 |
| T3 | `_is_derived()` on Cells and References | new for References (Cells: existing) | A N4 |
| T4 | `BaseSpace._get_inheritance()` | new | C E12 + B "definition in use" |
| T5 | ReferenceProxy: equality, liveness, `_refmodes`, resolved slots | new + fix | B/C E13, A F2 |
| T6 | `_address`; `Model._get_from_name` extended | new + extended | C E6/E7, B grammar |
| T7 | `BaseNode._get_repr()` | new | B/C |
| T8 | `Model._get_revision()` | new | A N2 |
| T9 | `Model._get_serial()`, `Model._is_open()` | new | C E15 |
| T10 | `_get_referents()` (+ `chains`), `Model._get_formula_links()` | new | A N3 + B/C |
| T11 | `_has_formula()` | new | B (narrowed) |
| T12 | Exceptions | new, in `modelx.core.errors` | A N5 + C E3–E5 |
| T13 | `is_valid_name`, `get_model_info`, `read_model(if_exists=)` | new top-level | A N6 + C E21–E23 |
| T14 | `set_calc_hook`, `clear_calc_hook`, `CalculationCancelled` | new, **provisional** | C E24 |
| F1–F11 | Fixes to existing members | behaviour | A, C; F8–F11 from verification |
| S1–S3 | Existing tool API declared stable | contract | A E1–E3, C §7 |
| C1–C3 | Contracts on existing public calls | contract | A C1–C2, judges |

### 3.1 New members on objects

#### T1 `_kind`

- **Signature.** A class attribute:
  - `Model._kind = 'Model'`, `UserSpace._kind = 'UserSpace'`, `ItemSpace._kind = 'ItemSpace'`, `DynamicSpace._kind = 'DynamicSpace'`, `Cells._kind = 'Cells'`, `Macro._kind = 'Macro'`;
  - `ReferenceProxy._kind = 'Reference'`, `BaseIOSpec._kind = 'IOSpec'`;
  - `Interface._kind = None`.

  Read it with `getattr(type(v), '_kind', None)`. On a modelx object, `obj._kind` also works.
- **Returns.** A string from a vocabulary that only ever grows, or `None` for any other value.
- **Semantics.**
  - It names the exact kind. An ItemSpace is never reported as a DynamicSpace, although it subclasses one (space.py:2152).
  - Because it is a class attribute, reading it never runs `Model.__getattr__` or `BaseSpace.__getattr__`. It never evaluates, and it still answers on a deleted object or an object of a closed model.
  - The attrdict `'type'` becomes `type(self)._kind or type(self).__name__`. That is byte-identical today (minimal/m02).
  - Every Model, Space, Cells, Macro and Reference resolves from its own `_idstr` and `_address` through `Model._get_from_name` (T6), with the exceptions T6 lists. That includes macros: a macro's `_idstr` is its name (`'mac'`), and on 0.33 `_get_from_name('mac')` raises KeyError (measured g01). An IOSpec has no `_idstr` (io/baseio.py:335), so it has no address.
- **Capability table** (documented with it):

  | question | answer |
  |---|---|
  | holds child spaces | Model, UserSpace, ItemSpace, DynamicSpace |
  | holds Cells | the kind ends in `'Space'` |
  | makes ItemSpaces when called or subscripted | the kind ends in `'Space'` and `formula is not None`. The formula may have no parameters: `new_space('Z', formula='lambda: None')` has `parameters == ()`, and `Z()` is an ItemSpace. A DynamicSpace qualifies when its dynbase has a formula: `P[1].Child[2]` works. A Space without a formula has `parameters` None, and a call raises (T6). Measured g01, g05 |
  | editable | Model, UserSpace |
  | object to bind instead of an ItemSpace | walk `.parent` while the kind is `'ItemSpace'` |

- **Edge cases.**
  - A Reference whose value is a modelx object: the value reports its own kind. Only the proxy reports `'Reference'`. That holds for a resolved slot too (T5).
  - ExcelRange is both a Reference value and an IOSpec, so it reports `'IOSpec'`.
  - Views, nodes, and the Namespace objects formulas see report `None`. Views and nodes keep their class name as attrdict `'type'`.
  - Guard against a foreign class that defines `_kind`: test membership in the vocabulary. 0 of 34 common value types define `_kind` (minimal/m02).
- **Internals.** Class lines model.py:225, space.py:729, :2112, :2152, cells.py:66, macro.py:51, reference.py:126, io/baseio.py:335; `Interface` at base.py:350. The attrdict `'type'` is set at base.py:660, :690 and reference.py:199, :205.
- **Cost.**
  - 0.078 µs (minimal/m02).
  - A miss on a non-modelx value costs 0.253 µs (measured f01).
  - The bridge codec's in-function imports cost 1.68–1.73 µs today.

#### T2 `_is_dynamic()` on every kind

- **Signature.** `obj._is_dynamic() -> bool` on Model, UserSpace/ItemSpace/DynamicSpace, Cells, Macro and ReferenceProxy.
- **Semantics.** True when modelx generated the object inside an ItemSpace:
  - the ItemSpace itself and its DynamicSpace children;
  - their Cells;
  - the References an ItemSpace creates, i.e. its arguments, the refs its Space formula returns, and its resolved slots (T5).

  A dynamic object's formula, name, doc and `is_cached` belong to its dynbase, and editing them raises `DynamicObjectError` (T12). Input values are still accepted, so "dynamic" does not mean "read-only".

  It is False for:
  - the Model, every UserSpace, and Cells in a UserSpace;
  - Space-level and global References;
  - the dynbase bindings an ItemSpace shares (`P[1].k` is `P.k`).
- **Internals.**
  - Existing `BaseSpace._is_dynamic` (space.py:169-171) is kept.
  - New `CellsImpl.is_dynamic()` returns False, and `DynamicCellsImpl` (cells.py:1030) returns True.
  - `ReferenceProxy._is_dynamic()` returns `not impl.parent.is_model() and impl.parent.is_dynamic()`. That covers arguments (dynamic.py:296-300) and formula refs (dynamic.py:97-101). With T5 a resolved slot is a ReferenceImpl whose parent is the dynamic Space, so the recipe answers True (measured fix-reference-identity/g02).
  - `Model._is_dynamic()` and `Macro._is_dynamic()` return False.
- **Edge cases.**
  - Measured on 0.33 (f01): `P[1]._is_dynamic()` and `P[1].Child._is_dynamic()` are True; `Sub._is_dynamic()` is False.
  - On 0.33, `cells.parent._is_dynamic()` matched the impl truth for 739 of 739 Cells (minimal/m06). The bridge can fix its ItemSpace false negative today.
  - A deleted Cells raises DeletedObjectError through NullImpl (base.py:332).
  - Cost: 0.166 µs for a Space (measured f01).

#### T3 `_is_derived()` on Cells and References

- **Signature.** `obj._is_derived() -> bool` (ReferenceProxy: `bool | None`).
- **Semantics.** True when the Cells or Reference has no definition of its own here: it is inherited from a base Space, or it is a dynamic copy. Spaces and Models have no `_is_derived()`: no Space is ever inherited (decision 4), and a dynamic Space is told by `_is_dynamic()` (T2).
  - `Cells._is_derived()` (cells.py:582-583) is unchanged. Measured f01: `Sub.bar` True, overridden `Sub.foo` False, `P[1].h` True, `P[1].Child.w` True.
  - New `ReferenceProxy._is_derived()` returns `impl.is_derived() if isinstance(impl, ReferenceImpl) else None` (reference.py:27; base.py:313-314). The guard stays even after T5, so spyder's whole-model extattr walk can never raise.
  - A resolved slot answers True: it is a dynamic copy, like `P[1].h` (measured fix-reference-identity/g02).
  - `ReferenceProxy.is_derived()` (reference.py:193) stays as an alias (decision 11).
- **Compositions** (documented):
  - inherited = `_is_derived() and not _is_dynamic()`;
  - generated = `_is_dynamic()`;
  - overriding comes from T4.
- **Edge cases.**
  - A Model-level Reference seen through a Space answers False (inventory probe4).
  - On 0.33 a naive alias raised `AttributeError: 'DynamicSpaceImpl' object has no attribute 'is_derived'` inside the whole-model `_get_attrdict` (minimal/m05). It also raises for `P[1]._get_object('rel', as_proxy=True).is_derived()` (measured f01).
  - With `'_is_derived'` requested as an extattr, Reference rows gain the key, which fills their blank "Is Derived" cells in spyder. Space and Model rows keep no key and stay blank (mxtreemodel.py:121-124), which is the right answer (decision 4).
  - Cost: 0.104 µs for Cells (measured f01).

#### T4 `BaseSpace._get_inheritance()`

- **Signature.** `space._get_inheritance() -> dict`
- **Returns.**
  ```python
  {'bases':        [UserSpace, ...],   # == space.bases (C3 MRO); [dynbase] for a dynamic Space
   'direct_bases': [UserSpace, ...],   # as added; [dynbase] for a dynamic Space
   'cells': {name: {'state': 'defined' | 'overriding' | 'derived',
                    'defined_in': UserSpace}},
   'refs':  {name: {'scope': 'space' | 'base' | 'argument' | 'formula' | 'global' | 'builtins',
                    'state': 'defined' | 'overriding' | 'derived' | None,
                    'defined_in': UserSpace | Model | None}}}
  ```
- **Semantics.** One bulk read per Space, computed with a single MRO walk. It evaluates nothing.
  - `defined_in` is where the definition in use lives: the Space itself for `defined` and `overriding`, otherwise the first base in MRO whose member is defined.
  - A dynamic Space reports its dynbase's states. Its refs carry scope `argument`, `formula` or `base`.
  - Scope `builtins` marks the reserved `__builtins__`, which replaces the bridge's `'_'` filter.
  - Until 0.36, a user global named with `_` has scope `'global'`, a `_` Space Reference made by `new_space(refs=)` has scope `'space'`, an ItemSpace argument with a `_` parameter name has scope `'argument'`, and a `_` ref a Space formula returns has scope `'formula'` (C2(2)). A tool that wants today's view also drops those `_` names.
  - The system references `_self`, `_space` and `_model` (`sys_refs`, space.py:1973-1977) are never reported, because the public `refs` view leaves them out (fix-spyder-snapshot/s01). T10 lists them under `'system'`.
  - It serves the "inherited"/"overrides" badges, own vs inherited vs global References, and a per-Space roll-up (count the states).
- **Internals.**
  - Normalise first: `static = impl._dynbase if impl.is_dynamic() else impl` (dynamic.py:80, :202-203).
  - MRO from the SpaceManager graph (inheritance/graph.py:96-139; manager.py:96-119).
  - Cells states from Derivable (base.py:296-329) and the sets of base member names.
  - Reference scopes from the ChainMap layers:
    - UserSpace: `own_refs` / `_global_refs`, the layers of `refs_outer` (space.py:2268-2269). `sys_refs` is in `refs` only, and is skipped;
    - dynamic: `_allargs` / `own_refs` / `_dynbase_refs` / `_global_refs`, the layers of `refs_outer` (dynamic.py:114-128). A resolved slot (T5) is in `_dynbase_refs`, so its scope is `'base'`;
    - `__builtins__` at model.py:1220-1222.
  - Requires fix F6.
- **Measured.**
  - Whole-model cost (inheritance/i04): 9.6 µs on BasicTerm_S, 58.3 µs on BasicTermASL_ME, 112.7 µs on simplelife. Per-member `Derivable.bases` costs 382, 717 and 1,768 µs.
  - The same state and scope rules, as consumer recipes on 0.33, had 0 mismatches over 739 Cells (230 derived, 4 overriding) and 179 Reference names (minimal/m06).
- **Edge cases.**
  - An ItemSpace whose base the formula chose (`{'base': X}`) takes its argument names from `parent.parameters`.
  - A derived relative ref to a base's child Space resolves to a null object (inventory). It is reported with `state='derived'`, not resolved.

#### T5 ReferenceProxy as a tool object

- **Signature.**
  - `__eq__`/`__hash__` by binding: `isinstance(o, ReferenceProxy) and o._impl is self._impl`, and `hash(id(self._impl))`.
  - A stricter `_is_valid() -> bool`.
  - A class attribute `_refmodes = ('auto', 'absolute', 'relative')`.
  - Explicit definitions of `_kind`, `_is_dynamic`, `_is_derived`, `_address` and `_has_formula`, and of the existing `_idstr` and `_get_repr`, each with a signature-golden entry. On 0.33 a proxy answers `_idstr` and `_get_repr` only through `__getattr__` forwarding (measured fix-final/k07), and the bridge reads both on every Reference (`_objid`, methods.py:2745-2749; `_display`, methods.py:2829-2848). ReferenceProxy gets no `_get_referents` or `_get_formula_links`: neither is on Interface, so forwarding keeps raising AttributeError (T10; fix-used-by/u06).
  - A resolved slot gets a binding of its own (decision 7).
  - `UserSpace.set_ref` validates `refmode` (F2).
- **Semantics.**
  - Two proxies to one binding are equal and hash equally. Today `a == b` is False although `a._impl is b._impl`, so `{a, b}` has 2 elements (measured f01).
  - `_is_valid()` is True only while the parent impl still owns its interface, `impl.parent.interface._impl is impl.parent`, and the container the binding records still holds it, `impl.container.get(impl.name) is impl`. Every ReferenceImpl records its container in its own `container` slot (reference.py:28-48): `global_refs` for a global, `own_refs` for a Space Reference or a formula ref, the ItemSpace's `_arguments` for an argument (identity_naming/p08b), `sys_refs` for a system name, and the dynamic Space's `_dynbase_refs` for a resolved slot. Measured (fix-used-by/u04): the container test is True for global, Space, derived, argument, formula-ref and system bindings while they are live, and False after a rebind or a delete. Today a proxy kept across a rebind or delete answers True (identity_naming/p08b).
  - `refmode` is one of `_refmodes` for Space References, formula refs and resolved slots, and `None` for global References and ItemSpace arguments. The docstring at reference.py:176-191 is corrected.
  - **Resolved slot (decision 7).** Inside an item tree, a relative Reference whose target is in the same tree is re-pointed at the in-tree copy. Take `P.rel = P.Child` with a formula on `P`. Today `wrap_impl` (dynamic.py:140-177) returns `P[1].Child`'s DynamicSpaceImpl, and `_init_dynbaserefs` (dynamic.py:130-138) stores that raw impl in `P[1]`'s slot. The same happens for a target that is a Cells in the tree or the ItemSpace itself.

    In 0.34 the slot gets a ReferenceImpl of its own. `_init_dynbaserefs` wraps the in-tree object with parent = the dynamic Space, `container = _dynbase_refs`, `is_derived=True` and the binding's refmode. `BaseSpaceImpl.on_update_ns` (space.py:1985-1996) keeps putting the target's namespace into `ns_dict` for such a slot, as 0.33 does, so formulas see exactly what they see today. The slot is then a Reference like an ItemSpace argument. Through `P[1]` (measured g02):
    - name `'rel'`, parent `P[1]`, `_idstr` `'P.__Space1.rel'`, `_address` `'P(1).rel'`, `_evalrepr` `'G2.P(1).rel'` in model `G2`;
    - `.value` is `P[1].Child`, the object a formula in `P[1]` sees;
    - its own `_idstr` and `_address` resolve back to it (T6);
    - `_is_dynamic()` and `_is_derived()` are True, like `P[1].h`. `refmode` is the binding's (`'auto'`);
    - it equals neither `P[2].rel` nor `P.rel`. Each has its own binding and its own value;
    - `_is_valid()` turns False when its ItemSpace goes, and stays False when an ItemSpace with the same arguments is built again.

    The binding it was made from is `r.parent.bases[0]._get_object(r.name, as_proxy=True)`, because `bases` of a dynamic Space is `[dynbase]` (dynamic.py:210-215; T4 `'bases'`). T10's "used by" for a slot goes through this. Measured True for `P[1].rel` and the nested `P[1][5].rel` (g02).

    Every other Reference seen through an ItemSpace keeps its 0.33 identity:
    - A dynbase binding that is not re-pointed is the static binding itself. That covers a value that is not a modelx object, an absolute Reference, a target outside the tree and a target that is a null object (dynamic.py:144, 159-177). `P[1].k`'s proxy is `P.k`'s, with `_idstr` `'P.k'`; `P[1].out` is `'P.out'` (measured g01, g02, critic_complete/c05).
    - A global is the Model's binding (`'glob'`).
    - Arguments and formula refs already have their own impl in the ItemSpace (`'P.__Space1.i'`, r02).

    Today the slot's proxy wraps the raw impl. Its name is the target's (`'Child'`), `_idstr` is `'P.__Space1.Child'`, `is_derived()` raises AttributeError, and `.refmode` raises `AttributeError: type object 'Interface' has no attribute 'refmode'` (measured f01, re-run in g01). Inside a formula of `P[1]`, `_space.rel` raises AssertionError at space.py:1888, which expects a ReferenceImpl. With the wrapped slot, `P[1].viaspace()`, which reads `_space.rel.w()`, returns 10 (measured g01, g02).
- **Internals.**
  - `DynamicSpaceImpl._init_dynbaserefs` (dynamic.py:130-138) wraps what `wrap_impl` returns when it is not a ReferenceImpl. There is no new slot; the ReferenceImpl goes into the existing `_dynbase_refs` dict (dynamic.py:116).
  - `BaseSpaceImpl.on_update_ns` (space.py:1985-1996) maps such a slot to `v.interface._impl._namespace` when the target is a Space.
  - `wrap_impl`'s in-tree test needs a dot boundary: `impl == root or impl.startswith(root + '.')`. Today it is `root == impl[:rootlen]` (dynamic.py:156). A Reference from `P` to a sibling `PX` is then taken as in-tree, `get_impl_from_name` returns `None`, and `P[1]`'s slot holds `None`. `P[1].h()` raises `AttributeError: 'NoneType' object has no attribute 'interface'` and `P[1].r` is missing (measured g06). Without this fix the wrapping above would fail when the ItemSpace is created. With it, `P[1].r` is the binding `'P.r'` and `P[1].h()` returns 5 (measured g06b).
  - No 0.33 pickle carries a raw slot into 0.34: `pickle.dumps(model)` raised AttributeError on 0.33 for a static model, after a calculation and with an ItemSpace (measured g04b).
- **Measured** (g02, g03, g04, g07). The prototype patches `_init_dynbaserefs` and `on_update_ns` inside the probe process; it is compared with doc0's design, a proxy over the dynbase binding carrying the in-tree value. A proxy passes when `_get_from_name(x, as_proxy=True)` on its own `_idstr`, and again on its `_address`, returns an equal proxy whose `.value` is the same object, and that object is what a formula in that Space sees.

  | model | resolved slots | this design | doc0's design |
  |---|---|---|---|
  | synthetic: `P[1]`, `P[2]`, nested `P[1][5]`, their `Child`, `Q(1)`, `Z()`, `T((1, 2))`, `T(None)`, `T(1.5)` | 19 | 75 of 75 | 56 of 75 |
  | simplelife, with `Projection(1)`, `Projection(2, 1)`, `Economic(1)` | 14 | 72 of 72 | 58 of 72 |
  | BasicTerm_SE with 2 items; BasicTerm_ME; CashValue_ME; BasicTerm_S | 0 | all (21, 6, 11, 6) | all |

  - The case is in lifelib. simplelife's `Projection.pol` is its child `Projection.Policy`, so `Projection[1, 1].pol` is `Projection[1, 1].Policy`. Each Projection item has 7 resolved slots: `pol` and `asmp` hold Spaces, and `PremTerm`, `gen`, `polt`, `prod` and `sex` hold Cells (measured g03b).
  - doc0's design fails exactly the resolved slots. Their id is the binding's (`'P.rel'`), which resolves to `P.Child`, not `P[1].Child`; `P[1].rel == P[2].rel` while their values differ; and the proxy stays valid after `del P[1]` and `P.clear_items()` while its value is deleted.
  - Formula results and `len(tracegraph)` are the same with and without the prototype: simplelife `PV_NetCashflow(0)` for 3 projections (5,142 nodes), and BasicTerm_SE `Projection[1].pv_net_cf()` = 108625.005624 (2,416 nodes). `_check_sanity` passes after deletes.
  - Recomputing `P[1].h()`, which reads `rel.w()`, costs 16.0–17.5 µs against 15.8–16.1 µs on 0.33 (g07: minimum of 7 × 20,000 calls, 3 processes each). `ns_dict` holds the same object as on 0.33, so the formula runs the same code and the spread is noise (inferred). Without the `on_update_ns` rule the formula reads through the Interface and costs 16.9–18.7 µs.
  - Memory: one ReferenceImpl per resolved slot, 7 per simplelife Projection item (g03b).
- **Edge cases.**
  - `del P[1]`, `P.clear_items()` and a rebind of `P.rel`, which deletes all of P's ItemSpaces (measured g01), each make a kept slot proxy answer `_is_valid()` False (measured g02).
  - An argument proxy whose ItemSpace was cleared passes the container check, so the parent check is needed (identity_naming/p08b; fix-used-by/u04). The same holds for a slot and a formula ref.
  - The parent check compares impls. It must not ask the parent's interface: re-creating an ItemSpace with the same arguments re-uses the old interface objects (`dynamic_cache`, space.py:1846-1854; `cache._impl = self`, dynamic.py:81-83; child DynamicSpaces, dynamic.py:256-262), and the old ItemSpace's dicts are never emptied. With `impl.parent.interface._is_valid()` as the parent check, a kept slot, argument or formula-ref proxy answered True again after `del P[3]; P[3]`, after `P.clear_items(); P[3]` and after a rebind of `P.rel` followed by `P[3]`. After `del P[3]; P[3]` the old slot's `_idstr` `'P.__Space1.rel'` no longer resolved (the live slot is `'P.__Space2.rel'`), and its impl was not the live slot's. With the impl test it answered False in all three cases, and Space, derived and global bindings answered as before (measured refute2/r08, r08b; fix-final/e03).
  - A closed model's bindings stay valid, as the closed Model's own `_is_valid()` does (T9). A host tests `model._is_open()` (measured fix-final/e03).
  - Rebinding a base Reference replaces every derived copy's ReferenceImpl (fix-used-by/u04), so a proxy to `Sub.k` goes stale when `Base.k` is rebound.
  - An argument with the name of a dynbase Reference hides it: BasicTerm_SE's `Projection[1].point_id` is the argument (measured g03).
  - `refmode='sideways'` is stored silently today (measured f01) and later fails with "must not happen" (values_formulas/p4b). 0.34 raises ValueError.
  - `space.x = v` resets the mode to `'auto'` (parent.py:98). Documented, not changed.

#### T6 `_address` and the extended `Model._get_from_name`

- **Signatures.**
  - `obj._address -> str | None` (a property on Interface, defined explicitly on ReferenceProxy).
  - `Model._get_from_name(name: str, as_proxy: bool = False)`.
- **`_address` returns** a model-relative address in call syntax. It is `_evalrepr` without the model name, except that a numpy scalar is written as its Python value (`T(np.int64(7))` gives `'T(7)'`, itemspaces_dynamic/p08):
  - `'Projection(1).claims'`, `'P(1).Child.w'`, `'P(1)(5).h'`, `'Q(1, 2).z'` (defaults bound), `'T((1, 2)).v'` (one tuple-valued argument);
  - `'Z().c'` for a Space formula with no parameters;
  - `'P(1).rel'` for a resolved slot (T5), and `'P.k'` for a binding an ItemSpace shares with its dynbase;
  - `'glob'` for a global Reference, `'mac'` for a macro, and `''` for the Model;
  - the same as `_idstr` outside ItemSpaces;
  - `None` when an argument is not a literal. Literals are int, finite float, complex, str, bytes, bool, None, and tuples of these; numpy scalars go through `.item()`. A date, a Space or an arbitrary object gives `None`.
- **Resolver semantics.**
  - It accepts three forms. They cannot collide, because member names cannot contain `(` or `[`:
    - the `_idstr` form, `'P.__Space1.h'`;
    - the call form, `'P(1).h'`;
    - the subscript form, `'P[1].h'`. It follows Python's subscript rule, plus one addition: `[]` means no arguments. So `'Z[].c'`, which is how modelx displays `Z().c`, resolves, although `ast.parse` rejects it (measured g01). By the same Python rule `'T[(1, 2)]'` means two arguments, so the display string of a single tuple-valued argument misses. Its address `'T((1, 2))'`, or `'T[(1, 2),]'`, resolves (measured g02).
  - `''` returns the Model.
  - A one-segment name resolves in the order of `Model.get_attr` (model.py:1323-1333): a Space, then a global Reference, then a macro.
  - Later segments resolve members first and never class attributes, so a Cells named `bases` is found. A `__SpaceN` segment resolves a named ItemSpace.
  - `__builtins__`, `_self`, `_space` and `_model` are refused, as the first segment or a later one. Every other `_` name resolves like any member. Until 0.36 the public `refs` views list user `_` globals, `_` Space References made by `new_space(refs=)`, `_` ItemSpace arguments and `_` formula refs (C2(2)), so their ids must resolve. Measured with reference-identity's prototype (fix-integrate/i03), on a model with a global `_ug`, an argument `_a` and a formula ref `_fr`: refusing every `_` name except `__SpaceN` failed 10 of 18 Reference proxies, through both `_idstr` and `_address`. Refusing only the four resolved 18 of 18, and still refused all four, including `S._space` and `Q(1)._space`.
  - Arguments bind as a call would, with defaults applied, so `'Q(1).z'` finds `Q(1, 2).z`. Then the existing ItemSpace is looked up. It **never creates** one.
  - A final Reference segment yields its value (unchanged), or, with `as_proxy=True`, the proxy of that Space's slot. A resolved slot therefore comes back as itself (T5).
  - Every miss raises `ObjectNotFoundError`. That includes an unknown name, a missing ItemSpace, arguments a call would refuse, and any arguments on a Space without a formula.
  - A name without `(` or `[` takes the plain `split('.')` path, with no `ast` cost.
- **Round trip.** For every Model, Space, Cells and macro `o`, `_get_from_name(o._idstr)` and `_get_from_name(o._address)` return `o`. For every Reference proxy `r`, the same calls with `as_proxy=True` return a proxy equal to `r` whose `.value` is the same object. The exceptions:
  - `__builtins__`, `_self`, `_space` and `_model` are refused, by design;
  - `_address` is `None` for a non-literal argument. The `_idstr` still resolves;
  - an `_idstr` with `__SpaceN` is good only for the session, and goes stale when the ItemSpace is re-created (see Edge cases);
  - a macro hidden by a Space, a 0.33 case that F10 removes. A macro whose name a Space also uses resolves to the Space. `new_macro` refuses a used name (model.py:1377-1378), but a Model-level `new_space` checks only `parent.namespace`, which has no macros (inheritance/manager.py:69-70). Measured g01: `new_space('mac')` succeeds while macro `mac` exists, and `m.mac` is then the Space. F10 refuses that name in `new_space`, which closes the gap in 0.34. No saved model loses by it: such a model writes on 0.33, but `read_model` raises `ValueError: Name 'mac' already used` (measured fix-integrate/i01).
  - an ItemSpace argument, or a ref the Space formula returns, that has the name of a Cells or child Space of its Space. modelx accepts that: with the Space formula `lambda h: {'refs': {'g': 100}}` and Cells `h` and `g`, `P[7]` holds the argument `h` and the ref `g` beside the Cells `h` and `g`, and a proxy and a Cells share each `_idstr`, `'P.__Space1.h'` and `'P.__Space1.g'`. Today `_get_from_name('P.__Space1.h')` returns the Cells, while `_get_object('h', as_proxy=True)` returns the argument. The resolver resolves members first, so it gives the Cells for the `_address` `'P(7).h'` too (inferred). A formula in `P[7]` reads the Cells by its bare name and the argument through `_space.h` (measured refute2/r11, re-run in fix-final). Decision 9 warns on such a name from 0.34, either way round. No lifelib model has one: 0 of 9 (refute2/r12).
- **Internals.**
  - `_idtuple` (base.py:717-722; ItemSpace at space.py:2201-2203) and `argvalues` (dynamic.py:304-307).
  - `ModelImpl.get_impl_from_name` (model.py:1266-1273), `ModelImpl.get_attr` (model.py:1323-1333) and `BaseSpaceImpl.get_impl_from_namelist` (space.py:2072-2091).
  - Global refs (model.py:1256); macros in `ModelImpl._macros` (model.py:1226).
  - Arguments bind through `get_node` (execution/trace.py:52) into `param_spaces` (space.py:1728).
  - Call and subscript syntax are parsed with `ast.parse(mode='eval')` and `ast.literal_eval`. `[]` is rewritten to `[()]` first. When the text holds a quote character, the rewrite goes through `tokenize`, so a `'[]'` inside a string argument is left alone (measured g02: `"T['a[]b'].v"` resolves).
  - Fix: calling a Space without a formula raises TypeError "takes no arguments" instead of `AttributeError: 'NoneType' object has no attribute 'signature'` (execution/trace.py:109-112). Measured g01: `NF(1)` and `NF.node(1).has_value()` both raise that AttributeError. A formula with no parameters is a different case: `Z(1)` already raises TypeError "too many positional arguments".
- **Today (measured f01, g01):**
  - `_get_from_name('')`, `_get_from_name('glob')` and `_get_from_name('mac')` raise KeyError;
  - `_get_from_name('Base.k')` returns 2;
  - a nested miss raises `AttributeError: 'NoneType' object has no attribute 'interface'`;
  - `_get_from_name('P.__Space1.rel')` already returns the in-tree `P[1].Child`, but it has no `as_proxy`.
- **Measured.**
  - A prototype of these semantics with T5's resolved slots (g02, g03) round-tripped every object and every Reference proxy through both `_idstr` and `_address`, and created 0 ItemSpaces. No address was `None`, because every argument was a literal.

    | model | objects | Reference proxies |
    |---|---|---|
    | synthetic (g02), with a macro, `Z()` and `T((1, 2))` | 44 of 44 | 75 of 75 |
    | simplelife, 3 ItemSpaces | 538 of 538 | 72 of 72 |
    | BasicTerm_SE, 2 ItemSpaces | 139 of 139 | 21 of 21 |
    | BasicTerm_ME / CashValue_ME / BasicTerm_S | 47 / 82 / 42 | 6 / 11 / 6 |

  - Cost (g07: minimum of 7 × 20,000 calls, 3 processes): resolving `P[1].rel` with `as_proxy=True` takes 3.3–3.9 µs by `_idstr` and 11.5–12.4 µs by `_address`; `'Z().c'` takes 6.6–7.1 µs and `'Z[].c'` 7.9–8.8 µs.
  - An earlier prototype resolved `_idstr` → `_get_from_name(..., as_proxy=True)` for 179 of 179 objects. Resolving a Reference cost 1.86 µs, against 3.02 µs for the bridge's `_resolve` (tool_contract/p04). It compared `_impl` only, never values, and predates T5's slots.
  - 11 of 11 literal address cases round-tripped with 0 ItemSpaces created (itemspaces_dynamic/p08). Building a nested address costs 7.5 µs; resolving one costs 16.1 µs, dominated by `ast.parse`.
  - The 0.33 fallback walk (`_idtuple` plus `node(*args).has_value()`/`.value`) round-tripped 62 of 62 objects and created nothing (minimal/m03).
  - `P.node(99).has_value()` and `Z.node().has_value()` created nothing (measured f01, g01).
- **Edge cases.**
  - `True` and `1` share an ItemSpace key, by dict semantics.
  - `nan != nan`, so its address is `None`.
  - A stale `__SpaceN` id can name *different* arguments after the parent is re-created or the model is re-read (identity_naming/p03, itemspaces_dynamic/p05). An address resolves to the same arguments or misses.
  - A Space formula with no parameters: `Z()` and `Z[()]` are the same ItemSpace. Its key in `Z.itemspaces` is `None`, but `Z[None]` raises TypeError "too many positional arguments" (measured g01). Its address is `'Z()'`.
  - To create an ItemSpace, call the Space.

#### T7 `BaseNode._get_repr()`

- **Signature.** `node._get_repr(fullname=True, add_value=False) -> str`
- **Semantics.** Gives the node's display name with arguments by parameter name, e.g. `'BasicTerm_S.Projection[2].claims(t=3)'`. It is `ItemNode.__repr__` without `=value`, and it uses F1's ItemSpace labels. Tools stop formatting `(t=3)` themselves.
- **Internals.** Factored from node.py:152-168 and :215-238.

#### T8 `Model._get_revision()`

- **Signature.** `Model._get_revision() -> tuple[int, int, int] | None`
- **Returns.** `(edits, values, saved)`, three stamps from one process-wide monotonic clock. A stamp is never reused across models or across a close and re-read. It returns `None` for a closed model. It is a plain tuple, so it pickles with no modelx class in it, for spyder's transport.
  - `edits` moves when what `write_model` would save changes.
  - `values` moves when stored values or the trace change.
  - `saved` is the `edits` stamp at the end of the last successful `read_model`, `write_model` or `zip_model` of this model. It is 0 when there was none; the clock starts at 1.
- **Semantics.**
  - `edits` moves on every change to what `write_model` saves (the encoders at serializer_6.py:547-824, macros at serializer_7.py:176, IOSpecs at serializer_8.py:406-429):
    - the definition: Spaces, Cells, References and refmodes, bases, Space and Cells formulas, docs, `allow_none`, `is_cached`, names, member order and macros;
    - input values, in UserSpaces and inside ItemSpaces, which are saved as `_dynamic_inputs` (serializer_6.py:685-736);
    - IOSpecs: a new, changed or deleted spec, a spec's path or sheet, and an ExcelRange cell set through the range.
  - `edits` never moves during evaluation. That includes building ItemSpaces and their DynamicSpaces, a Space formula that returns `base` or `refs`, failed evaluations and uncached Cells.
  - One calculation API moves `edits` by design: `Model.execute_actions` (model.py:843-849), the memory-optimised run. Its `paste` steps call `set_value_from_key` outside a formula, so the values become inputs and `write_model` saves them. Measured (refute2/r10, re-run in fix-final): `generate_actions` + `execute_actions` changed the written model and moved `edits` and `values`. A host then shows the run as an unsaved edit, which it is.
  - `edits` does not move on a save or a read, or when `Model.path` changes. The path is not saved in the model. It says where the model was last read or written.
  - `values` can move on a save. The `Model.path` setter clears every value computed from `_model.path` (model.py:489-494, through `clear_attr_referrers`, a `values` bump point), and `write_model` to a new path sets `model.path` (serialize/__init__.py:125-126). Measured (refute2/r13, re-run in fix-final): with a Cells `lambda: str(_model.path)` computed, a save to a new path cleared it and moved the stamps from (4, 6, 4) to (4, 7, 4). That is correct, because a value was cleared.
  - `values` moves when stored values or the trace change:
    - a top-level evaluation after which the trace graph or the reference graph has more or fewer nodes. Failed evaluations count when they leave nodes, which fixes the bridge's deferred defect B1 (PLAN.md:457);
    - a clear that removed a node;
    - an input set;
    - creating or deleting an ItemSpace.
  - An uncached Cells moves `values` only on a call that adds a node or a reference edge (`CallStack.pop`, executor.py:262-288). That happens on its first call with given arguments when its formula reads a Reference by attribute (`_space.x`), and on a cached caller's first call. A repeated call with the same arguments moves nothing, and an uncached Cells that only reads cached values never moves it. This keeps the bridge out of the bump loop at methods.py:337-341.
  - Nothing that only reads moves a stamp: cached calls, `node`/`preds`/`precedents`, attrdicts, `series` and `frame`, and a macro that only reads.
  - A refused edit moves nothing, because the edit is rolled back.
  - A stamp is not a content hash. `edits` moves even when the saved content ends up the same: `sort_cells` on sorted Cells, an input set to its current value, or an input on a derived Cells, which `write_model` does not save (serializer_6.py:610; measured p07). Undoing an edit does not move it back.
  - A host sees one move per call. Some calls pass two or three bump points: deleting a Cells that holds inputs passes the editor and then one point per input key. A host reads between calls, so it sees one new stamp.
- **How a host uses it.**
  - `rev != last` means something moved. `rev[:2] != last[:2]` means the content moved. A save or a read moves `saved`, and moves `values` only when it changes `model.path` and that clears a value (above).
  - `rev[0] != rev[2]` means the model is dirty: it has edits that no read or write has matched. This is a fact about the model, not about one host. A save made from the Console, by spyder or by modelx-mcp's `run_python` makes the model clean for every host, and no host keeps a baseline.
  - A model made by `new_model` and never written is dirty.
  - If only `values` moved, re-read only value and trace payloads.
- **Internals.**
  - Storage is on System (system.py:75-105): `_clock = itertools.count(1)` and `_revisions = {ModelImpl: [serial, edits, values, saved]}`.
    - The entry is created in `System.new_model` (system.py:180-187) and dropped in `close_model` (system.py:236-240).
    - The failure path of `SystemStateSnapshot` (serialize/reader_state.py:19-40) must drop the entry of the model it discards (inferred).
    - `SystemStateSnapshot` also copies every open model's entry when it is taken, and `restore()` puts each one back after its renames. `restore()` renames a displaced model back through `System.rename_model` (reader_state.py:30-34), an `edits` bump point, and `saved` is never set on a failed read. Measured with proto_t8 (refute2/r01, critic2/k06, fix-final/e01): a clean model whose name a broken copy's read displaced went from (3, 1, 3) to (8, 1, 3), dirty, through four bump points, and writing it again gave files identical to the saved copy. With the entries put back, a clean model stayed (3, 1, 3) and a dirty one (12, 9, 11), and a successful read still left the displaced model dirty.
  - **Bumps are inline**: each is one call written inside the method body, and no method is wrapped or replaced. The reader dispatches instructions by method `__name__` (serializer_6.py:297-302) and calls `UserSpaceImpl.set_formula` by that name (serializer_6.py:1028-1035, 1343-1352). A wrapping prototype silently dropped every Space formula on read_model (change_detection). A plain wrapper on `ItemSpaceParent.set_formula` did it again: BasicTerm_S's `Projection.formula` read back as `None`, and `Projection[2]` raised AttributeError (measured, fix-revision-counter/p03c).
  - **`edits` bump points:**
    - `ModelEditor.execute`, after `commit()` and `_finalize` (edit/pipeline.py:76-86). It covers new, delete, rename, copy and sort of Cells and Spaces; Cells formulas, docs and `is_cached`; Space and global References and refmodes; bases.
    - The six UserSpace members that set or delete a Space formula, after the impl call returns: the `formula` setter and deleter, `set_formula`, the `parameters` setter and deleter, and `del_formula` (space.py:1582-1697).
      - **Not** `ItemSpaceParent.set_formula`/`del_formula` (space.py:1744-1770). `ItemSpaceParent.__init__` calls `set_formula` (space.py:1730-1731) every time an ItemSpace or one of its DynamicSpaces is built (dynamic.py:86-90). Measured: it ran 35 times in the 15 evaluation workloads of p03, once per ItemSpace and 3 times for `D[1].In[2].v()`. With the bump placed there, `Projection[2].pv_net_cf()` moved `edits` (p08; also critic_complete/c03).
      - The reader sets Space formulas through the impl, so a read passes none of these six. It ends with `saved = edits` anyway.
    - The `doc` setters of Model (model.py:430-432) and UserSpace (space.py:1699-1701). A Cells doc goes through the editor (cells.py:953-965).
    - The `allow_none` setter (base.py:648-650), for Model, Space and Cells.
    - Macros: `ModelImpl.new_macro` (model.py:1363-1386), `MacroImpl.set_formula` (macro.py:185-192), and `ModelImpl.del_macro` (model.py:1389-1400). `del m.mac` reaches `del_macro` without the editor (model.py:1345-1350).
    - `System.rename_model` (system.py:189-202), including read_model's displacement to `<name>_BAK<n>`. A failed read's rename back is undone with the snapshot's copy (above).
    - Inputs:
      - `CellsImpl.set_value_from_key` outside a formula (cells.py:840-857) moves `edits` and `values`.
      - `CellsImpl.on_clear_trace` of an input key (cells.py:873-876) moves `edits`. Every path that drops an input passes it: `clear_at`, `clear_all`, `clear_cells(clear_input=True)`, an editor clear, and deleting an ItemSpace that holds inputs (space.py:2105-2108).
    - The deprecated `UserCellsImpl.reload` (cells.py:947-951), when the source changed. `UserSpace.reload()` reaches it without the editor (space.py:1047-1073 → 2451-2477).
    - IOSpecs, which live on the process-wide IOManager:
      - `IOManager.del_spec` (io/baseio.py:277-282), reached by `Model.del_spec` (model.py:168-181);
      - `IOManager.update_spec` (io/baseio.py:300-304), e.g. the `PandasData.sheet` setter (io/pandasio.py:321-323);
      - `IOManager.update_path` (io/baseio.py:306-318), reached by every spec's `path` setter (io/baseio.py:437-438);
      - `ExcelRange.__setitem__` (io/excelio.py:555-557).

      IOManager has no model pointer, so these bump every open model whose ValueRegistry holds the spec's value (refs.py:125-126). `new_pandas`, `update_pandas` and `update_module` already go through the editor (refs.py:180-204).
  - **`values` bump points:**
    - The top-level miss branch, `eval_node` → `_start_exec` (execution/executor.py:43-47, 67-118; ThreadedExecutor at :167-213). It reads the node counts before the run and compares them in a `finally`. Read them as `len(tracegraph._node)` and `len(refgraph._node)`. That is what networkx's `__len__` returns, without its Python-level call.
    - `TraceManager.clear_with_descs`/`clear_obj`/`clear_attr_referrers` (execution/trace.py:205-246), when a node was removed.
    - `set_value_from_key`, above.
  - **`saved`** is set to `edits` at the end of `serialize.write_model` (serialize/__init__.py:99-127) and of `serialize.read_model` (:130-158). `write_model`, `zip_model`, `Model.write` and `Model.zip` all reach the first. A write that raises leaves `saved` unchanged. The `Model.path` setter (model.py:489-494) is not an `edits` bump point; it moves `values` only when it clears a value (Semantics).
- **Measured.** The prototype `fix-revision-counter/proto_t8.py` installs exactly these bump points in-process (CPython 3.11.15, modelx 0.33.0). Each probe writes the model before and after the call and compares the files, with `.xlsx` files compared by their members minus timestamps.
  - **The 46-case edit-by-state matrix** (p01, the cases of change_detection/p06): a stamp moved in 46 of 46.
    - `edits` moved in 42. The file changed in 40 of them; the other 2 are `sort_cells` on sorted Cells.
    - The other 4 cases are `clear_all` + recompute and an ItemSpace creation. They left the file the same and moved only `values`.
    - No case changed the file without moving `edits`.
    - The bridge's `_fingerprint` and `_touch_key` both missed 23 of the 46 (change_detection/p06, re-run in minimal/m06_rerun_p06_out.txt).
  - **70 more calls** (p02): macros (new, replace, delete), all six Space-formula members, docs, `allow_none` on three kinds, renames, copies, bases, References and refmodes, inputs and their clears in UserSpaces and ItemSpaces, IOSpecs (new, sheet, path, `del_spec`, `update_pandas`, an ExcelRange cell, a module update), `reload`, `Model.path` by hand, and evaluation.
    - The file changed in 61, and `edits` moved in all 61.
    - `edits` also moved once with the file the same: an input set to its current value.
    - One call raised: `Cells.clear_formula()` is broken on 0.33. It calls `set_cells_formula` without its `func` argument (cells.py:466-470). F9 fixes it.
    - 9 calls passed two or three bump points; each showed one move.
  - **The earlier list** (p08: the design's own prototype plus its `ItemSpaceParent` and `Model.path` points) missed 7 of these paths: `del m.mac`, `PandasData.sheet`, two spec `path` setters, `del_spec`, an ExcelRange cell and `UserSpace.reload()`. It also moved `edits` on `Projection[2].pv_net_cf()` and on the first save (also refuter/r05, r11).
  - **Evaluation** (p03): 15 workloads on BasicTerm_S, BasicTerm_SE (20 ItemSpaces), BasicTerm_ME, CashValue_ME, simplelife (nested ItemSpaces), and a synthetic model with nested ItemSpaces, a Space formula returning `base` and `refs`, and uncached and failing Cells. They passed 0 `edits` bump points, and the written model stayed the same in all 15. simplelife's `Input/input.xlsx` differs by 20 bytes per sheet between the first and second write after `read_model`, with or without evaluation; later writes are identical (p03b).
  - **Saves** (p04):
    - `write_model` to a new path and to the same path, `zip_model` and `read_model` left `edits` alone and set `saved`.
    - A write that raised `NotADirectoryError` left the model dirty.
    - A later `write_model` to another path, as a Console would make it, left the model clean.
    - The model displaced to `B_BAK1` by a second read became dirty.
    - A failed read of a broken copy left the displaced model's stamps as they were, clean or dirty, only with the snapshot fix (fix-final/e01; refute2/r01 and critic2/k06 without it).
    - A save to a new path moved `values` when a computed Cells had read `_model.path` (refute2/r13).
  - **Twelve more paths** (refute2/r10, re-run in fix-final): `remove_bases`, `sort_cells`, `import_funcs`, `new_cells_from_module`/`_pandas`/`_csv`, `new_space_from_module`/`_pandas`/`_csv`/`_model`, `new_module`, and `generate_actions` + `execute_actions`. No miss. One over-report: `new_cells_from_module` set identical formulas again and moved `edits` with the file the same.
  - **Uncached Cells** (p06): one that reads only a cached value moved nothing over two calls. One that reads `_space.x` moved `values` on its first call only, and with arguments on each new argument.
  - **Cost** (p05, two runs of 40 alternating rounds):
    - Read: 0.151–0.156 µs for the 3-tuple, simulated; 0.143–0.145 µs for a 2-tuple. `_fingerprint` costs 5.07–5.67 µs and `_touch_key` 16.4–20.08 µs (change_detection/p12, p01).
    - One inline bump: 0.10 µs. The wrapping prototype measured 0.331 µs per touch. A `clear_all` of 1,832 nodes makes 603 `clear_with_descs` calls, and the whole run stayed within noise (change_detection/p07).
    - The top-level check, on a trivial uncached Cells called 20,000 times from Python, where every call is a top-level miss:
      - `len(tracegraph)` and `len(refgraph)` add 0.62–0.64 µs per call, +38–39% (1.62 → 2.25 µs, minimum; also refuter/r06b);
      - the node-dict reads add 0.21–0.25 µs, +13–15% (also refute2/r02, r03; fix-final/r03, two runs).

      p05's cached-miss workload (W2) timed a `clear()` of 20,000 nodes inside the per-call figure, which is why its base was about 12 µs. Re-run with the clear outside the timed loop (refute2/r03 and fix-final/r03, 60 alternating rounds each, three runs), a cached top-level miss costs 4.27–4.67 µs. The node-dict reads add +0.33–0.64 µs at the minimum and +0.18–0.44 µs at the median, +4–15%; `len()` adds +0.43–0.87 µs. That is a real cost, not noise. A BasicTerm_S `clear_all` + `pv_net_cf()` run stays within noise: within ±1.7 ms of 26–33 ms.
- **Edge cases.**
  - Cross-model evaluation records the callee's nodes in the caller's graph (execution/executor.py:72-73), so the callee's `values` stamp does not move. This is pre-existing and documented.
  - In-place mutation of a referenced object is invisible to the stamps, and to modelx's own cache (change_detection/p13). Documented.
  - An ExcelRange cell set through the range moves `edits`. modelx does not clear the Cells that read it, so `values` does not move and the cached value stays stale: 22 before and after, 1020 after a clear (measured, p07). Pre-existing; documented, not fixed.
  - A spec on an absolute path can be shared by several models (io/baseio.py:208-212). A change to it moves `edits` of each.
  - Stamps are per process and are not atomic under free-threading.

#### T9 `Model._get_serial()` and `Model._is_open()`

- **Signatures.** `Model._get_serial() -> int | None`; `Model._is_open() -> bool`.
- **Semantics.**
  - The serial is the clock value at model creation, stored in T8's System entry. It is never reused, and it is `None` after close.
  - A host diffs `{serial: name}` over `mx.get_models()`: the same serial under a new name is a rename, a new serial is an open, and a missing serial is a close. This replaces name diffing and the `_BAK` regex.
  - `_is_open()` is `self._impl.system.models.get(self.name) is self._impl` (system.py:213-215).
- **Measured** (f04, BasicTerm_S):
  - After a second `read_model`, the old object is named `BasicTerm_S_BAK1` and is still the registry's object, with the UserWarning "Existing model 'BasicTerm_S' renamed to 'BasicTerm_S_BAK1'".
  - After close, the handle's `_is_valid()` is True but its name is absent from `get_models()`. `_is_open()` is the only way to tell.
  - `id(impl)` of a closed model was reused by the next model (change_detection/p04, p08).

#### T10 Static formula links: `_get_referents()` and `Model._get_formula_links()`

- **Signatures.**
  - `Cells._get_referents() -> dict`
  - `BaseSpace._get_referents() -> dict | None` (the Space formula; `None` when it has none)
  - `Model._get_formula_links() -> list[tuple[precedent, dependent, via, defined_by]]`
  - Neither name goes on Interface. ReferenceProxy's forwarding looks names up on Interface (reference.py:163-168), so a proxy keeps raising AttributeError for both (measured fix-used-by/u06). A Reference has no formula.
  - Macros are not walked. MacroImpl is not an AlteredFunction and has no `get_referents` (macro.py:126).
- **`_get_referents` returns** a fresh dict. Every global name of the formula is in exactly one of six keys (measured on every formula of fix-used-by/u01):
  - `'cells': {name: ObjectNode}`, `'refs': {name: ReferenceNode}`, `'spaces': {name: ObjectNode}`, `'builtins': {name: object}`, `'system': {name: None}`, `'missing': {name: None}`.
  - **Order.** A name is classified the way a run of the formula sees it: Cells, then References, then child Spaces, then builtins. A run reads `ns_dict`, which is filled with Spaces, then References, then Cells, each overwriting the last (space.py:1984-1996). 0.33's `get_referents` checks Spaces before References (binding/boundfunc.py:144-157). The two differ when a child Space and a global Reference share a name, which modelx allows when the Space comes first. 0.33 reports the Space; the formula reads the global (measured fix-used-by/u03: `S.f()` returns 42).
  - **System references.** `_self`, `_space` and `_model` go under `'system'` when the binding a run reads for them is a system binding, the NameSpaceReferenceImpl in `sys_refs` (space.py:1973-1977). Then they are never under `'refs'` and never in a link. A user Reference of one of those names made by `new_space(refs=)`, a Space-formula parameter or a returned ref replaces the system binding for a run, so it is under `'refs'`; a global of that name does not replace it (fix-final/e04; refute2/r07). Decision 9 refuses those names on those routes from 0.34. 0.33 lists them under `'refs'` (measured refuter/r07, fix-used-by/u01). A link would then name `S._space`, which T6 refuses and whose container is `sys_refs`, not `own_refs`. In the lifelib models, 21 formulas name `_space`: 18 in simplelife and 3 in BasicTermASL_ME (fix-used-by/u02).
  - The **additive** key `'chains': {dotted: target | None}` lists attribute chains whose head is a UserSpace, a Reference to a UserSpace or to the Model, `_self`, `_space` or `_model`.
    - Later segments are looked up the way a run looks up an attribute of a namespace: References first, then Cells, then child Spaces (space.py:1884-1894). In the Model it is References, then Spaces (model.py:1155-1164). This differs from a bare name when a global Reference and a Cells share a name: a bare `Z` reads the Cells, and `_space.Z` reads the global (measured fix-used-by/u07).
    - A Cells ends the chain. So does a Reference whose value is not a UserSpace or the Model. A Reference bound to an ItemSpace therefore ends it, so no dynamic object is ever a target (measured fix-used-by/u05).
    - A segment that is a class attribute rather than a member ends the chain before it: `_space.SpecLookup.match` is listed as `_space.SpecLookup`.
    - A segment that names nothing gives the target `None`.
    - Otherwise the target is the Cells, UserSpace or ReferenceProxy of the last segment listed.
    - Module attribute chains such as `np.array` are not listed. The head `np` is already under `'refs'`.
    - Moving `_space` out of `'refs'` loses no link. In simplelife, each of the 18 formulas reads `SpecLookup` or `AsmpLookup` through `_space`, and the chain resolves it to that Space's Reference (measured fix-used-by/u09). These are the 18 chain-only Reference reads of depgraph/d07b (re-run).
  - **On a dynamic Cells**, names resolve in its ItemSpace, as a run there would. Arguments and formula refs are that item's own bindings, and a plain-valued dynbase Reference is the dynbase's binding itself. Measured (u01): `P[3].h` lists `fr` and `i` as `P[3]`'s bindings and `k` as `P.k`'s ReferenceImpl. A relative Reference follows T5's resolved-slot rule; today it is the in-tree Space's ObjectNode, under `'refs'` (u01).
- **`_get_formula_links` returns** every static link of the model, as 4-tuples:
  - `dependent`: a Cells of a UserSpace, defined or inherited, or a UserSpace that has a Space formula. Every UserSpace is walked, nested ones included. ItemSpaces, DynamicSpaces and their Cells never are.
  - `precedent`: what the formula names, resolved in the dependent's own namespace, which is the binding a run of this formula reads. It is a Cells, a UserSpace or a ReferenceProxy. An inherited formula reads its own Space's copy: inheritance gives each sub Space a separate derived ReferenceImpl (inheritance/sync.py:121-128). So `Sub.foo`'s precedent is `Sub.k`, not `Base.k` (measured refuter/r04: "Sub.k impl is Base.k impl? False").
  - `via`: `''` for a direct name, or the chain string.
  - `defined_by`: the member that holds the precedent's definition.
    - For a derived Cells or a derived Space Reference, it is the member of that name in T4's `defined_in` Space, the first base in the Space's MRO that defines the name. It carries the value: `MI(B1, B2)` with `k` in both reads B1's value (measured u01).
    - For anything else it is the precedent itself. It is never a derived member.

  It is cached per model on System and rebuilt when `_get_revision()[0]` moves, so it is only as complete as T8's `edits` stamp. Each call returns a fresh list.
- **"Used by"** for a Reference or a Cells `r`:

  ```python
  def is_ref(v):
      return getattr(type(v), '_kind', None) == 'Reference'

  def same(x, r):               # never == on a Cells or a Space
      return x is r or (is_ref(x) and is_ref(r) and x == r)

  used_by = list(dict.fromkeys(d for p, d, via, src in links
                               if same(p, r) or same(src, r)))
  ```

  It compares with `same`, never with a bare `==`. A link's precedent and its `defined_by` are Cells, UserSpaces or proxies. `p == r` with a Cells on the left runs `Cells.__eq__` (cells.py:368-376): on a scalar Cells it evaluates `single_value == other`, and otherwise it raises TypeError unless the other side is a Cells. T5's `ReferenceProxy.__eq__` never runs, because Python tries the left operand first. Interfaces are one object per impl (base.py:360-368), so `is` is exact for Cells and Spaces, and only two proxies need T5's equality. Measured with the T10 prototype, fresh proxies and T5's equality simulated (fix-final/e02; also critic2/k02):
  - the bare `==` recipe raised for every target: 42 of 42 on BasicTerm_S, 195 of 195 on BasicTermASL_ME and 235 of 235 on simplelife, with ValueError, TypeError, or a FormulaError from evaluating a scalar Cells. It moved `len(tracegraph)` from 0 to 2 or 3;
  - `same` raised nothing, left `len(tracegraph)` as it was, and gave the prototype's set for every target.

  For a resolved slot (`r._is_dynamic()` and T4 scope `'base'`), first map `r` to its binding: `r.parent.bases[0]._get_object(r.name, as_proxy=True)` (measured fix-reference-identity/g02: True for `P[1].rel` and `P[1][5].rel`). It returns:
  - the formulas that read this binding (`same(p, r)`);
  - for a defined `r`, also every formula in a sub Space, at any depth, that reads an inherited copy of it (`same(src, r)`). Inherited and overriding formulas both count;
  - never the formulas of a sub Space that defines the name again, because they read their own binding;
  - for a derived `r`, only the readers of that copy, because `defined_by` is never derived.

  A global Reference has one binding that every Space shares, because every Space's `refs` ends in the Model's `_global_refs` (space.py:2268; dynamic.py:117-122). So `same(p, r)` alone already finds all its readers (refuter/r04). A host that wants the exact binding only filters on `same(p, r)`.
- **Measured** (fix-used-by/u01; synthetic: Base → Mid → Sub, Sub2(Base) defines `k` again, Sub3(Base) gives `foo` its own formula, MI(B1, B2) with `k` in both):
  - `used_by(Base.k)` has 8 formulas: `foo` and `viaspace` (`_space.k`) of Base, Mid, Sub and Sub3. Sub2's are not listed. `same(p, r)` alone gives only Base's 2.
  - `used_by(Sub.k)` is Sub's 2. `used_by(B1.k)` includes `MI.foo`, and `used_by(B2.k)` is empty.
  - For a Cells: `used_by(Base.foo)` is `bar` of Base, Mid, Sub and Sub2. `Sub3.bar` is not listed, because it reads Sub3's own `foo`.
  - On lifelib models (fix-used-by/u02), `same(p, r)` alone misses:
    - BasicTermASL_ME (Projection and Pricing inherit from Base): 55 of 82 Reference entries and 319 of 496 Cells entries. For example, `Base.disc_rate_ann` gives `Base.disc_rate` but not the `disc_rate` of Projection or Pricing.
    - simplelife: 153 of 400 Cells entries. It misses no Reference entry, because all 23 References read there are defined where they are read.
    - BasicTerm_S, BasicTerm_ME, BasicTerm_SE and CashValue_ME: nothing, because they have no inheritance.
- **Relative References across inheritance.** A Reference to a member of its own Space is re-bound in each sub Space to the sub Space's counterpart (reference.py:85-104; inheritance/manager.py:128-143). Its readers are listed under the base's definition, but they see a different value. A host that shows a value shows `p.value`, not `defined_by.value`.
  - `Base.cref = Base.foo` makes `Sub.cref` hold `Sub.foo`, and `used_by(Base.cref)` lists `Sub.usec` (measured u01).
  - Sub Spaces do not inherit child Spaces (since 0.24). A derived Reference to a base's child Space therefore holds a null Space, whose `_is_valid()` is False (measured u01). Its readers are still listed under the base's definition, and a chain through it is not listed.
- **ItemSpaces and Space formulas.**
  - A dynbase's formula stands for every item's copy: `P.h` for `P[1].h`, `P[2].h` and so on. The links are the same before and after an item is created (measured u01).
  - A dynbase's names resolve in its static namespace. For a Reference with a plain value, that is the binding every item reads, because an item's `_dynbase_refs` holds the dynbase's ReferenceImpl itself (dynamic.py:131-135, 140-177; measured u01). So `used_by(P.k)` covers every item.
  - A relative Reference into the item tree links as `P.rel`. Each item reads its own in-tree object (T5).
  - Arguments, and the refs a Space formula returns, exist only in items. On the static Space they are under `'missing'` (u01: `P.h` missing `['fr', 'i']`), and they are never in a link. To find their readers in one item, call `_get_referents()` on that item's Cells. It creates and evaluates nothing (u01: ItemSpaces 1 → 1, `len(tracegraph)` 1 → 1).
  - A Space formula's dependent is its UserSpace, for example `(P.k, P, '', P.k)`. Space formulas are not inherited (u01: a sub Space of `P` has formula `None`), so no Space-formula link is ever folded.
- **Semantics.** The links mean *named by*, not *read by*. A branch that never runs still counts, and names built at run time are invisible: `getattr(Other, 'y')` yields only `Other` (measured final/f03), and `getattr(_space, 'k')` yields `_space` under `'system'` and nothing for `k` (u01). Nothing is evaluated.
- **Internals.**
  - Built on `self._impl.get_referents()` (binding/boundfunc.py:168-180 → `_get_referents` :134-166 → `global_names` :85-91 → `_extract_globals` :101-115).
  - The tool-API wrapper applies the order and the `'system'` key. It leaves the impl method unchanged, because `precedents()` reads it through `get_valuerefs` (boundfunc.py:182-190; node.py:337-338), and spyder's `precedentslen` is its length (node.py:102, :150).
  - Chains extend `_extract_globals` to `LOAD_GLOBAL` followed by `LOAD_ATTR`/`LOAD_METHOD`. They are cached with the global names, on F3's code-object key.
  - `defined_by` comes from one C3 MRO per Space (`space.bases`, inheritance/manager.py:91-94), the walk T4 makes. Per member, `Derivable.defined_bases` (base.py:321-323) gives the same links on all six models (u02), but it runs the MRO once per member: 4.3 ms against 0.26 ms on simplelife, and 7.1 ms against 0.34 ms on BasicTermASL_ME (fix-used-by/u08).
  - Requires fix F3.
  - No Interface member may be named `get_referents`: test_spyder_surface.py:56 requests that extattr. Never request `_get_referents` or `_get_formula_links` as an extattr either, because they return objects.
- **Cost and counts** (fix-used-by/u08 for times, min and median of 7; fix-used-by/u02 for counts; prototype fix-used-by/t10proto.py; CPython 3.11.15, modelx 0.33.0):

  | model | Cells | Space formulas | links | Reference bindings read | (Reference, dependent) pairs | links with a derived precedent | chains listed | whole model, uncached | rebuild, cached |
  |---|---|---|---|---|---|---|---|---|---|
  | BasicTerm_S | 40 | 1 | 91 | 6 | 8 | 0 | 0 | 6.6 (6.7) ms | 0.32 (0.36) ms |
  | CashValue_ME | 80 | 0 | 228 | 9 | 34 | 0 | 0 | 16.4 (18.8) ms | 0.67 (0.74) ms |
  | simplelife | 245 | 3 | 514 | 23 | 96 | 153 | 45 | 37.2 (38.7) ms | 1.64 (1.71) ms |
  | BasicTermASL_ME | 201 | 0 | 578 | 19 | 82 | 374 | 0 | 65.3 (76.0) ms | 1.68 (1.94) ms |

  - "Uncached" is 0.33's `global_names`, which is recomputed on every call (F3), plus a second `dis` pass for chains and the per-member MRO. "Cached" keys the global names and the chains on the code object and walks one MRO per Space. Both give the same links (u02).
  - `len(tracegraph)` stayed at 0 in every case.
  - The (Reference, dependent) pairs equal the bridge's per-Space `map.get` pairs on BasicTerm_S (8), BasicTerm_ME (22), CashValue_ME (34), BasicTermASL_ME (82) and simplelife (96) (depgraph/d07b, re-run). final/f02's 85 and 114 for the last two counted `_space` as a Reference.
  - Chain extraction gave the same set on CPython 3.10.20, 3.11.15, 3.12.3, 3.13.14 and **3.14.8** (measured final/f03). From 3.12 the order differs, because comprehensions are inlined.
  - Chain *resolution* was measured only with this prototype: simplelife lists 45 chains and resolves all 45 (u02). Whether they agree with what a run reads was not measured.
- **Edge cases.**
  - A Cells with no formula gives all-empty dicts.
  - A deleted object raises DeletedObjectError.
  - Rebinding a base Reference replaces the ReferenceImpl of every derived copy (measured fix-used-by/u04). Proxies taken from older links then compare unequal to the rebuilt ones.

#### T11 `_has_formula()`

- **Signature.** `obj._has_formula() -> bool`
- **Semantics.**
  - Cells: False exactly when it holds the null formula, `not isinstance(impl.formula, NullFormula)` (formula.py:484-488).
  - Space: `impl.formula is not None`, i.e. it has a Space formula, which may have no parameters. `new_space('Z', formula='lambda: None')` has `parameters == ()`; a Space without a formula has `parameters` None (measured fix-reference-identity/g01, g05).
  - Macro: True. Model and Reference: False.
  - A user's own `lambda: None` is a real formula (measured f04: not NullFormula).
- **Edge case (decision 10).** The value does not survive write and read: a no-formula Cells is written as `c = lambda: None` (serializer_6.py:775-782, where `if self.target.formula:` is always true) and reads back as a plain Formula (measured f04). Documented, not fixed in 0.34.

### 3.2 New names outside the objects (`modelx.core.errors`, `api.py`)

#### T12 Exceptions

All are defined in `core/errors.py`, beside `FormulaError`, and api.py imports none of them, so none becomes a top-level name (decision 3). Tools import them from `modelx.core.errors`, which toolapi.rst lists as a supported import path. On 0.33 a tool detects each one with `getattr(modelx.core.errors, name, None)`; the module itself exists there.

- **`ObjectNotFoundError(NameError, KeyError)`**, with `__str__ = Exception.__str__` and attributes `.name` and `.missing`.
  - Raised by `get_object` (system.py:242-254), `Interface._get_object` (base.py:376-391), `BaseSpace._get_object` (space.py:89-105), `Model._get_object` (model.py:650-657) and `Model._get_from_name` (model.py:646-648).
  - Existing `except NameError` handlers (spymx kernel.py:263-266) and `except KeyError` handlers both still catch it.
  - Layout: `(NameError, KeyError)` works on 3.11, and `(NameError, AttributeError)` is a layout conflict (measured f01). The same holds on 3.10–3.14 (tool_contract/p01). Without `__str__`, 3.14 quotes the message.
- **`FormulaError`**: the existing class (errors.py:20-28), where it is today, with:
  - `.error`, the original exception;
  - `.traceback`, a lazy `list[tuple[ItemNode, int]]` with line 0 meaning no frame.

  Both are captured at raise time (execution/executor.py:108-113 and ThreadedExecutor :195, from `ErrorStack.get_traceback` :400-406), so they survive the next calculation. Today `get_traceback()` is reset by the next top-level run: measured `[(Syn.Base.bad(t=1), 1)]`, then `[]` after `Base.foo(1)` (f01). The message text is not a contract. The attributes do not survive pickling.
- **`FormulaDefinitionError(ValueError)`**, with `.source` and `.reason ∈ {'empty', 'not_a_function', 'several_statements'}`. It keeps the message prefix "invalid function or lambda definition" (formula.py:319), so `except ValueError` still works.
- **`DynamicObjectError(ValueError)`**, with `.obj`. Raised for formula set and delete and for rename (cells.py:166-169, 443-453), and also for doc and `is_cached`, which today raise unrelated errors (measured f01):
  - `AttributeError: 'DynamicCellsImpl' object has no attribute 'set_doc'` (cells.py:588-590);
  - `NetworkXError: The node P.__Space1 is not in the digraph.` (cells.py:518-523).
- **`ToolAPIDeprecationWarning(UserWarning)`** (decision 2).
- **`CalculationCancelled(Exception)`** (T14).

#### T13 `is_valid_name`, `get_model_info`, `read_model(if_exists=)`

- **`modelx.is_valid_name(name) -> bool`.** A re-export of util.py:51-61, which api.py:42 already imports as `_is_valid_name` and never uses. It is the **syntax rule** modelx checks when it creates a model, a Space, a Cells, a macro, or a Reference by `set_ref` or by assignment to a Space: an identifier, not a keyword, not starting with `_`.
  - Four routes skip it today (decision 9):
    - a global Reference. `ModelImpl.set_attr` calls `new_ref` with no name check (model.py:1319-1321, 1335-1343; edit/pipeline.py:711-727). `setattr(m, n, 7)` accepted `class`, `lambda`, `None` and `for` (critic2/k01) and `a-b`, `1x`, `a b` and `''` (refute2/r06), and every Space lists them in `refs` (both re-run in fix-final). A keyword global survives a write and a read; `'a-b'`, `'1x'` and `'a b'` make `read_model` fail, and `''` makes `write_model` fail;
    - `new_space(refs=)` on a Model or a Space (edit/pipeline.py:572-574). It accepted `class`, `None`, `a-b`, `1x`, `a b`, `''` and `_` names (refute2/r06, r07). A keyword or a non-identifier name then makes `read_model` fail: `'a-b'` with TypeError (r07), `'class'` and `'None'` with `ValueError: Invalid name` (fix-final/e04). The writer drops `_` names (serializer_8.py:277);
    - the parameter names of a Space formula, and the refs a Space formula returns. `lambda _is_dynamic: None` and a returned ref `'_kind'` are both accepted (refuter/r12, re-run).

    Space attribute assignment, `set_ref`, `new_cells`, `new_space` and `new_macro` refused each of `class`, `None`, `a-b`, `1x`, `a b` and `''` (refute2/r06). `new_cells` checks the rule, but renames an invalid name instead of refusing it (decision 9).
  - It is necessary, not sufficient. A name that passes can still be refused, or be accepted and then hidden, because of the object that would hold it.
  - **Reserved names.** A name is reserved in a container when the container's class has an attribute of that name: `hasattr(type(parent), name)`. That is the test `set_ref` (space.py:1562) and `EditableParent.__setattr__` (parent.py:88) already apply. On 0.33, UserSpace has 56 such names (`bases`, `cells`, `refs`, `formula`, `parameters`, `itemspaces`, `doc`, `name`, `properties`, `frame`, `node`, ...), ItemSpace adds `argvalues`, and Model has 40. Every one passes `is_valid_name` (measured v01).
  - **Inside ItemSpaces.** A member of a Space that has a formula is also a member of each of its ItemSpaces, so the ItemSpace class counts as a container too. A Cells named `argvalues` in such a Space passes the UserSpace test, but `P[1].argvalues` returns `(1,)` while `P[1].cells` lists the Cells and formulas still read it (refute2/r09, re-run in fix-final). A Space-formula parameter or a returned ref with the name of a Cells or child Space of its Space shares that member's `_idstr` in every item (T6; refute2/r11).
  - What each route does with a reserved name (measured v01, v01b):

    | route | result on 0.33 |
    |---|---|
    | `UserSpace.set_ref` | refused: AttributeError "'x' is already defined" (56 of 56) |
    | `space.x = v`, `model.x = v` | never makes a Reference. A method's name raises AttributeError, and a read-only property's raises TypeError (F10). A settable property is set (`doc`, `allow_none`) or rejects the value (`formula`, `parameters`, `path`) |
    | `new_cells`, `new_space`, `Cells.rename`; `Model.new_space`, `Model.new_macro` | **accepted, then hidden**: attribute access returns the class attribute (56 of 56 on a UserSpace, 40 of 40 on a Model) |
    | a Space-formula parameter, or a ref the Space formula returns | accepted, then hidden on the ItemSpace (30 of 31; reading `frame` raises ValueError) |

  - A hidden member still works. It is listed in `S.cells`, formulas see it by its bare name, and it survives write and read. Measured v01: with Cells named `formula` and `name`, `user = lambda: formula(3) + name()` gave 13 before and after a write and read. Only attribute access and `get_object` miss it: `S.formula` is `None`, and `mx.get_object('VRT.S.formula')` returns that `None`. T6's resolver resolves members first, so `_get_from_name('S.formula')` finds the Cells.
  - The set grows when a class gains a public member, so a later release can hide a member that is fine today (§3.0 Placement). No lifelib model is affected today: 0 of 5,347 member names in 29 models collide (measured v02).
  - Model names are different. Only the registry holds a model, so no class attribute can hide it from `get_models()`. All 41 top-level names of `modelx` are accepted as model names. `mx.<name>` then returns the function, but `get_models()` finds the model (measured v01; decision 3).
- **Choosing a free name.** toolapi.rst documents two recipes beside `is_valid_name`:
  - a model: `is_valid_name(n) and n not in mx.get_models()`. An open name is not refused: `new_model` and `read_model` displace the open model to `<n>_BAK<k>` (system.py:204-211; measured v03);
  - a member of `parent`: `is_valid_name(n) and not hasattr(type(parent), n)`, and no current member of that name. modelx refuses most clashes with a current member by ValueError (measured v03). F10 closes the two clashes it accepts silently. When `parent._has_formula()` (T11; False on a Model, so no global named `formula` is read), also `n != 'argvalues'`, the one ItemSpace attribute a UserSpace lacks on 0.33 (refute2/r09), and `n not in parent.parameters`.

  Both recipes test the class, not the instance, as §5 requires. A member named like the check cannot fool them.
- **Recommended (decision 9):** in 0.34, `new_cells`, `new_space`, `Cells.rename`, `new_macro`, and a Space formula with a parameter that is reserved on ItemSpace, emit a UserWarning that names the class attribute that will hide the member. In a Space with a formula, the test includes the ItemSpace class. The parameter test runs in `NewSpace.validate` and the six UserSpace formula members, the routes that give a static Space a formula (decision 9). A clash between a parameter or a returned ref and a member of its Space warns the same way, from whichever side comes second. Each stays a warning and never becomes an error. `read_model` builds Cells through the same `SpaceManager.new_cells` (api.py:1503-1506, called at serializer_6.py:1676), so an error would make a saved model unloadable, and the warning tells its user which member is hidden.
- **`modelx.get_model_info(path) -> dict | None`.**
  - Returns `None` when read_model would refuse the container. Otherwise it returns `{name, format: 'folder' | 'zip', serializer_version, modelx_version, readable, backups: [paths, newest first], max_backups}`.
  - It reads metadata only. It never registers a model and never displaces one.
  - Internals:
    - read_model's container checks (serialize/__init__.py:130-158) are factored into one `_inspect(path)` that both functions use;
    - metadata comes from `_get_model_metadata` (:83-96);
    - `readable` means `_get_serializer` knows the version (:29-37). It does not promise that the read succeeds. It is honest for versions 1–3 only with F8: on 0.33 their readers fail on any model that holds a Cells (measured v07–v09);
    - `name` comes from an ast parse of the first top-level `_name = "..."` in `__init__.py` (written at serializer_6.py:571), or in `_model.py` for versions 1–3 (serializer_1.py:448; serializer_2.py:890, which v3 reuses, serializer_3.py:32);
    - `backups` and `max_backups` mirror `_increment_backups` (:56-80) and `DEFAULT_MAX_BACKUPS = 3` (:26).
  - Measured:
    - The bridge's heuristic disagrees with read_model in 4 cases: `_name` past an 8 KB docstring, a zip wrapped in a folder, no `_name` line (modelx names the model `Model2`), and serializer_version 99 (other/p01).
    - Prototype cost: 278 µs for a folder and 537 µs for a zip, against 14.3 and 50.8 µs for the heuristic (other/p01b).
- **`read_model(model_path, name=None, *, if_exists='rename')`.** With `'error'`, it raises ValueError before any side effect when the target name is open: no `_BAK` rename and no warning. The check goes in serialize/__init__.py:130-156, before `ModelReader`. It matters most where a failed read cannot undo the rename, which on 0.33 is versions 1–3 (F8).
- **Probes** for this element: `fix-validation-and-fixes/v01`, `v01b`, `v02`, `v03` (names) and `v07`–`v09` (old readers), all one fresh process on CPython 3.11.15 with modelx 0.33.0.

#### T14 Calculation hook, **provisional**

- **Signatures.**
  - `set_calc_hook(callback, every=1000, interval=None) -> None`, where `callback(evals: int, depth: int, node: ItemNode)`;
  - `clear_calc_hook() -> None`;
  - `CalculationCancelled`.
- **Semantics.**
  - While a hook is set, the callback runs every `every` formula evaluations, or once per `interval` seconds, **before** the call stack changes.
  - Raising `CalculationCancelled` (or any exception) from the callback stops cleanly: the stacks are reset, values already cached stay valid, and `CalculationCancelled` reaches the caller unwrapped.
  - The hook is process-wide, like `start_stacktrace`.
  - There is no total; the documented estimate is the `len(tracegraph)` of an earlier identical run.
  - Callbacks must use `_get_from_name`, not Space attribute access, which routes to the namespace during execution (space.py:75-84).
- **Internals.**
  - A `HookedCallStack(CallStack)` overrides `append` (executor.py:245-260).
  - It is installed and removed the way `TraceableCallStack` is (system.py:293-322; executor.py:338), and only while the stack is empty.
  - `_start_exec` (executor.py:67-118) re-raises the cancel after rollback.
  - Hardening: move `callstack.append` inside `_eval_formula`'s `try` (executor.py:51-61), and reset leftover frames in a `finally`.
- **Measured** (other/p05, p05b, p05d):
  - A cancel raised before `append` at evaluation 150,000 left clean stacks, kept 49,999 of 100,000 values and passed `_check_sanity`. One raised after `append` broke the executor.
  - Per append+pop: 1,091 ns without a hook, 1,428 ns with `every=1000`.
  - **Whole-run overhead while installed:** +39.3% on BasicTerm_S `pv_net_cf()` (1,832 evaluations) and +67.6% on a 300,001-evaluation synthetic model. `start_stacktrace` costs +55% and +106% on the same runs.
  - There is zero cost when no hook is installed, because the CallStack class is untouched.
  - Asynchronous KeyboardInterrupts left a dirty executor in 8 of 120 trials (p05b). Cooperative cancellation corrupted 0 of 40.

### 3.3 Fixes to existing members

- **F1 ItemSpace labels.**
  - `ItemSpaceImpl.repr_self` (dynamic.py:315-322) returns the argument form whatever `add_params` is, and labels a nested item by its parent's argument form.
  - `_get_repr(fullname=True, add_params=False)` then becomes the display name of every object.
  - Today it leaks (measured f01): `P[1]` → `'Syn.__Space1'`, `N[1]` → `'Syn.__Space1'`, `N[1].Inner[2]` → `'Syn.N[1].__Space1'`.
  - On 0.33 it already equals the bridge's `repr_parent()` recipe on 16 of 16 objects (measured f01) and 231 of 231 (minimal/m01).
  - The spyder snapshot is unchanged (minimal/m01). The only change to the default repr is `'__Space1[5]'` → `'P[1][5]'` for a nested item.
- **F2 `set_ref` validates `refmode`** before `set_attr` (space.py:1562-1565). `absref` and `relref` pass constants.
- **F3 `global_names` cache keyed on the code object** (boundfunc.py:85-91).
  - Today `_is_global_updated` is only ever set False (boundfunc.py:70, 83, 131).
  - The one-line fix of setting it True returns stale names after a formula edit (depgraph/d13). The cache must compare `code is self.altfunc.__code__`.
  - It makes `precedents()` drop from 50.5 to 6.9 µs (depgraph/d13), which also helps spyder's `precedentslen`.
- **F4 Lookup misses** (T12):
  - every miss raises `ObjectNotFoundError`;
  - `get_object(..., as_proxy=True)` no longer drops trailing segments (space.py:93-94, model.py:654-655);
  - traversal through a value no longer raises a raw `AttributeError: 'int' object has no attribute '_get_object'`.

  Both behaviours were measured on `'Syn.Base.k.x'` (f01).
- **F5 Formula refusals.**
  - The typed errors of T12.
  - The UserSpace formula is validated **before** `del_formula` (space.py:1744-1759). Today a refused source deletes the old formula and every ItemSpace: measured formula `lambda i: None` with 2 ItemSpaces became `None` with 0 (f01).
  - Text silently cut down to its first lambda (formula.py:217-239) now emits a UserWarning. Measured: `'import os\nlambda x: os.sep'` is accepted as `'lambda x: os.sep'` (f01).
  - `ErrorStack.tracemessage` tolerates a `None` source (executor.py:428-429). Today it raises TypeError instead of FormulaError.
- **F6 Inheritance graph.**
  - `SpaceGraph.ordered_preds` (inheritance/graph.py:81-83) returns `[]` for a node not in the graph; today networkx iterates the idstr's characters (inheritance/i08).
  - `_direct_bases` on a dynamic Space returns `[dynbase]`, as `bases` already does (dynamic.py:210-215).
- **F7 Docstrings** (api.py):
  - `get_object` raises `ObjectNotFoundError`, a NameError subclass. The docstring at api.py:650-651 says AttributeError.
  - `write_model` and `zip_model` keep up to 3 backups, from `<path>_BAK1` (newest) to `_BAK3`, with the suffix after any extension. `backup=False` replaces the folder. The name is stored in `__init__.py`, not `_model.py` as api.py:1004-1006 says.
  - `read_model` (api.py:1121-1139):
    - If it raises, no model is left registered, a model displaced during the read gets its name back, with its T8 stamps as they were (T8), and the current model is restored (reader_state.py:19-40).
    - That sentence needs F8. On 0.33 it holds for serializer versions 4–8 only. test_read_error_recovery.py:27 tests 4–8, and a corrupted Space file restored both the name and the current model on v4 and v6–v8 (measured v05, v06). The v1–v3 readers close the half-built model but leave the displaced one as `<name>_BAK1`, with no current model (measured v07, v09).
    - A name already open is displaced to `<name>_BAK<n>` with a UserWarning (system.py:204-211), unless `if_exists='error'` (T13).
  - `ReferenceProxy.refmode` can be `None` (T5).
- **F8 Old-format readers (serializer versions 1–3).** These are the formats of modelx before 0.9.0 (serialize/__init__.py:14-23). 0.33 cannot write them, or versions 4–5 (measured v05), and no test reads them: the read tests start at version 4 (test_serializer_compat.py:24, test_read_error_recovery.py:27).
  - **They cannot read a Cells on 0.33.** Their Cells parsers call `new_cells` on the UserSpaceImpl, which 0.33 no longer has: serializer_1.py:477 and :590-592; serializer_2.py:1270-1271 and :1302-1305 with :1323, through `getattr` at :107. Measured v07–v09: a hand-written v1, v2 or v3 model with one Cells fails with `AttributeError: 'UserSpaceImpl' object has no attribute 'new_cells'`. The same model without the Cells reads.
  - **Their failure path does not restore.** It closes the half-built model but takes no `SystemStateSnapshot` (serializer_1.py:423-426; serializer_2.py:875-877; v3 reuses v2's reader, serializer_3.py:32). They rename the new model at parse time (serializer_1.py:503-512; RenameParser, serializer_2.py:989-1016), so a later failure leaves an open model of the same name as `<name>_BAK1`, and no model is current. On 0.33 every v1–v3 model with a Cells fails this way (measured v07–v09).
  - Fix: build Cells through the Space's interface `new_cells`, and take the snapshot in both `read_model` methods as v4–v8 do (serializer_4.py:1073-1107). v1's ModelReader has no `system` attribute (measured v10), so it is passed one.
  - Prototype (v10, monkeypatched in process): the one-Cells models then read as v1, v2 and v3, with `S.a()` = 1. A corrupted model restores the open model's name and the current model. Only minimal hand-written models were tried. Old-format References, data files and `_method` calls were not.
- **F9 `Cells.clear_formula()`** (cells.py:466-470) calls `spmgr.set_cells_formula(self._impl)` without its `func` argument (inheritance/manager.py:193-194).
  - Measured v04: it raises `TypeError: SpaceManager.set_cells_formula() missing 1 required positional argument: 'func'`, and leaves the formula and the values as they were. It fails the same way on a derived Cells.
  - `del cells.formula` works. The deleter (cells.py:449-453) calls `del_cells_formula` (manager.py:199-200), which passes `NULL_FORMULA`.
  - Fix: `clear_formula()` calls `del_cells_formula`, as the deleter does. Measured v04: that call leaves a NullFormula and clears the Cells' values. It stays deprecated, as its docstring says, and listed in cells.rst:64.
  - No test calls it today: `test_clear_formula` (tests/core/cells/test_cells.py:48-75) exercises only `del source.formula`. The fix adds a test that calls `clear_formula()` by name.
- **F10 Name clashes that modelx accepts or reports wrongly** (measured v03, v01b). Each makes a valid name do something other than what was asked.
  - `UserSpace.set_ref(name, v, mode)`, where `name` is a Cells with no parameters, sets that Cells' input and creates no Reference. After `S.set_ref('a', 3, 'auto')`, `'a' in S.refs` is False and `S.a()` is 3. Its docstring says a clash with a Cells or a Space is refused (space.py:1526, :1532). A child Space's name already raises ValueError, and a Cells with parameters raises AttributeError "not a scalar" (space.py:2394-2398). Fix: set_ref raises AttributeError when the name is a Cells or a Space. `space.x = v` keeps setting a scalar Cells' input.
  - `Model.new_space(name)`, where `name` is a macro, is accepted, and the Space hides the macro: `m.mac` is the UserSpace while `'mac' in m.macros` stays True. The reverse is refused: `new_macro` refuses a Space or global name (model.py:1377-1378), and `m.mac = 7` raises KeyError "Macro named 'mac' already exists" (model.py:1339). For a Model parent, `_can_add` looks only at Spaces and global References (inheritance/manager.py:69-70). Fix: refuse a macro name there too. It needs no warning window, because no saved model depends on it: such a model writes on 0.33, and `read_model` raises `ValueError: Name 'mac' already used` (measured fix-integrate/i01).
  - `EditableParent.__setattr__` tests `hasattr(attr, 'fset')`, which every property passes, so assigning to a read-only property calls `None` (parent.py:91-92). All 13 read-only properties of UserSpace and all 10 of Model raise `TypeError: 'NoneType' object is not callable` instead of the intended `AttributeError: x is read-only` (parent.py:94). Fix: test `attr.fset is not None`.
- **F11 Extattrs resolve on the class only** (base.py:698-708; ReferenceProxy at reference.py:203-210; decision 13). Defined and measured in C3.
  - `_get_attrdict_extra` reads each name from `type(self)`. A property is read with its getter, a function is bound and called, and any other class attribute is taken as it is. A ReferenceProxy also looks on Interface, for properties and functions only.
  - A missing name, or a getter that raises AttributeError, is skipped.
  - RefView's `_get_attrdict` and `_baseattrs` (views.py:244-265) skip a key that is not a str. A Space formula can return a ref under such a key, `{'refs': {1: 'one'}}`, and no formula can read it. Today it makes the whole-model walk raise `KeyError: 1` from `BaseView.__getitem__` (views.py:52-60), with the shipped extattr code and with the rest of F11. With the skip, both walks passed, and the item's row listed its str refs (measured refute2/r14; fix-final/e05).
  - The prototype made 0 user calls where 0.33 made 28, with identical output on five lifelib models, and the spyder gate passed (fix-spyder-snapshot/s02, s03).

### 3.4 Existing tool API declared stable (what the consumers rely on)

These members are frozen as tool API from 0.34, with no rename. They are the frozen tier of §5. Each gets "tool API since 0.34.0" on toolapi.rst and an entry in the signature golden. The one exception is the `is_derived()` alias: it is in the golden, but toolapi.rst lists it only as "kept for modelx-bridge 0.10; use `_is_derived()`" (decision 11).

| set | member | where | used by |
|---|---|---|---|
| S1 identity and addressing | `_idstr` | base.py:724-726; ReferenceProxy from 0.34 (T5) | bridge, mcp, spyder (`namedid`) |
| | `_idtuple` | base.py:717-722; space.py:2201-2203 | 0.33 fallback walk |
| | `_evalrepr` | base.py:713-715; reference.py:212-214 | spyder |
| | `_get_repr(fullname, add_params)` | base.py:710-711; ReferenceProxy from 0.34 (T5) | bridge, spyder |
| | `_name`, `_parent` | base.py:398, 424 | — |
| | `_get_object(name, as_proxy)`, including leaf traversal | base.py:376-391; space.py:89-105; model.py:650-657 | bridge, spyder |
| | `Model._get_from_name` (extended by T6) | model.py:646-648 | bridge, spymx |
| | `BaseSpace._named_itemspaces` | space.py:314-317 | bridge, spyder |
| | `_is_valid()` | base.py:728-729; ReferenceProxy's stricter one (T5) | serializers, bridge |
| S2 inheritance and dynamic objects | `Cells._is_derived()`, `_is_defined()` | cells.py:582-586 | bridge, spyder |
| | `ReferenceProxy.is_derived()` (alias; not a first-class entry) | reference.py:193 | bridge 0.10 (methods.py:2726-2738) |
| | `BaseSpace._is_dynamic()`, `_is_static()`, `_is_root()`, `_is_base()`, `_is_sub()` | space.py:153-171 | bridge (from adoption) |
| | `BaseSpace._own_refs`, `_direct_bases` | space.py:402-405, 146-151 | 0.33 fallbacks; spymx kernel for #48 (C3) |
| | `ItemSpace.argvalues` (public) | space.py:2205-2208 | — (not on the wire; C3) |
| S3 snapshot wire | `_get_attrdict(extattrs, recursive)` on Interface, Model, BaseSpace, Cells, ReferenceProxy, the views, BaseNode, Formula and BaseIOSpec | base.py:686-708; model.py:659-671; space.py:704-726; cells.py:572-580; reference.py:203-210; views.py:120-129, 255-265; node.py:92-106; formula.py:480-481; io/baseio.py:562-570; extattrs resolve on the class only from 0.34 (F11, C3) | spyder, bridge (`value_type`) |
| | `_baseattrs` (legacy) | base.py:656-668 and per class | spyder ≤ Spyder 5 |
| | `Model._get_assoc_values()`, `_get_refs()` | model.py:673-691 | spyder |
| | `ReferenceProxy` forwarding of `name`, `fullname`, `parent`, `model`, `doc`, `allow_none`, `_idtuple` | reference.py:163-168 | spyder, bridge |
| | `ReferenceProxy._idstr`, `_get_repr` and `_is_valid`: forwarded on 0.33, defined explicitly from 0.34 (T5) | reference.py:124-217 | bridge (`_objid`, methods.py:2745-2749; `_display`, 2829-2848) |

Contract notes on S1–S3:
- Attrdict keys are additive only. test_spyder_surface.py compares whole snapshots for equality (test_spyder_surface.py:62-73), so even an additive key needs a regenerated golden. This design adds no always-present key.
- `'id'` is `id()` of a live impl and **is reused**: 198 of 200 ItemSpace re-creations reused an id (identity_naming/p05).
- `'valid'` is `id(value)` and is **not a revision**: 300 of 300 changed values reused an id (change_detection/p03e). Gate it on T8's `values` stamp.
- `bases` is the C3 MRO, not the direct bases.
- `_baseattrs_private` (views.py:93) is tool API, but not frozen: it is not listed, and a release may change it with a release note (§5).

### 3.5 Contracts on existing public calls

Probes `s01`–`s06` below were run for C2(2) and C3 in `fix-spyder-snapshot/`, on CPython 3.11.15 with modelx 0.33.0. `c01`, `c08`, `r03b`, `r03c` and `r12` were re-run there too, in `rerun/`, with the recorded outputs. C1(1) and C1(4) cite `fix-bridge-adoption/b04` and `b05`, run the same way.

**C1. Values, formulas and errors.**
1. **`len(Model.tracegraph)`** is the number of computed nodes:
   - one per value held by a cached Cells, inputs included, inside ItemSpaces too;
   - plus one per ItemSpace;
   - uncached Cells add none, and References are never nodes.

   `Model.tracegraph` is the same object as `_impl.tracegraph` (measured f01, `is` True); `len` costs 0.217 µs. The node layout is internal.

   The documented enumeration walks Spaces, recursively through `_named_itemspaces`, then each Cells `c` and key `k` in `c.keys()`, and reads `c.node(*args).preds` with `args = k if isinstance(k, tuple) else (k,)`. Two traps (measured fix-bridge-adoption/b04):
   - `preds` is a property (node.py:197-199), so `node(1).preds()` raises `TypeError: 'list' object is not callable`;
   - a one-parameter Cells keys by the bare value, so `node(*k)` raised TypeError for 1,933 keys of 16 Cells on BasicTerm_S.

   On BasicTerm_S after `pv_net_cf()` and `Projection[2].pv_net_cf()`, the walk gave 77 links, equal to the impl walk (test_trace `TRACED_LINKS = 77`), and 5,464 Cells nodes, equal to the tracegraph's; 3,632 of them are inside an ItemSpace. The tracegraph's 5,465 is those plus one ItemSpace node (b04). An earlier walk counted the same 5,465 nodes in 4.30 ms (depgraph/d11).
2. **Cells members that never evaluate:**
   - `len`, `iter`, `keys` and `in` (`in` applies no defaults);
   - `values()` and `items()`;
   - `series` and `frame`, and `to_series()`/`to_frame()` without arguments;
   - `node(*a).has_value()`, and `node(*a).value`, which raises when absent;
   - `is_input`.

   Members that evaluate: `[]`, `get`, a call, `to_series`/`to_frame` with arguments, `match`, `value`.

   "Is it cached" is `node(*args).has_value()`, for Cells and Spaces alike. Measured: `claims.get(130)` adds 8 nodes, and `(1,) in space` is False although `space[1]` exists (values_formulas/p5).
3. **Formulas.**
   - The Formula class gets its own page: `source`, `parameters`, `name`, `signature`.
   - `Cells.formula` is never `None`; `UserSpace.formula` is `None` without a formula. `parameters` is then `None`, and `()` for a formula with no parameters (measured fix-reference-identity/g01).
   - `cells.formula = "<source>"` is the documented route from text. `set_formula` stays deprecated.
   - `del cells.formula` is the route for clearing a formula. `clear_formula()` raises TypeError on 0.33, and F9 fixes it; it stays deprecated.
   - A def is renamed to the Cells name, or to `_formula` for a Space.
   - ItemSpaces, dynamic Cells and derived Cells share their base's Formula object.
4. **`get_traceback()`** returns the full chain of `(ItemNode, lineno)` pairs and is reset by the next top-level run. `FormulaError.traceback` (T12) is the stable copy.

   Under `use_formula_error(False)`, the exception the caller catches is `mx.get_error()`, and `get_traceback()` describes it. A call refused before any formula runs leaves both as they were from the previous run. Measured (fix-bridge-adoption/b05): `exc is mx.get_error()` was True for the formula's own ZeroDivisionError. For `f(1, 2)` it was False, while `get_traceback()` still held the previous run's 6 frames. The bridge relies on this (§7), so it is stated here and tested.

**C2. Names, registry and Reference attributes.**
1. `is_valid_name` (T13) is the syntax rule. A name is also reserved where its container's class has an attribute of that name. T13 gives the recipe for choosing a free name.
2. Names starting with `_` belong to modelx. Today the public `refs` views list these `_` names (measured s01):
   - `__builtins__`, in every `refs` view (model.py:1220-1222);
   - global References named with `_`. The Model takes any such name (r03), and it shows in the `refs` view of the Model and of every Space, ItemSpace and DynamicSpace. Decision 9 warns from 0.34 and refuses from 0.36;
   - Space References made by `new_space(refs=)` under `_` names, which that call never checks: `S.refs` lists `_is_derived` and `_kind` (refute2/r07). Decision 9 refuses the system names at once and warns for the others;
   - in an ItemSpace, arguments whose parameter names start with `_`, and refs a Space formula returns under `_` names. Neither is checked today (r12): `Q[1].refs` lists `_a` and `_fr` (s01). Decision 9 gives them the same path, a warning in 0.34 and an error in 0.36.

   The system bindings `_self`, `_space` and `_model` are never listed. They live in `sys_refs` (space.py:1973-1977), but the public view is built on `refs_outer` (space.py:400, :2269; dynamic.py:124-128), which leaves them out (s01). A user Reference of one of those names is listed: `T.refs` lists a `_space` and a `_self` made by `new_space(refs=)`, and `Q[1].refs` lists `_space` and `_model` that came from a parameter or a returned ref (refute2/r07c). It also replaces the system binding for that Space's formulas (fix-final/e04). From 0.34 decision 9 refuses those names on the routes that take them.

   So until 0.36 a tool that lists `refs` drops `_` names itself, as the bridge does (methods.py:2741-2742). From 0.36, `__builtins__` is the only one. The snapshot wire already drops them all: the `refs` view's `_baseattrs` and `_get_attrdict` keep only names that do not start with `_` (views.py:244-265).
3. `get_models()` returns the same Model object each time (base.py:360), across rename and `_BAK` displacement (measured f04).
4. `ReferenceProxy.name`, `fullname`, `parent` and `model` are the Reference's own. `doc` is its own docstring and is `None` today, because set_ref takes no doc.
5. `mx.setup_ipython()` replaces any use of `modelx.core.mxsys`.
6. `get_object` resolves a trailing non-object attribute: `'M.S.cells'` gives the CellsView (measured f01), as base.py:376-379 states for spyder. It is pinned by a test.

**C3. The snapshot wire: extattrs.**

*Today.* `_get_attrdict_extra` (base.py:698-708) resolves each requested name with `hasattr` and `getattr` on every object in the walk, and **calls** anything callable. On a Model or a Space, a name that is not a class attribute falls through to `__getattr__` (model.py:595-596; space.py:75-84), which returns a *member* of that name. Which names are class attributes differs by kind (measured s01): `argvalues` only on ItemSpace; `__len__` and `_is_derived` only on Cells; `formula` and `parameters` not on Model. So a name that is safe on one kind can reach user code on another. Measured on 0.33:
- spyder's own list, `['_is_derived', '__len__', '_evalrepr']`, called user functions 28 times in one walk. The model had global References named `__len__` and `_is_derived`, which 0.33 accepts, and a Space formula that returns a ref named `_is_derived` (s02; r12 re-run);
- adding `'argvalues'` also called a Space Reference of that name, put a DataFrame into another Space's row, and put a Cells named `argvalues` into a third as a nested attrdict (s02; c01, r03c re-run);
- the Properties list, `['formula', '_evalrepr', 'allow_none', 'parameters']`, called global References named `formula` and `parameters` on the Model (s02).

An underscore does not protect a name. Global References and `new_space(refs=)` take any name until 0.36, and Space-formula parameters and refs skip the name check (C2(2)).

*Fix F11 (0.34): extattrs resolve on the class only.* `_get_attrdict_extra` looks each name up on `type(self)`, never on the instance:
- a property is read with its getter, a function is bound and called, and any other class attribute (such as `_kind`) is taken as it is;
- a ReferenceProxy also looks on `Interface`, for properties and functions only. That is the rule its `__getattr__` already uses (reference.py:163-168), so `allow_none` still answers;
- a name the class does not define is skipped. So is a getter that raises AttributeError, as `hasattr` skips it today.

Nothing reaches `__getattr__`, so no user member is read or called, whatever its name. Node records pass their extattrs to their object (node.py:96), so F11 covers them too. F11 also makes the `refs` view skip a key that is not a str, which a Space formula can return. On 0.33, and with the rest of F11, one such key makes the whole walk raise `KeyError: 1`; with the skip it passes (refute2/r14; fix-final/e05). A prototype patched over 0.33 (s02, s03):
- made 0 user calls on the model above, where the shipped code made 28, 29 and 2. The only keys it dropped were those that had come from user members;
- gave identical output, after the gate's normalisation, on BasicTerm_S, BasicTerm_SE with 1,000 ItemSpaces, BasicTerm_ME, CashValue_ME and simplelife. That covers spyder's tree list, the same list with `_is_dynamic` and `argvalues` added, and the Properties list on all 53,526 objects;
- passed modelx's own spyder gate (test_spyder_surface.py) unchanged;
- was not slower: the BasicTerm_SE tree walk took 590 ms against 652 ms (minimum of 7 alternating rounds). Inferred cause: a missing name no longer reaches `BaseSpace.__getattr__`, which formats an error message (space.py:80-82).

F11 is a Bug Fix in §5's terms (decision 13). It changes only keys whose values came from user members.

*Wire names.* From 0.34 these are safe to request. Each is answered by a class attribute, evaluates nothing, and returns a literal or a Formula, whose attrdict is `{'source': ...}`. A kind without the name leaves the key out.

| name | answered on | value |
|---|---|---|
| `_is_dynamic` | every kind (T2) | bool |
| `_is_derived` | Cells and ReferenceProxy only (T3); absent on Spaces and Models (decision 4) | bool; a ReferenceProxy's can be `None` |
| `_kind`, `_has_formula` | every kind (T1, T11) | str; bool |
| `_evalrepr`, `_address` | every kind (S1, T6) | str; str or `None` |
| `__len__` | Cells | int, the number of stored values (C1(2)) |
| `formula`, `parameters` | Cells and Spaces | Formula attrdict or `None`; tuple of str or `None` |
| `allow_none` | every kind | bool or `None` |

`_evalrepr` formats ItemSpace arguments with `repr()`, as the always-present `'repr'` key already does (s04).

*Never request:*
- names that return modelx objects: `_direct_bases`, `bases`, `_get_inheritance`, `_get_referents`, `_get_formula_links`. A list of Spaces goes into the payload as live objects (c08 re-run). cloudpickle, spyder's transport (spymx kernel.py:273), cannot send a Space: `AttributeError: 'UserSpaceImpl' object has no attribute '_ns_dict'` (s04);
- `argvalues`. It is the raw tuple, so one Space-valued or unpicklable argument stops the whole tree from transferring. Measured: cloudpickle fails on the `argvalues` of `P[B]` and of `P[threading.Lock()]`, and on the whole tree that holds them (s04);
- members that run work. They are class attributes, so F11 does not stop them: `clear_all` is one on Model, Spaces and Cells (s01).

*On 0.33* there is no F11. Any name that a Model or a Space lacks at class level can reach a user member there. Cells and ReferenceProxy skip such names, because Cells has no `__getattr__` and the proxy forwards only to Interface. Consumers keep the names they request today, and add names only when `modelx.VERSION >= (0, 34, 0)`.

*Two needs the walk cannot serve as it stands, served without new members:*
- **#61, ItemSpace arguments.** An ItemSpace row's `_evalrepr` starts with its parent Space row's `_evalrepr`, and the rest is the arguments in parentheses: `'S05.P(1)(5)'` minus `'S05.P(1)'` is `'(5)'`. This held for 1,060 of 1,060 ItemSpace rows: 10 synthetic ones (string, tuple, Space-valued, zero-parameter, defaulted, nested, and an item of a child of an item), 1,000 on BasicTerm_SE and 50 on CashValue_SE (s05). `_evalrepr` is S1, and its call syntax is decision 5's address form. It works on 0.33.
- **#48, direct bases as names.** The `'bases'` key is the MRO: for `Derived(Base1(Base0), Base2)` it is `['Base1', 'Base0', 'Base2']`, against direct bases `['Base1', 'Base2']` (s04). spymx-kernels reads `_direct_bases` (S2) in the kernel and adds the idstrs to its own payload (s06). On 0.33 a dynamic Space's `_direct_bases` is wrong: `P[1].Child` reports `['Base2']`, a base of `P` (s04). There the kernel uses `bases`, which is `[dynbase]`; F6 makes the two agree from 0.34.

---

## 4. Coverage table

| # | need | class | served by |
|---|---|---|---|
| 1 | object-id-string | INTERNAL | S1 `_idstr` (kept); T5 defines `_idstr` and `_get_repr` on ReferenceProxy explicitly and gives a resolved slot its own id; T6 `_address` for an args-stable form |
| 2 | resolve-id-to-object | TOOL_API | S1 `_get_from_name`, extended by T6; misses raise T12 `ObjectNotFoundError` |
| 3 | reference-as-object | INTERNAL | T5; C2(4) documents `name`, `fullname`, `parent`, `model` and `doc`; T6 `as_proxy=True` |
| 4 | display-name | INTERNAL | F1 + S1 `_get_repr(fullname=True, add_params=False)`; T7 for nodes |
| 5 | valid-name-rule | INTERNAL | T13 `is_valid_name` (the syntax rule), the reserved-name rule and the free-name recipe; decision 9 checks the four routes that skip the rule today; C2(1); F10 |
| 6 | object-kind | INTERNAL | T1 `_kind`; §5 class-level detection |
| 7 | is-modelx-object | INTERNAL | T1 (`getattr(type(v), '_kind', None)` in the vocabulary) |
| 8 | is-dynamic | INTERNAL | T2 |
| 9 | derived-flag-cells-refs | INTERNAL | S2 `Cells._is_derived()` (kept); T3 `ReferenceProxy._is_derived()` replaces the undocumented `is_derived()`, which stays as an alias (decision 11); T4 `state` separates inherited from generated |
| 10 | derived-flag-space | N/A | Not applicable: a Space has no derived concept (decision 4). The bridge stops asking (§7) |
| 11 | space-ref-membership | INTERNAL | T4 `refs[...]['scope']`; C2(2) |
| 12 | computed-node-count | INTERNAL | C1(1): documented `len(Model.tracegraph)` |
| 13 | reference-edge-count | INTERNAL | Retired. T8 replaces its only use, the fingerprint |
| 14 | model-change-signal | UNMET | T8 |
| 15 | model-registry-events | UNMET | T9 serial and `_is_open`; T13 `if_exists='error'`; C2(3) |
| 16 | itemspace-enumeration | TOOL_API | S1 `_named_itemspaces` and public `itemspaces`; F1 labels |
| 17 | itemspace-addressing | UNMET | T6 |
| 18 | formula-source (B) | INTERNAL | T11; C1(3) |
| 19 | formula-set-refusals | INTERNAL | T12 `FormulaDefinitionError`, `DynamicObjectError`; F5 |
| 20 | formula-error-class | TOOL_API | `modelx.core.errors.FormulaError`, as today (decision 3); T12 adds `.error` and `.traceback` |
| 21 | formula-error-text-format | INTERNAL | T12 `.traceback`/`.error`; C1(4); the bridge protocol's `formula_frames` (§7), because modelx-mcp reads only the wire |
| 22 | reference-value-type (B) | TOOL_API | S3 `value_type` (kept); `type(proxy.value).__name__` documented as equal |
| 23 | cached-values-nonevaluating | INTERNAL | C1(2) |
| 24 | ref-used-by | UNMET | T10 + F3 (static "named by"; inherited copies folded onto the defining binding through `defined_by`), carried to the Studio and modelx-mcp by the bridge's new `links.used_by` (§7). **The runtime half is not covered**: recording every Reference read costs +525 ns per formula call, 5.2× (depgraph/d10) |
| 25 | formula-static-reads | UNMET | T10 + F3 |
| 26 | edit-impact-preview | UNMET | **Not covered** (decision 8). A dry run needs ModelEditor to cover the Space formula setters and declarative `finalize_ops`; until then a prototype predicts 0 where 260 are cleared. The after-the-fact `cleared` count stays available as a `len(Model.tracegraph)` delta |
| 27 | trace-graph-enumeration | INTERNAL | C1(1) public walk |
| 28 | model-file-format | INTERNAL | T13 `get_model_info` |
| 29 | backup-rotation | INTERNAL | T13 `backups`, `max_backups`; F7 |
| 30 | read-model-failure-cleanup | INTERNAL | F7 documented guarantee, true for versions 1–3 only with F8; T13 `if_exists` |
| 31 | refmode-values | UNMET | T5 `_refmodes`; F2 |
| 32 | reference-doc | INTERNAL | C2(4) documents `doc` as `None`. Storage is not covered (decision 10) |
| 33 | calc-progress-cancel | UNMET | T14 (provisional) |
| 34 | model-tree-snapshot | TOOL_API | S3 (kept byte-stable); T8 lets the host skip unchanged re-reads; F11 makes the walk call only modelx's own members |
| 35 | object-identity | TOOL_API | S3 `'id'` kept, with the documented reuse caveat; T9 for models. A per-object uid is deferred (decision 8) |
| 36 | named-id | TOOL_API | S1 |
| 37 | eval-repr | TOOL_API | S1 `_evalrepr`; T6 is its non-creating twin |
| 38 | display-repr | TOOL_API | S1 `_get_repr`; F1 |
| 39 | repr-parent | TOOL_API | S3 node attrdict; F1 fixes it for nested items |
| 40 | itemspace-address | UNMET | T6 |
| 41 | get-object-leaf-path | TOOL_API | S1 `_get_object` leaf traversal (kept); C2(6) states it on `get_object`, pinned by a test |
| 42 | lookup-miss-exception | INTERNAL | T12 `ObjectNotFoundError`; F4; F7 |
| 43 | kind-type-name | TOOL_API | S3 `'type'`, read from T1 (byte-identical) |
| 44 | value-kind-tests | INTERNAL | T1, including `'IOSpec'` |
| 45 | container-capabilities | INTERNAL | T1 capability table |
| 46 | user-visible-members | INTERNAL | C2(2); T4 scope `'builtins'` |
| 47 | is-derived | UNMET | T3 for Reference rows, through the `'_is_derived'` extattr; Space rows N/A (decision 4). F11 makes requesting it safe on every kind |
| 48 | space-bases-names | TOOL_API | S2 `_direct_bases`, read by spymx in the kernel and sent as idstrs (C3; fix-spyder-snapshot/s06); F6 for dynamic Spaces. S3 `'bases'` stays the MRO |
| 49 | node-record | TOOL_API | S3; F3 makes `precedentslen` cheaper |
| 50 | node-adjacent-counts | TOOL_API | S3; F3 |
| 51 | change-detection-full-diff | UNMET | T8 |
| 52 | value-identity-valid | TOOL_API | S3 `'valid'` kept with its caveat; gate on T8 `values` |
| 53 | cached-count | TOOL_API | S3 `'__len__'` |
| 54 | formula-source (S) | TOOL_API | S3 Formula attrdict; T11 |
| 55 | set-formula-from-source | INTERNAL | C1(3) `cells.formula = "<source>"`; T12 typed refusals; F9 makes `clear_formula()` work, and `del cells.formula` is the documented way to clear a formula |
| 56 | value-cached-check | INTERNAL | C1(2) `node(*args).has_value()` |
| 57 | reference-value-type (S) | TOOL_API | S3 |
| 58 | value-registry-refs | TOOL_API | S3 `_get_assoc_values`, `_get_refs` |
| 59 | iospec-attributes | TOOL_API | S3 `spec._get_attrdict` |
| 60 | named-itemspaces | TOOL_API | S1/S3 |
| 61 | itemspace-argvalues | TOOL_API | S1 `_evalrepr`: the ItemSpace row's `_evalrepr` minus its parent row's (C3; s05: 1,060 of 1,060). `'argvalues'` is never requested (C3; decision 11) |
| 62 | modelx-system-handle | INTERNAL | C2(5): `mx.setup_ipython()` replaces the only former use (spymx start_kernel.py:93, commented out), and §7 deletes `get_modelx`. System itself is not promoted, because that would expose the executor and the call stack |

Every INTERNAL and UNMET need maps to an element except #26, which is deferred (decision 8). #10 is N/A (decision 4). #13 is retired, not served: T8 replaces its only use, the bridge's fingerprint, so `refgraph` stays internal. Three needs are only partly covered: #24 (the runtime half), #32 (storage) and #35 (per-object uid).

---

## 5. Versioning, stability and deprecation

**What the tool API is.** The owner's rule decides it, and this design keeps it: every underscore member of an object users hold is tool API, public and meant for other software. Those objects are Model, the Spaces, Cells, Macro, ReferenceProxy, the views, nodes, Formula and the IOSpecs. The tool API has two tiers:
- **Frozen.** The members and behaviours listed on `doc/source/reference/toolapi.rst`: S1–S3, T1–T11, the classes in `modelx.core.errors` (`FormulaError` and T12's), the top-level names in T13, and the contracts C1–C3, with T14 marked **provisional**. They are in the signature golden, and the stability promise and the deprecation policy below apply to them.
- **Tool API, not frozen.** Every other underscore member of those objects. On 0.33 the classes users hold define 55 non-dunder underscore members; 26 of them were named nowhere in the previous revision of this document, and most of those are Formula and IOSpec hooks (measured critic2/k03, re-run in fix-final). Examples: Formula's `_init_from_source`, `_reload` and `_set_signature`; BaseIOSpec's `_on_update`, `_on_load_value` and `_can_update_value`; `CellsView._set_keys`; `_baseattrs_private` (views.py:93); `_reduce_serialize_3` on six kinds. A release may change them, with a release note. A consumer that needs one frozen asks for it to be listed, and it then joins the first tier.

Internal, and not tool API, means:
- `_impl` and anything reached through it, including `tracegraph` node tuples, `refgraph` and `repr_parent()`;
- `modelx.core.*` module paths and class names; use `_kind` instead;
- `mxsys`;
- undocumented behaviour of a call, such as what ReferenceProxy's `__getattr__` forwards beyond the names S3 lists.

**Versioned with modelx.** There is no separate number.
- New members carry `.. versionadded:: 0.34.0`; existing members say "tool API since 0.34.0".
- Every release-notes file gains a "Tool API" section: additions, value-changing fixes with before and after strings, and deprecations.

**Detection by consumers.** All three idioms were measured on 0.33 in f01.
- **Members:** `getattr(type(obj), name, None)`. On an instance, `hasattr` is fooled by a global Reference named `_get_revision`: `hasattr(m, ...)` True, `hasattr(type(m), ...)` False.
- **Top-level names:** `vars(modelx).get(name)`. `getattr(mx, 'FormulaError')` returned a *Model* of that name on 0.33.
- **Exception and warning classes:** `getattr(modelx.core.errors, name, None)` (decision 3). The module exists on 0.33, so importing it is safe there, and no model can shadow a name in it.
- **Behaviour changes to existing members** (F1, F2, F4, F5, F6, F8, F10, F11, T5's resolved slots and `_is_valid()`, T6's `_get_from_name` and its TypeError for a Space without a formula, and decision 9's refusals): `modelx.VERSION >= (0, 34, 0)`. For F6, a kernel on 0.33 reads a dynamic Space's direct bases from `bases`, not `_direct_bases` (C3).

**Stability promise for the 0.x series.**
- A listed member's name, signature, return type and documented semantics change only additively:
  - new optional keyword parameters;
  - new keys in returned dicts and attrdicts, never removed or retyped;
  - `_kind` values only added;
  - stamps only growing;
  - a new exception only if it subclasses the one raised before.
- A bug fix that makes a member match its documentation is allowed, with a "Bug Fixes" note and, where a golden changes, a regenerated golden called out in the commit message.
- **Provisional** (T14) may change shape at the next minor release, with a release note.

**Deprecation policy, in house style plus one subclass.**
1. The replacement ships first.
2. The member is marked deprecated on toolapi.rst and in the release notes' "Deprecations" section.
3. Using it emits `warnings.warn("'X' is deprecated and will be removed in a future release.", modelx.core.errors.ToolAPIDeprecationWarning, stacklevel=2)`.
4. It stays for **at least two minor releases**, and until the downstream job (§8) is green against the latest released modelx-bridge and modelx-mcp.
5. Only then is it removed, under "Backward Incompatible Changes", with migration text, as 0.24 did.

**Gates.**
- `core/base/test_spyder_surface.py` stays byte-stable.
- A new `core/api/test_tool_api_surface.py` pins every listed name with its `inspect.signature`. Regenerate it with `--write` and call out the diff in the commit message.
- Contract tests (§6) pin C1–C3 and the 0.33 fallback recipes.

**Behaviour changes in 0.34** (relnotes "Backward Incompatible Changes" unless marked otherwise):
- Lookup misses raise `ObjectNotFoundError`. Code that caught the accidental `AttributeError` of a nested `_get_from_name` miss must change.
- `_get_from_name('')` returns the Model, and global References and macros resolve.
- `get_object(as_proxy=True)` with trailing segments raises instead of truncating.
- `set_ref` rejects an unknown refmode.
- `set_ref` refuses a name held by a Cells or a Space, as its docstring says, instead of setting a scalar Cells' input (F10).
- `Model.new_space` refuses a macro's name (F10). A model that holds both cannot be read back on 0.33 anyway (fix-integrate/i01).
- ReferenceProxy equality and hash go by the binding.
- `ReferenceProxy._is_valid()` reports stale bindings, including a binding of an ItemSpace that was deleted and built again with the same arguments.
- Names that no saved model can hold, or that break the Space's own formulas, are refused at once with ValueError (decision 9): a global or `new_space(refs=)` name that is not an identifier, a `new_space(refs=)` keyword, `__builtins__` as a global, and `_self`, `_space`, `_model` or `__builtins__` as a `new_space(refs=)` name or a Space-formula parameter. On 0.33 each is accepted, and the model then fails to write, fails to read, or fails in its formulas (refute2/r06, r07; fix-final/e04).
- A relative Reference seen through an ItemSpace with its target in the tree gets its own id, name, refmode and flags (`'P.__Space1.rel'`, not `'P.__Space1.Child'`). It equals neither `P.rel` nor another item's slot. `_space.<ref>` in its formulas stops raising AssertionError (space.py:1888; fix-reference-identity/g01, g02).
- `_get_repr` of nested ItemSpaces changes (Bug Fix).
- Dynamic Cells doc and `is_cached` raise `DynamicObjectError` (Bug Fix).
- The UserSpace formula is validated before the old one is deleted (Bug Fix).
- `_get_attrdict` extattrs resolve on the class only. A key whose value came from a user member is no longer emitted, and the `refs` view skips a key that is not a str (Bug Fix, F11).
- Assigning to a read-only property raises AttributeError instead of TypeError (Bug Fix, F10).
- `Cells.clear_formula()` works (Bug Fix, F9).
- Serializer v1–v3 models with Cells read, and a failed v1–v3 read restores the displaced model (Bug Fix, F8).
- `_direct_bases` of a dynamic Space returns `[dynbase]`, as `bases` does, and `SpaceGraph.ordered_preds` returns `[]` for a node not in the graph (Bug Fix, F6). On 0.33, `P[1].Child._direct_bases` reports a base of `P` (fix-spyder-snapshot/s04).
- Calling a Space that has no formula raises TypeError "takes no arguments" instead of `AttributeError: 'NoneType' object has no attribute 'signature'` (Bug Fix, T6; execution/trace.py:109-112).
- A Reference from `P` to a sibling whose name starts with `P`, such as `PX`, is no longer `None` inside `P`'s ItemSpaces, and their formulas stop raising AttributeError (Bug Fix, T5's `wrap_impl` boundary; fix-reference-identity/g06, g06b).
- A reserved name, and a clash between a Space-formula parameter or returned ref and a member of its Space, warn (Enhancements; warnings only, T13 and decision 9).
- The six cases of decision 9 warn (Deprecations).

---

## 6. Implementation plan in modelx

Each PR stands alone and keeps `test_spyder_surface.py` byte-identical.

**PR 1: Contract, docs and gates (no behaviour change)**
- `doc/source/reference/toolapi.rst`, added to the `reference/index.rst` toctree. Sections:
  - the underscore convention;
  - detection idioms;
  - stability and deprecation;
  - identity and addressing;
  - kinds and the capability table;
  - inheritance and dynamic objects;
  - change detection;
  - static links;
  - the snapshot wire format per kind, with extattr rules (C3);
  - names and registry, with the reserved-name rule and the free-name recipes (T13);
  - errors and warnings: `modelx.core.errors` as the supported import path, its classes and their attributes (T12, decision 3);
  - what is not tool API.

  Every member is listed explicitly in `autosummary` blocks with the `mxbase` template. `ReferenceProxy.is_derived()` appears only as "kept for modelx-bridge 0.10; use `_is_derived()`" (decision 11).
- A new `doc/source/reference/formula.rst`.
- `reference.rst`: name, fullname, parent, model and doc; `_refmodes`; refmode `None`.
- `cells.rst`: a "Value operations" section (C1(2)); `del cells.formula` as the way to clear a formula (C1(3)).
- `model.rst`: what `len(tracegraph)` counts.
- `userspace.rst`: an "Inheritance" note. Also fix `tutorial/api_tutorial.rst:508-514`, which says the Space formula is inherited.
- F7 docstrings in api.py. The `read_model` failure guarantee names serializer versions 4–8 here; PR 7 widens it to 1–3 with F8.
- devnotes/DependentPackages.md §3 checklist: point it at toolapi.rst and the downstream job, and add rows for T8's bump points and T10's `dis` dependence.
- Tests:
  - `modelx/tests/core/api/test_tool_api_surface.py`, the signature golden over S1–S3;
  - `modelx/tests/core/api/test_tool_contracts.py`:
    - C1(2): `len(tracegraph)` is unchanged around every listed non-evaluating member;
    - C1(1): `len(Model.tracegraph)` equals the sum of `len(cells)` over every Cells, those inside ItemSpaces included (through `_named_itemspaces`), plus the ItemSpace count; the public walk gives test_trace's 77 links on BasicTerm_S (fix-bridge-adoption/b04);
    - C1(4): under `use_formula_error(False)`, the caught exception is `mx.get_error()`; a call refused before any formula runs leaves `get_error()` and `get_traceback()` as they were (b05);
    - C2(3): get_models identity across `_BAK` displacement;
    - C2(6): the get_object leaf path;
    - the 0.33 fallback recipes: the `_idtuple` walk of minimal/m03 and the E2 state and scope recipes of minimal/m06, on the conftest inheritance and ItemSpace fixtures;
  - a second spyder golden for what spyder actually requests: the tree list `['_is_derived', '__len__', '_evalrepr']`, the Properties list `['formula', '_evalrepr', 'allow_none', 'parameters']` per object, node and IOSpec records, and `_get_assoc_values` keys. Today's golden requests only `get_referents`, which is a no-op.

**PR 2: Kinds, flags, display and extattrs (T1, T2, T3, T7, F1, F6, F11)**
- Files:
  - base.py:350, 660, 690, 698-708;
  - model.py:225; space.py:146-171, 729, 2112, 2152; cells.py:66, 582-586, 1030; macro.py:51; reference.py:126, 193, 199-210; io/baseio.py:335;
  - dynamic.py:315-322; node.py:152-238; inheritance/graph.py:81-83.
- Tests:
  - `core/base/test_kind.py`: every kind, including nested `P[1][5]`; proxies to scalar, global, Space-valued and argument References; PandasData, ExcelRange and ModuleData give `'IOSpec'`; `None` for the 34 value types of minimal/m02 and for Namespace objects; deleted and closed objects; attrdict `'type'` unchanged;
  - `core/space/dynamic_spaces/test_itemspace_repr.py`: `P[1]`, `P[1][5]`, `P[1].Child[2]`, `Q[1, 2]`, `N[]`, `MI[5]`, Cells inside them, and node reprs;
  - `core/space/inheritance/test_tool_flags.py`: the `_is_dynamic` table on Model, UserSpaces including multiple inheritance, ItemSpace and DynamicSpace; the `_is_derived` table on static, derived, overriding and dynamic Cells and References; that Spaces and Models have no `_is_derived` class attribute (decision 4); a whole-model `_get_attrdict(['_is_derived', '_is_dynamic', '__len__', '_evalrepr'])` that does not raise;
  - `core/base/test_extattrs.py` (F11): a model with global References named `__len__`, `_is_derived`, `formula` and `parameters`, a Space Reference and a Cells named `argvalues`, and a Space formula returning a `_is_derived` ref. spyder's tree and Properties lists call nothing and emit no key from a member. The fixture and lifelib outputs are unchanged. `allow_none` still answers on a proxy, and a getter that raises AttributeError is skipped (fix-spyder-snapshot/s02, s03). A Space formula returning `{'refs': {1: 'one'}}`: the whole-model walk passes and the item's row lists its str refs (refute2/r14; fix-final/e05).

**PR 3: References and inheritance (T4, T5, F2, F10)**
- Files: reference.py:124-217; space.py:89-105, 1510-1565, 1985-1996 (`on_update_ns`); dynamic.py:116-177 (`_init_dynbaserefs`, `wrap_impl`); views.py:241-265; parent.py:87-98; inheritance/manager.py:58-82, and model.py:1373-1378 for symmetry; new `core/inheritance/query.py` for `_get_inheritance`.
- Tests:
  - `core/reference/test_refproxy.py` additions:
    - equality and hash;
    - `_is_valid` by the container test on global, Space, derived, argument, formula-ref and system bindings; False after a rebind, a delete, an ItemSpace clear, and a rebind of the base of a derived copy (fix-used-by/u04); still False for an argument, a formula ref and a resolved slot after their ItemSpace is deleted and built again with the same arguments, by `del P[3]; P[3]`, by `clear_items()` and by a rebind (refute2/r08, r08b; fix-final/e03); a closed model's bindings documented as valid (e03);
    - `_refmodes`; ValueError for `'sideways'`, `None` and `42`;
  - resolved slots (fix-reference-identity/g02, g06): `P[1].rel != P[2].rel != P.rel`; `_is_valid` is False after `del P[1]`, `clear_items` and a rebind; `r.parent.bases[0]._get_object(r.name, as_proxy=True)` is the binding; formula results and `len(tracegraph)` are unchanged; `_space.rel` works; the `P`/`PX` prefix case. The round trips through `_idstr` and `_address` are PR 4's;
  - F10: `set_ref` on a scalar Cells' name raises AttributeError; `Model.new_space` with a macro's name raises ValueError; `S.bases = 1` raises AttributeError;
  - `core/space/inheritance/test_get_inheritance.py`: the inheritance/i05 and i12 expectations and the i08 regression; scopes of `_` globals, `_` refs made by `new_space(refs=)`, arguments and formula refs; no system name is reported (fix-spyder-snapshot/s01).

**PR 4: Resolution, errors and name checks (T6, T12, F4, F5, F9; decision 9)**
- Files:
  - errors.py (the new classes; api.py imports none of them);
  - edit/pipeline.py:514-552 (`NewSpace.validate`);
  - model.py:646-657, 1266-1273, 1323-1333 (`get_attr`), 1335-1343 (`set_attr`); space.py:89-105, 1581-1662, 1744-1770, 2072-2091; base.py:376-391; system.py:242-254; dynamic.py:97-101;
  - execution/executor.py:108-113, 195, 428-429; execution/trace.py:109-112;
  - formula.py:217-239, 311-319;
  - cells.py:166-169, 443-453, 466-470, 518-523, 588-590, 670-681.
- Decision 9's checks, refusals and warnings: global names in `ModelImpl.set_attr` (model.py:1335-1343), skipped while `System.serializing` is set; `new_space(refs=)` names and Space-formula parameter names in `NewSpace.validate` (edit/pipeline.py:514), and parameter names also in the six UserSpace formula members (space.py:1581-1662), never in `ItemSpaceParent.set_formula`; ref names a Space formula returns, where formula refs are made (dynamic.py:97-101); clashes inside an ItemSpace at the same three places and in `new_cells`/`new_space`; lambda truncation (F5, formula.py:217-239); `new_cells` renaming an invalid name (cells.py:670-681).
- Tests:
  - `core/model/test_resolver.py`:
    - `_address` and `_idstr` round trips for every object of both fixtures; `''`; globals; `as_proxy`; misses caught by both `except NameError` and `except KeyError`; 0 ItemSpaces created; a Cells named `bases`; after `clear_items`, a rebind and write/read, never a different-arguments match;
    - every Reference proxy of the g02 fixture and of simplelife, resolved slots included, round-trips through `_idstr` and `_address` with the same value (fix-reference-identity/g02, g03);
    - macros; `'Z()'`, `'Z[]'` and `'Z[()]'`; `'T[(1, 2)]'` misses and `'T((1, 2))'` resolves; `"T['a[]b']"`; a call on a Space without a formula raises `ObjectNotFoundError`; `'Q(1).z'` finds `Q(1, 2).z`;
    - `_` names: a global `_ug`, `Q(1)._a` and `Q(1)._fr` resolve; `__builtins__`, `_self`, `_space` and `_model` are refused as the first segment and as a later one (fix-integrate/i03);
    - the documented exception: an argument named like a Cells of its Space resolves to the Cells (refute2/r11);
  - `core/api/test_errors.py`: `.error`/`.traceback` survive a second run; typed refusals; a `None` source; str() unquoted;
  - `core/space/test_space_formula_refusal.py`: the old formula and ItemSpaces survive a refused source;
  - F9: a test that calls `clear_formula()` by name and checks the NullFormula and the cleared values (fix-validation-and-fixes/v04). `test_clear_formula` (test_cells.py:48-75) never calls it;
  - decision 9 (refute2/r06, r07; critic2/k01, k04; fix-final/e04):
    - each of the six cases warns once, and a valid name does not;
    - each name refused at once raises ValueError on its route: `setattr(m, 'a-b', 1)`, `setattr(m, '__builtins__', {})`, `new_space(refs={'class': 1})`, `new_space(refs={'_space': 5})`, `new_space(formula='lambda _space: None')`;
    - `m.new_space(formula=)`, `S.new_space(formula=)`, `copy` and `S.formula = ` all run the parameter check;
    - reading BasicTerm_S warns nothing, and a model saved on 0.33 with a keyword global reads with no warning and keeps the global;
    - a parameter or returned ref named like a Cells of its Space warns, and so does `new_cells` with a parameter's name (refute2/r11); a Cells named `argvalues` in a Space with a formula warns (refute2/r09);

**PR 5: Change detection (T8, T9)**
- Files: system.py:75-105, 180-240; serialize/__init__.py:99-158; serialize/reader_state.py:19-40; and the T8 bump points in edit/pipeline.py, space.py, model.py, base.py, macro.py, system.py, cells.py, io/baseio.py, io/excelio.py, execution/executor.py and execution/trace.py.
- Tests: `core/model/test_revision.py`:
  - the 46-case matrix of change_detection/p06 and the 70 calls of fix-revision-counter/p02. Each asserts which stamp moves, and that `edits` moves whenever `write_model`'s output changes (write before and after; compare `.xlsx` members without docProps/core.xml);
  - evaluation never moves `edits`: the p03 workloads, including a calculation that builds an ItemSpace (`Projection[2].pv_net_cf()`), a nested one (`D[1].In[2].v()`), a Space formula returning `base`/`refs`, and uncached and failing Cells;
  - the paths outside the editor: `del m.mac`, defmacro replacing a macro, `del_spec`, `PandasData.sheet`, a spec `path` setter, an ExcelRange cell, and `UserSpace.reload()`;
  - saves: write_model to a new path and the same path, zip_model and read_model leave `edits` and set `saved`; a failed write leaves the model dirty; a `_BAK` displacement makes the old model dirty; `Model.path` set by hand moves no `edits`; a save to a new path moves `values` when a computed Cells has read `_model.path`, and only then (refute2/r13);
  - a failed `read_model` leaves every open model's stamps as they were, a clean displaced model clean and a dirty one dirty, for serializer versions 4–8 and, with F8, 1–3 (refute2/r01; critic2/k06; fix-final/e01);
  - the twelve paths of refute2/r10, including `generate_actions` + `execute_actions`, which moves `edits` and `values`;
  - read-only controls: cached reads, node/preds/precedents and attrdicts move nothing; an uncached Cells does not move it on a repeated call with the same arguments;
  - a failed evaluation that leaves nodes moves `values`; a rolled-back edit moves nothing;
  - `None` after close; serials are never reused; a rename moves `edits`;
  - a benchmark of top-level calls of a trivial uncached Cells (p05's W1) and of cached top-level misses with the clear outside the timed loop (refute2/r03). It times the inline check against a frozen copy of 0.33's `_start_exec` in the same process, in alternating rounds, and fails when W1's minimum is more than 25% slower. The measured cost is +13–15% (§3.0). An absolute gate of +0.3 µs would sit within 0.05–0.09 µs of what this machine measures, and a slower runner scales the delta (inferred);
  - no Impl class gains a slot: a golden of each Impl class's `__slots__`, taken from 0.33. A ModelImpl pickled by 0.33 cannot be the fixture, because `pickle.dumps(model)` raises AttributeError on 0.33 for a static model, after a calculation and with an ItemSpace (fix-reference-identity/g04b; re-run in fix-integrate/i02).

**PR 6: Static links (T10, T11, F3)**
- Files: binding/boundfunc.py:85-180; cells.py; space.py; model.py.
- Tests: `core/cells/test_referents.py`:
  - the classification: six keys, in the order a run sees names;
  - `len(tracegraph)` unchanged;
  - dynamic Cells and argument refs; Space formula; null formula;
  - the stale-name regression after a formula edit (the depgraph/d13 trap), and chains cached on the code object beside it;
  - chains, using the f03 function, on every leg of the 3.9–3.14 matrix;
  - BasicTerm_S's 8 used-by pairs (lifelib is already in requirements-travis.txt);
  - the used-by recipe with `same` for every Reference and Cells that is a precedent on BasicTerm_S: no exception, and `len(tracegraph)` unchanged. A bare `==` raised for all 42 there (fix-final/e02);
  - ReferenceNode `==` and hash;
  - inheritance used-by: Base → Mid → Sub, Sub2(Base) redefining `k`, Sub3(Base) with its own `foo`, MI(B1, B2). Assert the T10 used-by sets and the `same(p, r)` sets as in fix-used-by/u01. `used_by(Base.k)` has 8 entries and excludes Sub2; `used_by(B2.k)` is empty;
  - system references are under `'system'`, never under `'refs'` and never in links; `_space.k` produces a chain link;
  - name order: a child Space created before a global of the same name (u03), and `_space.Z` reading a global over a Cells `Z` (u07);
  - ItemSpaces: links unchanged by creating an item; arguments and formula refs under `'missing'` on the static Space; per-item `_get_referents` resolves them; a Reference bound to an ItemSpace ends a chain (u05);
  - relative derived References: `Base.cref = Base.foo`, and a derived Reference to a base's child Space, which holds a null Space;
  - BasicTermASL_ME: 55 of 82 Reference used-by entries come only through `defined_by` (u02).

**PR 7: Model files (T13, F8)**
- Files: serialize/__init__.py:26-158; api.py:999-1138; serialize/serializer_1.py:410-428, :477, :590-592; serializer_2.py:842-880, :1270-1271, :1302-1305.
- The reserved-name warning (T13) at `SpaceManager.new_cells`, `Cells.rename`, `new_space` and `new_macro`, and in `NewSpace.validate` and the six UserSpace formula members beside decision 9's parameter check (PR 4). In a Space with a formula the test includes the ItemSpace class.
- The `read_model` docstring's failure guarantee widens to serializer versions 1–3.
- Tests:
  - `serialize/test_model_info.py`. For each case, `read_model`'s accept or refuse agrees with `get_model_info`:
    - v6, v7 and v8 folders and zips;
    - v1, v2 and v3 `_model.py`, where `name` is read from `_model.py`;
    - a 9,000-character docstring;
    - a wrapped zip;
    - no `_name`;
    - serializer_version 99;
    - a non-model directory, a plain file and a missing path;
    - backups;
    - `if_exists='error'` with no side effect;
  - `test_read_error_recovery.py`: VERSIONS extended to 1–3, with hand-written fixtures like fix-validation-and-fixes/v07 and v09 that include a Cells;
  - the reserved-name warning, and no warning for a free name.

**PR 8: Calculation hook, provisional (T14)**
- Files: execution/executor.py:51-118, 216-260; system.py:293-322; api.py.
- Tests: `core/execution/test_calc_hook.py`:
  - a cancel at a count leaves clean stacks, keeps values and passes `_check_sanity`;
  - zero overhead when not installed, checked by CallStack class identity;
  - interaction with `start_stacktrace`.

**PR 9: CI.** §8.

**Release notes: `doc/source/releases/relnotes_v0_34_0.rst`**
- "Enhancements": "API for tools", T1–T14 with measured numbers. For example, the change check at about 0.15 µs against 5–20 µs today, and the static link table rebuilt in about 0.3 ms with F3's cache, against 6.6 ms uncached, on BasicTerm_S (fix-used-by/u08). Also the reserved-name warning (T13), which is not a deprecation.
- "Bug Fixes": F1 with before and after strings (`'Syn.__Space1'` → `'Syn.P[1]'`), F3–F6, F8, F9, F11 with the `refs` view's non-str keys, F10's read-only-property error, T5's `wrap_impl` boundary, and T6's TypeError for a call on a Space without a formula.
- "Backward Incompatible Changes": the §5 list, including F10's `set_ref` and `new_space` refusals and decision 9's names refused at once.
- "Deprecations": the six cases of decision 9: global `_` and keyword Reference names; `_` names in `new_space(refs=)`; Space-formula parameter names and returned ref names that fail `is_valid_name`; lambda truncation; `new_cells` renaming an invalid name.
- A "Tool API" section listing S1–S3.
- Also an `updates.rst` bullet and a `whatsnew.rst` toctree entry.

---

## 7. Adoption

### modelx-bridge

**Shape.** All modelx access moves into one new module, `modelx_bridge/mxcompat.py`. Every helper has a ≥0.34 branch that touches only listed tool API, and a 0.33 branch that is today's code.

```python
import keyword
import modelx as mx
V034 = mx.VERSION >= (0, 34, 0)                  # behaviour fixes: F1, F2, F4, F5, T6
def has(obj, name):                              # members: class level only (§5)
    return getattr(type(obj), name, None) is not None
def top(name):                                   # top-level: never mx.__getattr__
    return vars(mx).get(name)
from modelx.core import errors as mxerrors       # a supported import path (decision 3)
def err(name):                                   # exception and warning classes
    return getattr(mxerrors, name, None)
KINDS = frozenset({'Model', 'UserSpace', 'ItemSpace', 'DynamicSpace', 'Cells',
                   'Macro', 'Reference', 'IOSpec'})
ADDRESSABLE = KINDS - {'IOSpec'}                 # an IOSpec has no _idstr and no _get_repr
def kind(v):
    k = getattr(type(v), '_kind', None)
    if k in KINDS:
        return k
    if V034 or not (type(v).__module__ or '').startswith('modelx.'):
        return None                              # never a user's own class named Model
    n = type(v).__name__                         # 0.33 fallback
    return 'Reference' if n == 'ReferenceProxy' else (n if n in KINDS else None)
def is_valid_name(name):                         # T13; on 0.33 a copy of util.py:51-61
    f = top('is_valid_name')
    if f is not None:
        return f(name)
    return (isinstance(name, str) and name.isidentifier()
            and not keyword.iskeyword(name) and not name.startswith('_'))
```

**Helper by helper** (paths relative to lifelib-app/python):

| bridge code | ≥0.34 | works on 0.33 too |
|---|---|---|
| `_is_model`, `_is_reference` (methods.py:2681-2686); wire `kind` (495, 533, 656, 664, 800, 852, 1036, 1225, 2015) | `kind(v)`. `doc.get` then sends `'Reference'`, not `'ReferenceProxy'` | the fallback branch |
| codec `_mx_ref` (codec.py:63-77) | An `mx` tag only when `kind(v) in ADDRESSABLE`. Any other value, an IOSpec included, stays `opaque` as today. This drops both `modelx.core` imports. mxcompat is imported after the `sys.modules` check (codec.py:65-67), so the codec still never imports modelx itself | the same rule, through the fallback |
| Capability probes by a public name: `hasattr(parent, "set_ref")` (methods.py:778, 847); `getattr(target, "formula", None)` (491); `obj.parameters` in `_parameters` (2817-2821); `getattr(target, "node", None)` in `_make_node` (2852); `getattr(space, "cells", None)` (1032) | `has(obj, name)` first, then the member. On a Model, a name that is not a class attribute resolves a global Reference (model.py:595-596); on a Space it resolves a member (space.py:75-84) | the same. It needs no version branch |
| `_is_dynamic` (methods.py:2617-2627) | `obj._is_dynamic()` | Spaces: `obj._is_dynamic()`; Cells: `obj.parent._is_dynamic()`. Fixes the ItemSpace false negative now |
| `_derived` (methods.py:2726-2738); tree.get `derived` | Cells and References only: `_is_derived() and not _is_dynamic()`; `overrides` and `dynamic` from T4. A Space is never asked, and tree.get's Space entries drop `derived` (decision 4) | Cells as today, asked through `has()`. Never `getattr(space, 'is_derived')`, which finds and calls a member |
| `_ref_names` (methods.py:2741-2742) | `_get_inheritance()['refs']` scopes. Until 0.36 it still drops `_` names, because T4 reports a user's `_` global, `new_space(refs=)` Reference, argument or formula ref under its scope (C2(2)) | today's filter |
| `_objid` (methods.py:2745-2749) | `obj._idstr`; drop the dead `namedid` fallback | same |
| `_resolve`, `_lookup` (methods.py:2752-2778) | `model._get_from_name(obj, as_proxy=True)`, mapping `ObjectNotFoundError` to `not_found` | today's walk |
| `_display` (methods.py:2829-2848) | `obj._get_repr(fullname=True, add_params=False)`; nodes through `BaseNode._get_repr()` | the same call (16 of 16 and 231 of 231 equal on 0.33); ItemSpaces stop reading `__Space1` from 0.34 |
| `_free_model_name` (methods.py:2365-2380), `_verify_name` (2393-2406) | each candidate passes `is_valid_name` (T13). With the `not in` test both helpers already make, that is T13's model recipe, `is_valid_name(n) and n not in mx.get_models()`. Reserved names do not affect model names (fix-validation-and-fixes/v01: 41 of 41 accepted, and `get_models()` found each) | the copy of the rule in mxcompat |
| `_fingerprint`, `_touch_key`, `_structure_size`, `_ref_ids` (methods.py:2441-2524); `prime`, `on_execute`, `_remember` (316-385); `_baseline_now`, `_edited` (1735-1765) | `model._get_revision()`; dirty is `rev[0] != rev[2]` (edits against saved), so the bridge keeps no baseline and a save from the Console counts | the heuristics, plus the explicit bump at 548-556 and 638-642 |
| Registry: name diffing (353-362), `_BAK_RE` (1504-1521, 2310) | `_get_serial()` diff | diff by Model object identity (C2(3)) |
| `_traced`, `_computed` (methods.py:2582-2614) | `len(model.tracegraph)` | same object (measured f01) |
| `_is_null_formula`, `_formula_source` (methods.py:2689-2700) | `_has_formula()`, `formula.source` | the type-name check |
| Refusals (methods.py:624-636, 669-673, 2630-2678) | `isinstance` against `err('FormulaDefinitionError')` and `err('DynamicObjectError')` | message matching |
| `_evaluate` (methods.py:2168-2206) | `err('FormulaError')`, the import it uses today. Its frames come from `exc.traceback` (T12) and go out as `formula_frames` (Protocol, below). Under `mx.use_formula_error(False)` the formula's own exception arrives instead; it is a formula error when `exc is mx.get_error()`, tested before the TypeError branch (2204-2206), with frames from `mx.get_traceback()` | `importlib.import_module('modelx.core.errors')`; frames from `mx.get_traceback()`, read at once; the same `get_error()` test |
| map.get, `_names_read` (methods.py:995-1078, 2703-2723) | `model._get_formula_links()` across Spaces. It returns 4-tuples. map.get's per-Space ref_edges are the `p`-level pairs (equal on 5 models, depgraph/d07b re-run). The Inspector's "used by" reads the new `links.used_by` (Protocol, below), which applies T10's recipe with `same`, so inherited readers appear under the base's Reference. A bare `==` raised on every target and evaluated scalar Cells (fix-final/e02) | the per-Space ast scan; no `links.used_by` |
| `REFMODES` (methods.py:184-187) | `type(proxy)._refmodes` | the local copy |
| files.py:398-473, `backup_limit` (files.py:245-249) | `top('get_model_info')`: `name`, `backups`, `max_backups` | the heuristics |
| samples.py:617-643 | `read_model(..., if_exists='error')` | **Stop closing a same-named model after a failed read on both versions**: it closes the user's model, because the snapshot already restored it (other/p03) |

**Measured for this table.** Probes are in `fix-bridge-adoption/`. T1 is simulated by setting the `_kind` class attributes in the probe process.
- **Codec** (b01). Over its static Spaces, simplelife holds 29 Reference values. 13 are ExcelRange: 8 in Input (s6models/simplelife_model/Input/__init__.py:7-47) and 5 in LifeTable, Economic and two Projection children. Tagging every kind except `None` raised `AttributeError: 'ExcelRange' object has no attribute '_idstr'` for all 13, and `value.get` of `Input.PolicyData` came back `internal`. With `ADDRESSABLE`, all 29 encoded byte for byte as today. So did a Model, UserSpace, ItemSpace, Cells, dynamic Cells, Macro, ReferenceProxy, ExcelRange and module.
- **Foreign class names** (b01b). A fallback to `type(v).__name__` whenever `_kind` is absent broke a Reference that holds a user's own `class Model` or `class Cells`: `value.get` failed with `AttributeError: 'Model' object has no attribute '_idstr'`, on 0.33 and with T1 simulated. The module test and the 0.34 cut-off keep both values `opaque`, as today.
- **Capability probes** (b03). The Model held global References named `set_ref`, `formula`, `parameters` and `node`. Today:
  - `ref.set` of an unrelated global `rate` failed with `TypeError: 'int' object is not callable`, and `rate` kept its value (also critic_complete/c07);
  - `formula.get` of the Model returned a formula it does not have: `{"source": "lambda: 42", "kind": "Model", "parameters": ["a", "b"]}`;
  - `trace.succs` and `value.get` with arguments on the Model called the user's `node` function, then failed;
  - `tree.get` of a Space holding a Cells named `is_derived` evaluated that Cells (tracegraph 0 → 1) and reported the Space `derived: true`. Protocol §7 holds every introspection call to never evaluating (methods.py:522-524, 954).

  With five probes (six sites) asked of the class instead (`b03_make_fixed.py`), every case answered correctly. The row's last site, `getattr(space, "cells", None)` (1032), only reads a global named `cells` before the Model is refused; it is listed for uniformity and was not changed in the probe. The released suites passed unchanged: bridge 831 passed, mcp 975 passed, the same as the shipped code (b03b).
- **Name rule** (b02). The bridge's copies disagree with modelx: `_free_model_name('_x')` gives `'_x_2'`, and `_verify_name('x-y')` gives `'x-y_verify1'`. modelx refuses both. No such input reaches them today: modelx refuses an invalid name at `new_model`, at `read_model` (the file's `_name` and `name=`) and at `rename`, so every open model's name is valid. The row removes a copy of an undocumented rule. It fixes no live defect.
- **Formula errors** (b05). With `use_formula_error(False)`, `value.get` answered `internal` for a `ZeroDivisionError` raised in a formula. It answered `bad_request` "FE.S.h: unsupported operand type(s) …" for a `TypeError` raised inside one, because methods.py:2204-2206 reads every TypeError as a bad call. `exc is mx.get_error()` was True for the formula's own exception. It was False for `f(1, 2)`, refused before any formula ran, while `get_traceback()` still held the previous run's 6 frames.

**Tests in the bridge.**
- Replace `len(model._impl.tracegraph)` with `len(model.tracegraph)` in test_cells_page.py:81, 84, 330, 334; test_edit.py:113, 119; test_ref.py:92, 104, 120, 155, 158; and test_mcp_support.py:149 (read again at :231).
- test_trace.py:102 binds `graph = model._impl.tracegraph`. Its `len(graph)` checks become `len(model.tracegraph)`. Its edge walk at :216-220 reads impl tuples (`u[0].name`), so it becomes the C1(1) public walk: for each Cells `c` and each key `k` in `c.keys()`, the names in `c.node(*args).preds`, with `args = k if isinstance(k, tuple) else (k,)`. Measured (b04): the same 77 links as the impl walk (`TRACED_LINKS = 77`). Two traps: a one-parameter Cells keys by the bare value, so `node(*k)` raised TypeError for 1,933 keys of 16 Cells; and `preds` is a property, so `node(1).preds()` raises `TypeError: 'list' object is not callable`.
- test_files.py:63-66 imports `DEFAULT_MAX_BACKUPS` from `modelx.serialize`. On ≥0.34 it reads `top('get_model_info')(SHIPPED)['max_backups']` (T13); the 0.33 branch keeps the import.
- modelx_mcp/tests/test_basicterm_s.py:586-609 and test_lifelib.py:102-104 walk impl tuples and test `type(iface).__name__ != "Cells"`. They become the public walk over Spaces, recursively through `_named_itemspaces`, then Cells and their keys, with `kind()`. Measured (b04) on BasicTerm_S after `pv_net_cf()` and `Projection[2].pv_net_cf()`: 5,464 Cells nodes both ways, the same set, 3,632 of them inside an ItemSpace.
- New cases, because no released suite has them: a Reference holding an ExcelRange (openpyxl is already a bridge dependency, modelx-bridge/pyproject.toml:76) and one holding a user class named `Model`; a Model with globals named `set_ref`, `formula`, `parameters` and `node`; a Space with a Cells named `is_derived`; a formula error under `use_formula_error(False)`; a deep chain that `formula_frames` trims; `links.used_by` for a base Reference and a base Cells on an inheritance fixture, which lists the readers in sub Spaces, never evaluates, and is absent from `features` on 0.33.
- One suite forces `V034 = False` on 0.34, so the fallback branch stays tested.

**Protocol.** `docs/bridge-protocol-v0.md`:
- §4 gains an optional `addr` (the `_address`), alongside the opaque `obj`.
- tree.get gains `dynamic` and `overrides`.
- tree.get's Space entries drop `derived`, which has always been `false` for a Space and has no meaning there (decision 4). Cells and Reference entries keep it.
- No new version field. `session.info` already sends `modelx` (methods.py:400; bridge-protocol-v0.md:212). The frontend shows "used by" only when `features` lists `links.used_by`, and Stop only when `modelx` is 0.34 or later. That follows the project rule that nothing is shipped dead.
- A new method, `links.used_by` `{model?, obj}` → `{model, revision, obj, readers}`, with a `features` entry of the same name. map.get cannot carry what T10 finds: its `ref_edges` are `[ref name, cells name]` pairs inside one Space (bridge-protocol-v0.md:1593-1605), so they cannot name a reader in a sub Space, the inherited copy it reads, or a chain. And modelx-mcp never imports modelx or the bridge (modelx_mcp/tools.py:3-7), so it cannot call `_get_formula_links()` itself.
  - `obj` is a Reference or a Cells, addressed as in §4. A resolved slot is first mapped to its binding (T5).
  - Each reader is `{obj, display, via, binding}`: the dependent, a Cells or the UserSpace of a Space formula; `via`, `""` or the chain such as `"_space.k"`; and `binding`, the precedent it names as a §4 obj, which is the inherited copy (`Sub.k`) when it is not `obj` itself.
  - It answers from `_get_formula_links()` with T10's recipe and never evaluates, like every introspection call (methods.py:522-524, 954).
  - The kernel lists the feature only on modelx 0.34 or later. On 0.33 the method is absent, so no client shows a "used by" that misses the readers in sub Spaces.
- `formula_error` (§3, bridge-protocol-v0.md:139) gains optional `formula_frames` and `formula_frames_total`. Today the wire names the failing node (`error_obj`, `error_args`, `error_display`) and carries the chain only as text: `formula_traceback` is `str(exc)` (methods.py:2197-2203). modelx-mcp is a protocol client and cannot reach `exc.traceback`, so without a field it keeps parsing that text.
  - A frame is `{i, obj, args, display, line}`: modelx's frame number, the node addressed as in §4, its display, and the line in its formula's source. The last frame also carries `text`, that source line.
  - `line` is 1-based in `formula.source`, as modelx-mcp already assumes (tools.py:2370-2371). Measured (b05b): a def failing at line 5 gives `'return x / 0'`; a lambda gives line 1.
  - Frames are kept the way modelx-mcp's `_chain` keeps them (tools.py:2379-2392): all of them up to 12, otherwise the first 6 and the last 5 (`keep = frames if len(frames) <= 12 else frames[:6] + frames[-5:]`, tools.py:2385). `i` lets a reader count the gap.
  - `formula_traceback` stays, for 0.10.0 clients. Under `use_formula_error(False)` it is `str(exc)` of the formula's own exception.
  - Measured (b05): `f(200)`, failing at the bottom, has 201 frames. modelx's text keeps 18 frame lines and an ellipsis, 615 characters (executor.py:408-432 keeps 20 lines). The trimmed field is 897 bytes, against 15,750 for all 201 frames, and took 1.05 ms to build. A DeepReferenceError at `set_recursion(300)` had 301 frames.

**Pin (decision 12).**
- After modelx 0.34 ships with the downstream job green, `modelx>=0.33.0,<0.34` (modelx-bridge/pyproject.toml:54) becomes `modelx>=0.33.0,<0.36`.
- The bridge's ci.yml keeps its floors job at `modelx==0.33.0` and adds a `modelx-main` job that installs modelx from GitHub.

### modelx-mcp

modelx-mcp pins `modelx-bridge>=0.10.0,<0.11` (modelx-mcp/pyproject.toml:40) and follows the bridge.
- The resolver (tools.py:396-470, 563-595) maps `Space[k]` onto `_address` and `_get_from_name`, and stops constructing `__SpaceN` ids (tools.py:422). The LEAK checks in tests/checks.py:27-29 then pass by construction.
- With F1 and the bridge's `_display` row, map.get's display of an ItemSpace stops being its `__SpaceN` name (inferred), so the workaround that prints the ref instead (tools.py:1314-1317) can go once `session.info`'s existing `modelx` field reports 0.34.
- `formula_error_text` (tools.py:2338-2392) reads the bridge's new `formula_frames` (Protocol, above) when they are present. It names the gap from each frame's `i` and quotes the last frame's `text`. It parses `formula_traceback` only from bridge 0.10.0. mcp cannot read `FormulaError.traceback` itself: it sees only the wire.
- `"(inherited)"` (tools.py:1075, 1187) keeps reading tree.get's `derived`, which the bridge computes as `_is_derived() and not _is_dynamic()` from 0.34 (its `_derived` row), and adds a per-Space roll-up from the new `overrides` and `dynamic` fields (T4).
- `trace` of a Reference (tools.py:2028-2032) answers from the bridge's `links.used_by` (Protocol, above) when `session.info.features` lists it, so readers in sub Spaces are listed under the defining Reference. Without the feature it keeps today's ToolError, which points to `get_formulas`. mcp never calls `_get_formula_links()` itself: it never imports modelx or the bridge (tools.py:3-7).
- `run_python`'s change report (python_tool.py:73-181) uses `_get_revision()` and `_get_serial()`. Today it already diffs models by object, not by name (python_tool.py:86-92, 116, 161-164), which C2(3) makes a contract.
- Its tests change with the bridge's: the impl-tuple walks in test_basicterm_s.py:586-609 and test_lifelib.py:102-104 (above).

### spyder-modelx / spymx-kernels

All of these changes are additive. An un-updated plugin keeps working against 0.34 (inferred from the additive-keys rule and minimal/m01, m02). F11 alone leaves its payloads identical on ordinary models, and stops its tree walk from calling user members (s02, s03; the probes are listed in §3.5).
- **Explorer tree** (`update_modeltree`, mxshell_6.py:364-367):
  - On ≥0.34 the extattrs become `['_is_derived', '__len__', '_evalrepr', '_is_dynamic']`. All four are C3 wire names. `'_is_derived'` fills the blank "Is Derived" cells of References; Space rows stay blank, correctly (decision 4) (mxtreemodel.py:120-124).
  - On 0.33 the list stays `['_is_derived', '__len__', '_evalrepr']`. `_is_dynamic` is not a Model class attribute there, so on the Model row it would resolve a global Reference of that name (s01), the same path that called a global `_is_derived` in s02. The three names spyder requests today already reach user members on a model with global References named `__len__` or `_is_derived` (s02: 28 calls in one walk). Only F11 closes that.
  - `'argvalues'` is not requested, on any version (C3). Requested, it would call a Space Reference of that name, and one Space-valued argument would stop the whole tree from transferring (s02, s04).
  - The Parameters column of an ItemSpace row comes from `_evalrepr`, which the walk already requests. Override `getParams` in `ItemSpaceItem` (mxtreemodel.py:244-256): take the row's `_evalrepr`, cut off its parent Space row's `_evalrepr`, and drop the parentheses. That gives `'1'`, `"'x'"`, `'1, 2'` and `'<UserSpace S05.B>'`, and `'5'` for a nested item whose column-0 repr still reads `'__Space1[5]'` before F1 (s05: 1,060 of 1,060 rows). The parent Space row is `self.parent().parent()`, because an ItemSpaceMapItem sits between them (mxtreemodel.py:226-230, 259-264). This works on 0.33 too.
- **Properties** (`update_mxproperty`, mxshell_6.py:331-334) and the Analyzer (mxshell_6.py:233-236) keep `['formula', '_evalrepr', 'allow_none', 'parameters']`; all four are C3 wire names.
  - For a Space, spymx's `mx_get_attrdict` (kernel.py:257-273) adds `'direct_bases'`, the idstrs of `obj._direct_bases`. On 0.33 it uses `obj.bases` for a dynamic Space instead (C3, s06). The kernel already post-processes payloads in `mx_get_value_info` (kernel.py:393-414).
  - The "Base Spaces" row (mxproperty.py:161-162, 175-176) then shows the direct bases. Today it shows `bases`, the MRO, so `Derived(Base1(Base0), Base2)` reads `Base1, Base0, Base2` (s04).
- Replace the kernel's isinstance dispatch (kernel.py:159-199, 416-504) with `getattr(type(v), '_kind', None)`, keeping the version-gated imports for <0.34.
- Fix the ItemSpace walk-up at kernel.py:176-177 (`parent = parent.parent`).
- Properties, the Data viewer and the Analyzer store `_address` and resolve it with `model._get_from_name(addr, as_proxy=True)` instead of `__SpaceN` fullnames (mxproperty.py:358-362; dataview_plugin_6.py:224-226; mxanalyzer_6.py:684-710).
- `update_mx_widgets` (mxshell_6.py:85-98) skips the re-read and the deep compare when no open model's `_get_revision()[:2]` moved. A save moves `saved`, and moves `values` only when it changes `model.path` and that clears a value computed from `_model.path`; the re-read then shows the cleared value (T8; refute2/r13). Today that costs 0.51 ms to 742 ms per execution.
- The Analyzer's `'valid'` comparison is gated on the `values` stamp.
- `ObjectNotFoundError` is a NameError, so kernel.py:263-266 is unchanged.
- Delete `get_modelx` (mxsys).

---

## 8. CI: the downstream job in modelx

**New file `.github/workflows/downstream.yml`.**
- It is reusable. `python-publish.yml` gains:

  ```yaml
  downstream:
    uses: ./.github/workflows/downstream.yml
  ```

  and `needs: downstream` on its existing `deploy` job (python-publish.yml:18-19), so no release uploads while a released consumer fails.
- The job installs the *released* bridge and mcp from PyPI, then replaces modelx with this checkout using `--no-deps`. The released bridge requires `modelx<0.34`, so **`pip check` must not run**; it reports exactly that conflict (tool_contract/ci_rehearsal).
- The suites are not in the wheels, so they come from the release tags (`bridge-v0.10.0` and `mcp-v0.1.0` exist today).
- **A use of deprecated tool API fails the job.** Both `run_all` modules start one interpreter per suite (modelx_bridge/tests/run_all.py:37-41; modelx_mcp/tests/run_all.py:41-46), so a warning filter set in the runner never reaches a suite. Two ways that look right were measured not to work (b06):
  - The earlier `run_strict.py`, which set `simplefilter("error")` and then ran `run_all`. With a modelx copy that deprecates `Cells._is_derived`, which the bridge calls, the bridge suites passed 831 and exited 0.
  - `PYTHONWARNINGS=error::modelx.ToolAPIDeprecationWarning` (measured before decision 3; with the class in `modelx.core.errors` the option would name `modelx.core.errors.ToolAPIDeprecationWarning`, which needs the same import at start-up, so the same failure is expected, inferred). Python imports the category's module while it starts. With modelx installed in site-packages, and with a copy on `PYTHONPATH`, it printed `Invalid -W option ignored: invalid module name: 'modelx'` and set no filter. A stdlib-only stand-in on `PYTHONPATH` worked (b06d), so the cause is inferred to be that site-packages, where modelx and networkx live, is not on the path yet.

  So the suite steps put `.github/scripts/toolapi_audit/` on `PYTHONPATH`. Its `sitecustomize.py` runs in every interpreter the suites start, because each one keeps an inherited `PYTHONPATH`: the two `run_all` modules (modelx_bridge/tests/run_all.py:32-33; modelx_mcp/tests/run_all.py:36-37), test_stdio's server (test_stdio.py:37-41), and the children of test_lifelib and test_python_tool (test_lifelib.py:283-284; test_python_tool.py:240-241). It appends each `ToolAPIDeprecationWarning` to a file and changes nothing the code under test sees. A warning raised where the bridge catches every exception, as `_derived` does (methods.py:2726-2738), is still counted. A last step fails the job when the file is not empty.

```yaml
name: downstream
on:
  push: {branches: [main]}
  pull_request: {branches: [main]}
  workflow_dispatch:
  workflow_call:
permissions: {contents: read}
jobs:
  suites:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        python: ['3.11', '3.13', '3.14']        # 3.14 = Pyodide 314's language level
    steps:
      - uses: actions/checkout@v4
        with: {path: modelx}
      - uses: actions/setup-python@v5
        with: {python-version: '${{ matrix.python }}'}
      - name: Released modelx-bridge and modelx-mcp, with their dependencies
        run: python -m pip install modelx-bridge modelx-mcp
      - name: Replace modelx with this checkout
        run: |
          python -m pip install --no-deps --force-reinstall ./modelx
          python -m pip install 'networkx>=2.2' asttokens libcst
          python -c "import modelx; print(modelx.__file__, modelx.VERSION)"
      - name: Installed versions
        id: v
        run: |
          python -c "from importlib.metadata import version as v; print('bridge=' + v('modelx-bridge')); print('mcp=' + v('modelx-mcp'))" >> "$GITHUB_OUTPUT"
      - uses: actions/checkout@v4
        with: {repository: fumitoh/modelx-bridge, ref: 'bridge-v${{ steps.v.outputs.bridge }}', path: src-bridge}
      - uses: actions/checkout@v4
        with: {repository: fumitoh/modelx-bridge, ref: 'mcp-v${{ steps.v.outputs.mcp }}', path: src-mcp}
      - name: Put the suites beside the installed packages
        run: |
          site="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
          cp -r src-bridge/modelx-bridge/modelx_bridge/tests "$site/modelx_bridge/"
          cp -r src-mcp/modelx-mcp/modelx_mcp/tests "$site/modelx_mcp/"
      - name: modelx-bridge suites
        working-directory: ${{ runner.temp }}
        env: {PYTHONPATH: '${{ github.workspace }}/modelx/.github/scripts/toolapi_audit', TOOLAPI_DEPRECATIONS: '${{ runner.temp }}/toolapi-deprecations.txt'}
        run: python -m modelx_bridge.tests.run_all
      - name: modelx-mcp suites
        working-directory: ${{ runner.temp }}
        env: {PYTHONPATH: '${{ github.workspace }}/modelx/.github/scripts/toolapi_audit', TOOLAPI_DEPRECATIONS: '${{ runner.temp }}/toolapi-deprecations.txt'}
        run: python -m modelx_mcp.tests.run_all
      - name: No deprecated tool API was used
        if: always()
        run: |
          log="$RUNNER_TEMP/toolapi-deprecations.txt"
          if [ -s "$log" ]; then
            echo "::error::the released suites called deprecated tool API"
            sort "$log" | uniq -c | sort -rn | head -50
            exit 1
          fi

  lifelib:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with: {path: modelx}
      - uses: actions/setup-python@v5
        with: {python-version: '3.13'}
      # lifelib with --no-deps, so it cannot change what was resolved, and
      # --no-compile, so lifelib.create copies no __pycache__ into the models
      # (modelx-bridge ci.yml:171-181).
      - name: Released modelx-mcp, this modelx, then lifelib
        run: |
          python -m pip install modelx-bridge modelx-mcp
          python -m pip install --no-deps --force-reinstall ./modelx
          python -m pip install 'networkx>=2.2' asttokens libcst
          python -m pip install --no-deps --no-compile lifelib==0.17.1
      - name: Installed version
        id: v
        run: |
          python -c "from importlib.metadata import version as v; print('mcp=' + v('modelx-mcp'))" >> "$GITHUB_OUTPUT"
      - uses: actions/checkout@v4
        with: {repository: fumitoh/modelx-bridge, ref: 'mcp-v${{ steps.v.outputs.mcp }}', path: src-mcp}
      - name: Put the suites beside the installed package
        run: |
          site="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
          cp -r src-mcp/modelx-mcp/modelx_mcp/tests "$site/modelx_mcp/"
      # Copied from modelx-bridge ci.yml:186-192. lifelib.create writes
      # basiclife/ and savings/; test_lifelib reads the three models from one folder.
      - name: Write lifelib's models
        working-directory: ${{ runner.temp }}
        run: |
          python -c "import lifelib; lifelib.create('basiclife', 'basiclife'); lifelib.create('savings', 'savings')"
          mkdir models
          mv basiclife/BasicTerm_ME basiclife/BasicTerm_SE savings/CashValue_ME models/
          ls -l models/*/_system.json
      # shell: bash runs with -o pipefail. Without it a failing run_all piped
      # into tee leaves the step green (modelx-bridge ci.yml:207).
      - name: modelx-mcp with test_lifelib, which must not be skipped
        working-directory: ${{ runner.temp }}
        shell: bash
        env:
          MODELX_MCP_MODELS: ${{ runner.temp }}/models   # BasicTerm_ME, BasicTerm_SE, CashValue_ME
          PYTHONPATH: ${{ github.workspace }}/modelx/.github/scripts/toolapi_audit
          TOOLAPI_DEPRECATIONS: ${{ runner.temp }}/toolapi-deprecations.txt
        run: |
          python -m modelx_mcp.tests.run_all | tee mcp.txt
          if grep -q '^SKIPPED test_lifelib' mcp.txt; then
            echo "::error::test_lifelib was skipped; this job exists to run it"
            exit 1
          fi
      - name: No deprecated tool API was used
        if: always()
        run: |
          log="$RUNNER_TEMP/toolapi-deprecations.txt"
          if [ -s "$log" ]; then
            echo "::error::the released suites called deprecated tool API"
            sort "$log" | uniq -c | sort -rn | head -50
            exit 1
          fi
```

The `lifelib` job installs lifelib and stages its models exactly as modelx-bridge's own ci.yml `lifelib` job does (ci.yml:171-192), and checks the skip the same way (ci.yml:199-215).

`.github/scripts/toolapi_audit/sitecustomize.py`:

```python
# On PYTHONPATH for the suite steps, so every interpreter the suites start
# imports it. Records each modelx ToolAPIDeprecationWarning, with the caller
# that triggered it, to $TOOLAPI_DEPRECATIONS. It changes nothing the code
# under test sees: the warning is still shown, or filtered, as before.
import os
import sys
import warnings

_LOG = os.environ.get("TOOLAPI_DEPRECATIONS")
_warn = warnings.warn


def warn(message, category=None, stacklevel=1, source=None, **kwargs):
    errors = sys.modules.get("modelx.core.errors")
    cat = getattr(errors, "ToolAPIDeprecationWarning", None)
    if _LOG and cat is not None and isinstance(category, type) and issubclass(category, cat):
        caller = sys._getframe(stacklevel)
        with open(_LOG, "a", encoding="utf-8") as log:
            log.write("%s:%d: %s\n" % (caller.f_code.co_filename, caller.f_lineno, message))
    return _warn(message, category, stacklevel + 1, source, **kwargs)


warnings.warn = warn
```

It sees every call, because modelx calls `warnings.warn` through the module everywhere (no `from warnings import` in modelx/, by grep). It does work only when a warning is raised. It does not turn the warning into an error, so a deprecated call behaves as it would for a user, and the job fails at the end with the call sites listed. Measured on CPython 3.10.20, 3.11.15, 3.12.3, 3.13.14 and 3.14.8 (b06d): the warning is still shown at the caller's line, and the file names the same line. Re-checked on the same five interpreters on 2026-10-09 with the lookup in `modelx.core.errors`, against a stand-in package that defines the class there: the same result, and an ordinary UserWarning was not recorded. It misses a warning in an interpreter started without `site` or with `-E`, or after code replaces `warnings.warn` itself; no suite does either (inferred from the launch lines cited above).

**Rehearsed** by Design C on 2026-10-07 (tool_contract/ci_rehearsal), with a copy of the checkout carrying `VERSION = (0, 34, 0)`, the PyPI wheels installed with `--no-deps`, and the suites from tag `bridge-v0.10.0`:
- modelx-bridge: 830 passed, 0 failed, 3 skipped by design, 85 s;
- modelx-mcp: 975 passed, 68 s;
- test_lifelib on BasicTerm_ME, BasicTerm_SE and CashValue_ME: 190 passed, 33 s.

**Re-measured for this section** (fix-bridge-adoption/, CPython 3.11.15, the released suites from the public repo, whose package folders equal tags `bridge-v0.10.0` and `mcp-v0.1.0` (git diff empty), the steps run by hand, not on a GitHub runner):
- **The audit** (b06). Two modelx copies carry the category; one also deprecates `Cells._is_derived`, which the bridge calls.
  - With the deprecation, the earlier `run_strict.py` left the bridge suites at 831 passed, exit 0. The audit left them at 831 passed too, and wrote 17,953 lines from 2 call sites: methods.py:2735 (`_derived`) and the bundled bootstrap.
  - With the deprecation, test_stdio failed 1 check with and without the audit: the warning reached its server's stderr, which that check requires to hold only the `open` line. The audit recorded 622 calls from that server process (b06c). So without the audit, the mcp suites go red only by that accident, and only for a deprecation the server reaches before that check.
  - Without the deprecation, the audit left the bridge suites at 831 passed and the mcp suites at 975, and the file empty.
  - 831, not Design C's 830: the third skip (ci.yml:121-124) is for `__pycache__` in an installed sample, which this copy did not have.
- **The model staging** (b07). As the job was written before, with only `lifelib.create`, there is no `models/` folder. test_lifelib then reported SKIPPED and the step exited 1, so the job is red for a reason that has nothing to do with modelx. With the `mkdir` and `mv` step, under `-eo pipefail` and the audit: test_lifelib passed 190, the mcp suites 1,165 in all, the step exited 0, and the audit file stayed empty. (The lifelib here was installed without `--no-compile`, so the staged folders also held `__pycache__`; test_lifelib passed regardless.)
- **The pipe** (b07). The same two lines with a `run_all` that fails: under `bash -e`, which GitHub documents as the default for `run` without `shell`, the step exits 0; under `bash --noprofile --norc -eo pipefail`, what `shell: bash` runs, it exits 1.

**Transition.** While the released bridge is 0.10.0, the job also gates modelx on that release's internal reads: `_impl.tracegraph`/`refgraph`, class names and `repr_parent()`. This is intended, and it ends when the adopted bridge ships.

**Policy.** A red job blocks the release. A deliberate break ships a bridge release that handles it first.

---

## 9. Risks and measurements

### Risks

1. **T8 completeness.** The bump points are 28 code sites in 12 files: the editor, six UserSpace formula members, two doc setters, `allow_none`, three macro methods, `rename_model`, two input hooks, `reload`, four IOSpec methods, two executors, three trace clears and two serialize functions. A future edit path that skips them under-reports silently, which is the failure class CLAUDE.md warns about. Mitigations:
   - the 46-case matrix and p02's 70 calls, each asserting that `edits` moves whenever the written model changes, plus the p03 evaluation workloads asserting that it never moves;
   - a DependentPackages.md checklist row;
   - the bridge keeps its explicit dirty-marking on 0.33.

   A path that undoes a rename passes a bump point too. `SystemStateSnapshot.restore` does, so it must put the stamps back, or a failed read leaves a clean model dirty (T8; refute2/r01, critic2/k06, fix-final/e01).

   Bumps must be inline (serializer_6.py:297-302; the reader also calls `UserSpaceImpl.set_formula` by name, serializer_6.py:1343-1352; fix-revision-counter/p03c) and must not use an Impl slot (base.py:163-180).
2. **Behaviour changes to existing tool-API members** (§5 list). Each is signalled by `VERSION`. spyder catches `NameError`, which the new exception still is. F1 changes visible strings for nested ItemSpaces; a consumer that parsed `__SpaceN` breaks, which is intended.
3. **Static links are "named by", not "read by".**
   - Run-time names are invisible.
   - The links depend on CPython bytecode. Chain extraction was measured identical on 3.10.20–3.14.8 (f03), but Pyodide 314 is inferred to match CPython 3.14 bytecode, not measured.
   - The cache must key on the code object (depgraph/d13).
   - Used by is folded onto the definition. For a relative derived Reference, the readers listed under the base see a different value (the sub Space's counterpart); hosts show `p.value` (T10).
   - A host must compare link members with T10's `same`, never a bare `==`. `Cells.__eq__` evaluates a scalar Cells and raises TypeError for anything else (cells.py:368-376); the bare `==` recipe raised on every target of three lifelib models (fix-final/e02).
4. **Pre-existing gaps T8, T10 and C1 inherit, documented and not fixed:**
   - cross-model evaluation records the callee's nodes in the caller's graph (execution/executor.py:72-73);
   - in-place mutation of a referenced object (change_detection/p13: stale 910.920661 against a true 2551.633285);
   - 0.33's impl `get_referents` checks Spaces before References and lists `_space` and `_model` Namespace objects. So `precedents()` and spyder's `precedentslen` miss a global read when a child Space of the same name exists, and count the system names (fix-used-by/u03; refuter/r07). T10 applies its own order in the wrapper and leaves the impl alone, so `precedentslen` stays byte-stable. Fixing `precedents()` would be a separate Bug Fix.
5. **ReferenceProxy forwarding stays.** Every future Interface member must be defined explicitly on ReferenceProxy, or `__getattr__` will forward it onto a ReferenceImpl. The signature golden makes this visible.
6. **New top-level names hide same-named models** (api.py:614-620), and api.py has no `__all__`, so new non-underscore imports leak into `from modelx import *`. This now applies only to T13's and T14's functions: the exception and warning classes stay in `modelx.core.errors` (decision 3).
7. **Detection must be class-level** (measured f01; §5). The released bridge breaks this rule at seven sites, methods.py:491, 778, 847, 1032, 2731, 2819 and 2852 (§2a #6; fix-bridge-adoption/b03). §7's capability-probe row fixes six of them, and its `_derived` row the seventh.
8. **The CI job depends on PyPI and on the bridge's tags**, needs `--no-deps`, must skip `pip check`, and finds deprecations through a sitecustomize on `PYTHONPATH`, because each suite runs in its own interpreter (§8).
9. **T14 costs +39% to +68% of whole-run time while installed** (prototype, other/p05). It is provisional and opt-in.
10. **"No formula" does not persist**, and the obvious encoder fix breaks 0.33 readers (f04). Documented; decision 10.
11. **No thread safety is promised.** Core state is unlocked (api.py:1469-1470) and the stamps are not atomic. Cold O(model) scans (6.6–76 ms for the T10 prototype, fix-used-by/u08) block Pyodide's single thread; T10's cache, with F3's code-object keys for global names and chains, brings a rebuild to 0.32–1.94 ms on CPython.
12. **`id()` reuse in spyder's `'id'` key remains** (198 of 200), because a per-object uid is deferred (decision 8).
13. **Every new class member reserves a name.** A new public member hides a user's member of that name from attribute access and `get_object` (T13). Until 0.36 a new underscore member also hides a user's `_` global, `_` Space Reference made by `new_space(refs=)`, `_` argument or `_` formula ref (§3.0). Formulas, F11's walk and T6's resolver still find the user's member. No lifelib model collides today: 0 of 5,347 member names (fix-validation-and-fixes/v02).

### Measured (what, value, on what, probe)

The `fix-*` folders hold the probes run while the verifiers' findings were fixed: `fix-revision-counter/`, `fix-used-by/`, `fix-reference-identity/`, `fix-spyder-snapshot/`, `fix-bridge-adoption/`, `fix-validation-and-fixes/` and `fix-integrate/`. Each probe ran in one fresh process on CPython 3.11.15 with modelx 0.33.0. cloudpickle 3.1.2 was installed into `fix-spyder-snapshot/` only. `fix-integrate/rerun/` re-ran u04, p04, s02, v03, b04 and b05; all matched their recorded outputs except b05's build time (1.14 ms against 1.05 ms).

Two later verifiers wrote `critic2/probes/` (k01–k07) and `refute2/` (r01–r16). For the last revision, `fix-final/probes/` re-ran k01–k04, k06, k07, r01, r03, r06–r14 in fresh processes, with the same CPython and modelx. Every output matched its recorded one, except temporary paths and timings; r12 needed its model folders on the command line. `fix-final/probes/` also holds new probes e01–e05.

| what | value | on | probe |
|---|---|---|---|
| `_get_repr(fullname=True, add_params=False)` equal to the bridge's `repr_parent` recipe | 16 of 16; leaks `'Syn.__Space1'`, `'Syn.N[1].__Space1'` | synthetic, 0.33 | final/f01 |
| Relative-ref proxy in an ItemSpace | wraps DynamicSpaceImpl; name `'Child'`; `is_derived()` and `refmode` raise AttributeError; `_idstr` `'P.__Space1.Child'`; `_space.rel` AssertionError | synthetic | final/f01; fix-reference-identity/g01 |
| Resolved-slot round trip | 75 of 75 synthetic, 72 of 72 simplelife; previous design 56 / 58 | synthetic, simplelife | fix-reference-identity/g02, g03 |
| Formula results with resolved slots | equal; 16.0–17.5 µs vs 15.8–16.1 µs on 0.33 | simplelife, BasicTerm_SE, synthetic | fix-reference-identity/g04, g07 |
| Resolver by `_idstr` / `_address` of `P[1].rel` | 3.3–3.9 / 11.5–12.4 µs | synthetic | fix-reference-identity/g07 |
| `wrap_impl` prefix test | a `P` → `PX` slot is `None`; `P[1].h()` raises AttributeError; fixed with a dot boundary | synthetic | fix-reference-identity/g06, g06b |
| `_` names through the T6 resolver | refusing every `_` name: 10 of 18 proxies fail; refusing only `__builtins__`, `_self`, `_space`, `_model`: 18 of 18, and the four refused | synthetic | fix-integrate/i03 |
| Live-model pickle on 0.33 | `pickle.dumps(model)` raises AttributeError for a static model, after a calculation and with an ItemSpace | synthetic | fix-reference-identity/g04b; fix-integrate/i02 |
| Proxy equality | `a == b` False with the same impl; `len({a, b})` 2 | synthetic | final/f01 |
| `allow_none`, `_idtuple` on a proxy | answered only by forwarding | synthetic | final/f01 |
| `'argvalues'` extattr on an ItemSpace | `(1,)`; absent unless requested | synthetic | final/f01 |
| `_get_from_name` today | `''` and `'glob'`: KeyError; nested miss: AttributeError | synthetic | final/f01 |
| `get_object('Syn.Base.k.x')` | raw AttributeError; with `as_proxy`, returns the proxy of `Base.k` | synthetic | final/f01 |
| `(NameError, KeyError)` layout | works; `(NameError, AttributeError)` conflicts | CPython 3.11.15 (3.10–3.14 in tool_contract/p01) | final/f01 |
| Instance vs class detection | `hasattr(m, '_get_revision')` True after `m._get_revision = 1`; `hasattr(type(m), ...)` False; `getattr(mx, 'FormulaError')` returns a Model | synthetic | final/f01 |
| Refused Space formula | formula and 2 ItemSpaces become `None` and 0 | synthetic | final/f01 |
| Dynamic Cells doc / `is_cached` | AttributeError / NetworkXError | synthetic | final/f01 |
| Lambda truncation | `'import os\nlambda x: os.sep'` stored as `'lambda x: os.sep'` | synthetic | final/f01 |
| `get_traceback()` after the next run | `[]` | synthetic | final/f01 |
| Costs (µs) | absent `_kind` 0.253; `_idstr` 0.910; full `_get_repr` 1.006; `_idtuple` 1.506; `len(tracegraph)` 0.217; Cells `_is_derived` 0.104; ItemSpace `_is_dynamic` 0.166 | CPython 3.11.15 | final/f01 |
| Static links (T10 prototype), model-wide | uncached 6.6–76 ms; cached rebuild 0.32–1.94 ms; same links both ways; tracegraph unchanged | BasicTerm_S, CashValue_ME, simplelife, BasicTermASL_ME | fix-used-by/u02, u08 |
| Used by across inheritance | `same(p, r)` alone misses 55 of 82 Reference and 319 of 496 Cells entries on BasicTermASL_ME, and 153 of 400 Cells entries on simplelife | lifelib models | fix-used-by/u02 |
| 0.33 `get_referents` order | reports a child Space where a run reads a same-named global | synthetic | fix-used-by/u03 |
| Reference container test | True for 7 binding kinds while live; False after a rebind or a delete; an argument passes it after its ItemSpace is cleared | synthetic | fix-used-by/u04 |
| `_is_valid` after an ItemSpace is built again | parent test by interface: slot, argument and formula ref True again after `del P[3]; P[3]`, `clear_items(); P[3]` and a rebind + `P[3]`; by impl: False in all three; Space, derived and global bindings unchanged; every binding still True after `close()` | synthetic | refute2/r08, r08b; fix-final/e03 |
| Used-by recipe: bare `==` against `same` | `==` raised on 42 of 42, 195 of 195 and 235 of 235 targets and moved `len(tracegraph)` 0 → 2 or 3; `same` raised on 0, left it alone, and matched the prototype's sets | BasicTerm_S, BasicTermASL_ME, simplelife | fix-final/e02; critic2/k02 |
| Chain extraction | the same chains on 3.10.20, 3.11.15, 3.12.3, 3.13.14, 3.14.8 | stdlib only | final/f03 |
| NullFormula round trip | `c = lambda: None` → plain Formula; `c = None` → 0.33 read_model TypeError | 0.33 | final/f04 |
| Model identity across `_BAK1`; closed handle | same object; closed handle `_is_valid()` True, not in registry | BasicTerm_S | final/f04 |
| Revision prototype, corrected list | 46 of 46 moved (`edits` in 42; the other 4 left the file the same); 70 more calls: file changed in 61, `edits` moved in all 61; 0 misses | BasicTerm_S + synthetic | fix-revision-counter/p01, p02; detectors: change_detection/p06 |
| T8's original list | missed 7 paths (del macro, spec sheet, 2 spec paths, `del_spec`, ExcelRange cell, reload); moved `edits` on `Projection[2].pv_net_cf()` and on the first save | BasicTerm_S + synthetic | fix-revision-counter/p08 |
| Evaluation vs `edits` | 0 bump points over 15 workloads; `ItemSpaceParent.set_formula` ran 35 times | BasicTerm_S/SE/ME, CashValue_ME, simplelife, synthetic | fix-revision-counter/p03 |
| Saves and the `saved` stamp | write (new and same path), zip and read leave `edits` and set `saved`; a failed write stays dirty; a displaced `_BAK1` model becomes dirty | synthetic | fix-revision-counter/p04 |
| A failed `read_model` and the stamps | displaced clean model (3, 1, 3) → (8, 1, 3), dirty, files unchanged; with the snapshot putting stamps back: (3, 1, 3) clean, and a dirty one unchanged | synthetic | refute2/r01; critic2/k06; fix-final/e01 |
| A save to a new path | moves `values` (4, 6, 4) → (4, 7, 4) when a computed Cells read `_model.path` | synthetic | refute2/r13 |
| Twelve more edit paths | 0 misses, 1 over-report; `execute_actions` moves `edits` and `values` | synthetic | refute2/r10 |
| Revision read / fingerprint / touch key | 0.151–0.156 (3-tuple) / 5.07–5.67 / 16.4–20.08 µs | BasicTerm_S | fix-revision-counter/p05; change_detection/p12, p01 |
| Top-level check | uncached top-level call: +0.62–0.65 µs (`len`) vs +0.21–0.25 µs, +13–15% (node dicts); cached top-level miss (4.27–4.67 µs): +0.33–0.64 µs minimum, +0.18–0.44 µs median (node dicts); W3 within noise | synthetic, BasicTerm_S | fix-revision-counter/p05; refute2/r02, r03; fix-final/r03 |
| Name routes that skip `is_valid_name` | globals: `class`, `lambda`, `None`, `for`, `a-b`, `1x`, `a b`, `''` accepted; `new_space(refs=)`: `class`, `None`, `a-b`, `1x`, `a b`, `''` and `_` names accepted; `'a-b'`, `'1x'`, `'a b'` and a `refs=` keyword fail `read_model`; `''` fails `write_model`; `_` names dropped on write | synthetic | critic2/k01; refute2/r06, r07; fix-final/e04 |
| User bindings named like system ones | `_space` from `refs=`, a parameter or a returned ref breaks `_space.y`; `__builtins__` from any route breaks `len`; a global `_space` does not | synthetic | fix-final/e04; refute2/r07 |
| Where a name check can sit | `new_space(formula=)`, `S.new_space(formula=)`, `copy` pass `NewSpace.validate` and none of the six formula members; the reader passes `NewSpace` with no formula or refs, and its `set_attr` runs with `System.serializing` set | synthetic | critic2/k04; fix-final/e04 |
| Non-str returned ref | listed in `refs`; `refs[1]` and `dict(refs)` raise KeyError; the whole-model walk raises KeyError, shipped and F11; passes with RefView skipping non-str keys | synthetic | refute2/r14; fix-final/e05 |
| Argument or returned ref named like a Cells | accepted; proxy and Cells share `'P.__Space1.h'`; `_get_from_name` gives the Cells; 0 of 9 lifelib models | synthetic, lifelib | refute2/r11, r12 |
| ReferenceProxy members by forwarding | `_idstr`, `_get_repr`, `_is_valid`, `_idtuple`, `doc`, `name`, `parent` not defined on the class | synthetic | critic2/k07 |
| Underscore members on user-held classes | 55 non-dunder; 26 named nowhere in the previous revision, 18 nowhere in this one, all Formula, IOSpec or Cells helpers | 0.33 classes | critic2/k03; fix-final/k03 on this revision |
| `_kind` lookup; foreign `_kind` | 0.078 µs; 0 of 34 common types | BasicTerm_S | minimal/m02 |
| E2 recipes on 0.33 | 0 of 739 Cells, 0 of 179 refs mismatched | 5 models | minimal/m06 |
| `_idtuple` walk | 62 of 62, nothing created | synthetic | minimal/m03 |
| Address round trip | 11 of 11 literal cases; build 7.5 µs, resolve 16.1 µs | synthetic | itemspaces_dynamic/p08 |
| Resolver prototype | 179 of 179, comparing `_impl` only, not values; Reference 1.86 µs against 3.02 µs | BasicTerm_S + synthetic | tool_contract/p04 |
| `_get_inheritance`-style read | 9.6 / 58.3 / 112.7 µs, against 382 / 717 / 1,768 µs | BasicTerm_S, BasicTermASL_ME, simplelife | inheritance/i04 |
| `precedents()` with F3 | 50.5 → 6.9 µs | BasicTerm_S | depgraph/d13 |
| id reuse; `'valid'` reuse | 198 of 200; 300 of 300 | synthetic | identity_naming/p05; change_detection/p03e |
| Calc hook | +337 ns per append+pop; +39.3% / +67.6% whole run; clean cancel before append | BasicTerm_S, synthetic | other/p05 |
| `get_model_info` prototype | 278 / 537 µs; 4 disagreement cases with the heuristic | lifelib models | other/p01, p01b |
| spyder tree cost | 0.51 ms (BasicTerm_S) to 742 ms (1,000 ItemSpaces) | BasicTerm_S, BasicTerm_SE | spyder-inventory p4_perf |
| spyder's extattrs on a model whose members are named like the requests | 28 user calls (today's list), 29 (with `argvalues`), 2 (Properties on the Model); 0 with the F11 prototype | synthetic | fix-spyder-snapshot/s02 |
| F11 prototype on ordinary models | identical on 53,526 objects; spyder gate passes; BasicTerm_SE + 1,000 tree 652 → 590 ms min | 5 lifelib models | fix-spyder-snapshot/s03 |
| Raw `argvalues` over cloudpickle | fails for a Space or lock argument, and for the whole tree | synthetic | fix-spyder-snapshot/s04 |
| ItemSpace args from `_evalrepr` | 1,060 of 1,060 rows | synthetic, BasicTerm_SE, CashValue_SE | fix-spyder-snapshot/s05 |
| `_` names in public refs views | `__builtins__`; `_` globals in every view; `_a`, `_fr` in an ItemSpace; no system refs | synthetic | fix-spyder-snapshot/s01 |
| Codec and IOSpec | 13 of 29 values raise with a naive tag; 0 differ with `ADDRESSABLE` | simplelife | fix-bridge-adoption/b01 |
| Foreign class names | a name fallback breaks value.get | synthetic | fix-bridge-adoption/b01b |
| Capability probes | 4 wrong answers today; 0 with class-level checks; suites 831 / 975 unchanged | synthetic | fix-bridge-adoption/b03, b03b |
| Public walk (C1(1)) | 77 links; 5,464 Cells nodes equal | BasicTerm_S | fix-bridge-adoption/b04 |
| Formula frames | 201 frames; 897 bytes trimmed against 15,750; 1.05 ms | synthetic | fix-bridge-adoption/b05 |
| Deprecation audit | 17,953 records; suites unchanged | released suites | fix-bridge-adoption/b06b, b06c, b06d |
| lifelib staging | old: SKIPPED, exit 1; new: 190 / 1,165, exit 0 | lifelib 0.17.1 | fix-bridge-adoption/b07 |
| Downstream rehearsal | 830 / 975 / 190 passed | CPython 3.11, bridge-v0.10.0 | tool_contract/ci_rehearsal |
| Reserved names | UserSpace 56, ItemSpace +1, Model 40 pass `is_valid_name`; `set_ref` refuses all; `new_cells`/`new_space`/rename/`new_macro` accept and hide all | synthetic, 0.33 | fix-validation-and-fixes/v01, v01b |
| lifelib name collisions | 0 of 5,347 member names in 29 models | lifelib 0.17.1 libraries + s6models | fix-validation-and-fixes/v02 |
| Space over a macro name | `new_space('mac')` accepted; `write_model` succeeds; `read_model` raises `ValueError: Name 'mac' already used` | synthetic | fix-integrate/i01 |
| v1–v3 readers on 0.33 | a Cells fails with AttributeError; a failed read leaves `<name>_BAK1` and no current model; the prototype fix reads and restores | hand-written models | fix-validation-and-fixes/v07–v10 |
| `clear_formula()` | TypeError, nothing changed; the fix leaves NullFormula | synthetic | fix-validation-and-fixes/v04 |

### Not measured

- **Pyodide:** every timing above is CPython. Pyodide's speed, the T14 callback polling Pyodide's interrupt buffer, and Pyodide 314's bytecode (inferred equal to CPython 3.14.8's).
- **Real implementations:** T5's resolved slots, T6's resolver, T8's bump points, T10's links, F8 and F11 exist only as prototypes patched into a probe process (fix-reference-identity/g02–g07, fix-revision-counter/proto_t8.py, fix-used-by/t10proto.py, fix-validation-and-fixes/v10, fix-spyder-snapshot/s02–s03). T10's chain resolution cost was measured on four lifelib models (u08), and simplelife resolved 45 of 45 listed chains (u02). Its agreement with run-time reads was not measured. T8's snapshot restore (fix-final/e01), F11's RefView skip (e05) and the `same` recipe (e02) were patched in the same way. Decision 9's checks were not prototyped: e04 measured only which routes reach their sites and that the reader runs with `System.serializing` set. The bridge's `links.used_by` was not prototyped.
- **F8 on real pre-0.9 models:** only minimal hand-written v1–v3 models were tried. References, data files and `_method` calls in those formats were not.
- **All changes together:** each change was checked against `test_spyder_surface.py` separately, in process. The combined suite was not run, because pytest is not installed here. T5's effect on RefView output for relative refs inside ItemSpaces is inferred to leave the spyder fixture unchanged, because the fixture has none.
- **Python 3.9** (in modelx's CI matrix): the `ObjectNotFoundError` layout and chain extraction.
- **The CI job on a GitHub runner:** it has not run there. Its suites, audit, model staging and pipe were rehearsed by hand on CPython 3.11 (fix-bridge-adoption/b06, b07). The audit's mechanism alone was checked on 3.10–3.14 (b06d).
- **Free-threaded builds:** T8 and T14 under free threading.
- **A 0.34-written model read by 0.33:** inferred unaffected, because no file-format change is proposed (decision 10 keeps it that way).

