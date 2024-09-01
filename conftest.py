import pytest
from pathlib import Path
from build123d import Solid, Color, import_step
from ocp_vscode import show_clear, set_port

DEFAULT_PORT = 3939


def pytest_addoption(parser):
    parser.addoption(
        "--animate",
        action="store_true",
        default=False,
        help="Animate machining operations",
    )

    parser.addoption(
        "--show_result",
        action="store_true",
        default=False,
        help="Shows results at end of test",
    )


@pytest.fixture(scope="session")
def animate(pytestconfig):
    val = pytestconfig.getoption("animate")

    if val:
        set_port(DEFAULT_PORT)
        show_clear()

    return val


@pytest.fixture(scope="session")
def show_result(pytestconfig):
    val = pytestconfig.getoption("show_result")

    if val:
        set_port(DEFAULT_PORT)
        show_clear()

    return val


def part_load(fn: str) -> Solid:

    assert isinstance(fn, str)
    assert Path(fn).exists()

    part = import_step(fn)
    part.label = Path(fn).stem
    part.color = Color("Orange")
    return part
