import sys
sys.path.append("..")
from MachineMotion import *

mm = MachineMotion(DEFAULT_IP_ADDRESS.usb_windows)

# Toggles the output pins on all connected IO Modules
detectedIOModules = mm.detectIOModules()
for IO_Name, IO_NetworkID in detectedIOModules.items():
    writePins ={"Pin 1":1, "Pin 2":2, "Pin 3":3, "Pin 4":4}
    for writePin in writePins:
        print(writePin + " on " + IO_Name + " is going to flash twice")
        
        mm.digitalWrite(IO_NetworkID, writePins[writePin], 1)
        time.sleep(1)
        mm.digitalWrite(IO_NetworkID, writePins[writePin], 0)
        time.sleep(1)
        mm.digitalWrite(IO_NetworkID, writePins[writePin], 1)
        time.sleep(1)
        mm.digitalWrite(IO_NetworkID, writePins[writePin], 0)
