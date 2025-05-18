# Generates peck drill operations using only G0 & G1 commands

from pathlib import Path
import math


class Drill:
    """Drill class to generate peck drill operations using only G0 & G1 commands."""

    def __init__(self) -> None:
        """Initialize the Drill class with the provided G-code."""
        self._drill_depth = 0.0
        self._peck_depth = 0.0
        self._drill_feedrate = 20.0
        self._x = 0.0
        self._y = 0.0
        self._z_top = 0.0
        self._z_safe = 5
        self._travel_feedrate = 500.0

    @property
    def drill_depth(self) -> float:
        """Get the drilling operation total depth."""
        return self._drill_depth

    @drill_depth.setter
    def drill_depth(self, value: float) -> None:
        """Set the drilling operation total depth."""
        if not isinstance(value, (int, float)):
            raise TypeError("Hole depth must be a number.")
        if value <= 0:
            raise ValueError("Hole depth must be greater than zero.")
        self._drill_depth = value

    @property
    def peck_depth(self) -> float:
        """Get the peck depth."""
        return self._peck_depth

    @peck_depth.setter
    def peck_depth(self, value: float) -> None:
        """Set the peck depth."""
        if not isinstance(value, (int, float)):
            raise TypeError("Peck depth must be a number.")
        self._peck_depth = value

    @property
    def drill_feedrate(self) -> float:
        """Get the feedrate."""
        return self._drill_feedrate

    @drill_feedrate.setter
    def drill_feedrate(self, value: float) -> None:
        """Set the feedrate."""
        if not isinstance(value, (int, float)):
            raise TypeError("Feedrate must be a number.")
        self._drill_feedrate = value
        if self._drill_feedrate <= 0:
            raise ValueError("fDrill eedrate must be greater than zero.")

    @property
    def travel_feedrate(self) -> float:
        """Get the travel feedrate."""
        return self._travel_feedrate

    @travel_feedrate.setter
    def travel_feedrate(self, value: float) -> None:
        """Set the travel feedrate."""
        if not isinstance(value, (int, float)):
            raise TypeError("Travel feedrate must be a number.")
        self._travel_feedrate = value
        if self._travel_feedrate <= 0:
            raise ValueError("Travel feedrate must be greater than zero.")

    @property
    def x(self) -> float:
        """Get the X coordinate."""
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        """Set the X coordinate."""
        if not isinstance(value, (int, float)):
            raise TypeError("X coordinate must be a number.")
        self._x = value

    @property
    def y(self) -> float:
        """Get the Y coordinate."""
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        """Set the Y coordinate."""
        if not isinstance(value, (int, float)):
            raise TypeError("Y coordinate must be a number.")
        self._y = value

    @property
    def z_top(self) -> float:
        """Get the Z top coordinate."""
        return self._z_top

    @z_top.setter
    def z_top(self, value: float) -> None:
        """Set the Z top coordinate."""
        if not isinstance(value, (int, float)):
            raise TypeError("Z top coordinate must be a number.")
        self._z_top = value

    @property
    def z_safe(self) -> float:
        """Get the Z safe coordinate."""
        return self._z_safe

    @z_safe.setter
    def z_safe(self, value: float) -> None:
        """Set the Z safe coordinate."""
        if not isinstance(value, (int, float)):
            raise TypeError("Z travel coordinate must be a number.")
        self._z_safe = value

    @property
    def gcode(self) -> str:
        """Drill G-code."""
        gcode = []

        # Error checks
        if self._peck_depth > self._drill_depth:
            raise ValueError("Peck depth must be less than hole depth.")
        if self._z_safe <= self._z_top:
            raise ValueError("Z safe must be greater than Z top.")

        # Go to safe Z
        gcode.append("; Travel to hole position")
        gcode.append(f"G0 Z{self.z_safe:.3f} F{self._travel_feedrate}")

        # Travel to hole
        gcode.append(f"G0 X{self.x:.3f} Y{self.y:.3f}")
        gcode.append(f"G0 Z{self.z_top:.3f}\n")

        # Peck drill
        cycles = int(self._drill_depth / self._peck_depth)
        for i in range(cycles):
            if (i + 1) * self._peck_depth <= self._drill_depth:
                gcode.append(f"; Peck drill cycle {i + 1}")
                gcode.append(
                    f"G1 Z{self._z_top - (i + 1) * self._peck_depth:.3f} F{self._drill_feedrate}"
                )
                gcode.append(f"G0 Z{self.z_safe:.3f} F{self._travel_feedrate}\n")

        # Final drill
        gcode.append("; Drill final depth")
        gcode.append(
            f"G1 Z{self._z_top - self._drill_depth:.3f} F{self._drill_feedrate}\n"
        )
        gcode.append(f"G0 Z{self.z_safe:.3f} F{self._travel_feedrate}")
        gcode.append("; End of drill cycle\n")

        # Return G-code
        return "\n".join(gcode)


