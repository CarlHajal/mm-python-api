# Testing the speed functions on Marlin using gCode and thin client
# System imports
import sys
import random
import time
import threading

# Custom imports
sys.path.append("..")
from MachineMotion import *

m1 = MachineMotion("192.168.7.2", None)

m1.releaseEstop()
m1.resetSystem()

time.sleep(2.0)

sampling = 2.0

def speed_reading() :
    previous_position = m1.readEncoder(2)

    while (True) :
        time.sleep(sampling)
	
        position = m1.readEncoder(2)
	print(position)
        speed_read = (position - previous_position) / sampling / 3600.0 * MECH_GAIN.belt_conveyor_mm_turn
        speed_read_ustep = int((position - previous_position) / sampling / 3600.0 * 200.0 * 8.0)

        previous_position = position

        print("Speed -> " + str(speed_read) + " mm / sec")
        print("Speed -> " + str(speed_read_ustep) + " ustep / sec")
        print("-----------------------------------------------------------")

    return

t2 = threading.Thread(target=speed_reading)
t2.daemon = True
t2.start()

while True:
    time.sleep(1)
