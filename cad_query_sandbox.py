# CAD Query GUI bin:
# C:\Users\harriman\cq-editor\Scripts\CQ-editor.exe

# Interesting alternative to CAD Query:
# https://github.com/gumyr/build123d

# Using visualization server
# https://github.com/bernhard-42/jupyter-cadquery

# VS Code plugin by Bernhard 42
# https://marketplace.visualstudio.com/items?itemName=bernhard-42.ocp-cad-viewer

# CAM package:
# https://ocp-freecad-cam.readthedocs.io/en/latest/index.html


import cadquery as cq
from cadquery_massembly import MAssembly, relocate

# stock = cq.Workplane("XY" ).box(150, 150, 20).edges("|Z").fillet(0.125)

from jupyter_cadquery.viewer.client import show
from jupyter_cadquery import web_color, set_defaults
from jupyter_cadquery import Edges, Faces, Part, Vertices

# Path
# Looks like you can't sweep an object, just a wire.
# tool = cq.Workplane("XY").cylinder(50,3.175/2,(0,0,1))
# tool = tool.translate((-100,0,30))

# fn_step = "c:\\tmp\\simple-part.step"
fn_step = "simple-part.step"
step = cq.importers.importStep(fn_step)


if False:
    # Points we will use to create spline and polyline paths to sweep over
    pts = [(0, 1), (1, 2), (2, 4)]

    # Switch to a polyline path, but have it use the same points as the spline
    path1 = cq.Workplane("XZ").polyline(pts, includeCurrent=True)

    # Using a polyline path leads to the resulting solid having segments rather than a single swept outer face
    plineSweep = cq.Workplane("XY").circle(1.0).sweep(path1, transition="round")

    show_object(plineSweep, options={"color": (64, 64, 64), "alpha": 0.25})
    show_object(path1)


# Translate the resulting solids so that they do not overlap and display them left to right

# CQ GUI version of show
# show_object(step,options={'color':(64,64,64),'alpha':0.25})
# show_object(step.faces('|Z').wires())
# show_object(step.faces('+Z').wires())

display_options = {
    "reset_camera": True,
    "axes": True,
    "axes0": True,  # Show origin at (0,0,0)
    "grid": [True, False, False],
    "ortho": True,
    "cad_width": 1200,
    "height": 800,
    # "default_color": (128, 128, 128),
    "default_edge_color": "#FFFFFF",
    "black_edges": True,
}
set_defaults(**display_options)

# To display multiple objects, they must be in an assembly.
assy = MAssembly(step, name="Part", color=web_color("lightblue"))

# Add in some other stuff
assy = assy.add(
    step.faces("+Z").wires(),
    name="Edges",
    color=web_color("orange"),
)
assy = assy.add(
    step.faces("+Z"),
    name="Faces",
    color=web_color("green"),
)

# Jupyter CAD Query version of show
# show(assy)

# https://github.com/bernhard-42/jupyter-cadquery/tree/master?tab=readme-ov-file#jupyter-cadquery-classes
edges = Edges(step.faces("+Z").edges(), color=web_color("red"))
show(edges)

# faces = Faces(
#     step.faces("+Z"),
#     color=web_color("green"),
#     show_edges=True,
# )
# show(faces)
