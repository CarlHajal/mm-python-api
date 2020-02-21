# Testing the speed functions on Marlin using gCode and thin client
# System imports
import sys
import random
import time

# Custom imports
sys.path.append("..")
from MachineMotion import *


m1 = MachineMotion("192.168.7.2", None)
m1.emitgCode("V4 S0 A10000 X")
m1.emitgCode("V4 S0 A10000 Y")
m1.emitgCode("V4 S0 A10000 Z")

m1.emitgCode("V5 X1")
m1.emitgCode("V5 Y1")
m1.emitgCode("V5 Z2")

m1.configAxis(1, MICRO_STEPS.ustep_8, MECH_GAIN.timing_belt_150mm_turn)
m1.configAxis(2, MICRO_STEPS.ustep_8, MECH_GAIN.timing_belt_150mm_turn)

# Configuring the travel speed to 10 000 mm / min
m1.emitSpeed(100000)

# Configuring the travel speed to 1000 mm / second^2
m1.emitAcceleration(10000)
# Homing axis one
m1.emitHome(1)
m1.emitHome(2)
m1.waitForMotionCompletion()

while (1) :
    speed = 6000.0
    accel = 3000.0
    
    for x in range (0, 3):
        m1.emitgCode("G0 X300 Y300")
        m1.emitgCode("G0 X10 Y10")
        
    m1.emitAbsoluteMove(1, 300)
    m1.emitAbsoluteMove(2, 300)
    m1.emitAbsoluteMove(1, 10)
    m1.emitAbsoluteMove(2, 10)

    m1.emitgCode("V4 S" + str(speed) + " A" + str(accel) + " Z")

    print(m1.digitalRead(1,3))

    while (m1.digitalRead(1,3)) :
        time.sleep(0.1)

    m1.emitgCode("V4 S" + str(-speed) + " A" + str(accel*4) + " Z")

    time.sleep(speed/(accel*4.0))

while (1) :
    speed = int(10000.0 * random.random() / 2.0)
    accel = int(4000.0 * random.random() / 2.0 + 1000.0)
    m1.emitgCode("V4 S" + str(speed) + " A" + str(accel) + " Z")

    time.sleep(5.0)
