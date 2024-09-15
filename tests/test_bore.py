# from build123d import (
#     Solid,
#     Axis,
#     Color,
#     import_step,
# )

from ocp_vscode import show, show_clear
import time
from operations import OperationBore, stock_make
from tools import Tool

# import numpy as np
from conftest import part_load
import pytest


@pytest.fixture
def part():
    return part_load("tests/bore-test-part.step")


def test_find_bores(part, show_result, animate):
    """
    Test to find bores by diameter and stock to leave.
    """

    # Alsways need 3 pieces of geometry for a machining operation:
    # 1) The part
    # 2) The stock
    # 3) The tool

    # 1) Load a 3D model from a file -> Provided by fixture
    # Part has 4 bores of dia: 2mm, 4mm (2x), 6mm

    # 2) Generate fitting stock
    stock = stock_make(part, margin=0)

    # 3) Create tool and home it
    tool = Tool(diameter=1.5, length=25.4)

    # Create a bore operation
    op = OperationBore(part=part, tool=tool, stock=stock)

    # Look for bores.
    op.find_bores()
    assert len(op.bores) == 1  # Only the small bore

    tool = Tool(diameter=2.5, length=25.4)
    op = OperationBore(part=part, tool=tool, stock=stock)
    bores = op.find_bores()
    assert len(bores) == 2  # The two 4mm dia bores

    op.stock_to_leave_radial = 1
    op.find_bores()
    assert len(op.bores) == 1  # Only 6mm bore works with 1mm radial leave
    assert 6 == pytest.approx(op.bores[0].diameter, 0.01)


def test_find_shallow_bore(part):
    """
    Test to find bore with limited tool length.
    """

    # 3 of the 4 bores in the part are 10mm deep.
    # The other is 7mm deep.

    # 1) Load a 3D model from a file -> Provided by fixture

    # 2) Generate fitting stock
    stock = stock_make(part, margin=0)

    # 3) Create tool and home it
    tool = Tool(diameter=2.5, length=8)

    # Create a bore operation
    op = OperationBore(part=part, tool=tool, stock=stock)

    # Should only be able to find one bore we can reach the depth.
    op.find_bores()
    assert len(op.bores) == 1  # 7 mm deep bore

    # Now, leave some extra axial stock to reach the 10mm deep bores.
    op.stock_to_leave_axial = 4
    op.find_bores()
    assert len(op.bores) == 2  # Both 4mm bores accessible now.


def test_accessible_bores(show_result):
    """
    When finding bores, return only those that don't have stock above them.
    """

    # In the more complex part, one bore starts on the top,
    # the other 3 are in a pocket.

    # 1) Load a 3D model from a file
    part = part_load("tests/simple-part-with-holes.step")

    # 2) Generate fitting stock
    stock = stock_make(part, margin=0)

    # 3) Create tool and home it
    tool = Tool(diameter=2.5, length=8)

    # Create a bore operation
    op = OperationBore(part=part, tool=tool, stock=stock)

    # Should only be able to find one bore we can reach the depth.
    op.find_bores()
    assert len(op.bores) == 1  # Only 1 bore is accessible

    if show_result:
        show(part, stock)
        time.sleep(3)
        show_clear()


def test_boring(part, show_result, animate):
    """
    Test boring operation.
    """

    # Alsways need 3 pieces of geometry for a machining operation:
    # 1) The part
    # 2) The stock
    # 3) The tool

    # 1) Load a 3D model from a file -> Provided by fixture

    # 2) Generate fitting stock
    stock = stock_make(part, margin=0)
    stock_vol_pre = stock.solid().volume

    # 3) Create tool and home it
    tool = Tool(diameter=1.5, length=25.4)

    # Create a bore operation
    op = OperationBore(part=part, tool=tool, stock=stock)
    op.diameter_max = 4

    # Look for bores.
    op.find_bores()

    # TODO: Estimate the volume of the bores to be removed.
    # Calcuate material volume removed for later check.
    stock_vol_post = stock_vol_pre
    for bore in op.bores:
        stock_vol_post -= bore.volume

    # Machine the bores
    op.generate()
    op.save_gcode()
    stock = op.cut(animate=animate)

    assert stock_vol_post == pytest.approx(
        stock.solid().volume, 0.1
    )  # Stock volume vs. expected

    if show_result:
        show(part, stock)
        time.sleep(3)
        show_clear()
