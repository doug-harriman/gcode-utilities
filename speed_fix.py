#!/usr/bin/python
#

# Fixes non-engagement feedrate for positioning
# moves in Fusion360 generated CNC machining 
# tool paths.
# Fusion360 deliberately ignores positining move 
# speed increases for the free version.  This 
# script identifies moves to or above the retract
# height and uses a higher speed for those moves.
# This is a grbl dialect specific G Code parser.

import re
import os
from enum import Enum, auto


class ZState(Enum):
    Unknown   = auto()
    Retracted = auto()
    Cutting   = auto()

class FusionSpeedFix():

    def __init__(self,retract_height:float=5,positioning_speed:float=1000):

        self._retract_height = retract_height
        self._positioning_speed = positioning_speed
        self._z_state = ZState.Unknown

    @property
    def retract_height(self) -> float:
        """
        Returns retract height property value.
        """

        return self._retract_height

    @retract_height.setter
    def retract_height(self,value:float):
        """
        Sets retract height proprty value.
        """

        self._retract_height = value
        print(f"Retract height set to: {value}")

    @property
    def positioning_speed(self) -> float:
        """
        Returns positioning speed property value.
        """

        return self._positioning_speed

    @positioning_speed.setter
    def positioning_speed(self,value:float=1000):
        """
        Sets positioning speed property value.
        """

        self._positioning_speed = value
        print(f"Positioing speed set to: {self._positioning_speed}")

    def speed_fix(self,gcode:str='') -> str:
        """
        Takes G Code string input and returns a new G Code string
        that changes the speed of all positioning moves where the
        tool is not engaged with the workpiece.  Non-engagement
        is defined as moves that take place at or above the 
        retract height.
        """

        linesep = os.linesep
        linesep = '\n'

        re_speed = re.compile('.*F([.\d]+)')
        re_z_pos = re.compile('.*Z([-?.\d]+)')

        # Process file line-by-line looking for:
        # Speed sets.  Track those.
        # Z-height
        last_speed = 0
        gcode_out = ''

        for line in gcode.splitlines():

            # Attempt to read speed from every line.
            # Positioning moves may have a speed specifier.
            new_speed = None
            speed_str = re_speed.match(line)
            if speed_str is not None:
                new_speed = float(speed_str.group(1))
                last_speed = new_speed
                # print(f'Captured speed: {last_speed}')                
                
            # Look for Z moves
            z_pos = None
            z_str = re_z_pos.match(line)
            if z_str is not None:
                z_pos = float(z_str.group(1))
                # print(f'Z move to: {z_pos}')

            # State machine transition detection
            # Transitions can only happen on Z moves
            state_new = None
            if z_pos is not None:
                if self._z_state == ZState.Unknown:
                        if z_pos >= self._retract_height:
                            state_new = ZState.Retracted
                            print("  Retracted")
                        else:
                            state_new = ZState.Cutting

                elif self._z_state == ZState.Cutting:
                        if z_pos >= self._retract_height:
                            state_new = ZState.Retracted
                            print("  Retracted")

                elif self._z_state == ZState.Retracted:
                        if z_pos < self._retract_height:
                            state_new = ZState.Cutting
                            print("  Cutting")

                else:
                    raise(Exception(f'Unknown ZState: {state_new}'))

            # Handle state transition
            if state_new is not None:
                if state_new == ZState.Retracted:
                    # If there was no speed command set, go fast
                    if new_speed is None:
                        line += f' F{self.positioning_speed}'

                elif state_new == ZState.Cutting:
                    # If there was no new speed set, use last known speed
                    if new_speed is None:
                        # If we have a new speed, put it on it's own line _after_
                        # the down move so that the down move is fast.
                        # Fusion360 always puts a Z positioning move, then a cutting move
                        # for down Z moves.
                        line += f'{linesep}F{last_speed}'
                else:
                    raise(Exception(f'Unknown ZState: {state_new}'))

                self._z_state = state_new

            gcode_out += line
            gcode_out += linesep

        # End file with newline
        gcode_out += os.linesep

        return gcode_out

if __name__ == "__main__":

    import argparse
    import sys
    import os

    parser = argparse.ArgumentParser(description="Speed fix for Fusion 360 CNC Positioning Moves.")
    parser.add_argument('-r',
                        action='store',
                        help="Retract height value.",
                        required=True,
                        type=float,
                        default=None)
    parser.add_argument('-s',
                        help="Desired positioning speed",
                        action='store',
                        required=True,
                        type=float,
                        default=None)
    parser.add_argument("filename",
                        help="Name of file to update.",
                        type=str)

    args = parser.parse_args()

    # Error checks
    if not os.path.exists(args.filename):
        print(f"Input file does not exist: {args.filename}")
        sys.exit(-1)

    if args.r < 0:
        print("Retract height must be non-negative.")
        sys.exit(-2)

    if args.s < 0:
        print("Positioning speed must be non-negative.")
        sys.exit(-2)

    # Read in file
    with open(args.filename,mode='r') as fp:
        gcode = fp.read()

    # Process it.
    sf = FusionSpeedFix()
    sf.retract_height = args.r
    sf.positioning_speed = args.s
    gcode_updated = sf.speed_fix(gcode)

    # Write new file
    parts = os.path.splitext(args.filename)
    fn_out = f'{parts[0]}-updated{parts[1]}'

    with open(fn_out,'w') as fp:
        fp.write(gcode_updated)
    