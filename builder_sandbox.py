from build123d import *
from ocp_vscode import show, show_object, show_clear
from pathlib import Path
from operations import OperationBore, stock_make
from tools import Tool

show_clear()

# Alsways need 3 pieces of geometry for a machining operation:
# 1) The part
# 2) The stock
# 3) The tool

# 1) Load a 3D model from a file
# fn_part = "simple-part.step"
# fn_part = "simple-part-with-holes.step"
fn_part = "tests/bore-test-part.step"
part = import_step(fn_part)
part.label = Path(fn_part).stem
part.color = Color("Orange")

# 2) Generate fitting stock
stock = stock_make(part, margin=0)

show(part, stock)

# 3) Create tool and home it
tool = Tool(diameter=1, length=25.4)
tool.to_stock_home(stock)

op = OperationBore(part=part, tool=tool, stock=stock)