class DrillPattern:
    """Drill pattern class to generate a pattern of holes."""

    def __init__(self, drill: Drill | None = None) -> None:
        """Initialize the DrillPattern class."""
        if drill:
            self._drill = drill
        self._dx = 0.0
        self._dy = 0.0
        self._nx = 1
        self._ny = 1

    @property
    def drill(self) -> Drill:
        """Get the drill object."""
        return self._drill

    @drill.setter
    def drill(self, value: Drill) -> None:
        """Set the drill object."""
        if not isinstance(value, Drill):
            raise TypeError("Drill must be a Drill object.")
        self._drill = value

    @property
    def dx(self) -> float:
        """Get the X distance between holes."""
        return self._dx

    @dx.setter
    def dx(self, value: float) -> None:
        """Set the X distance between holes."""
        if not isinstance(value, (int, float)):
            raise TypeError("X distance must be a number.")

        self._dx = value

    @property
    def dy(self) -> float:
        """Get the Y distance between holes."""
        return self._dy

    @dy.setter
    def dy(self, value: float) -> None:
        """Set the Y distance between holes."""
        if not isinstance(value, (int, float)):
            raise TypeError("Y distance must be a number.")

        self._dy = value

    @property
    def nx(self) -> int:
        """Get the number of holes in the X direction."""
        return self._nx

    @nx.setter
    def nx(self, value: int) -> None:
        """Set the number of holes in the X direction."""
        if not isinstance(value, int):
            raise TypeError("Number of holes in X direction must be an integer.")
        if value <= 0:
            raise ValueError(
                "Number of holes in X direction must be greater than zero."
            )

        self._nx = value

    @property
    def ny(self) -> int:
        """Get the number of holes in the Y direction."""
        return self._ny

    @ny.setter
    def ny(self, value: int) -> None:
        """Set the number of holes in the Y direction."""
        if not isinstance(value, int):
            raise TypeError("Number of holes in Y direction must be an integer.")
        if value <= 0:
            raise ValueError(
                "Number of holes in Y direction must be greater than zero."
            )

        self._ny = value

    @property
    def gcode(self) -> str:
        """Drill pattern G-code."""
        gcode = []

        # Error checks
        if not isinstance(self._drill, Drill):
            raise ValueError("Drill object must be set before generating G-code.")
        if math.fabs(self._dx) <= 0:
            raise ValueError("X distance must have magnitude greater than zero.")
        if math.fabs(self._dy) <= 0:
            raise ValueError("Y distance must have magnitude greater than zero.")

        # Hold base position
        x_base = self._drill.x
        y_base = self._drill.y

        cnt = 1
        for i in range(self._nx):
            self._drill.x = i * self._dx + x_base
            for j in range(self._ny):
                gcode.append(";----------------------------------")
                gcode.append(f"; Hole {cnt}/{self.nx*self.ny}: (row={j+1},col={i+1})\n")
                cnt += 1

                self._drill.y = j * self._dy + y_base
                gcode.append(self._drill.gcode)
        return "\n".join(gcode)


if __name__ == "__main__":
    drill = Drill()
    drill.drill_depth = 4.0
    drill.peck_depth = 1.5
    drill.drill_feedrate = 20.0
    drill.travel_feedrate = 500.0
    drill.x = 5.0
    drill.y = 5.0
    drill.z_top = 0.0
    drill.z_safe = 5.0

    pattern = DrillPattern(drill)
    pattern.dx = 10.0
    pattern.dy = 10.0
    pattern.nx = 2
    pattern.ny = 2

    # print(pattern.gcode)

    # Save to file
    output_file = Path("drill-pattern.gcode")
    with open(output_file, "w") as f:
        f.write(pattern.gcode)
    print(f"G-code saved to {output_file}")
