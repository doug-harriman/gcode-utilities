# gcode_utils.py
#
# G-Code manipulation utility functions.
#
# Copyright (c) Doug Harriman (doug.harriman@gmail.com)
#

# Methods yet to be implemented:
# TODO: Speed and power value changes.
# TODO: Rotate & RotateAbout.  Requires tracking of point state
# TODO: Rotate: If you center you can rotate.
# TODO: Array: rect or rotational arrays.
# TODO: Fill: Fill the given 2D space (scale up/down & center)
# TODO: Unit conversion in <-> mm.  Include changing Gxx to set units.
# TODO: Read units from file.
# TODO: Convert spindle commands to laser commands.  One way?
# TODO: Concatenate G-Code files.  Might want to deal with headers.

import copy
import re
import os
import numpy as np
from invoke import task


class ZBlock:
    def __init__(
        self,
        lines: list = [],
        x: float = None,
        y: float = None,
        z: float = None,
    ) -> None:
        # Defaults
        self._z = None
        self._x_start = x
        self._y_start = y
        self._z_start = z

        self._re_num = "([+-]?[0-9.]+)"

        if not isinstance(lines, list):
            raise ValueError("lines must be a list.")
        lines = [line.strip() for line in lines if line.strip() != ""]
        self._lines = lines
        self._lines[-1] += "\n"

        # Current z
        res = re.search(f"Z{self._re_num}", self._lines[0])
        if res:
            self._z = float(res[0].replace("Z", ""))

    def __repr__(self) -> str:
        return f"ZBlock(z={self.z}, lines={len(self._lines)}, start=[{self.xstart},{self.ystart},{self.zstart}])"

    @property
    def z(self) -> float:
        """
        Z position of this block

        Returns:
            float: Z position
        """
        return self._z

    @z.setter
    def z(self, value: float) -> None:
        if not isinstance(value, float):
            value = float(value)

        # Modify first line of G-code
        self._lines[0] = re.sub(f"Z{self._re_num}", f"Z{value}", self._lines[0])
        self._z = value

    @property
    def lines(self) -> list:
        """
        G-code for block as a list of individual lines.

        Returns:
            list: G-code lines for block
        """
        return self._lines

    @property
    def gcode(self) -> str:
        """
        G-code for block.

        Returns:
            str: G-code for block.
        """

        return "\n".join(self._lines)

    @property
    def zstart(self) -> float:
        """
        Z position prior to this block

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """

        return self._z_start

    @property
    def xstart(self) -> float:
        """
        X position prior to this block.

        Raises:
            ValueError: _description_

        Returns:
            np.float: _description_
        """
        return self._x_start

    @property
    def ystart(self) -> float:
        """
        X position prior to this block.

        Raises:
            ValueError: _description_

        Returns:
            np.float: _description_
        """
        return self._y_start

    @property
    def start(self) -> str:
        """
        G0 command going to XYZ position prior to this block.
        Useful if block is replicated to get back to starting position.

        Returns:
            str: G-code to preposition ahead of this block.
        """

        gcode = ""
        if self._x_start is not None:
            gcode += f"G0 X{self._x_start} "
        if self._y_start is not None:
            gcode += f"Y{self._y_start} "
        if self._z_start is not None:
            gcode += f"Z{self._z_start} "

        gcode = gcode.strip()
        gcode += "\n"

        return gcode

    def prepend(self, gcode: str = ""):
        """
        Prepend specified G-code to this block.

        Args:
            gcode (str, optional): G-code to prepend. Defaults to ''.
        """

        if not isinstance(gcode, str):
            raise ValueError("gcode must be a string.")

        self._lines.insert(0, gcode)

    def append(self, gcode: str = ""):
        """
        Append specified G-code to this block.

        Args:
            gcode (str, optional): G-code to append. Defaults to ''.
        """

        if not isinstance(gcode, str):
            raise ValueError("gcode must be a string.")

        self._lines.append(gcode)


