#!/usr/bin/python
#
# toolpath.py  
# G-Code generator for simple 3D tool paths.
#
# Intent:
# * Paths for milling, but some paths may be applicable to laser cutting.
# * For paths and patterns that are simpler to specify with code than CAD.
#

# TODO: Optional job header - In case you want to have mulitple paths in a file
# TODO: Optional job footer - In case you want to have mulitple paths in a file
# TODO: Support units

from enum import Enum, unique
import numpy as np

@unique
class Operation(Enum): 
    CUTOUT = 1  # Cut shape out.  Tool on outside of boundary.
    POCKET = 2  # Create a pocket.  Tool on inside of boundary.


class ToolPath():

    # Common path parameters
    # Defaults for 3018 wood
    _speed_feed     = 300
    _speed_position = 1500

    _stepover  = 0.5
    _tool_dia = 3.175

    _x = 0.0
    _y = 0.0

    _z_top     =  0.0
    _z_bottom  = -3.0
    _z_retract =  3.0
    _z_step    = 0.25  # Stepdown between passes

    _operation = Operation.CUTOUT

    _gcode = ''  # Generated G-Code

    # Constants
    RETRACT_CLEARANCE_MIN = 0.5  # [mm]

    def ParamCheck(self):
        '''
        Check parameter values for errors.
        '''

        # Heights
        if self.z_top < self.z_bottom:
            raise ValueError(f"Top height ({self.z_top}) < bottom height ({self.z_bottom})")

        if self.z_retract < self.z_top + self.RETRACT_CLEARANCE_MIN:
            self.z_retract = self.z_top + self.RETRACT_CLEARANCE_MIN
            print(f'Warning: retract height adjusted to: {self.z_retract}')

        if self.z_step > self.z_top - self.z_bottom:
            self.z_step = self.z_top - self.z_bottom
            print(f'Warning: Z step was greater than total height, adjusted to: {self.z_step}')

        # Cutting
        if self.tool_dia < self.stepover:
            raise ValueError(f"Tool diameter ({self.tool_dia}) is smaller than stepover ({self.stepover})")

    @property
    def operation(self) -> Operation:
        '''
        Operation type: CUTOUT or POCKET.
        '''
        return self._operation

    @operation.setter
    def operation(self,value:Operation):
        self._operation = value

    @property
    def x(self) -> float:
        '''
        X-position for tool path geometry.
        '''
        return self._x

    @x.setter
    def x(self,value:float):
        self._x = value

    @property
    def y(self) -> float:
        '''
        Y-position for tool path geometry.
        '''
        return self._y

    @y.setter
    def y(self,value:float):
        self._y = value

    @property
    def z_top(self) -> float:
        '''
        Top surface Z position.
        Operations go from this Z position down.
        '''
        return self._z_top

    @z_top.setter
    def z_top(self,value:float):
        self._z_top = value

    @property
    def z_bottom(self) -> float:
        '''
        Bottom surface Z position.
        Operations go down to this Z position.
        '''
        return self._z_bottom

    @z_bottom.setter
    def z_bottom(self,value:float):
        self._z_bottom = value        

    @property
    def z_retract(self) -> float:
        '''
        Rectraction height Z position.
        The value should be high enough such that tool tip clears work piece
        and other tooling.  Tool should be clear for any XY motion.
        '''
        return self._z_retract

    @z_retract.setter
    def z_retract(self,value:float):
        self._z_retract = value        
    
    @property
    def z_step(self) -> float:
        '''
        Z step down per pass.
        Stored as a positive value.
        '''
        return self._z_step

    @z_step.setter
    def z_step(self,value:float):
        if value > 0:
            value = -value

        self._z_step = value

    @property
    def stepover(self) -> float:
        '''
        Multi-pass horizontal stepover or radial depth of cut.
        Must be smaller than tool diameter.
        '''
        return self._stepover

    @stepover.setter
    def stepover(self,value:float):
        if value < 0:
            value = -value

        self._stepover = value

    @property
    def tool_dia(self) -> float:
        '''
        Tool diameter.
        '''
        return self._tool_dia

    @tool_dia.setter
    def tool_dia(self,value:float):
        if value < 0:
            value = -value

        self._tool_dia = value

    @property
    def tool_rad(self) -> float:
        '''
        Tool radius.
        Read only. Set via tool diameter.
        '''
        return self.tool_dia / 2

    @property
    def gcode(self) -> str:
        '''
        Generated G-Code.
        Read only.  

        See: GCode()
        '''
        return self._gcode

    def Save(self,filename:str):
        '''
        Saves current G-Code string back to specified file name.
        
        See also: GCode()
        '''
        if self.gcode is None:
            self.GCode()

        with open(filename,'w') as fp:
            fp.write(self._gcode)

    def GCode(self) -> str:
        '''
        Generates and stores GCode.
        Abstract method to be overriden by implementation classes.
        '''
        self.ParamCheck()
        return self._gcode

class ToolPathRectange(ToolPath):
    '''
    Tool path geneation for a rectangle.
    '''

    _width  = 10.0  # X-width
    _height = 10.0  # Y-height

    def __init__(self):
        super().__init__()


    def GCode(self):
        '''
        Generate G-Code for rectangular tool path.
        '''

        # Verify parameters
        self.ParamCheck()

        # Call parent for header.
        #super().header

        # Generate array of corner positions.
        rt = self.tool_rad
        if self.operation == Operation.POCKET:
            rt = -rt

        position = np.array([[-rt, -rt], 
                             [self.width+rt,-rt],
                             [self.width+rt, self.height+rt], 
                             [-rt, self.width+rt]])



        # Call parent for footer.
        #super().footer

if __name__ == '__main__':

    tp = ToolPathRectange(x=1, y=2, width=30, height=20)
    tp.GCode()
    tp.Save('rectangle-test.nc')

