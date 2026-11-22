import importlib

import pytest

import modelx as mx


@pytest.mark.parametrize(
    "formula",
    [
        'lambda i: {"refs": {"scale": i * 10}}',
        'lambda i: dict(refs=dict(scale=i * 10))',
        '''
def formula(i):
    refs = {"scale": i * 10}
    params = dict(refs=refs)
    return params
''',
        '''
def formula(i):
    if i == 0:
        return {}
    if i == 1:
        return None
    if i == 2:
        return {"refs": None}
    if i < 0:
        refs = {"offset": -i}
    else:
        refs = {"scale": i * 10}
    return {"refs": refs}
''',
    ],
    ids=["literal", "dict-call", "local-variables", "branches"],
)
@pytest.mark.parametrize("use_slots", [True, False])
def test_dynamic_references_match_live(formula, use_slots, tmp_path, monkeypatch):
    model = mx.new_model()
    try:
        space = model.new_space("S", formula=formula.strip(), refs={"scale": 1, "offset": 1})
        space.new_cells("value", "lambda: scale + offset")
        package = f"dynamic_refs_{tmp_path.name.replace('-', '_')}"
        model.export(tmp_path / package, use_slots=use_slots)
        monkeypatch.syspath_prepend(str(tmp_path))
        exported = importlib.import_module(package).mx_model
        for i in (-3, 0, 1, 2, 3):
            assert exported.S[i].value() == space[i].value()
    finally:
        model.close()


@pytest.mark.parametrize(
    "formula",
    [
        'lambda i: {"refs": {str(i): i}}',
        '''
def formula(i):
    refs = {}
    refs["scale"] = i
    return {"refs": refs}
''',
        '''
def formula(i):
    refs = {}
    try:
        raise ValueError()
    except ValueError as refs:
        return {"refs": refs}
''',
        '''
def formula(i):
    def dict():
        return {"refs": {"scale": i}}
    return dict()
''',
    ],
    ids=["computed-key", "mutated-local", "rebound-local", "shadowed-dict"],
)
def test_unsupported_dynamic_references_fail_at_export(formula, tmp_path):
    model = mx.new_model()
    try:
        model.new_space("S", formula=formula.strip())
        with pytest.raises(ValueError, match=r"Cannot export Space formula for .*\.S:.*statically named"):
            model.export(tmp_path / "unsupported_refs")
    finally:
        model.close()
