# Generate set of bores for testing heat insert diameters.

import os
from toolpaths import ToolPathCylinder


# Parameters
TOOL_DIA = 2.0

# Speeds & feeds
FEED_RATE = 300
POS_RATE = 1500
STEPDOWN = 0.75

# Bore parameters
BORE_DEPTH = 7  # Unsigned
BORE_DIA = 3.6
BORE_TOP = 0

# Create a bore
bore = ToolPathCylinder()
bore.x = 0
bore.y = 0
bore.z_top = BORE_TOP
bore.z_bottom = -BORE_DEPTH
bore.diameter = BORE_DIA
bore.bore = True

bore.tool_dia = TOOL_DIA
bore.speed_feed = FEED_RATE
bore.speed_position = POS_RATE
bore.stepdown = STEPDOWN


# Generate GCode

# The g-code file name should be the name of this file
# with the extension changed to .nc and "_" chars replaced with "-"
fn = os.path.basename(__file__)
fn = fn.replace(".py", ".nc").replace("_", "-")

bore.Save(fn)
print(f"G-code saved to: {fn}")
print(f"Estimated job duration: {bore.estimated_duration}")

# Shoulder cut
fn = fn.replace(".nc", "-shoulder.nc")
bore.diameter += 0.4
bore.z_bottom = -1
bore.GCode()  # Force regen
bore.Save(fn)
print(f"G-code saved to: {fn}")
