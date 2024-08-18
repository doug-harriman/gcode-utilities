# operations.py
# Operations for CNC machining using builder123d.

from abc import ABC, abstractmethod
import re
from build123d import (
    Solid,
    Plane,
    Wire,
    Edge,
    Vector,
    Location,
    Color,
    Rectangle,
)

# TODO: Check bounding box dimensions against machine limits
# TODO: Rotate the model if necessary to fit


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
    vec_margin = Vector(margin, margin, margin)

    corner1 = bbox.min - vec_margin
    corner2 = bbox.max + vec_margin

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
    part.move(loc)

    return stock


class Operation(ABC):
    def __init__(
        self,
        part=None,
        tool=None,
        stock=None,
        height_safe: float = 5.0,
        speed_feed: int = 100,
        speed_position: int = 100,
        doc: float = 0.3,
        woc: float = 0.5,
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

        self._ops = []
        self.locations = None

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
        return self._part

    @part.setter
    def part(self, value):
        self._part = value

    @property
    def tool(self):
        return self._tool

    @tool.setter
    def tool(self, value):
        self._tool = value

    @property
    def stock(self):
        return self._stock

    @stock.setter
    def stock(self, value):
        self._stock = value

    @property
    def height_safe(self):
        return self._height_safe

    @height_safe.setter
    def height_safe(self, value):
        self._height_safe = value

    @property
    def speed_feed(self):
        return self._speed_feed

    @speed_feed.setter
    def speed_feed(self, value):
        self._speed_feed = int(value)

    @property
    def speed_position(self):
        return self._speed_position

    @speed_position.setter
    def speed_position(self, value):
        self._speed_position = int(value)

    @property
    def doc(self) -> float:
        """
        Depth of Cut (doc)
        """
        return self._doc

    @doc.setter
    def doc(self, value: float):
        self._doc = value

    @property
    def woc(self) -> float:
        return self._woc

    @woc.setter
    def woc(self, value: float):
        self._woc = value

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

        self.locations = locations

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

        if not self.locations:
            self.to_wire()

        # Get stock properties.
        props = {}
        props["label"] = self.stock.label
        props["color"] = self.stock.color
        props["material"] = self.stock.material

        # Move to first position
        self.tool.location = self.locations[0]
        self.stock -= self.tool

        # Iterate through the edges, removing material.
        for loc in self.locations[1:]:

            cut_solid = self.tool.sweep(loc)
            if cut_solid:
                self.stock -= cut_solid

            if animate:
                self.stock.label = props["label"]
                self.stock.color = props["color"]
                show(self.part, self.stock, self.tool)  # , cut_solid)
                time.sleep(0.1)

            # Remove end point from stock
            self.tool.location = loc
            self.stock -= self.tool

        # Replace stock proprties
        self.stock.label = props["label"]
        self.stock.color = props["color"]
        self.stock.material = props["material"]

        return self.stock


class OperationFace(Operation):

    # TODO: Face over all of stock or just part
    # TODO: Machining direction: both, climb, standard(?)

    def __init__(
        self, part=None, tool=None, stock=None, height_safe: float = 5.0
    ):
        super().__init__(part, tool, stock, height_safe)

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
        z_min = self.part.bounding_box().max.Z
        i_pass = 0
        z = -self.doc
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
