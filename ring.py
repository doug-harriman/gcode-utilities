# Generates G-Code for a ring.
from toolpaths import ToolPathCylinder, ToolPathFace, AppendFiles
import datetime as dt
import os

# Ring
ID = 18.85
RING_RADIAL_THICKNESS = 2
OD = ID + RING_RADIAL_THICKNESS * 2
HEIGHT = 6

# Tool
TOOL_DIA = 3.175

# Workpiece
WORKPIECE_HEIGHT = 20
WORKPIECE_X_LEN = 28
WORKPIECE_Y_LEN = 28

# Speeds & feeds
FEED_RATE = 500
POS_RATE = 1500
STEPDOWN = 0.5
STEPOVER = 0.25

# Locate center of ring inside workpiece
x_center = OD / 2 + TOOL_DIA + STEPOVER
y_center = x_center

# File name
fn_ring = f"ring-id={ID}-od={OD}-h={HEIGHT}.nc"
with open(fn_ring, "w") as fp:
    fp.write("\n; ---- Operations ----\n\n")

# Total job time
job_time = dt.timedelta(seconds=0)

# Facing
if WORKPIECE_HEIGHT > HEIGHT:
    # Need to face top of workpiece down.

    # Create facing toolpath
    facing = ToolPathFace(x=WORKPIECE_X_LEN, y=WORKPIECE_Y_LEN)
    facing.z_top = 0
    facing.z_bottom = -(WORKPIECE_HEIGHT - HEIGHT)
    facing.stepdown = 1.5
    facing.stepover = TOOL_DIA * 0.4
    facing.speed_feed = FEED_RATE
    facing.speed_position = POS_RATE
    facing.tool_dia = TOOL_DIA
    facing.GCode()
    job_time += facing.estimated_duration

    depth = facing.z_top - facing.z_bottom
    fn_facing = "ring-facing.nc"
    facing.Save(fn_facing)
    AppendFiles(fn_ring, fn_facing)

# Cut inner bore
bore = ToolPathCylinder(x=x_center, y=y_center)
bore.segments = 120
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
job_time += bore.estimated_duration

fn_bore = f"ring-bore-id={bore.diameter}.nc"
bore.Save(fn_bore)
AppendFiles(fn_ring, fn_bore)

# Cut outer profile
profile = bore
profile.bore = False
profile.diameter = OD
profile.GCode()
job_time += profile.estimated_duration

fn_profile = f"ring-profile-od={profile.diameter}.nc"
profile.Save(fn_profile)
AppendFiles(fn_ring, fn_profile)


# ADd in header
fn_header = "header.nc"
with open(fn_header, "w") as fp:
    fp.write(f"; Ring ID={ID} OD={OD} H={HEIGHT}\n")
    fp.write(f"; Estimated job time: {job_time}\n")

AppendFiles(fn_header, fn_ring)
os.rename(fn_header, fn_ring)