class GcodeUtils:
    """
    G-Code utility class.

    This class provides methods for manipulation of G-Code
    positions with elementery geometric transforms.

    NOTE: Meant for operation on simple G-Code.  Only the simplest
          G-Code files should be expected to be able to be transformed
          without error.  If the source file uses relative positioning
          or multiple coordinate systems, geometric operations will
          cause unintended errors.
    """

    # File related data
    _filename = None
    _gcode = None  # G-Code string

    _re_num = "([+-]?[0-9.]+)"

    def __init__(self, file: str = None, gcode: str = None):
        if file is not None:
            self.Load(file)

        if gcode is not None:
            self.gcode = gcode

    def __str__(self) -> str:
        return self._gcode

    def _to_str(self, value) -> str:
        """
        Converts a numeric scalar to a string value, making integer if possible.
        """
        if np.mod(value, 1) == 0:
            # Integer
            return str(int(value))
        else:
            return format(value, "0.3f")

    @property
    def filename(self) -> str:
        """
        Returns name of G-Code file loaded for processing.
        """
        return self._filename

    @property
    def gcode(self) -> str:
        """
        G-Code string.
        """
        return self._gcode

    @gcode.setter
    def gcode(self, value: str):
        self._gcode = value

    def Load(self, filename: str):
        """
        Loads a G-code file for processing.

        Parameters
        ----------
        filename: str
            Name of file to load with path.
        """
        with open(filename, "r") as fp:
            self._gcode = fp.read()

        # Store file name if everything worked out.
        self._filename = filename

    def Save(self):
        """
        Saves current G-Code string back to file from which it was loaded.

        See also: GcodeUtils.SaveAs
        """
        self.SaveAs(self._filename)

    def SaveAs(self, filename: str):
        """
        Saves current G-Code string back to specified file name.

        See also: GcodeUtils.Save
        """
        with open(filename, "w") as fp:
            fp.write(self._gcode)

    def Translate(
        self, x: float = 0, y: float = 0, z: float = 0, xyz: np.array = None
    ):
        """
        Translates G-code by the specified X, Y and Z distances.

        Parameters
        ----------
        x:float
            X direction translation distance.  Default is 0.

        y:float
            Y direction translation distance.  Default is 0.

        z:float
            Z direction translation distance.  Default is 0.
        """

        # Support array input.
        if xyz is not None:
            x = xyz[0]
            y = xyz[1]
            z = xyz[2]

        # Replacement functions
        def offset_x(match):
            value = float(match.group(1)) + x
            value = self._to_str(value)
            return f"X{value}"

        def offset_y(match):
            value = float(match.group(1)) + y
            value = self._to_str(value)
            return f"Y{value}"

        def offset_z(match):
            value = float(match.group(1)) + z
            value = self._to_str(value)
            return f"Z{value}"

        self._gcode = re.sub(f"X{self._re_num}", offset_x, self._gcode)
        self._gcode = re.sub(f"Y{self._re_num}", offset_y, self._gcode)
        self._gcode = re.sub(f"Z{self._re_num}", offset_z, self._gcode)

    def MirrorY(self):
        """
        Mirrors G-Code about the Y-axis.

        See also: GcodeUtils.MirrorX
        """

        # Have to handle circle/arc mode also

        # Replacement functions
        def mirror_y(match):
            value = float(match.group(1)) * -1
            value = self._to_str(value)
            return f"X{value}"

        def mirror_i(match):
            value = float(match.group(1)) * -1
            value = self._to_str(value)
            return f"I{value}"

        self._gcode = re.sub(f"X{self._re_num}", mirror_y, self._gcode)
        self._gcode = re.sub(f"I{self._re_num}", mirror_i, self._gcode)

    def MirrorX(self):
        """
        Mirrors G-Code about the X-axis.

        See also: GcodeUtils.MirrorY
        """

        # Have to handle circle/arc mode also

        # Replacement functions
        def mirror_x(match):
            value = float(match.group(1)) * -1
            value = self._to_str(value)
            return f"Y{value}"

        def mirror_j(match):
            value = float(match.group(1)) * -1
            value = self._to_str(value)
            return f"J{value}"

        self._gcode = re.sub(f"Y{self._re_num}", mirror_x, self._gcode)
        self._gcode = re.sub(f"J{self._re_num}", mirror_j, self._gcode)

    def Extents(self) -> np.array:
        """
        Calculates extents of G-code in workspace.
        Note: If moves to origin/home are in code, those will be included.

        Returns
        -------
        tuple
            (x_min,y_min,z_min,x_max,y_max,z_max) for extreme corners of bounding box.

        See also: GcodeUtils.Center
        """
        # TODO: Figure out how to remove origin inclusion constraint.  Filter out G0/G1 X0,Y0?

        # Iterate through all matches for each dimension.
        x_min = y_min = z_min = np.inf
        x_max = y_max = z_max = -np.inf
        for match in re.finditer("X" + self._re_num, self._gcode):
            val = float(match.group(1))
            if val < x_min:
                x_min = val
            elif val > x_max:
                x_max = val

        for match in re.finditer("Y" + self._re_num, self._gcode):
            val = float(match.group(1))
            if val < y_min:
                y_min = val
            elif val > y_max:
                y_max = val

        for match in re.finditer("Z" + self._re_num, self._gcode):
            val = float(match.group(1))
            if val < z_min:
                z_min = val
            elif val > z_max:
                z_max = val

        # Package
        ext = np.array([x_min, y_min, z_min, x_max, y_max, z_max])

        # Clean up inf's
        ext[np.isinf(ext)] = 0

        return ext

    def Center(self) -> np.array:
        """
        Returns coordinate of center of G-Code points.

        Returns
        -------
        center: numpy.array
            [center_x, center_y, center_z]

        See also: GcodeUtils.Extents
        """

        ext = self.Extents()
        center = np.array(
            [
                (ext[0] + ext[3]) / 2,
                (ext[0 + 1] + ext[3 + 1]) / 2,
                (ext[0 + 2] + ext[3 + 2]) / 2,
            ]
        )
        return center

    def TranslateCenter(self):
        """
        Translates G-Code so that it is centered at the origin/home position.

        See also: GcodeUtils.TranslateLowerLeft
        """
        center = self.Center()
        self.Translate(xyz=-center)

    def TranslateLowerLeft(self):
        """
        Translates G-Code so that lower left corner is at the origin/home position.

        See also: GcodeUtils.TranslateCenter
        """
        ext = self.Extents()
        self.Translate(xyz=-ext)

    def TranslateLowerRight(self):
        """
        Translates G-Code so that lower right corner is at the origin/home position.

        See also: GcodeUtils.TranslateCenter
        """
        ext = self.Extents()
        self.Translate(x=-ext[3], y=-ext[1], z=-ext[2])

    def TranslateUpperLeft(self):
        """
        Translates G-Code so that upper left corner is at the origin/home position.

        See also: GcodeUtils.TranslateCenter
        """
        ext = self.Extents()
        self.Translate(x=-ext[0], y=-ext[4], z=-ext[5])

    def TranslateUpperRight(self):
        """
        Translates G-Code so that upper right corner is at the origin/home position.

        See also: GcodeUtils.TranslateCenter
        """
        ext = self.Extents()
        self.Translate(x=-ext[3], y=-ext[4], z=-ext[5])

    def Scale(self, scale_factor: float = 1.0):
        """
        Performs an in-place scaling of the G-Code.

        Parameters
        ----------
        scale_factor: float
            G-Code is scaled by this value. >1 => increase in size,
            <1 => decrease in size
        """

        # Steps:
        # - find our center
        # - scale all values
        # - find our new center
        # - tranlate back to our original center
        center_pre = self.Center()

        # Helper functions
        def scale_x(match):
            value = self._to_str(float(match.group(1)) * scale_factor)
            return f"X{value}"

        def scale_y(match):
            value = self._to_str(float(match.group(1)) * scale_factor)
            return f"Y{value}"

        def scale_z(match):
            value = self._to_str(float(match.group(1)) * scale_factor)
            return f"Z{value}"

        # Perform scaling
        self._gcode = re.sub(f"X{self._re_num}", scale_x, self._gcode)
        self._gcode = re.sub(f"Y{self._re_num}", scale_y, self._gcode)
        self._gcode = re.sub(f"Z{self._re_num}", scale_z, self._gcode)

        # Translate back
        center_post = self.Center()
        center_delta = center_pre - center_post
        self.Translate(xyz=center_delta)

    def Speeds(self) -> np.array:
        """
        Lists all unique speed values used in G-Code.

        Returns
        -------
        np.array
             Numpy Array with one entry per speed value used in G-Code.
        """

        speeds = re.findall(f"F{self._re_num}", self._gcode)
        speeds = list(set(speeds))  # Get unique values.
        speeds = list(map(lambda x: float(x), speeds))  # string -> float
        speeds.sort()
        speeds = np.array(speeds)

        return speeds

    def Powers(self) -> np.array:
        """
        Lists all unique laser power values in G-Code.

        Returns
        -------
        np.array
            Numpy Array with one entry per power value used in G-Code.
        """

        powers = re.findall(f"M4\sS{self._re_num}", self.gcode)
        powers = list(set(powers))  # Get unique values.
        powers = list(map(lambda x: float(x), powers))  # string -> float
        powers.sort()
        powers = np.array(powers)

        return powers

    def ZLevels(self) -> np.array:
        """
        Lists all unique Z-levels in G-Code.

        Returns
        -------
        np.array
            Numpy Array with one entry per Z-level used in G-Code.
        """

        # Find all Z coordinates with line number

        zlevels = re.findall(f"Z{self._re_num}", self.gcode)
        zlevels = list(map(lambda x: float(x), zlevels))

        return zlevels

    def zblocks(self) -> list:
        """
        Separates gcode into sections by Z-level.
        Useful for stacked Z operations (2.5D operations).
        True 3D operations with constant Z motion will return
        will not be useful.

        Returns:
            list: Lists of Z-block objects.
        """

        if self.gcode is None:
            raise ValueError("No G-code loaded.")

        # Separate G-code into lines.
        lines = self.gcode.splitlines()

        # List of blocks of commands by z-level.
        blocks = []
        block = []
        x = x_prev = None
        y = y_prev = None
        z = z_prev = None
        regex = re.compile(f"Z{self._re_num}")
        for line in lines:
            # If we have a Z command, start a new block.
            # TODO: need to cache from block for this block.
            if re.search(regex, line):
                blocks.append(ZBlock(lines=block, x=x_prev, y=y_prev, z=z_prev))
                x_prev = x
                y_prev = y
                z_prev = z
                block = []

            # Track starting position for next block.
            if re.search(f"X{self._re_num}", line):
                res = re.search(f"X{self._re_num}", line)
                x = float(res[0].replace("X", ""))
            if re.search(f"Y{self._re_num}", line):
                res = re.search(f"Y{self._re_num}", line)
                y = float(res[0].replace("Y", ""))
            if re.search(f"Z{self._re_num}", line):
                res = re.search(f"Z{self._re_num}", line)
                z = float(res[0].replace("Z", ""))

            # Append line to current block
            block.append(line)

        return blocks

    def zmultipass(self, z_top: float = None, stepdown: float = None):
        """
        Converts a single pass Z cut into multiple Z-passes.
        Useful for 2.5D operations.

        Algoirthm assumes that moves above the lowest Z-position are moved
        at a clearance height, thus the material z_top must be specified.

        The filename is modified to denote a multi-pass version of the
        original file.

        Arguments:
            (float) z_top: Top of material.
            (float) stepdown: Distance to step down for each pass.
        """

        if z_top is None:
            raise ValueError("z_top must be specified.")
        if stepdown is None:
            raise ValueError("stepdown must be specified.")
        if stepdown == 0:
            raise ValueError("stepdown must be non-zero.")
        if stepdown < 0:
            stepdown = -stepdown

        # Determine pass heights
        z_min = np.min(self.ZLevels())
        z_heights = np.arange(z_top - stepdown, z_min, -stepdown)
        z_heights = np.append(z_heights, z_min)
        n_heights = len(z_heights)

        # Create new filename
        fn, ext = os.path.splitext(self.filename)
        fn += f"-multipass-stepdown-{stepdown:0.3f}"
        fn += ext
        self._filename = fn

        # Process the z-blocks in the file.
        blocks = self.zblocks()
        code = ""
        op_num = 1
        for block in blocks:
            if block.z == z_min:
                # Convert to multiple passes
                op_num += 1
                for i, z in enumerate(z_heights):
                    b = copy.deepcopy(block)
                    b.z = z

                    header = "\n"
                    header += f"(Operation {op_num})\n"
                    header += f"(Pass {i+1}/{n_heights}, z={z})"

                    # Return to starting position
                    if i > 0:
                        header += f"\nG0 X{b.xstart:0.3f} Y{b.ystart:0.3f}"
                    b.prepend(header)

                    # Apppend z-lift
                    if i < n_heights - 1:
                        lift = f"G0 Z{b.zstart:0.3f}"
                        b.append(lift)

                    code += b.gcode + "\n"

            else:
                # Leave alone
                code += block.gcode

        self._gcode = code

    def ReplaceValue(self, command: str, oldvalue: float, newvalue: float):
        """
        Replaces a specific numeric value of a command with a new value.
        Values are matched with numpy.isclose

        Parameters
        ----------
        command: str
            Command of interest for value replacement.

        oldvalue: float
            Current value in G-Code.

        newvalue: float
            Replacement value.

        Example
        -------
        ReplaceValue(command="F",1000.0,1500.0)
        Will replace all occurences of "F1000" with "F1500"

        See also: Speeds, Powers
        """

        # Helper functions
        def check_replace(match):
            value = float(match.group(1))
            if np.isclose(value, oldvalue):
                return f"{command}{self._to_str(newvalue)}"
            else:
                return f"{command}{self._to_str(value)}"

        # Perform scaling
        self._gcode = re.sub(
            f"{command}{self._re_num}", check_replace, self.gcode
        )

    def Rotate(self, rotation: np.ndarray = np.eye(3)):
        """
        Performs an in-place 3D rotation of the G-Code.
        Will only modify lines that have an X, Y and Z position.

        Parameters
        ----------
        rotation: 3x3 numpy.ndarray rotation matrix.
        """

        # Steps:
        # - find our center point
        # - tranlate so we're centered at the origin.
        # - perform the rotation
        # - tranlate back to our original position
        center = self.Center()
        self.TranslateCenter()

        # Rotation
        def rot(match):
            x = float(match.group(1))
            y = float(match.group(2))
            z = float(match.group(3))

            v = np.array([x, y, z])
            # print(f'Before: {v}')
            v = np.matmul(rotation, v)
            # print(f'After : {v}')

            xs = self._to_str(v[0])
            ys = self._to_str(v[1])
            zs = self._to_str(v[2])

            return f"X{xs} Y{ys} Z{zs}"

        expr = f"X{self._re_num}\s*Y{self._re_num}\s*Z{self._re_num}"
        self._gcode = re.sub(expr, rot, self._gcode)

        # Return to starting position
        self.Translate(xyz=center)

    # def RotateAbout(self,x_center:float=0.0,y_center:float=0.0,angle_deg:float=0.0):
    #     '''
    #     Performs a 2D rotation of the G-Code in the X-Y plane about the
    #     specified point.

    #     Parameters
    #     ----------
    #     angle_deg: float
    #         Angle of rotation expressed in degrees.
    #     x_center: float
    #         X coordinate of center point of rotation.
    #     y_center: float
    #         Y coordinate of center point of rotation.

    #     See also: GcodeUtils.Center
    #     '''
    #     raise NotImplementedError()


