# tools.py
# Tool definition and database.
from build123d import (
    BasePartObject,
    Solid,
    Location,
    Edge,
    Plane,
    Vector,
    Rectangle,
    Color,
    sweep,
)
import numpy as np


# Create a tool
class Tool(BasePartObject):
    def __init__(self, diameter, length):

        self.type = "Flat End Mill"
        self.diameter = diameter
        self.length = length

        solid = Solid.make_cylinder(self.diameter / 2, self.length)
        solid.label = self.name

        super().__init__(part=solid)
        self.color = Color("Gray")

        # TODO: Subclass for different tool types.
        # TODO: Add shank/holder

    def __str__(self):
        n = self.name.replace(" (", ", ")
        return f"Tool:({n}"

    @property
    def name(self) -> str:
        return f"{self.type} (d={self._diameter}, L={self.length})"

    @property
    def diameter(self) -> float:
        return self._diameter

    @diameter.setter
    def diameter(self, value: float):
        self._diameter = value

    @property
    def length(self) -> float:
        return self._length

    @length.setter
    def length(self, value: float):
        self._length = value

    @property
    def radius(self) -> float:
        return self.diameter / 2

    def sweep(self, loc: Location) -> Solid:
        """
        Sweeps the tool from current location to specified location.

        TODO: Should move the tool too.

        Args:
            loc (Location): The location to sweep to.
        Returns:
            Solid: The swept volume.
        """
        # Need to project the cutting end & sides of the tool.

        # Create an edge to sweept through for cut.
        edge = Edge.make_line(self.position, loc.position)

        # Generate a vector from the edge to define a sweep plane normal.
        normal = Vector(edge.vertices()[1] - edge.vertices()[0]).normalized()

        # Tool endpoint solid.
        self.location = loc
        vol = self

        # Currently only handling XY cutting motions.
        if not np.isclose(normal.Z, 0):
            return vol

        # Side projection
        # 2D geo always created on the XY plane.
        r = Rectangle(
            self.diameter, self.length
        )  # Created with center at origin.
        r = r.translate((0, self.length / 2))  # Tool bottom centered on origin.

        # Create a plane for projection, centered on the end of the tool,
        # p = Plane.XY.rotated((90, 0, 0))  # Y-axis is normal to the tool end.
        p = Plane.XY.rotated((90, 0, 0)).rotated(
            (0, 0, 90)
        )  # X-axis is normal to the tool end.

        # Move the plane from the origin to the current tool location.
        p = p.move(self.location)

        # Rotate the plane to match the tool orientation in the XY plane
        theta = Vector((1, 0, 0)).get_signed_angle(normal, Vector((0, 0, 1)))
        p = p.rotated((0, 0, theta))

        # Extrude the 2D geometry to create the swept volume.
        vol += sweep(p * r, path=edge)

        return vol

    def to_stock_home(self, stock: Solid) -> None:
        """
        Move the tool to the stock home position.
        The home position is defined as the point:
        * Touching the top of the stock
        * Tool centered at the front left corner of the stock
          (min X, min Y, max Z).

        Args:
            stock (Solid): The stock to move the tool to.

        """

        bb = stock.bounding_box()
        x = bb.min.X
        y = bb.min.Y
        z = bb.max.Z

        loc = Location((x, y, z))
        self.move(loc)
