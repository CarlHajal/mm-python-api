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

m1.configAxisDirection(AXIS_NUMBER.DRIVE3, DIRECTION.NORMAL)
m1.configAxis(AXIS_NUMBER.DRIVE3, MICRO_STEPS.ustep_8, MECH_GAIN.roller_conveyor_mm_turn)

m1.releaseEstop()
m1.resetSystem()

time.sleep(2.0)

speed = 500.0
acceleration = 500.0

move = 100.0

m1.emitSpeed(speed)
m1.emitAcceleration(acceleration)
m1.emitRelativeMove(3, DIRECTION.NORMAL, move)

time.sleep(3.0)

previous_position = m1.readEncoder(2)

print(previous_position)

m1.emitRelativeMove(3, DIRECTION.NORMAL, move)

time.sleep(3.0)

position = m1.readEncoder(2)

print(position)

distance = position - previous_position

print("Encoder distance -> " + str(distance) + " pulses")

required_distance = move / float(MECH_GAIN.roller_conveyor_mm_turn)

print("Marlin distance -> " + str(required_distance) + " turn")

pulses_per_turn = distance / required_distance

print("Encoder resolution -> " + str(pulses_per_turn) + " pulses / turn")

sampling = 2.0

def speed_update() :
    speed = 0.0
    while (True) :
        pspeed = speed
        if speed < 1000.0 :
            speed = speed + 50.0
        else :
            speed = 100.0

        m1.setContinuousMove(AXIS_NUMBER.DRIVE3, speed, acceleration)

        print("Speed set at : " + str(speed) + " mm/sec")

        time.sleep(abs(speed - pspeed) / (acceleration) + 4.0)

    return

def speed_reading() :
    previous_position = m1.readEncoder(2)

    while (True) :
        time.sleep(sampling)

        position = m1.readEncoder(2)

        speed_read = (position - previous_position) / sampling / 3600.0 * MECH_GAIN.roller_conveyor_mm_turn

        previous_position = position

        print("Speed -> " + str(speed_read) + " mm / sec")

    return

t1 = threading.Thread(target=speed_update)
t1.daemon = True
t1.start()

t2 = threading.Thread(target=speed_reading)
t2.daemon = True
t2.start()

while True:
    time.sleep(1)
