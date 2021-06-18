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
    PLUNGE_N_DIA = 5  # Execute plunge move in N tool diameters
    EOL = '\n'

    def ParamCheck(self):
        '''
        Check parameter values for errors.
        '''

        # Heights
        if self.z_top < self.z_bottom:
            raise ValueError(f"Top height ({self.z_top:03.f}) < bottom height ({self.z_bottom:03.f})")

        if self.z_retract < self.z_top + self.RETRACT_CLEARANCE_MIN:
            self.z_retract = self.z_top + self.RETRACT_CLEARANCE_MIN
            print(f'Warning: retract height adjusted to: {self.z_retract:03.f}')

        if self.z_step > self.z_top - self.z_bottom:
            self.z_step = self.z_top - self.z_bottom
            print(f'Warning: Z step was greater than total height, adjusted to: {self.z_step:03.f}')

        # Cutting
        if self.tool_dia < self.stepover:
            raise ValueError(f"Tool diameter ({self.tool_dia:03.f}) is smaller than stepover ({self.stepover:03.f})")

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

    def _to_str(self,value) -> str:
        '''
        Converts a numeric scalar to a string value, making integer if possible.
        '''
        if np.mod(value,1) == 0:
            # Integer
            return str(int(value))
        else:
            return format(value,'0.3f')

    def AddLine(self,line:str=''):
        '''
        Adds a line to the document.
        '''
        self._gcode += line + self.EOL

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

    def __init__(self,x:float=0,y:float=0,width:float=10,height:float=10,operation:Operation=Operation.POCKET):
        super().__init__()

        self.x = x
        self.y = y
        self.width  = width
        self.height = height

    @property
    def width(self) -> float:
        '''
        Width (x dimension) of rectangle.
        '''
        return self._width

    @width.setter
    def width(self,value:float):
        if value < 0:
            value = -value
        self._width = value

    @property
    def height(self) -> float:
        '''
        Height (y dimension) of rectangle.
        '''
        return self._height

    @height.setter
    def height(self,value:float):
        if value < 0:
            value = -value
        self._height = value

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

        # Base positions with lower left at (0,0)
        positions = np.array([[-rt,                 -rt    ], 
                             [self.width+rt,       -rt     ],
                             [self.width+rt, self.height+rt], 
                             [-rt,           self.height+rt ]])
        
        # Add in offsets
        positions[:,0] += self.x
        positions[:,1] += self.y
        
        # Side lengths
        # TODO: Convert to for loop
        lengths = np.array([positions[1,0]-positions[0,0],
                            positions[2,1]-positions[1,1]])
        lengths = np.append(lengths,lengths,axis=0)

        # Simple for a rectangle.  Should convert to a polygon formula for abstraction.
        width  = self.width  + 2*rt
        height = self.height + 2*rt
        perimeter = 2*width + 2*height
        
        # Figure out which point we get to full depth.  
        plunge_dist = self.tool_dia * self.PLUNGE_N_DIA
        if plunge_dist > perimeter:
            # Limit ourselves to 1 pass around perimeter for plunge.
            print(f'Warning: limiting plunge distance from ({plunge_dist:0.3f}) to ({perimeter:0.3f})')
            plunge_dist = perimeter

        # Calulate Z height at each corner for the first pass.
        z = np.zeros(lengths.size)
        for idx in range(0,z.size-1):
            length = lengths[idx]
            if length < plunge_dist: 
                # Won't complete plunge on this side.
                z[idx+1] = z[idx] - self.z_step * length / plunge_dist
                plunge_dist -= length  # Remaning plunge distance

            else:
                z[idx+1] = -self.z_step

        # Determine total number of passes
        n_passes = (self.z_top - self.z_bottom) / self.z_step
        n_passes = int(np.ceil(n_passes))

        # Add in an additional pass at the bottom to make sure we get full final depth
        n_passes += 1 

        # Pre conversions
        z_retract      = self._to_str(self.z_retract)
        speed_position = self._to_str(self._speed_position)
        speed_feed     = self._to_str(self._speed_feed)

        # Information
        # TODO: Update when units supported
        self.AddLine(f'; Rectangle: {self._to_str(self.width)}mm X {self._to_str(self.height)}mm')
        self.AddLine(f';  offset: x:{self._to_str(self.x)}, y:{self._to_str(self.y)}')
        self.AddLine(f';  top   : {self._to_str(self.z_top)}')
        self.AddLine(f';  bottom: {self._to_str(self.z_bottom)}')
        self.AddLine(f';  DOC   : {self._to_str(self.z_step)}')
        self.AddLine(f';  passes: {self._to_str(n_passes)}')
        self.AddLine()

        # Go to starting position
        self.AddLine('; Position for start')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')
        self.AddLine(f'G0 X{self._to_str(positions[0,0])} Y{self._to_str(positions[0,1])}')

        # Start spindle (or laser?)
        # TODO: Start spindle

        # Set initial Z position
        self.AddLine(f'G1 Z{self._to_str(self.z_top)} F{speed_feed}')

        for i_pass in range(0,n_passes):
            self.AddLine()
            self.AddLine(f'; Pass {i_pass}')

            for idx, position in enumerate(positions):
                x_str = self._to_str(position[0])
                y_str = self._to_str(position[1])
                z_str = self._to_str(z[idx])
                
                self.AddLine(f'G1 X{x_str} Y{y_str} Z{z_str}')

            # Step down
            z -= self.z_step

            # Cap at bottom
            z[z<self.z_bottom] = self.z_bottom

        # Retract
        self.AddLine()
        self.AddLine('; Retract')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')

        # Call parent for footer.
        #super().footer

if __name__ == '__main__':

    tp = ToolPathRectange(x=1, y=1, width=30, height=20, operation=Operation.CUTOUT)
    tp.tool_dia = 3.175
    tp.GCode()
    tp.Save('rectangle-test.nc')

