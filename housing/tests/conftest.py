"""Session fixtures: reference solids that are slow to build are built once."""
import pytest

from housing import reference
from housing.base import build_base


@pytest.fixture(scope="session")
def base():
    return build_base()


@pytest.fixture(scope="session")
def cover():
    from housing.cover import build_cover   # imported here, so a broken cover fails only the tests that use it

    return build_cover()


@pytest.fixture(scope="session")
def board():
    return reference.load_board()


@pytest.fixture(scope="session")
def disc():
    return reference.disc_envelope()


@pytest.fixture(scope="session")
def drive():
    return reference.drive_box()
