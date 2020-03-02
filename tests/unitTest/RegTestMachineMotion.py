import sys
import time
import pytest

sys.path.append("../..")

from MachineMotion import *

# Init variables
IP = "192.168.7.2"


def testInitMachineMotion():

    global IP
    try:
        mm = MachineMotion(IP, None)
    except:
        print("Exception thrown when initialising MachineMotion object")
    else:
        pass    


# testInitMachineMotion(IP)

print("Test Complete")