def checkfile(filename: str):
    """
    Checks for validity of filename.
    Raise exception if filename is not valid.
    """
    from pathlib import Path

    if not isinstance(filename, str):
        raise TypeError("filename must be a string")
    if not Path(filename).exists():
        raise FileNotFoundError(f"File not found: {filename}")


@task
def powers(ctx, filename: str):
    """
    Lists all unique laser power values in G-Code.
    """

    checkfile(filename)
    gcu = GcodeUtils(file=filename)
    print(gcu.Powers())


@task
def power_replace(ctx, filename: str, old: float, new: float):
    """
    Replaces all instances of a power level with a new power level.
    """

    checkfile(filename)

    if not isinstance(old, float):
        old = float(old)
    if not isinstance(new, float):
        new = float(new)

    gcu = GcodeUtils(file=filename)
    gcu.ReplaceValue(command="M4 S", oldvalue=old, newvalue=new)
    gcu.Save()


@task
def speeds(ctx, filename: str):
    """
    Lists all unique move speed values in G-Code.
    """

    checkfile(filename)

    gcu = GcodeUtils(file=filename)
    print(gcu.Speeds())


@task
def speed_replace(ctx, filename: str, old: float, new: float):
    """
    Replaces all instances of a move speed with a new speed.
    """

    checkfile(filename)

    if not isinstance(old, float):
        old = float(old)
    if not isinstance(new, float):
        new = float(new)

    gcu = GcodeUtils(file=filename)
    gcu.ReplaceValue(command="F", oldvalue=old, newvalue=new)
    gcu.Save()


