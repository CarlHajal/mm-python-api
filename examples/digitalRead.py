# System imports
import sys
# Custom imports
sys.path.append("..")

from MachineMotion import *

mm = MachineMotion(DEFAULT_IP_ADDRESS.usb_windows)


#Reads and Prints all input values on all connected digital IO Modules
detectedIOModules = mm.detectIOModules()
for IO_Name, IO_NetworkID in detectedIOModules.items():
   readPins = {"Pin 1":1, "Pin 2":2, "Pin 3":3, "Pin 4":4}
   for readPin in readPins:
       pinValue = mm.digitalRead(IO_NetworkID, readPins[readPin])
       print(readPin + " on " + IO_Name + " has value " + str(pinValue))
