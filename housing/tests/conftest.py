"""Session fixtures: reference solids that are slow to build are built once."""
import pytest

from housing import reference


@pytest.fixture(scope="session")
def board():
    return reference.load_board()


@pytest.fixture(scope="session")
def disc():
    return reference.disc_envelope()


@pytest.fixture(scope="session")
def drive():
    return reference.drive_box()
