import pytest

import modelx as mx


@pytest.fixture
def close_new_models():
    """Close every model created during the test, including partially
    built ones left behind if a reader raises mid-load."""
    before = set(mx.get_models())
    yield
    for name, model in list(mx.get_models().items()):
        if name not in before:
            model.close()
