#!/usr/bin/python
#
# gcu.py  
# G-Code Utilities command line program.
#

from gcode_utils import GcodeUtils
import argparse
import sys

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='G-Code utiltity functions for simple G-Code files.')
    parser.add_argument("file",
                        help="G-Code input file name.")
    filegroup = parser.add_argument_group(title="Output file for G-Code transforms")
    filegroup.add_argument("-o","--out",
                           default=None,
                           help="Output file name..")
    filegroup.add_argument("-r","--replace",
                           action='store_true',
                           help="Replace input file with output.")

    # Transformative
    transformgroup = parser.add_argument_group(title="Tranformation commands")
    transformgroup.add_argument("-tc","--translate_center",
                        action='store_true',
                        help="Translate G-Code so that bounding box center point is (0,0,0).")
    transformgroup.add_argument("-tll","--translate_lower_left",
                        action='store_true',
                        help="Translate G-Code so that bounding box lower left point is (0,0,0).")
    
    # Informational                         
    infogroup = parser.add_argument_group(title="Informational commands",
                                          description="Processed after any trasnformation commands.")
    infogroup.add_argument("-c","--center",
                        action='store_true',
                        help="Display G-Code center position coordinates.")
    infogroup.add_argument("-e","--extents",
                        action='store_true',
                        help="Display G-Code bounding box extents.")
    
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

    # Output G-Code
    if have_transform:
        # Mutual exclusion on replace or output file
        if args.replace and (args.out is not None):
            print(f'{__file__}: error: argument -r/--replace: not allowed with argument -o/--out')
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
        print(f'Center : x={c[0]}, y={c[1]}, z={c[2]}')
    if args.center:
        have_informational = True
        print_center()
        
    def print_extents():
        ext = gcu.Extents()
        print(f'Extents: ')
        print(f'  x_min={ext[0]}, \ty_min={ext[1]}, \tz_min={ext[2]}')
        print(f'  x_max={ext[3]}, \ty_max={ext[4]}, \tz_max={ext[5]}')
    if args.extents:
        have_informational = True
        print_extents()

    # Default if given filename and nothing else:
    if not (have_informational or have_transform):
        print()
        print('G-Code Utilities Information')
        print(f'File   : {gcu.filename}') 
        print_center()
        print_extents()
