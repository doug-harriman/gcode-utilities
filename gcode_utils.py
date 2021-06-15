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

import re
import numpy as np

class GcodeUtils():
    '''
    G-Code utility class.
    
    This class provides methods for manipulation of G-Code 
    positions with elementery geometric transforms.  

    NOTE: Meant for operation on simple G-Code.  Only the simplest
          G-Code files should be expected to be able to be transformed
          without error.  If the source file uses relative positioning
          or multiple coordinate systems, geometric operations will
          cause unintended errors.
    '''

    # File related data
    _filename  = None
    _gcode     = None  # G-Code string

    _re_num = '([+-]?[0-9.]+)'

    def __init__(self,file:str=None,gcode:str=None):
        if file is not None:
            self.Load(file)

        if gcode is not None:
            self.gcode = gcode

    def __str__(self) -> str:
        return self._gcode

    @property
    def filename(self) -> str:
        '''
        Returns name of G-Code file loaded for processing.
        '''
        return self._filename

    @property
    def gcode(self) -> str:
        '''
        G-Code string.
        '''
        return self._gcode

    @gcode.setter
    def gcode(self,value:str):
        self._gcode = gcode

    def Load(self,filename:str):
        '''
        Loads a G-code file for processing.

        Parameters
        ----------
        filename: str
            Name of file to load with path.
        '''
        with open(filename,'r') as fp:
            self._gcode = fp.read()

        # Store file name if everything worked out.
        self._filename = filename

    def Save(self):
        '''
        Saves current G-Code string back to file from which it was loaded.
        
        See also: GcodeUtils.SaveAs
        '''
        self.SaveAs(self._filename)

    def SaveAs(self,filename:str):
        '''
        Saves current G-Code string back to specified file name.
        
        See also: GcodeUtils.Save
        '''
        with open(filename,'w') as fp:
            fp.write(self._gcode)

    def Translate(self,x:float=0, y:float=0,z:float=0,xyz:np.array=None):
        '''
        Translates G-code by the specified X, Y and Z distances.

        Parameters
        ----------
        x:float
            X direction translation distance.  Default is 0.

        y:float
            Y direction translation distance.  Default is 0.

        z:float
            Z direction translation distance.  Default is 0.
        '''

        # Support array input.
        if xyz is not None:
            x = xyz[0]
            y = xyz[1]
            z = xyz[2]

        # Replacement functions
        def offset_x(match):
            return f'X{float(match.group(1))+x}'
        def offset_y(match):
            return f'Y{float(match.group(1))+y}'
        def offset_z(match):
            return f'Z{float(match.group(1))+z}'

        self._gcode = re.sub(f'X{self._re_num}',offset_x,self._gcode)        
        self._gcode = re.sub(f'Y{self._re_num}',offset_y,self._gcode)        
        self._gcode = re.sub(f'Z{self._re_num}',offset_z,self._gcode)        

    def Extents(self) -> np.array:
        '''
        Calculates extents of G-code in workspace.
        Note: If moves to origin/home are in code, those will be included.

        Returns
        -------
        tuple
            (x_min,y_min,z_min,x_max,y_max,z_max) for extreme corners of bounding box.
        
        See also: GcodeUtils.Center
        '''
        #TODO: Figure out how to remove origin inclusion constraint.  Filter out G0/G1 X0,Y0?

        # Iterate through all matches for each dimension.
        x_min = y_min = z_min =  np.inf 
        x_max = y_max = z_max = -np.inf
        for match in re.finditer('X'+self._re_num, self._gcode):
            val = float(match.group(1))
            if val < x_min:
                x_min = val
            elif val > x_max:
                x_max = val

        for match in re.finditer('Y'+self._re_num, self._gcode):
            val = float(match.group(1))
            if val < y_min:
                y_min = val
            elif val > y_max:
                y_max = val

        for match in re.finditer('Z'+self._re_num, self._gcode):
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
        '''
        Returns coordinate of center of G-Code points.

        Returns
        -------
        center: numpy.array
            [center_x, center_y, center_z]

        See also: GcodeUtils.Extents
        '''

        ext = self.Extents()
        center = np.array([(ext[0]   + ext[3]  ) / 2, 
                           (ext[0+1] + ext[3+1]) / 2,
                           (ext[0+2] + ext[3+2]) / 2])
        return center

    def TranslateCenter(self):
        '''
        Translates G-Code so that it is centered at the origin/home position.

        See also: GcodeUtils.TranslateLowerLeft
        '''
        center = self.Center()
        self.Translate(xyz=-center)

    def TranslateLowerLeft(self):
        '''
        Translates G-Code so that lower left corner is at the origin/home position.
        
        See also: GcodeUtils.TranslateCenter
        '''
        ext = self.Extents()
        self.Translate(xyz=-ext)

    def TranslateLowerRight(self):
        '''
        Translates G-Code so that lower right corner is at the origin/home position.
        
        See also: GcodeUtils.TranslateCenter
        '''
        ext = self.Extents()
        self.Translate(x=ext[0],y=-ext[1],z=-ext[2])

    def Scale(self,scale_factor:float=1.0):
        '''
        Performs an in-place scaling of the G-Code.

        Parameters
        ----------
        scale_factor: float
            G-Code is scaled by this value. >1 => increase in size, 
            <1 => decrease in size
        '''

        # Steps:
        # - find our center
        # - scale all values
        # - find our new center
        # - tranlate back to our original center
        center_pre = self.Center()
        
        # Helper functions
        def scale_x(match):
            return f'X{float(match.group(1))*scale_factor}'
        def scale_y(match):
            return f'Y{float(match.group(1))*scale_factor}'
        def scale_z(match):
            return f'Z{float(match.group(1))*scale_factor}'

        # Perform scaling
        self._gcode = re.sub(f'X{self._re_num}',scale_x,self._gcode)        
        self._gcode = re.sub(f'Y{self._re_num}',scale_y,self._gcode)        
        self._gcode = re.sub(f'Z{self._re_num}',scale_z,self._gcode)        

        # Translate back
        center_post  = self.Center()
        center_delta = center_pre - center_post
        self.Translate(xyz=center_delta)

    # def Rotate(self,angle_deg:float=0.0):
    #     '''
    #     Performs an in-place 2D rotation of the G-Code in the X-Y plane.

    #     Parameters
    #     ----------
    #     angle_deg: float
    #         Angle of rotation expressed in degrees.
    #     '''

    #     # TODO: Rotation requires tracking of points, as XY may not be in the same line.

    #     # Steps:
    #     # - find our center point
    #     # - tranlate so we're centered at the origin.
    #     # - perform the rotation
    #     # - tranlate back to our original position
    #     center = self.Center()
    #     self.TranslateCenter()

    #     # Rotation
    #     theta = np.radians(angle_deg)

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

# if __name__ == '__main__':

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