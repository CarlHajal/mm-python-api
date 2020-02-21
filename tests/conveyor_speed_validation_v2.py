# Testing the speed functions on Marlin using gCode and thin client
# System imports
import sys
import random
import time
import statistics

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
inputSpeed = 0.0
errorList = []
meanError = 0.0

for i in range(1, 11):

    inputSpeed = random.random

    print("Loop: " + str(i))
    # inputSpeed = 50.0*i
    inputSpeed = 500.0
    # Increment speed by 50 mm/s
    m1.setContinuousMove(AXIS_NUMBER.DRIVE3, inputSpeed, 5000)

    time.sleep(sampling)

    position = m1.readEncoder(2)

    outputSpeed = abs(float((position - previous_position) / sampling / 3600.0 * MECH_GAIN.roller_conveyor_mm_turn))

    speedDiff = abs(inputSpeed - outputSpeed)
    percentError = (speedDiff/inputSpeed) * 100.0

    previous_position = position

    print("Input speed -> " + str(inputSpeed) + " mm / sec")
    print("Speed -> " + str(outputSpeed) + " mm / sec")
    print("Percent error -> " + str(percentError))

    errorList.append(percentError)

print("--------------")
m1.stopContinuousMove(3)
meanError = statistics.mean(errorList) 
print("Average error: " + str(meanError))
print("End of Test")
