import itertools
import modelx as mx
import pytest

import numpy as np

ref_values = [
    ('a', True, 'True'),
    ('b', False, 'False'),
    ('c', None, 'None'),
    ('d', np.inf, 'Infinity'),
    ('e', np.pi, '3.141592653589793')
]


@pytest.mark.parametrize(
    "parent_type, name, obj, literal",
    list([p[0], *p[1]] for p in itertools.product(['model', 'space'], ref_values))
)
def test_serialize_primitive(parent_type, name, obj, literal, tmp_path):

    m = mx.new_model()
    parent = m if parent_type == 'model' else m.new_space('Space1')
    setattr(parent, name, obj)
    m.write(tmp_path / 'model')
    m.close()

    line = name + " = " + literal
    file = tmp_path / 'model' / ('__init__.py' if parent_type == 'model' else 'Space1/__init__.py')

    with open(file, "r") as fp:
        assert any(l == line for l in fp)

    m2 = mx.read_model(tmp_path / 'model')
    parent = m2 if parent_type == 'model' else getattr(m2, 'Space1')

    assert getattr(parent, name) == obj


