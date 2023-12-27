#!/usr/bin/python
#
# gcu.py
# G-Code Utilities command line program.
#

from gcode_utils import GcodeUtils
import argparse
import sys

if __name__ == "__main__":
    # Parser
    parser = argparse.ArgumentParser(
        description="G-Code utiltity functions for simple G-Code files."
    )
    parser.add_argument("file", help="G-Code input file name.")
    filegroup = parser.add_argument_group(title="Output file for G-Code transforms")
    filegroup.add_argument("-o", "--out", default=None, help="Output file name..")
    filegroup.add_argument(
        "-r", "--replace", action="store_true", help="Replace input file with output."
    )

    # Transformative - Basic
    btransformgroup = parser.add_argument_group(
        title="Basic G-Code tranformation commands"
    )
    btransformgroup.add_argument(
        "-tc",
        "--translate_center",
        action="store_true",
        help="Translate G-Code so that bounding box center point is (0,0,0).",
    )
    btransformgroup.add_argument(
        "-tll",
        "--translate_lower_left",
        action="store_true",
        help="Translate G-Code so that bounding box lower left point is (0,0,0).",
    )
    btransformgroup.add_argument(
        "-tlr",
        "--translate_lower_right",
        action="store_true",
        help="Translate G-Code so that bounding box lower right point is (0,0,0).",
    )
    btransformgroup.add_argument(
        "-tul",
        "--translate_upper_left",
        action="store_true",
        help="Translate G-Code so that bounding box lower left point is (0,0,0).",
    )
    btransformgroup.add_argument(
        "-tur",
        "--translate_upper_right",
        action="store_true",
        help="Translate G-Code so that bounding box lower right point is (0,0,0).",
    )

    # TranTransformative - Complex
    ctransformgroup = parser.add_argument_group(
        title="Complex G-Code tranformation commands"
    )
    ctransformgroup.add_argument(
        "-tx",
        "--translate",
        help="Translate G-Code position based on values set by 'x', 'y' and 'z' options.",
        action="store_true",
    )
    ctransformgroup.add_argument(
        "-x", help="X direction value.", type=float, default=0.0
    )
    ctransformgroup.add_argument(
        "-y", help="Y direction value.", type=float, default=0.0
    )
    ctransformgroup.add_argument(
        "-z", help="Z direction value.", type=float, default=0.0
    )
    ctransformgroup.add_argument(
        "-s",
        "--scale",
        help="Scale G-Code by value provided.",
        type=float,
        default=None,
    )
    ctransformgroup.add_argument(
        "--change_speed",
        help="Change speed value from old value to new value, specified by --old and --new.",
        action="store_true",
    )
    ctransformgroup.add_argument(
        "--change_power",
        help="Change power value from old value to new value, specified by --old and --new.",
        action="store_true",
    )
    ctransformgroup.add_argument(
        "--old", help="Original value for value changes.", type=float, default=None
    )
    ctransformgroup.add_argument(
        "--new", help="New value for value changes.", type=float, default=None
    )

    # Informational
    infogroup = parser.add_argument_group(
        title="Informational commands",
        description="Processed after any trasnformation commands.",
    )
    infogroup.add_argument(
        "-c",
        "--center",
        action="store_true",
        help="Display G-Code center position coordinates.",
    )
    infogroup.add_argument(
        "-e",
        "--extents",
        action="store_true",
        help="Display G-Code bounding box extents.",
    )
    infogroup.add_argument(
        "--speeds", action="store_true", help="Display unique speed values in G-Code."
    )
    infogroup.add_argument(
        "--powers",
        action="store_true",
        help="Display unique laser power values in G-Code.",
    )
    infogroup.add_argument(
        "--zlevels", action="store_true", help="Display unique Z values in G-Code."
    )

    args = parser.parse_args()

    # TODO: Allow input of G-Code text
    #      Check if file is value file, if not assume text
    gcu = GcodeUtils(args.file)

    # Transformative
    have_transform = False
    if args.translate_center:
        have_transform = True
        gcu.TranslateCenter()

    if args.translate_lower_left:
        have_transform = True
        gcu.TranslateLowerLeft()

    if args.translate_lower_right:
        have_transform = True
        gcu.TranslateLowerRight()

    if args.translate_upper_left:
        have_transform = True
        gcu.TranslateUpperLeft()

    if args.translate_upper_right:
        have_transform = True
        gcu.TranslateUpperRight()

    if args.translate:
        have_transform = True
        gcu.Translate(x=args.x, y=args.y, z=args.z)

    if args.scale is not None:
        have_transform = True
        gcu.Scale(scale_factor=args.scale)

    if args.change_speed:
        have_transform = True
        if args.old is None:
            print("error: old value required for change_speed")
        if args.new is None:
            print("error: new value required for change_speed")

        gcu.ReplaceValue(command="F", oldvalue=args.old, newvalue=args.new)

    if args.change_power:
        have_transform = True
        if args.old is None:
            print("error: old value required for change_power")
        if args.new is None:
            print("error: new value required for change_power")

        gcu.ReplaceValue(command="M4 S", oldvalue=args.old, newvalue=args.new)

    # Output G-Code
    if have_transform:
        # Mutual exclusion on replace or output file
        if args.replace and (args.out is not None):
            print(
                f"{__file__}: error: argument -r/--replace: not allowed with argument -o/--out"
            )
            sys.exit()

        if args.replace:
            gcu.Save()
        elif args.out is not None:
            gcu.SaveAs(args.out)
        else:
            # Dump G-Code to console
            print(str(gcu))

    # Informational
    have_informational = False

    def print_center():
        c = gcu.Center()
        print(f"Center : x={c[0]}, y={c[1]}, z={c[2]}")

    if args.center:
        have_informational = True
        print_center()

    def print_extents():
        ext = gcu.Extents()
        print(f"Extents: ")
        print(f"  x_min={ext[0]}\t\ty_min={ext[1]}\t\tz_min={ext[2]}")
        print(f"  x_max={ext[3]}\t\ty_max={ext[4]}\t\tz_max={ext[5]}")
        print(
            f"     dx={ext[3]-ext[0]}\t\t   dy={ext[4]-ext[1]}\t\t   dz={ext[5]-ext[2]}"
        )

    if args.extents:
        have_informational = True
        print_extents()

    def print_speeds():
        values = gcu.Speeds()
        if values is None:
            return
        values = list(values)  # str will now comma separate
        values = str(values).replace("[", "").replace("]", "")
        print(f"Speeds : {values}")

    if args.speeds:
        have_informational = True
        print_speeds()

    def print_powers():
        values = gcu.Powers()
        if values is None:
            return
        values = list(values)  # str will now comma separate
        values = str(values).replace("[", "").replace("]", "")
        print(f"Powers : {values}")

    if args.powers:
        have_informational = True
        print_powers()

    def print_zlevels():
        values = gcu.ZLevels()
        if values is None:
            return
        values = set(values)
        values = str(values).replace("{", "").replace("}", "")
        print(f"ZLevels: {values}")

    if args.zlevels:
        have_informational = True
        print_zlevels()

    # Default if given filename and nothing else:
    if not (have_informational or have_transform):
        print()
        print("G-Code Utilities Information")
        print(f"File   : {gcu.filename}")
        print_speeds()
        print_powers()
        print_center()
        print_extents()
