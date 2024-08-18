from build123d import *
from ocp_vscode import show, show_object, show_clear
from pathlib import Path
from operations import OperationFace, stock_make
from tools import Tool


# Alsways need 3 pieces of geometry for a machining operation:
# 1) The part
# 2) The stock
# 3) The tool

# 1) Load a 3D model from a file
fn_part = "simple-part.step"
part = import_step(fn_part)
part.label = Path(fn_part).stem
part.color = Color("Orange")

# 2) Generate fitting stock
stock = stock_make(part, margin=2)

# 3) Create tool and home it
tool = Tool(diameter=3.175, length=25.4)
tool.to_stock_home(stock)

f = OperationFace(part=part, tool=tool, stock=stock)
f.woc = tool.diameter * 0.4
f.doc = 0.75
f.generate()
f.save_gcode()
toolpath = f.toolpath
stock = f.cut()


show(part, stock, tool, toolpath)