@task
def center(ctx, filename: str):
    """
    Prints the center of the G-Code.
    """

    checkfile(filename)

    gcu = GcodeUtils(file=filename)
    c = gcu.Center()
    print(f"Center: x={c[0]}, y={c[1]}, z={c[2]}")


@task
def extents(ctx, filename: str):
    """
    Prints the center of the G-Code.
    """

    checkfile(filename)

    gcu = GcodeUtils(file=filename)
    ext = gcu.Extents()
    print(f"Extents: ")
    print(f"\tx_min={ext[0]}\t\ty_min={ext[1]}\t\tz_min={ext[2]}")
    print(f"\tx_max={ext[3]}\t\ty_max={ext[4]}\t\tz_max={ext[5]}")
    print(
        f"\tdx={ext[3]-ext[0]}\t\t   dy={ext[4]-ext[1]}\t\t   dz={ext[5]-ext[2]}"
    )


# if __name__ == '__main__':

#     gcu = GcodeUtils(file='logo.nc')
#     print('Before:')
#     print(gcu.Powers())
#     print('')

#     gcu.ReplaceValue('F',1000,1000)

#     print('After:')
#     print(gcu.Powers())
#     gcu.Save()

# gu = GcodeUtils()
# gu.Load("C:\\tmp\\logo_0001.nc")
# print(f'Pre-move extents: {gu.Extents()}')
# print(f'Pre-move center : {gu.Center()}')
# gu.TranslateCenter()
# print(f'Post-move extents: {gu.Extents()}')
# print(f'Post-move center : {gu.Center()}')
# gu.SaveAs("c:\\tmp\\logo-centered.nc")

# gu.Scale(scale_factor=2)
# gu.SaveAs("c:\\tmp\\logo-scaled2x.nc")

# gu = GcodeUtils()
# fn = "notebook-logo"
# # fn = fn + "text"
# # fn = fn + "outline"
# gu.Load(fn + ".nc")
# gu.TranslateCenter()
# # gu.Translate(x=1,y=1)
# gu.SaveAs(fn + "-fixed.nc")


if __name__ == "__main__":
    fn = "servo-control-module-Edge_Cuts.gbr_iso_combined_cnc.nc"
    gcu = GcodeUtils(file=fn)
    gcu.zmultipass(stepdown=0.4, z_top=1.3)
    gcu.Save()
