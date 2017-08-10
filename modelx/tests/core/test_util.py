from modelx.core.util import (is_valid_name,
                              AutoNamer)

import pytest



@pytest.mark.parametrize("name",
                         [
                             "Cells123",
                             "Space_123",
                         ]
                         )
def test_is_valid_name_valid(name):
    assert is_valid_name(name)


@pytest.mark.parametrize("name",
                         [
                             "123foo",
                             "_foo",
                             "foo bar",
                             "*foo",
                             "__foo__",
                             "foo.bar",
                             "boo/bar"
                         ]
                         )
def test_is_valid_name_invalid(name):
    assert not is_valid_name(name)


@pytest.fixture
def simplenamer():
    autonamer = AutoNamer("Cells")

    for i in range(10):
        autonamer.get_next([])

    return autonamer


def test_get_next(simplenamer):
    assert simplenamer.get_next([]) == "Cells11"


def test_get_next_skip_existing(simplenamer):
    existing_names = ["Cells11",
                      "Cells12",
                      "Cells13"]

    assert simplenamer.get_next(existing_names) == "Cells14"


