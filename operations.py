# operations.py
# Operations for CNC machining using builder123d.

from abc import ABC, abstractmethod
import logging
import re
from typing import List
import numpy as np
from build123d import (
    Solid,
    Plane,
    Axis,
    Wire,
    Edge,
    Vector,
    Vertex,
    Location,
    Color,
    # Rectangle,
)
from builder123d_utils import *
from tools import Tool

# TODO: Check bounding box dimensions against machine limits
# TODO: Rotate the model if necessary to fit.
# - If we can get principle axes, that should identify the minimum bounding box.
# TODO: Pull  machining direction enum from toolpaths.py
# TODO: Leverage concept of a gcode document from gcode_doc.py to manage general setup.
# TODO: Allow setting of a bottom position just below bottom of part.

# Operations todo list:
# - Bore - spiral in.  Needed for starting a pocket.
# - Slot - Useful for optimizing profiling to avoid completely machining stock that can be left alone.
# - Face - Add new face operation to spiral in.
# - Pocket - Spiral out.
# - Profile - Spiral in, with slotting optimization.
# - Drill - Pecking.  Easy one.  Good to have auto drill matching diameters.
# - Profile - 3D profile.  Need to add a ball end mill.
# - Chamfer - 3D chamfer.  Need to add a chamfer tool.
# - Engrave - V-carve.  Need to add a V-bit tool.
# - Simple single tool width cutting operations to cut out circles, rectangles, etc.  Leverage toolpaths.py.


def stock_make(part, margin: float = 1.0) -> Solid:
    """
    Create a stock object from a part.

    Applies a constant margin around the part bounding box.

    Assumes that tools will be homed on the top  corner of the stock
    closest to the X,Y origin.

    Side effects:
    - Modifies the part position.

    Args:
        part: Part object to create stock from.
        margin: Margin to add to part bounding box.

    Returns:
        Solid: Stock object.
    """

    bbox = part.bounding_box()
    vec_margin = Vector(margin, margin, 0)

    corner1 = bbox.min - vec_margin
    corner2 = bbox.max + vec_margin + Vector(0, 0, margin)

    # Stock size
    sz = corner2 - corner1

    # Create stock box
    # TODO: Assign material
    stock = Solid.make_box(sz.X, sz.Y, sz.Z)
    stock.label = "stock"
    stock.color = Color("LightGray", alpha=0.5)

    # Move the stock to the expected home position.
    loc = Location()
    loc.position = Vector(0, 0, -sz.Z)
    stock.move(loc)

    # Move the part to be centered in the stock.
    loc.position = stock.center() - bbox.center()
    loc.position.Z = stock.position.Z  # Put part on bottom of stock
    part.move(loc)

    return stock


