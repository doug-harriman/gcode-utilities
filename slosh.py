# slosh.py
# Oscillates a tub of liquid back and forth to create a sloshing effect.

# Notes on using heated bed to pre-heat
# M86 sets/gets the heater timeout when no other commands are processed.
# M86 S<timeout in sec>
# Ender3Pro Default is 300 sec.
# It takes quite a long time to heat a resonable volume of water in a glass dish.
# Max supported bed temp is 110C.
# M140 S<temperature deg> ; to set temperature.
# Heating for 10-15 min at high temp, then reduce to ~40C should work.
# Per MG Chemicals, optical etch temp is 35-55C, but should not be heated above 55C.
# Density: 0.79 gm/ml

import math
from pint import Quantity as Q

# TODO: May need allow for different density and viscosity of liquids.


def generate_sloshing_gcode(tub_length: Q, duration: Q = Q(10, "s")) -> str:
    """
    Generate G-code to cause resonant sloshing of water in a tub.

    Parameters:
        length (float): Length of the tub (in mm).

    Returns:
        str: G-code as a string.
    """

    # Input checks
    if not isinstance(tub_length, Q):
        raise TypeError("Tub length must be a pint Quantity.")
    if not isinstance(duration, Q):
        raise TypeError("Duration must be a pint Quantity.")

    if not tub_length.check("[length]"):
        raise ValueError("Tub length must be a length quantity.")
    if not duration.check("[time]"):
        raise ValueError("Duration must be a time quantity.")

    # Convert to calculation units
    tub_length_m = tub_length.to("m").magnitude
    tub_length_mm = tub_length_m * 1000
    duration_s = duration.to("s").magnitude

    if tub_length_m <= 0:
        raise ValueError("Tub length must be greater than 0.")
    if duration_s <= 0:
        raise ValueError("Duration must be greater than 0.")

    # Constants
    gravity = 9.81  # Acceleration due to gravity (m/s^2)

    # Calculate the natural frequency of sloshing (first mode)
    # Formula: f = (1 / (2 * pi)) * sqrt(g / L)
    natural_frequency = (1 / (2 * math.pi)) * math.sqrt(gravity / tub_length_m)

    # Calculate the period of oscillation
    period_s = 1 / natural_frequency  # in seconds

    # Amplitude of motion
    amplitude_mm = tub_length_mm / 4  # Oscillation amplitude (1/4 of tub length)

    # Convert period to milliseconds for G-code timing
    period_ms = period_s * 1000

    # Calculate the number of oscillation cycles
    oscillation_count = int((duration_s + period_s / 2) / period_s)  # round up

    # Calculate motion profile parameteters
    # Assume:
    # * Move time is 1/2 the period.
    # * Constant acceleration
    # * Trapezoidal velocity profile - accel for 1/2 the time.
    t_acc = period_s / 2 / 2
    acc = amplitude_mm / t_acc**2
    vel_mm_per_s = acc * t_acc
    vel_mm_per_min = vel_mm_per_s * 60
    vel_mm_per_min = 5000  # int(vel_mm_per_min)
    print(f"Move time: {t_acc} [sec]")

    # Generate G-code
    gcode = []
    gcode.append("; G-code to cause resonant sloshing of water")
    gcode.append(f"; Tub length: {tub_length:0.1f~P}")
    gcode.append(
        f"; Natural frequency: {natural_frequency:.2f} [Hz], Period: {period_s:.3f} [sec]"
    )
    gcode.append(f"; Duration   : {duration_s:.0f} [s]")
    gcode.append(f"; Cycle Count: {oscillation_count}")
    gcode.append("")

    # Enable motors
    gcode.append("M17  ; Enable all motors")
    gcode.append("M107 ; All fans off")

    # Home Y- axis
    gcode.append("G28 Y; Home Y")
    gcode.append("")

    # Set acceleration and speed parameters
    gcode.append(f"M203 Y{5000}          ; Set max speed")
    gcode.append(
        f"M204 S{int(acc)} P{int(acc)} T{int(acc)} ; Set acceleration (P: printing, T: travel)"
    )
    gcode.append("M205 Y100           ; Set jerk limits")
    gcode.append("")

    # Move to start position
    p0 = 5
    p1 = 10
    gcode.append(f"G0 {p0} F100; Move to inital position just off of home")
    gcode.append("")

    period_ms = period_ms / 2

    for i in range(oscillation_count):
        msg = f"Cycle {i+1}/{oscillation_count}"
        gcode.append(f'M117 "{msg}"')
        gcode.append(f"G0 Y{p1:.2f} F{int(vel_mm_per_min)} ; Move to +amplitude")
        gcode.append(f"G4 P{period_ms / 2:.0f} ; Wait for half period")
        gcode.append(f"G0 Y{p0:.2f} F{int(vel_mm_per_min)} ; Move to -amplitude")
        gcode.append(f"G4 P{period_ms / 2:.0f} ; Wait for half period")
        gcode.append("")

    gcode.append("M140 S0      ; Turn off the bed heater")
    gcode.append("G0 Y235 F500 ; Send bed to presentation position")
    gcode.append("M18          ; Disable motors")
    gcode.append("")

    gcode.append("; Beep to tell the user job complete")
    beep_freq = 2000
    beep_duration = 250  # [ms]
    for i in range(3):
        gcode.append(
            f"M300 S{beep_freq} P{beep_duration} ; Beep at {beep_freq/1000:0.1f}kHz for {beep_duration}ms"
        )
        gcode.append(f"G4 P{beep_duration} ; wait")

    return "\n".join(gcode)


# Example usage
if __name__ == "__main__":
    # Parameters
    tub_length = Q(177.5, "mm")  # Length of the tub, long axis
    # tub_length = Q(127.5, "mm")  # Length of the tub, short axis
    duration = Q(20, "s")  # Duration of sloshing
    filename = "slosh.gcode"  # Output G-code filename

    # Generate G-code
    gcode = generate_sloshing_gcode(tub_length, duration=duration)

    # Output the G-code
    with open(filename, "w") as f:
        f.write(gcode)
    print(f"G-code saved to {filename}")
