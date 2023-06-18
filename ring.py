# Generates G-Code for a ring.
from toolpaths import ToolPathCylinder, ToolPathFace, AppendFiles

# Ring
ID = 18.85
OD = ID + 3 * 2
HEIGHT = 5.5

# Tool
TOOL_DIA = 3.175

# Workpiece
WORKPIECE_HEIGHT = 19

# Speeds & feeds
FEED_RATE = 600
POS_RATE = 1500
STEPDOWN = 0.5
STEPOVER = TOOL_DIA * 0.2

# Locate center of ring inside workpiece
x_center = OD / 2 + TOOL_DIA / 2 + STEPOVER
y_center = x_center

# File name
fn_ring = f"ring-id={ID}-od={OD}-h={HEIGHT}.nc"
with open(fn_ring, "w") as fp:
    fp.write(f"; Ring ID={ID} OD={OD} H={HEIGHT}\n")

# Facing
if WORKPIECE_HEIGHT > HEIGHT:
    # Need to face top of workpiece down.

    # Create facing toolpath
    side_len = OD + TOOL_DIA + STEPOVER
    facing = ToolPathFace(x=side_len, y=side_len+7)
    facing.z_top = 0
    facing.z_bottom = -(WORKPIECE_HEIGHT - HEIGHT)
    facing.stepdown = 1.5
    facing.stepover = TOOL_DIA * 0.4
    facing.speed_feed = FEED_RATE
    facing.speed_position = POS_RATE
    facing.tool_dia = TOOL_DIA
    facing.GCode()

    depth = facing.z_top - facing.z_bottom
    fn_facing = f"facing-side={side_len:0.2f}-depth={depth:0.2f}.nc"
    facing.Save(fn_facing)
    AppendFiles(fn_ring, fn_facing)

# Cut inner bore
bore = ToolPathCylinder(x=x_center, y=y_center)
bore.bore = True
bore.diameter = ID
bore.z_top = -(WORKPIECE_HEIGHT - HEIGHT)
bore.z_bottom = -WORKPIECE_HEIGHT + 0.1
bore.z_retract_dist = bore.z_top + 2
bore.speed_feed = FEED_RATE
bore.speed_position = POS_RATE
bore.tool_dia = TOOL_DIA
bore.stepdown = STEPDOWN
bore.stepover = STEPOVER
bore.GCode()
fn_bore = f"bore-id={bore.diameter}.nc"
bore.Save(fn_bore)
AppendFiles(fn_ring, fn_bore)

# Cut outer profile
profile = bore
profile.bore = False
profile.diameter = OD
profile.GCode()
fn_profile = f"profile-id={profile.diameter}.nc"
profile.Save(fn_profile)
AppendFiles(fn_ring, fn_profile)
