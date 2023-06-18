#!/usr/bin/python
#
# toolpath.py  
# G-Code generator for simple 3D tool paths.
#
# Intent:
# * Paths for milling, but some paths may be applicable to laser cutting.
# * For paths and patterns that are simpler to specify with code than CAD.
#

# TODO: Make everything relative.  See G-Codes in CNCjs macro for 3-axis tool homing.
# TODO: Z-retract should be relative to Z-top
# TODO: Support units
# TODO: CLI.  Use click.
# TODO: JSON config?

import numpy as np
import math

class ToolPath():

    # Common path parameters
    # Defaults for 3018 wood
    _speed_feed     = 300
    _speed_position = 1500

    _stepover = 0 # Default to no stepover.
    _tool_dia = 3.175

    _z_top     =  0.0
    _z_bottom  = -3.0
    _z_retract =  3.0
    _stepdown  = 0.25  

    _gcode = ''  # Generated G-Code

    # Constants
    RETRACT_MIN = 0.5  # [mm]
    PLUNGE_N_DIA = 5  # Execute plunge move in N tool diameters
    EOL = '\n'

    def ParamCheck(self):
        '''
        Check parameter values for errors.
        '''

        # Heights
        if self.z_top < self.z_bottom:
            raise ValueError(f"Top height ({self.z_top:03.f}) < bottom height ({self.z_bottom:03.f})")

        if self.z_retract < self.z_top + self.RETRACT_MIN:
            self.z_retract = self.z_top + self.RETRACT_MIN
            print(f'Warning: retract height adjusted to: {self.z_retract:03.f}')

        if self.stepdown > self.z_top - self.z_bottom:
            self.stepdown = self.z_top - self.z_bottom
            print(f'Warning: Z step was greater than total height, adjusted to: {self.stepdown:03.f}')

        # Cutting
        if self.tool_dia < self.stepover:
            raise ValueError(f"Tool diameter ({self.tool_dia:03.f}) is smaller than stepover ({self.stepover:03.f})")

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
    def stepdown(self) -> float:
        '''
        Z step down per pass.
        Stored as a positive value.
        '''
        return self._stepdown

    @stepdown.setter
    def stepdown(self,value:float):
        if value < 0:
            value = -value

        self._stepdown = value

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
    def speed_feed(self) -> float:
        '''
        Feed speed for cutting operations.
        '''
        return self._speed_feed

    @speed_feed.setter
    def speed_feed(self,value:float):
        if value < 0:
            value = -value
        self._speed_feed = value

    @property
    def speed_position(self) -> float:
        '''
        Speed for non-cutting tool positioning operations.
        '''
        return self._speed_position

    @speed_position.setter
    def speed_position(self,value:float):
        if value < 0:
            value = -value
        self._speed_position = value

    @property
    def tool_rad(self) -> float:
        '''
        Tool radius.
        Read only. Set via tool diameter.
        '''
        return self._tool_dia / 2

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

    def XYZ_string(self,x:float=None,y:float=None,z:float=None) -> str:
        """
        Utility function to convert X, Y, and Z values to a string.
        If a value is not passed, it is not rendered.

        Args:
            x (float): X-coordinate, optional.
            y (float): Y-coordinate, optional.
            z (float): Z-coordinate, optional.

        Returns:
            str: Formatted string ready for G-Code.
        """
        
        s = ''
        if x is not None:
            s += f'X{self._to_str(x)} '
        if y is not None:
            s += f'Y{self._to_str(y)} '
        if z is not None:
            s += f'Z{self._to_str(z)} '
            
        return s.strip()

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
        Abstract method to be overridden by implementation classes.
        '''
        self.ParamCheck()
        return self._gcode

class ToolPathSlotUniDi(ToolPath):
    '''
    Tool path generation for a slot relative to current position cut in one direction.
    First pass is cutting pass.  To cut in reverse direcion, set start position to far
    end and set cut target as a negative position.
    '''

    _x = 0.0
    _y = 0.0
    _depth = 1

    def __init__(self,x:float=0,y:float=1,depth:float=1):
        super().__init__()

        self._x = x
        self._y = y
        self._depth = depth

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
    def depth(self) -> float:
        '''
        Depth of cut.
        '''
        return self._depth

    @depth.setter
    def depth(self,value:float):

        if value < 0:
            value = -value

        self._depth = value

    def GCode(self):
        '''
        Generate G-Code for unidirectional cut slot tool path.
        '''

        # Verify parameters
        self.ParamCheck()

        # Call parent for header.
        #super().header

        # Prerender
        x0 = self._to_str(-self._x)
        y0 = self._to_str(-self._y)
        x1 = self._to_str(self._x)
        y1 = self._to_str(self._y)

        fG0 = self._to_str(self.speed_position)
        fG1 = self._to_str(self.speed_feed)

        # Header
        self.AddLine('; ---- Job Description ----')
        self.AddLine('; Unidirectional slot cut')
        self.AddLine(f'; X Distance: {x1} [mm]')
        self.AddLine(f'; Y Distance: {y1} [mm]')
        self.AddLine(f'; Depth     : {self._to_str(self._depth)} [mm]')
        self.AddLine(f'; Stepdown  : {self._to_str(self._stepdown)} [mm]')
        self.AddLine('')

        self.AddLine(f'; Feed Speed       : {fG1} [mm/min]')
        self.AddLine(f'; Positioning Speed: {fG0} [mm/min]')
        self.AddLine('')

        self.AddLine('; ---- Setup ----')
        self.AddLine('G21 ; Units: mm')
        self.AddLine('G94 ; Speed in units per minute')
        self.AddLine('G17 ; XY Plane')
        self.AddLine('G54 ; Coordinate system 1')
        self.AddLine('G91 ; REL positioning mode')
        self.AddLine('')

        # Start spindle
        self.AddLine('; Start Spindle')
        self.AddLine('M3 S5000')  # TODO: Should make this configurable.
        self.AddLine('G4 P1    ; Wait to spin up')
        self.AddLine('')


        cnt_pass = math.ceil(self.depth / self.stepdown)
        cur_pass = 0

        # Loop
        z = self.depth
        stepdown = self.stepdown
        while(z > 0):  
            # Calc next z cut position
            z -= stepdown

            # Do short stepdown if needed to get to bottom.
            # If already at zero, we're done.
            if z < 0:
                stepdown += z 
                z = 0

            # Move down to cut position
            # NOTE: Assumes starting off of workpiece.  No 
            cur_pass += 1
            self.AddLine(f'; ---- Pass {cur_pass}/{cnt_pass} ----')
            self.AddLine('; Cut')
            self.AddLine(f'G0 Z{self._to_str(-stepdown)}')

            # Cut pass
            self.AddLine(f'G1 X{x1} Y{y1} F{fG1}')
            self.AddLine('')

            # Retrace reverse pass
            if z > 0:
                self.AddLine('; Retrace')
                self.AddLine(f'G1 Z{self._to_str(self.z_retract)} F{fG0}')
                self.AddLine(f'G1 X{x0} Y{y0}')
                self.AddLine(f'G1 Z{self._to_str(-self.z_retract)}')
                self.AddLine('')

        # Return to original position
        self.AddLine('; Cleanup')
        self.AddLine('M5    ; Stop Spindle')
        self.AddLine(f'G0 Z{self._to_str(self.depth + self.z_retract)} F{fG0}; Return Home')
        self.AddLine(f'G0 X{x0} Y{y0}')
        self.AddLine(f'G0 Z{self._to_str(-self.z_retract)}')
        self.AddLine('M2    ; Job end')
        self.AddLine('')

class ToolPathRectangle(ToolPath):
    '''
    Tool path geneation for a rectangle.
    '''

    _x = 0.0
    _y = 0.0

    _width  = 10.0  # X-width
    _height = 10.0  # Y-height

    def __init__(self,x:float=0,y:float=0,width:float=10,height:float=10):
        super().__init__()

        self.x = x
        self.y = y
        self.width  = width
        self.height = height

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
        # if self.operation == Operation.Pocket:
        #     rt = -rt

        # Base positions with lower left at (0,0)
        positions = np.array([[-rt,                 -rt    ], 
                             [self.width+rt,       -rt     ],
                             [self.width+rt, self.height+rt], 
                             [-rt,           self.height+rt ]])

        # Add in offsets
        positions[:,0] += self.x
        positions[:,1] += self.y
        pos_start = positions[0,:]

        # Side lengths
        # TODO: Convert to for loop
        lengths = np.array([positions[1,0]-positions[0,0],
                            positions[2,1]-positions[1,1]])
        lengths = np.append(lengths,lengths,axis=0)

        # Now we get a bit trick.  We want the first move to be from the LL corner
        # to the LR corner, and the last move to be from the UL to the LL.
        # Rotate the position matrix.
        positions = np.roll(positions,positions.shape[0]-1,axis=0)

        # print(pos_start)
        # print(positions)

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

        # Calculate Z height at each corner for the first pass.
        z = np.zeros(lengths.size)
        for idx in range(0,z.size):
            length = lengths[idx]
            if length < plunge_dist: 
                # Won't complete plunge on this side.
                z[idx] = z[idx-1] - self.stepdown * length / plunge_dist
                plunge_dist -= length  # Remaning plunge distance

            else:
                z[idx] = -self.stepdown

        # print(z)

        # Determine total number of passes
        n_passes = (self.z_top - self.z_bottom) / self.stepdown
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
        self.AddLine(f';  position: x:{self._to_str(self.x)}, y:{self._to_str(self.y)}')
        self.AddLine(f';  z top   : {self._to_str(self.z_top)}')
        self.AddLine(f';  z bottom: {self._to_str(self.z_bottom)}')
        self.AddLine(f';  DOC     : {self._to_str(self.stepdown)}')
        self.AddLine(f';  passes  : {self._to_str(n_passes)}')
        self.AddLine(f';  tool dia: {self._to_str(self.tool_dia)}')
        op = format(self.operation).replace('.',': ')
        self.AddLine(f'; {op}')
        self.AddLine()

        # TODO: Move this to base class header.
        # Header
        self.AddLine('G21 ; Units: mm')
        self.AddLine('G94 ; Speed in units per minute')
        self.AddLine('G17 ; XY Plane')
        self.AddLine('G54 ; Coordinate system 1')
        self.AddLine('G90 ; ABS positioning mode')
        self.AddLine()

        # Go to starting position
        self.AddLine('; Position for start')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')
        self.AddLine(f'G0 X{self._to_str(pos_start[0])} Y{self._to_str(pos_start[1])}')
        self.AddLine()

        # Start spindle (or laser?)
        # Start spindle
        self.AddLine('; Start Spindle')
        self.AddLine('M3 S5000')  # TODO: parameterize spindle speed
        self.AddLine('G4 P1    ; Wait to spin up')
        self.AddLine()

        # Set initial Z position
        self.AddLine('; Move to start position')
        self.AddLine(f'G1 Z{self._to_str(self.z_top)} F{speed_feed}')

        for i_pass in range(0,n_passes):
            self.AddLine()
            self.AddLine(f'; Pass {i_pass+1}')

            for idx, position in enumerate(positions):
                x_str = self._to_str(position[0])
                y_str = self._to_str(position[1])
                z_str = self._to_str(z[idx])
                
                self.AddLine(f'G1 X{x_str} Y{y_str} Z{z_str}')

            # Step down
            z -= self.stepdown

            # Cap at bottom
            z[z<self.z_bottom] = self.z_bottom

        # Retract
        self.AddLine()
        self.AddLine('; Retract')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')

        # Call parent for footer.
        #super().footer

class ToolPathCylinder(ToolPath):
    '''
    Tool path geneation for a cylinder.
    '''

    _x = 0.0
    _y = 0.0

    _radius  = 3.0

    def __init__(self,x:float=0,y:float=0,
                 radius:float=3,
                 bore:bool=False,
                 segments:int=30):
        super().__init__()

        # Use setters for validation
        self.x = x
        self.y = y
        self.radius  = radius
        self.bore = bore
        self.segments = segments

    @property
    def x(self) -> float:
        '''
        X-position of cylinder center.
        '''
        return self._x

    @x.setter
    def x(self,value:float):
        self._x = value

    @property
    def y(self) -> float:
        '''
        Y-position of cylinder center.
        '''
        return self._y

    @y.setter
    def y(self,value:float):
        self._y = value

    @property
    def radius(self) -> float:
        '''
        Radius of cylinder.
        '''
        return self._radius

    @radius.setter
    def radius(self,value:float):
        if value < 0:
            value = -value
        self._radius = value

    @property
    def diameter(self) -> float:
        '''
        Diameter of cylinder.
        '''
        return 2*self._radius

    @diameter.setter
    def diameter(self,value:float):
        if value < 0:
            value = -value
        self._radius = value/2

    @property
    def bore(self) -> bool:
        """
        Is cylinder a bore.
        """
        
        return self._bore

    @bore.setter
    def bore(self,value:bool):
        
        self._bore = value
    
    @property
    def segments(self) -> int:
        """
        Number of segments with which to approximate circle.

        Returns:
            int: Segment count
        """
        return self._segments
   
    @segments.setter
    def segments(self,value:int):
        
        value = round(value) # enforce int
        self._segments = value
    
    def GCode(self):
        '''
        Generate G-Code for cutting out a cylinder.
        '''

        # TODO: Allow 2 pass with a step in/out depending on bore.

        # Verify parameters
        self.ParamCheck()

        # Call parent for header.
        #super().header

        # G-Code arc commands:
        # G2 - Clockwise arc
        # G3 - Counter-clockwise arc
        # 
        # Unfortunatly, the helical arc commands are not supported by Grbl.
        # Implement as series of XY moves with Z plunge.
        
        # Determine total number of passes
        n_passes_float = (self.z_top - self.z_bottom) / self.stepdown
        n_passes = int(np.ceil(n_passes_float))

        # Add in an additional pass at the bottom to make sure we get full final depth
        # Unless we have integer number of stepdowns.
        if n_passes != n_passes_float and self.stepover == 0:
            n_passes += 1 

        # Pre conversions
        z_retract      = self._to_str(self.z_retract)
        speed_position = self._to_str(self._speed_position)
        speed_feed     = self._to_str(self._speed_feed)

        # Position of helix start
        r_helix = self._radius
        if self._bore:
            r_helix -= self.tool_rad + self.stepover
        else:
            r_helix += self.tool_rad + self.stepover
            
        # Helix points for one pass
        angles = np.linspace(0,2*np.pi,self.segments+1)
        x_helix = r_helix * np.cos(angles) + self.x
        y_helix = r_helix * np.sin(angles) + self.y
        z_helix = np.linspace(self.z_top,self.z_top - self.stepdown, self.segments+1)
        
        # Radius of finishing cut
        r_finish = self._radius
        if self._bore:
            r_finish -= self.tool_rad
        else:
            r_finish += self.tool_rad
        
        # Finishing cut points
        x_finish = r_finish * np.cos(angles) + self.x
        y_finish = r_finish * np.sin(angles) + self.y

        # Information
        # TODO: Update when units supported
        if self._bore:
            self.AddLine( '; Bore:')
        else:
            self.AddLine( '; Cyinder:')
        self.AddLine(f';  center  : x:{self._to_str(self.x)}, y:{self._to_str(self.y)}')
        self.AddLine(f';  radius  : {self._to_str(self.radius)}')
        self.AddLine(f';  z top   : {self._to_str(self.z_top)}')
        self.AddLine(f';  z bottom: {self._to_str(self.z_bottom)}')
        self.AddLine(f';  DOC     : {self._to_str(self.stepdown)}')
        self.AddLine(f';  passes  : {self._to_str(n_passes)}')
        self.AddLine(f';  tool dia: {self._to_str(self.tool_dia)}')
        if self.stepover > 0:
            self.AddLine(f';  stepover: {self._to_str(self.stepover)} for finishing cut')
        self.AddLine()

        # TODO: Move this to base class header.
        # Header
        self.AddLine('G21 ; Units: mm')
        self.AddLine('G94 ; Speed in units per minute')
        self.AddLine('G17 ; XY Plane')
        self.AddLine('G54 ; Coordinate system 1')
        self.AddLine('G90 ; ABS positioning mode')
        self.AddLine()

        # Go to starting position
        self.AddLine('; Position for start')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')
        self.AddLine(f'G0 X{self._to_str(x_helix[0])} Y{self._to_str(y_helix[0])}')
        self.AddLine()

        # Start spindle (or laser?)
        # Start spindle
        self.AddLine('; Start Spindle')
        self.AddLine('M3 S5000')  # TODO: parameterize spindle speed
        self.AddLine('G4 P1    ; Wait to spin up')
        self.AddLine()

        # Set initial Z position
        self.AddLine('; Move to start position')
        self.AddLine(f'G1 Z{self._to_str(self.z_top)} F{speed_feed}')

        for i_pass in range(0,n_passes):
            self.AddLine()
            self.AddLine(f'; Pass {i_pass+1}')

            # Helix cut
            for idx in range(0,len(x_helix)-1):
                coords = self.XYZ_string(x=x_helix[idx],
                                         y=y_helix[idx],
                                         z=z_helix[idx])
                self.AddLine(f'G1 {coords}')

            # Finishing cut.
            if self.stepover > 0:
                # Move to last point in helix
                idx = -1
                coords = self.XYZ_string(x=x_helix[idx],
                                         y=y_helix[idx],
                                         z=z_helix[idx])
                self.AddLine(f'G1 {coords}')
                
                # Now finish out the helix circle.
                self.AddLine()
                self.AddLine(f'; Finishing Rough, Pass {i_pass+1}')
                for idx in range(0,len(x_helix)):
                    coords = self.XYZ_string(x=x_helix[idx],  
                                             y=y_helix[idx])
                    self.AddLine(f'G1 {coords}')
                
                # Circular finishing cut
                self.AddLine()
                self.AddLine(f'; Finishing Cut, Pass {i_pass+1}')
                for idx in range(0,len(x_helix)):
                    coords = self.XYZ_string(x=x_finish[idx],  
                                             y=y_finish[idx])
                    self.AddLine(f'G1 {coords}')

            # Step down
            z_helix -= self.stepdown

            # Cap at bottom
            z_helix[z_helix<self.z_bottom] = self.z_bottom
            
        # Add in very last point
        idx = -1
        coords = self.XYZ_string(x=x_helix[idx],y=y_helix[idx],z=z_helix[idx])
        self.AddLine(f'G1 {coords}')

        # Retract
        self.AddLine()
        self.AddLine('; Retract')
        self.AddLine(f'G0 Z{z_retract} F{speed_position}')
        self.AddLine(f'G0 X0 Y0')
        
        # Call parent for footer.
        #super().footer

class ToolPathFace(ToolPath):
    '''
    Tool path generator for a facing operation.

    Tool is assumed to start at (0,0,0), with axes:
    * +X to the right
    * +Y to the back
    * +Z up

    Facing operation will move in +X, +Y and -Z.

    '''

    def __init__(self,x:float=0,y:float=1,depth:float=1, stepover:float=0.5, stepdown:float=0.5):
        super().__init__()

        self._x = x
        self._y = y
        self._depth = depth    

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
    def depth(self) -> float:
        '''
        Depth of cut.
        '''
        return self._depth

    @depth.setter
    def depth(self,value:float):

        if value < 0:
            value = -value

        self._depth = value

    def GCode(self):
        '''
        Generate G-Code for unidirectional cut slot tool path.
        '''

        # Verify parameters
        self.ParamCheck()

        # Call parent for header.
        #super().header

        # Prerender
        x0 = self._to_str(-self.tool_rad+self.stepover)
        y0 = self._to_str(-0.75*self.tool_dia)
        y1 = self._to_str(self.y + 0.75*self.tool_dia)

        fG0 = self._to_str(self.speed_position)
        fG1 = self._to_str(self.speed_feed)

        # Header
        self.AddLine(f'; Code Generated by: {__file__}')
        self.AddLine('')
        self.AddLine( '; ---- Job Description ----')
        self.AddLine( '; Facing operation')
        self.AddLine( '; Cuts performed bi-directionally in Y')
        self.AddLine( '; Stepover performed in X.')
        self.AddLine(f'; Facing X Distance: {self.x} [mm]')
        self.AddLine(f'; Facing Y Distance: {self.y} [mm]')
        self.AddLine(f'; Depth     : {self._to_str(self.depth)} [mm]')
        self.AddLine(f'; Stepover  : {self._to_str(self.stepover)} [mm]')
        self.AddLine(f'; Stepdown  : {self._to_str(self.stepdown)} [mm]')
        self.AddLine(f'; Tool Dia  : {self._to_str(self.tool_dia)} [mm]')
        self.AddLine('')

        self.AddLine(f'; Feed Speed       : {fG1} [mm/min]')
        self.AddLine(f'; Positioning Speed: {fG0} [mm/min]')
        self.AddLine('')

        self.AddLine('; ---- Setup ----')
        self.AddLine('G21 ; Units: mm')
        self.AddLine('G94 ; Speed in units per minute')
        self.AddLine('G17 ; XY Plane')
        self.AddLine('G54 ; Coordinate system 1')
        self.AddLine('G90 ; ABS positioning mode')
        self.AddLine('')

        # Position for first cutting pass.
        self.AddLine( '; ---- Pre-Position ----')
        self.AddLine(f'G0 Z{self._to_str(self.z_retract)} F{fG0}')
        self.AddLine(f'G0 X{x0} Y{y0}')
        self.AddLine('')

        # Start spindle
        self.AddLine('; Start Spindle')
        self.AddLine('M3 S5000')  # TODO: Should make this configurable.
        self.AddLine('G4 P1    ; Wait to spin up')
        self.AddLine('')


        cnt_levels = math.ceil(self.depth / self.stepdown)
        cur_level  = 0

        # Loop
        z = 0
        stepdown = self.stepdown
        while(z > -self.depth):  
            # Calc next z cut position
            z -= stepdown

            # Do short stepdown if needed to get to bottom.
            # If already at zero, we're done.
            if z < -self.depth:
                z = -self.depth

            # Move down to cut position
            # NOTE: Assumes starting off of workpiece.  No 
            cur_level += 1
            self.AddLine(f'; ---- Facing Pass {cur_level}/{cnt_levels} ----')
            self.AddLine('; Cut')
            self.AddLine(f'G0 Z{self._to_str(z)} F{fG0}')

            # Loop on cuts
            x = -self.tool_rad+self.stepover
            while x <= self.x:

                # Cut pass forward
                self.AddLine(f'G1 Y{y1} F{fG1}  ; cut fwd')

                x += self.stepover
                if x <= self.x + self.stepover:
                    # Cut pass back
                    self.AddLine(f'G0 X{self._to_str(x)} F{fG0} ; stepover')
                    self.AddLine(f'G1 Y{y0} F{fG1} ; cut rev')

                x += self.stepover
                if x <= self.x:
                    self.AddLine(f'G0 X{self._to_str(x)} F{fG0} ; stepover')

            self.AddLine('')

            # Retrace to first cut pass
            if z > -self.depth:
                self.AddLine( '; Retrace')
                self.AddLine(f'G1 Z{self._to_str(self.z_retract)} F{fG0}')
                self.AddLine(f'G1 X{x0} Y{y0}')
                self.AddLine('')

        # Return to original position
        self.AddLine( '; Cleanup')
        self.AddLine( 'M5    ; Stop Spindle')
        self.AddLine(f'G0 Z{self._to_str(self.z_retract)} F{fG0} ; Retract')
        self.AddLine(f'G0 X0 Y0 ; Return Home')
        self.AddLine( 'M2    ; Job end')
        self.AddLine('')

def AppendFiles(fn1:str, fn2:str):
    """
    Appends one file onto another.
    Output file is fn1.

    Args:
        fn1 (str): First file name.
        fn2 (str): Second file name.
    """
    
    with open(fn2,'r') as fp:
        data = fp.read()
    
    with open(fn1,'w') as fp:
        fp.write(data)
        

if __name__ == '__main__':

    # # Generate cutout path.
    # clearance = 1 
    # tp = ToolPathRectangle(x=ext[0]-clearance, y=ext[1]-clearance, 
    #                       width=w+2*clearance, height=h+2*clearance, 
    #                       operation=Operation.CutOut)
    # tp.tool_dia = 3.175
    # tp.speed_position = 1500
    # tp.speed_feed     = 1000
    # tp.z_top = 0
    # tp.z_bottom = -6 # Acrylic thickness, not in laser file.
    # tp.stepdown = 0.25
    # tp.GCode()
    # tp.Save('rectangle-test.nc')

    # Slot tool path
    # tp = ToolPathSlotUniDi(y=50, depth=5)
    # tp.speed_position = 1500
    # tp.speed_feed     = 1000
    # tp.stepdown       = 2
    # tp.z_retract      = 0.5
    # tp.GCode()
    # tp.Save('vertical-slot.nc')

    # Facing
    # tp = ToolPathFace(x=180,y=120,depth=2)
    # tp.speed_position = 1500
    # tp.speed_feed     = 1000
    # tp.stepdown       = 0.5
    # tp.tool_dia       = 3.175
    # tp.stepover       = tp.tool_dia * 0.40
    # tp.z_retract      = 2
    # tp.GCode()
    # tp.Save(f'face-x{tp.x}mm-y{tp.y}mm-z{tp.depth}mm.nc')

    # Test cylinder
    if False:
        diameter=0.25*25.4
        x = diameter/2 + 2
        y = x

        tp = ToolPathCylinder(x=x,y=y)
        tp.diameter = diameter
        tp.speed_position = 1500
        tp.speed_feed     = 600
        tp.stepdown       = 0.5
        tp.tool_dia       = 3.175
        tp.z_retract      = 2

        # Tests
        tp.stepdown=5
        tp.z_top = 0
        tp.z_bottom = tp.z_top - 2.5*tp.stepdown

        from pprint import pprint
        pprint(vars(tp))

        tp.GCode()
        fn = f'cylinder-x{tp.x}mm-y{tp.y}mm-rad{tp.radius}mm-z{tp.z_top-tp.z_bottom}mm.nc'
        tp.Save(fn)
        print(f"Saved: {fn}")
    
    