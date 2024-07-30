# wallplate_cutout.py
# Cut out recangular hole in wallplate for an outlet box.

# TODO: Should ramp in and add another pass at bottom.
# TODO: Should chlid objs should use **kwargs to pass in parameters to parent.
# TODO: Support config file for milling params.
#       Maybe a to/from JSON or TOML.
# TODO: Toolpath repr and str

from toolpaths import ToolPathRectangle, Operation

# Rectangle dimensions
WIDTH_X = 70 + 2
HEIGHT_Y = 115 + 2
DEPTH_Z = 25.4 * (1 / 8)

# Rectangle location
# Relative to tool starting position.
X = 0
Y = 0

# Milling parameters
# Tool
TOOL_DIA = 3.175

# Speeds & feeds
FEED_RATE = 500
POS_RATE = 1500
STEPDOWN = 0.75
STEPOVER = TOOL_DIA * 0.4


# Create base rectangle.
rect = ToolPathRectangle(x=X, y=Y, width=WIDTH_X, height=HEIGHT_Y)

# Fill in rest of toolpath parameters
rect.z_top = 0
rect.z_bottom = -DEPTH_Z
rect.z_retract_dist = 2
rect.speed_feed = FEED_RATE
rect.speed_position = POS_RATE
rect.tool_dia = TOOL_DIA
rect.stepdown = STEPDOWN
rect.stepover = STEPOVER
rect.operation = Operation.Pocket

# Generate GCode
fn = "wallplate-cutout.nc"
# rect.GCode()
rect.Save(fn)
print(f"G-code saved to: {fn}")
print(f"Estimated job duration: {rect.estimated_duration}")
