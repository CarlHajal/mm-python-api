from _MachineMotion import *

# Define a callback to process controller gCode responses (if desired)
def templateCallback(data):
   print "Controller gCode responses " + data

machine_motion_example = MachineMotion(templateCallback, DEFAULT_IP_ADDRESS.usb_windows)

# Configuring the travel speed to 10 000 mm / min
machine_motion_example.emitSpeed(10000)

print "--> Machine moves are now set to 10 000 mm / min"