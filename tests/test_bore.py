# from build123d import (
#     Solid,
#     Axis,
#     Color,
#     import_step,
# )

# from ocp_vscode import show, show_clear
from operations import OperationBore, stock_make
from tools import Tool

# import numpy as np
from conftest import part_load
import pytest


@pytest.fixture
def part():
    return part_load("tests/bore-test-part.step")


def test_bore_count(part, show_result, animate):

    # Alsways need 3 pieces of geometry for a machining operation:
    # 1) The part
    # 2) The stock
    # 3) The tool

    # 1) Load a 3D model from a file -> Provided by fixture

    # 2) Generate fitting stock
    stock = stock_make(part, margin=0)

    # 3) Create tool and home it
    tool = Tool(diameter=1.0, length=25.4)

    # Create a bore operation
    op = OperationBore(part=part, tool=tool, stock=stock)

    # Look for bores.
    # Part has 4 bores
    op.find_bores()
    assert len(op.bores) == 4  # All bores

    op.diameter_min = 3
    assert op.diameter_min == 3
    bores = op.find_bores()
    assert len(bores) == 3  # 3 bores > 3 mm

    op.stock_to_leave_radial = 2
    op.find_bores()
    assert len(op.bores) == 1  # Only 6mm bore works with 1mm radial leave

    op._stock_to_leave_radial = 0
    op.diameter_max = 5
    op.diameter_min = None
    op.find_bores()
    assert len(op.bores) == 3  # All but the 6mm bore
