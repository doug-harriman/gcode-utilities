# Preheat of ferric cloride solution before etching.


def generate_preheat_gcode(temp: int = 55, time: int = 30) -> str:
    """
    Generate G-code to preheat a ferric chloride solution.

    Parameters:
        temp (int): Target temperature in degrees Celsius.  Default is 55C.
        time (int): Duration in minutes. Default is 30 minutes.

    Returns:
        str: G-code as a string.
    """
    # Input checks
    if not isinstance(temp, int):
        raise TypeError("Temperature must be an integer.")
    if not isinstance(time, int):
        raise TypeError("Time must be an integer.")

    if temp < 30 or temp > 55:
        raise ValueError("Temperature must be between 30 and 55 degrees Celsius.")
    if time <= 0:
        raise ValueError("Time must be greater than 0 minutes.")

    # G-code commands
    # The safety firmware has a timeout of ~10 minutes, so we need to resend the command
    # every so often to keep the heater on.
    resend_period = 1  # minuintes,  in seconds
    cycle_cnt = time // resend_period

    gcode = ["; Preheat G-code for Ferric Chloride Solution"]
    gcode.append(f"; Target temperature: {temp}C")
    gcode.append(f"; Duration: {time} min\n")
    for i in range(cycle_cnt):
        gcode.append(f'M117 "Preheat: {time-i*resend_period} min"')
        gcode.append(f"M140 S{temp}")
        gcode.append(f"G4 P{resend_period*60} ; Wait\n")

    gcode.append('M117 "Preheat complete"\n')

    gcode.append("; Beep to tell the user job complete")
    beep_freq = 2000
    beep_duration = 250  # [ms]
    for i in range(3):
        gcode.append(
            f"M300 S{beep_freq} P{beep_duration} ; Beep at {beep_freq/1000:0.1f}kHz for {beep_duration}ms"
        )
        gcode.append(f"G4 P{beep_duration} ; wait\n")

    gcode.append("M140 S0 ; Turn off bed heater")

    return "\n".join(gcode)


# Example usage
if __name__ == "__main__":
    # Generate G-code
    temperature = 55
    time = 30
    gcode = generate_preheat_gcode(temp=temperature, time=time)

    # Output the G-code
    filename = f"preheat-{temperature}C-{time}min.gcode"
    with open(filename, "w") as f:
        f.write(gcode)
    print(f"G-code saved to {filename}")
