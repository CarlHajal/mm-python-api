# Testing the speed functions on Marlin using gCode and thin client
# System imports
import sys
import random
import time

# Custom imports
sys.path.append("..")
from MachineMotion import *

m1 = MachineMotion("192.168.7.2", None)

m1.configAxisDirection(AXIS_NUMBER.DRIVE3, DIRECTION.NORMAL)
m1.configAxis(AXIS_NUMBER.DRIVE3, MICRO_STEPS.ustep_8, MECH_GAIN.roller_conveyor_mm_turn)

m1.releaseEstop()
m1.resetSystem()

time.sleep(2.0)

move = 100.0

m1.emitSpeed(500)
m1.emitAcceleration(500)
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

sampling = 5.0

count = 0

for i in range(10) :

    print("STart of loop: " + str(i))
    # speedModeSpeed = 350.0 * (2 * random.random()-1.0) 
    speedModeSpeed = 350.0

    print("--Continous Move with speed: " + str(speedModeSpeed))
    m1.setContinuousMove(3, speedModeSpeed, 1000)
    time.sleep(sampling)

    # positionModeSpeed = 350.0 * (2 * random.random()-1.0) 
    positionModeSpeed = 350.0

    print("--Position Move with speed: " + str(positionModeSpeed))
    m1.emitgCode("G0 Z" + str(positionModeSpeed*sampling) + " F" + str(positionModeSpeed/150*8*STEPPER_MOTOR.steps_per_turn))
    m1.waitForMotionCompletion()
    
    count+=1
    print("End of Looop")
