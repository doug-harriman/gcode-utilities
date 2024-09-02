from build123d import (
    Solid,
    Axis,
    Color,
    import_step,
)
from ocp_vscode import show
from operations import OperationFace, stock_make
from tools import Tool
import numpy as np
from conftest import part_load


def test_basic_face(show_result, animate):

    # Alsways need 3 pieces of geometry for a machining operation:
    # 1) The part
    # 2) The stock
    # 3) The tool

    # 1) Load a 3D model from a file
    fn_part = "simple-part.step"
    part = part_load(fn_part)

    # 2) Generate fitting stock
    stock = stock_make(part, margin=2)

    # Craeting stock will move the part
    part_face_top = part.faces() >> Axis.Z
    part_face_top_z = part_face_top.vertices()[0].Z

    # 3) Create tool and home it
    tool = Tool(diameter=3.175, length=25.4)
    tool.to_stock_home(stock)

    f = OperationFace(part=part, tool=tool, stock=stock)
    # f.stock_to_leave_axial = 0.5
    # f.stock_to_leave_radial = 0.5
    f.woc = tool.diameter * 0.4
    f.doc = 0.75
    f.generate()
    f.save_gcode()
    toolpath = f.toolpath
    stock = f.cut(animate=animate)

    # TODO: Add an axial stock to leave test

    if show_result:
        show(part, stock, tool, toolpath)

    stock_face_top = stock.faces() >> Axis.Z
    stock_face_top_z = stock_face_top.vertices()[0].Z

    # TODO: Looks like the G-code generated is correct, but the wire representation is not.
    #       Beliveve I broke something in updates made for the bore operation.
    assert np.isclose(part_face_top_z, stock_face_top_z)