class Operation(ABC):
    def __init__(
        self,
        part: Solid,
        tool: Tool,
        stock: Solid,
        height_safe: float = 5.0,
        speed_feed: int = 100,
        speed_position: int = 100,
        doc: float = 0.3,
        woc: float = 0.5,
        stock_to_leave_radial: float = 0.0,
        stock_to_leave_axial: float = 0.0,
    ):

        self.part = part
        self.tool = tool
        self.stock = stock
        self.height_safe = height_safe
        self.speed_feed = speed_feed
        self.speed_position = speed_position
        self._toolpath = None
        self._gcode = None

        self.doc = doc
        self.woc = woc

        self._stock_to_leave_radial = stock_to_leave_radial
        self._stock_to_leave_axial = stock_to_leave_axial

        self._ops = []
        self._locations = None

        self._logger = logging.getLogger(__name__)

    def __str__(self) -> str:
        return f"Operation({self.name}, Tool: {self.tool.type})"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def part(self):
        """
        Part machining operation is generating.
        """
        return self._part

    @part.setter
    def part(self, value):

        if not isinstance(value, Solid):
            raise ValueError("Part must be a Solid object.")

        self._part = value
        self._ops = []  # Clear out operations settings change

    @property
    def tool(self):
        """
        Tool used for this machining operation.
        """
        return self._tool

    @tool.setter
    def tool(self, value):

        if not isinstance(value, Tool):
            raise ValueError("Tool must be a Tool object.")

        self._tool = value
        self._ops = []  # Clear out operations settings change

    @property
    def stock(self):
        """
        Stock from which to machine the part.
        """

        return self._stock

    @stock.setter
    def stock(self, value):

        if not isinstance(value, Solid):
            raise ValueError("Stock must be a Solid object.")

        self._stock = value
        self._ops = []  # Clear out operations settings change

    @property
    def height_safe(self):
        return self._height_safe

    @height_safe.setter
    def height_safe(self, value):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._height_safe = value
        self._ops = []  # Clear out operations settings change

    @property
    def speed_feed(self):
        return self._speed_feed

    @speed_feed.setter
    def speed_feed(self, value):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._speed_feed = int(value)
        self._ops = []  # Clear out operations settings change

    @property
    def speed_position(self):
        return self._speed_position

    @speed_position.setter
    def speed_position(self, value):

        try:
            value = int(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._speed_position = value
        self._ops = []  # Clear out operations settings change

    @property
    def doc(self) -> float:
        """
        Depth of Cut (doc)
        """
        return self._doc

    @doc.setter
    def doc(self, value: float):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._doc = value
        self._ops = []  # Clear out operations settings change

    @property
    def woc(self) -> float:
        return self._woc

    @woc.setter
    def woc(self, value: float):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._woc = value
        self._ops = []  # Clear out operations settings change

    @property
    def stock_to_leave_radial(self) -> float:
        """
        Stock to leave radial direction.
        """

        return self._stock_to_leave_radial

    @stock_to_leave_radial.setter
    def stock_to_leave_radial(self, value: float):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._stock_to_leave_radial = value
        self._ops = []  # Clear out operations settings change

    @property
    def stock_to_leave_axial(self) -> float:
        """
        Stock to leave axial direction.
        """

        return self._stock_to_leave_axial

    @stock_to_leave_axial.setter
    def stock_to_leave_axial(self, value: float):

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")

        if value < 0:
            raise ValueError("Value must be positive.")

        self._stock_to_leave_axial = value
        self._ops = []  # Clear out operations settings change

    @property
    def gcode(self) -> str:
        """
        Generate GCode for operation.

        Args:
            filename: Optional filename to which to save G-Code.

        Returns:
            str: G-Code as a string.
        """

        if not self._ops:
            self.generate()

        s = "\n".join(self._ops)

        return s

    def save_gcode(self, filename: str = None) -> None:
        """
        Save G-Code to a file.

        Args:
            filename: Filename to save G-Code to.
        """

        if filename is None:
            filename = f"{self.name.lower()}.nc"

        if not isinstance(filename, str):
            raise ValueError("Filename must be a string.")

        with open(filename, "w") as f:
            f.write(self.gcode)

    @abstractmethod
    def generate(self):
        pass

    @property
    def toolpath(self) -> Wire:
        """
        Generate toolpath for operation.

        Alias for to_wire() method.
        """

        return self.to_wire()

    def to_wire(self) -> Wire:
        """
        Converts operations to a wire.
        """

        if not self._ops:
            self.generate()

        expr = "G[01]\s*(X(?P<X>-?\d*\.?\d*))?\s*(Y(?P<Y>-?\d*\.?\d*))?\s*(Z(?P<Z>-?\d*\.?\d*))?"
        expr = re.compile(expr)

        # Initial position
        pos = self.tool.position

        # Process operations
        edges = []
        locations = [Location(pos)]
        for op in self._ops:

            # Skip empty lines
            op = op.strip()
            if not op:
                continue

            # Skip comments
            if op.startswith(";"):
                continue

            # Parse operation
            # TODO: Assumes G0 or G1 for now
            cmd = "G1"

            res = expr.match(op)

            # Skip ops that don't match
            if res is None:
                continue

            vals = res.groupdict()
            vals = {
                k: float(v) if v is not None else None for k, v in vals.items()
            }

            for k, v in vals.items():
                if v is None:
                    if k == "X":
                        vals[k] = pos.X
                    elif k == "Y":
                        vals[k] = pos.Y
                    elif k == "Z":
                        vals[k] = pos.Z

            vec = Vector(**vals)

            # Process command
            if cmd == "G0":
                # Move to position
                pass
            elif cmd == "G1":
                # Linear move
                e = Edge.make_line(pos, vec)
                edges.append(e)
                pos = vec
                locations.append(Location(pos))

            elif cmd == "G2":
                # Arc clockwise
                pass
            elif cmd == "G3":
                # Arc counter-clockwise
                pass

        wire = Wire(edges)
        wire.label = f"Toolpath: {self}"

        self._locations = locations

        return wire

    def cut(self, animate: bool = False) -> Solid:
        """
        Apply the machining operation, cutting the part.

        Assumptions: Wire is continuous.

        Side effects:
        - Modifies the stock, removing material per the tool path.
        """

        if animate:
            from ocp_vscode import show
            import time

        if not self._locations:
            self.to_wire()  # Generates locations too.

        # Get stock properties.
        props = {}
        props["label"] = self.stock.label
        props["color"] = self.stock.color
        props["material"] = self.stock.material

        # Move to first position
        self.tool.location = self._locations[0]
        self._stock -= self.tool  # Avoid type check.

        # Iterate through the edges, removing material.
        for loc in self._locations[1:]:

            # Remove cut volume from stock
            cut = self.tool.sweep(loc)
            self._stock -= cut

            if animate:
                self.stock.label = props["label"]
                self.stock.color = props["color"]
                show(self.part, self.stock, self.tool)  # , cut_solid)
                time.sleep(0.1)

        # Replace stock proprties
        self.stock.label = props["label"]
        self.stock.color = props["color"]
        self.stock.material = props["material"]

        return self.stock


class Bore:
    """
    Defines a circular bore into a part.
    """

    def __init__(self, circle: Wire, part: Solid):

        if not circle.is_circle:
            raise ValueError("Circle must be a circle.")

        # Make sure circle is in the XY plane
        vertices = circle.edges()[0].vertices()
        if vertices[0].Z != vertices[1].Z:
            raise ValueError("Circle must be in the XY plane.")

        self._circle = circle
        self._part = part

        # The bore top and bottom are a Vertex at the center of the circle
        # at the top and bottom positions.
        x = np.mean([vertices[0].X, vertices[1].X])
        y = np.mean([vertices[0].Y, vertices[1].Y])
        z = vertices[0].Z
        self._top = Vertex(x, y, z)

        # Find the bottom face of the bore.
        v = vertices[0]

        # Find the non-horizontal faces that contain the vertex.
        v_faces = [face for face in part.faces() if v in face.vertices()]
        v_faces = [
            face
            for face in v_faces
            if np.isclose(face.normal_at(face.center()).Z, 0)
        ]

        # Find a vertex on the bottom odf those faces.
        z_min = (v_faces[0].vertices() << Axis.Z)[0].Z

        self._bottom = Vertex(x, y, z_min)

    @property
    def top(self) -> Vertex:
        """
        Vertex at top center of bore.
        """
        return self._top

    @property
    def bottom(self) -> Vertex:
        """
        Vertex at bottom center of bore.
        """
        return self._bottom

    @property
    def radius(self) -> float:
        """
        Radius of bore.
        """

        return self._circle.edges()[0].radius

    @property
    def diameter(self) -> float:
        """
        Diameter of bore.
        """
        return 2 * self.radius

    @property
    def depth(self) -> float:
        """
        Depth of bore.
        """
        return self.top.Z - self.bottom.Z

    @classmethod
    def find_bores(self, part: Solid) -> List["Bore"]:
        """
        Find all circular bores in a part.

        Args:
            part: Part to search for bores.

        Returns:
            List[Bore]: List of bores in the part.
        """

        if not isinstance(part, Solid):
            raise ValueError("Part must be a Solid object.")

        circles = []
        for face in part.faces() | Plane.XY:

            # Faces parallel with the XY plane.
            if np.isclose(face.normal_at(face.center()).Z, 1):
                # Positive Z face
                face_circles = face.circular_holes

                if face_circles:
                    for circle in face_circles:
                        circles.append(circle)

        bores = []
        for circle in circles:
            bores.append(Bore(circle, part))

        return bores

    def show(self):
        """
        Show the bore.
        """
        from ocp_vscode import show_object

        show_object(self._circle)
        show_object(self._top)
        show_object(self._bottom)


class OperationBore(Operation):
    """
    Boring operation.

    See: Operation
    """

    def __init__(
        self,
        part: Solid,
        tool: Tool,
        stock: Solid,
        diameter_min: float = None,
        diameter_max: float = None,
        **kwargs,
    ):
        super().__init__(
            part,
            tool,
            stock,
            **kwargs,
        )

        self._diameter_min = diameter_min
        self._diameter_max = diameter_max

        self._holes = None

    @property
    def name(self) -> str:
        return "Bore"

    @property
    def diameter_min(self) -> float:
        """
        Minimum diameter hole to bore.

        All ciricular holes with a diameter equal to or larger
        than this value will be bored.

        If None, the minimum diameter to bore is 1.1 times the tool diameter plus
        the radial stock to leave.

        Defaults to None.
        """

        return self._diameter_min

    @diameter_min.setter
    def diameter_min(self, value: float):

        # Allow value to be cleared
        if value is None:
            self._diameter_min = None
            self._ops = []
            return

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")
        if value < 0:
            raise ValueError("Value must be positive.")
        self._diameter_min = value
        self._ops = []

    @property
    def diameter_max(self) -> float:
        """
        Maximum diameter hole to bore.

        All ciricular holes with a diameter equal to or smaller
        than this value will be bored.

        If None, there is no upper limit imposed.

        Defaults to None.
        """
        return self._diameter_max

    @diameter_max.setter
    def diameter_max(self, value: float):

        # Allow value to be cleared
        if value is None:
            self._diameter_max = None
            self._ops = []
            return

        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be numeric.")
        if value < 0:
            raise ValueError("Value must be positive.")
        self._diameter_max = value
        self._ops = []

    @property
    def holes(self) -> List[Wire]:
        """
        List of wires representing holes to bore.

        This value will be automatically generated from the part if not set.

        If set, autogeneration of list will not be performed.

        """

        if self._holes:
            return self._holes

        # Minimum diameter to bore
        if self.diameter_min is None:
            diameter_min = self.tool.diameter * 1.1 + self.stock_to_leave_radial
            self.diameter_min = diameter_min

        # Maximum diameter to bore
        if self.diameter_max is None:
            diameter_max = np.inf
            self.diameter_max = diameter_max

        # No holes set, generate from part
        circles = []
        for face in self.part.faces() | Plane.XY:

            # Faces parallel with the XY plane.
            if np.isclose(face.normal_at(face.center()).Z, 1):
                # Positive Z face
                face_circles = face.circular_holes

                if face_circles:
                    for circle in face_circles:
                        circles.append(circle)

        # Find circles that have a diameter within the range.
        self._holes = []
        for circle in circles:
            if (
                circle.edges()[0].radius * 2 >= self.diameter_min
                and circle.edges()[0].radius * 2 <= self.diameter_max
            ):
                self._holes.append(circle)

        return self._holes

    @holes.setter
    def holes(self, value: list[Wire]):

        # Allow value to be cleared
        if value is None:
            self._holes = value
            self._ops = []
            return

        # Allow single wire to be passed in.
        if not isinstance(value, list):
            if isinstance(value, Wire):
                value = [value]

        if not isinstance(value, list):
            raise ValueError("Value must be a list.")
        if not all(isinstance(v, Wire) for v in value):
            raise ValueError("All values must be Wire objects.")
        self._holes = value
        self._ops = []

    def generate(self) -> None:
        """
        Generate toolpath for operation.
        """

        raise NotImplementedError("Bore operation not implemented.")

        # Operations list
        ops = []

        # Precalculated data
        # Save Z position
        safe_z = self.stock.bounding_box().max.Z + self.height_safe
        str_speed_feed = f"F{self.speed_feed:d}"
        str_speed_position = f"F{self.speed_position:d}"
        op_safe_z = f"G0 Z{safe_z:0.3f} {str_speed_position}"

        # Move the tool to the first position
        z = self.stock.bounding_box().max.Z
        ops.append(op_safe_z)

        # Move to pre-cut position
        x_start = -self.tool.radius + self.woc
        y_start = self.stock.bounding_box().min.Y


class OperationFace(Operation):
    """
    Back and forth facing operation.

    See: Operation
    """

    # TODO: Face over all of stock or just part
    # TODO: Machining direction: both, climb, standard(?)

    def __init__(
        self,
        part: Solid,
        tool: Tool,
        stock: Solid,
        **kwargs,
    ):
        super().__init__(part, tool, stock, **kwargs)

        # Facing does not support radial stock to leave
        if not np.isclose(self._stock_to_leave_radial, 0.0):
            self._logger.warning(
                "Facing operation does not support radial stock to leave."
            )
            self._stock_to_leave_radial = 0.0

    @property
    def name(self) -> str:
        return "Face"

    def generate(self) -> None:
        """
        Generate toolpath for operation.
        """

        # Operations list
        ops = []

        # Precalculated data
        # Save Z position
        safe_z = self.stock.bounding_box().max.Z + self.height_safe
        str_speed_feed = f"F{self.speed_feed:d}"
        str_speed_position = f"F{self.speed_position:d}"
        op_safe_z = f"G0 Z{safe_z:0.3f} {str_speed_position}"

        # Y extents moving tool center clear of stock
        y_max = self.stock.bounding_box().max.Y + self.tool.radius * 1.1
        y_min = self.stock.bounding_box().min.Y - self.tool.radius * 1.1

        # Test position to make sure ends getting cut.
        # y_max = self.stock.bounding_box().max.Y
        # y_min = self.stock.bounding_box().min.Y

        # Move the tool to the first position
        z = self.stock.bounding_box().max.Z
        ops.append(op_safe_z)

        # Move to pre-cut position
        x_start = -self.tool.radius + self.woc
        y_start = y_min

        # TODO: Spin up tool

        # Do the facing operations
        # TODO: Loop to top face of part
        x_max = self.stock.bounding_box().max.X
        z_min = self.part.bounding_box().max.Z + self.stock_to_leave_axial
        i_pass = 0
        z = -self.doc

        # Degenerate case of a single pass that's smaller than the DOC.
        if z < z_min:
            z = z_min

        while z >= z_min:
            i_pass += 1
            ops.append("\n")
            ops.append(f"; Pass {i_pass}")

            # Move to start position
            # TODO: need to reverse order of operations.
            x = x_start
            ops.append(
                f"G0 X{x_start:0.3f} Y{y_start:0.3f} {str_speed_position}"
            )

            # Move to new Z position
            ops.append(f"G0 Z{z:0.3f} {str_speed_position}")

            while x < x_max:
                # Move to +Y
                ops.append(f"G1 Y{y_max:0.3f} {str_speed_feed}")

                # Index over
                x += self.woc
                ops.append(f"G1 X{x:0.3f} {str_speed_position}")

                # Move to -Y
                ops.append(f"G1 Y{y_min:0.3f} {str_speed_feed}")

                # Index over
                x += self.woc
                ops.append(f"G1 X{x:0.3f} {str_speed_position}")

            # Look for last pass.
            if z == z_min:
                break

            # Index down
            z -= self.doc
            if z < z_min:
                z = z_min

        # Leave the tool at a safe height
        ops.append(op_safe_z)

        self._ops = ops
