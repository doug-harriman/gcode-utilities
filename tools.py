# tools.py
# Tool definition and database.
from build123d import BasePartObject, Solid, Location, Color


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
