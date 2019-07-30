# File name:            _MachineMotion_1_6_5.py                     #
# Version:              1.6.5                                       #
# Author:               Francois Giguere                            #
# Note:                 Information about all the g-Code            #
#                       commands supported are available at         #
#                       the following location of the SDK:          #
#                       ./documentation                             #

# Import standard libraries
import json, time, threading, sys

# Import package dependent libraries
from pathlib import Path
from socketIO_client import SocketIO, BaseNamespace
import paho.mqtt.client as mqtt

# Misc. Variables
motion_completed = "false"
waiting_motion_status = "false"

machineMotionRef = None
gCodeCallbackRef = None
lastSendTimeStamp = None

class CONTROL_DEVICE_SIGNALS:
    SIGNAL0 = "SIGNAL0"
    SIGNAL1 = "SIGNAL1"
    SIGNAL2 = "SIGNAL2"
    SIGNAL3 = "SIGNAL3"
    SIGNAL4 = "SIGNAL4"
    SIGNAL5 = "SIGNAL5"
    SIGNAL6 = "SIGNAL6"

class CONTROL_DEVICE_TYPE:
    IO_EXPANDER_GENERIC = "IO_EXPANDER_GENERIC"
    ENCODER             = "ENCODER"

class CONTROL_DEVICE_PORTS:
    SENSOR4 = "SENSOR4"
    SENSOR5 = "SENSOR5"
    SENSOR6 = "SENSOR6"

class DIRECTION:
    positive = "positive"
    negative = "negative"

class AXIS_NUMBER:
    DRIVE1 = 1
    DRIVE2 = 2
    DRIVE3 = 3

class DEFAULT_IP_ADDRESS:
    usb_windows     = "192.168.7.2"
    usb_mac_linux   = "192.168.6.2"
    ethernet        = "192.168.0.2"

class NETWORK_MODE:
    static  = "static"
    dhcp    = "dhcp"

class MICRO_STEPS:
    ustep_full  = 1
    ustep_2     = 2
    ustep_4     = 4
    ustep_8     = 8
    ustep_16    = 16

class MECH_GAIN:
    timing_belt_150mm_turn          = 150
    legacy_timing_belt_200_mm_turn  = 200
    ballscrew_10mm_turn             = 10
    legacy_ballscrew_5_mm_turn      = 5
    indexer_deg_turn                = 85
    conveyor_mm_turn                = 157

def fastMotionStatusCallback(data, mm):
    global motion_completed
    global waiting_motion_status

    # Was a motion status request received
    if data.find("Motion Status") != -1:
        # print "A motion status was requested"
        if data.find("Motion Status = COMPLETED") != -1 and waiting_motion_status == "true":
            # print "Move was completed"
            motion_completed = "true"
            waiting_motion_status = "false"
        else:
            # print "move is in progress"
            motion_completed = "false"
            waiting_motion_status = "true"
            mm.__emit__("V0")

#
# Class that handles all gCode related communications
# @status
#
class GCode:
    mySocket = "unassigned"
    ackReceived = "false"
    waiting_motion_status = "false"
    motion_completed = "false"
    lineNumber = 1
    lastPacket = {"data": "null", "lineNumber": "null"}
    gCodeErrors = {"checksum": "Error:checksum mismatch, Last Line: ", "lineNumber": "Error:Line Number is not Last Line Number+1, Last Line: "}
    userCallback = None

    #
    # Class constructor
    # PRIVATE
    # @param socket --- Description: The GCode class requires a socket object to communicate with the controller. The socket object is passed at contruction time.
    # @status
    #
    def __init__(self, socket):
        # Passing in the socket instance at construction
        self.mySocket = socket

    #
    # Function that indicates if the GCode communication port is ready to send another command.
    # @status
    #
    def __isReady__(self):
        return self.ackReceived

    #
    # Function that indicates if the the last move has completed
    # @status
    #
    def __isMotionCompleted__(self):
        global motion_completed
        return motion_completed

    #
    # Function to add the transport layer over a raw gCode packet.
    # PRIVATE
    # @param string --- Description: The GCode command to send.
    # @status
    #
    def __addTransLayer__(self, string):
        # Save the last packet sent
        self.lastPacket = {"data": string, "lineNumber": self.lineNumber}

        # Add the line number to the packet
        string = "N" + str(self.lineNumber) + " " + string

        # Increment the line number
        self.lineNumber = self.lineNumber + 1

        cs = 0

        # Calculate the checksum
        for i in range (0, len(string)):
            cs = cs ^ ord(string[i])

        # Returns the completed packet with checksum and line number
        return string + "*" + str(cs);

    #
    # Upon reception of an error message, this function extract the line number in the communication at which the error occured.
    # PRIVATE
    # @param string --- Description: The error message from the controller.
    # @status
    #
    def __extractLineNumberInError__(self, message):
        if message.find(self.gCodeErrors['checksum']) != -1:
            lineNumberBaseIndex = len(self.gCodeErrors['checksum']) - 1
            return int(message[lineNumberBaseIndex:])
        elif message.find(self.gCodeErrors['lineNumber']) != -1:
            lineNumberBaseIndex = len(self.gCodeErrors['lineNumber']) - 1
            return int(message[lineNumberBaseIndex:])

    #
    # Upon reception of a resend message, this function extract the line number in the message.
    # PRIVATE
    # @param string --- Description: The error message from the controller.
    # @status
    #
    def __extractLineNumberInResend__(self, message):
        lineNumberBaseIndex = len('Resend: ') - 1
        return int(message[lineNumberBaseIndex:])

    #
    # Function to reset the current line number in the communication.
    # PRIVATE
    # @param line --- Description: The new line number.
    # @status
    #
    def __setLineNumber__(self, line):
        self.lineNumber = line
        self.__emit__("M110 N" + str(line))

    #
    # Function to map API axis labels to motion controller axis labels
    # PRIVATE
    # @param axis --- Description: The API axis label.
    # @status
    #
    def __getTrueAxis__(self, axis):
        if axis == 1: return "X"
        elif axis == 2: return "Y"
        elif axis == 3: return "Z"
        else: return "Axis Error"

    #
    # Function that packages the data in a JSON object and sends to the MachineMotion server over a socket connection.
    # PRIVATE
    # @param axis --- Description: The API axis label.
    # @status
    #
    def __send__(self, cmd, data):
        global lastSendTimeStamp

        # Add the transport layer data
        data['value'] = self.__addTransLayer__(data['value'])

        # Serialize the dictionary in json format
        packet = json.dumps(data)

        # Reset the GCode status
        self.ackReceived = "false"

        lastSendTimeStamp = time.time()

        # Sending
        self.mySocket.emit(cmd, packet)

    #
    # Function to send a raw G-Code ASCII command
    # @param gCode --- Description: gCode is string representing the G-Code command to send to the controller. Type: string.
    # @status
    #
    def __emit__(self, gCode):

        # # When a G-Code command is sent, it is assumed that it is a motion command and the move_completed attriute is set to "false". The user has to used
        # # the isMotionCompleted() function to verify if the motion is completed.
        # if(gCode != "V0"):
            # self.motion_completed = "false"

        # Object to transmit data
        gCodeCmd = {"command": "gCode", "value": gCode}

        self.__send__('gCodeCmd', gCodeCmd)

        time.sleep(0.05)

    @staticmethod
    def __userCallback__(data): return

    #
    # Function that executes upon reception of messages from the motion controller. The user configured callback in ran after this function.
    # PUBLIC
    # @param data --- Description: The data sent by the motion controller. Type: string.
    # @status
    #
    def __rxCallback__(self, data):

        global waiting_motion_status
        global lastSendTimeStamp

        # print "DEBUG---Last command sent: " + str(self.lastPacket)
        # print "DEBUG---Last received data: " + data

        # Look if the echo of the last command was found in the incoming data
        if (data.find(self.lastPacket['data'])) != -1:
            # The last command was acknowledged
            self.ackReceived =  "true"
            # print "DEBUG---Received ack for packet " + str(self.lastPacket['data']) + ", line = " + str(self.lastPacket['lineNumber']) + "\n"
            #self.lastPacket = {"data": "null", "lineNumber": "null"}
        # Special ack for homing
        elif data.find('X:0.00') != -1 and self.lastPacket['data'].find('G28') != -1:
            # The last command was acknowledged
            self.ackReceived =  "true"
            # print "DEBUG---Received ack for homing"
            #self.lastPacket = {"data": "null", "lineNumber": "null"}
        # Special ack for homing
        elif data.find('DEBUG') != -1 and self.lastPacket['data'].find('M111') != -1:
            # The last command was acknowledged
            self.ackReceived =  "true"
            # print "DEBUG---Received ack for debug setup" + "\n"
            #self.lastPacket = {"data": "null", "lineNumber": "null"}
        # Look if errors were received
        elif (data.find('Error:') != -1):
            # print "DEBUG--Error received from controller. Last line correct line was " + str(self.__extractLineNumberInError__(data))
            # print "DEBUG--Error received from controller. Last line number sent " + str(self.lastPacket['lineNumber'])

            if (self.__extractLineNumberInError__(data) == (int(self.lastPacket['lineNumber']) - 1)):
                # print "DEBUG--Error received on line " + str(self.__extractLineNumberInError__(data))
                self.lastPacket = {"data": self.lastPacket['data'], "lineNumber": int(self.__extractLineNumberInError__(data))+1}
                self.ackReceived = "false"
                self.__emit__(self.lastPacket['data'])
        elif (data.find('Resend:') != -1):
            self.lineNumber = self.__extractLineNumberInResend__(data)

        fastMotionStatusCallback(data, self)

        self.__userCallback__(data)



    # Private function
    class ListenToSocket(threading.Thread):
        def __init__(self, gCode):
            self.gcode = gCode
            threading.Thread.__init__(self)
        def run(self):
            global lastSendTimeStamp

            self.gcode.mySocket.on('machineMotionAck', self.gcode.__rxCallback__)
            while True:
                if (self.gcode.mySocket.connected and self.gcode.ackReceived == 'false' and (lastSendTimeStamp is not None) and (time.time() - lastSendTimeStamp > 5)):
                    # Trigger a reconnection
                    self.gcode.mySocket.disconnect()
                    self.gcode.mySocket.connect('', True)
                self.gcode.mySocket.wait(1)

    def __keepSocketAlive__(self):
        thread = GCode.ListenToSocket(self)
        thread.daemon = True # Stops this thread if main one exits
        thread.start()

    # Private function
    def __setUserCallback__(self, userCallback):

        # Save the user function to call on incoming messages locally
        self.__userCallback__ = userCallback

        # Start the periodic process that fetches the sockets that were received by the OS
        self.__keepSocketAlive__()

#
# Class that encapsulates code that waits for a certain socket topic to be received
# @status
#
class WaitForSocketTopic:

    response_received = False
    mySocket = None
    myTopic = None

    # Function redefined by the user
    @staticmethod
    def _user_callback_(data): return

    # Wrapper to invoke the user defined function and manage the completion flag
    def _callback_(self, data):
        self.response_received = True
        self._user_callback_(data)

    def set_user_callback(self, callback):
        self._user_callback_ = callback

    def wait_for_response(self, socket, topic, callback):
        self.response_received = False

        self.mySocket = socket
        self.myTopic = topic
        self._user_callback_ = callback

        while self.response_received == False:
            self.mySocket.on(self.myTopic, self._callback_)
            self.mySocket.wait(seconds = 0.1)

#
# Class used to encapsulate the MachineMotion controller
# @status
#
class MachineMotion:
    # Class variables
    mySocket = "notInitialized"
    myConfiguration = {"machineIp": "notInitialized", "machineGateway": "notInitialized", "machineNetmask": "notInitialized"}
    myGCode = "notInitialized"
    myGCode = "notInitialized"

    myMqttClient = None

    myAxis1_steps_mm = "notInitialized"
    myAxis2_steps_mm = "notInitialized"
    myAxis3_steps_mm = "notInitialized"

    validPorts   = ["AUX1", "AUX2", "AUX3"]
    valid_u_step = [1, 2, 4, 8, 16]
    
    # -- Local storage of device information. --
    digitalInputs            = [[]]
    ioExpanderAvailability   = []
    encoderRealtimePositions = []

    # ------------------------------------------------------------------------
    # Utility function to convert the given input to a boolean value.
    #
    # @param value - The valur to be converted to a boolean
    def toBool(self, value):
        if ( type(value) is bool ): return value
        if ( type(value) is int ):
            if ( value == 0 ): return False
            return True
        if ( type(value) is str ):
            value = value.upper()
            if ( value == 'TRUE' or value == 'YES' or value == '1'):
                return True
            return False
        # -- Default to false if no conversion exists. --
        return False
        
    # ------------------------------------------------------------------------
    # Determines if the given id is valid for an IO Exapnder.
    #
    # @param {int} id - Device identifier
    # @return {Bool}  - True if valid; False otherwise
    def isIoExpanderIdValid(self, id):
        if (id < 1 or id > 3):
            return False
        return True
        
    # ------------------------------------------------------------------------
    # Determines if the given input pin identifier is valid for an IO Exapnder.
    #
    # @param {int} deviceId - Device identifier
    # @param {int} pinId    - Pin identifier
    # @return {Bool}        - True if valid; False otherwise
    def isIoExpanderInputIdValid(self, deviceId, pinId):
        if (self.isIoExpanderIdValid( deviceId ) == False):
            return False
        if (pinId < 0 or pinId > 3):
            return False
        return True
        
    # ------------------------------------------------------------------------
    # Determines if the given output pin identifier is valid for an IO Exapnder.
    #
    # @param {int} deviceId - Device identifier
    # @param {int} pinId    - Pin identifier
    # @return {Bool}        - True if valid; False otherwise
    def isIoExpanderOutputIdValid(self, deviceId, pinId):
        if (self.isIoExpanderIdValid( deviceId ) == False):
            return False
        if (pinId < 0 or pinId > 3):
            return False
        return True
        
    # ------------------------------------------------------------------------
    # Converts encoder alias to encoder internal index
    #
    # @param alias - The encoder alias
    # @return      - The encoder internal index
    def toEncoderIndex(alias):
        if ( type(alias) is int ): return alias
        return self.validPorts.index(alias)
        
    # ------------------------------------------------------------------------
    # Determines if the given id is valid for an encoder.
    #
    # @return {Bool} - True if valid; False otherwise
    def isEncoderIdValid(self, id):
        if id in self.validPorts:
            return True
        return False
            

    #
    # Function that will immediately stop all motion of all the axes
    # @status
    #
    def emitStop(self):
        global motion_completed

        motion_completed = "false"

        self.myGCode.__emit__("M410")

        # Wait and send a dummy packet to insure that other commands after the emit stop are not flushed.
        time.sleep(0.500)
        self.myGCode.__emit__("G0 X0")
        while self.isReady() != "true": pass

    #
    # Function that will initiate the homing sequence of all axes. The sequence will home all axes using the endstop signals
    # @status
    #
    def emitHomeAll(self):
        global motion_completed

        motion_completed = "false"

        self.myGCode.__emit__("G28")

    #
    # Function that will initiate the homing sequence for the axis specified. The sequence will home the axis using the endstops signals.
    # @param axis --- Description: "axis" is the axis number that will be set to home location.  --- Type: number.
    # @status
    #
    def emitHome(self, axis):
        global motion_completed

        motion_completed = "false"

        self.myGCode.__emit__("G28 " + self.myGCode.__getTrueAxis__(axis))

    #
    # Function to send a displacement speed configuration command
    # @param mm_per_min --- Description: mm_per_mim is the displacement speed in mm/min --- Type: number.
    # @status
    #
    def emitSpeed(self, mm_per_min):
        self.myGCode.__emit__("G0 F" +str(mm_per_min))
        while self.isReady() != "true": pass

    #
    # Function to send a displacement acceleration configuration command
    # @param mm_per_sec_sqr --- Description: mm_per_sec_sqr is the displacement acceleration in mm/sec^2 --- Type: number.
    # @status
    #
    def emitAcceleration(self, mm_per_sec_sqr):
        self.myGCode.__emit__("M204 T" + str(mm_per_sec_sqr))
        while self.isReady() != "true": pass

    #
    # Function to send an absolute move command to the MachineMotion controller
    # @param axis --- Description: axis is the axis on which the command will be applied. --- Type: string or number.
    # @param position --- Description: position is the position from its home location where the axis will go. --- Type: string or number.
    # @status
    #
    def emitAbsoluteMove(self, axis, position):
        global motion_completed

        motion_completed = "false"

        # Set to absolute motion mode
        self.myGCode.__emit__("G90")
        while self.isReady() != "true": pass

        # Transmit move command
        self.myGCode.__emit__("G0 " + self.myGCode.__getTrueAxis__(axis) + str(position))
        while self.isReady() != "true": pass

    # ------------------------------------------------------------------------
    # Move the axis to an absolute position
    #
    # @param axis     - The axis to move
    # @param position - The absolute position to move to.
    def moveToAbsolutePosition(self, axis, position):
        self.emitAbsoluteMove(axis, position)
    
    #
    # Function to send a relative move command to the MachineMotion controller
    # @param axis --- Description: axis is the axis on which the command will be applied. --- Type: int or string.
    # @param direction --- Description: direction is the direction in which the relative move will be conducted. --- Type: string of value equal to "positive" or "negative"
    # @param distance is the distance of the relative move.
    # @status
    #
    def emitRelativeMove(self, axis, direction, distance):
        global motion_completed

        motion_completed = "false"

        # Set to relative motion mode
        self.myGCode.__emit__("G91")
        while self.isReady() != "true": pass

        if direction == "positive":distance = "" + str(distance)
        elif direction  == "negative": distance = "-" + str(distance)

        # Transmit move command
        self.myGCode.__emit__("G0 " + self.myGCode.__getTrueAxis__(axis) + str(distance))
        while self.isReady() != "true": pass

    #
    # Function to send a raw G-Code ASCII command
    # @param gCode --- Description: gCode is string representing the G-Code command to send to the controller. Type: string.
    # @status
    #
    def emitgCode(self, gCode):
        global motion_completed

        motion_completed = "false"

        self.myGCode.__emit__(gCode)

    #
    # Function that indicates if the GCode communication port is ready to send another command.
    # @status
    #
    def isReady(self):
        return self.myGCode.__isReady__()

    #
    # Function that indicates if the the last move has completed
    # @status
    #
    def isMotionCompleted(self):
        global motion_completed
        return motion_completed

    def waitForMotionCompletion(self):
        self.emitgCode("V0")
        while  self.isMotionCompleted() != "true": pass

    #
    # Function to setup the static IP and the router gateway of the MachineMotion controller
    # @param machineIp --- Description: desired static ip address to assign to the MachineMotion controller. --- Type: string (xxx.xxx.xxx.xxxx) where x are numbers.
    # @param gatewayIP --- Description: ip address of the LAN router. Setting a proper gateway ip addreess enables MachineMotion to access the internet for downloads --- Type: string (xxx.xxx.xxx.xxxx) where x are numbers.
    # @note:           --- For the MachineMotion to access the Internet after an configIp() call, the MachineMotion device must be rebooted.
    # @status
    #
    def configMachineMotionIp(self, mode, machineIp, machineNetmask, machineGateway):

        # Create a new object and augment it with the key value.
        self.myConfiguration["mode"] = mode
        self.myConfiguration["machineIp"] = machineIp
        self.myConfiguration["machineNetmask"] = machineNetmask
        self.myConfiguration["machineGateway"] = machineGateway


        self.mySocket.emit('configIp', json.dumps(self.myConfiguration))

        time.sleep(1)

    #
    # Function to configure the axis motion.
    # @param axis       --- Description: The axis number.                           --- Type: number [1, 2, 3]
    # @param _u_step    --- Description: uStep setting.                             --- Type: number either [1, 2, 4, 8, 16]
    # @param _mech_gain --- Description: Mechanical gain of the axis in mm / turn.  --- Type: number
    # @status
    #
    def configAxis(self, axis, _u_step, _mech_gain):
        u_step    = float(_u_step)
        mech_gain = float(_mech_gain)

        # validate that the uStep setting is valid
        if (self.valid_u_step.index(u_step) != -1):
            if(axis == 1):
                self.myAxis1_steps_mm = 200 * u_step / mech_gain
                self.myGCode.__emit__("M92 " + self.myGCode.__getTrueAxis__(axis) + str(self.myAxis1_steps_mm))
            elif(axis == 2):
                self.myAxis1_steps_mm = 200 * u_step / mech_gain
                self.myGCode.__emit__("M92 " + self.myGCode.__getTrueAxis__(axis) + str(self.myAxis1_steps_mm))
            elif(axis == 3):
                self.myAxis1_steps_mm = 200 * u_step / mech_gain
                self.myGCode.__emit__("M92 " + self.myGCode.__getTrueAxis__(axis) + str(self.myAxis1_steps_mm))
            else:
                pass
                # print "Argument error, {configAxis(self, axis, u_step, mech_gain)}, {axis} argument is invalid"

        else:
            pass
            # print "Argument error, {configAxis(self, axis, u_step, mech_gain)}, {u_step} argument is invalid"
    #
    # Function to save/persist data in the MachineMotion Controller (key - data pair)
    # @param key --- Description: key is a string that identifies the data to save for future retrieval. --- Type: string or number.
    # @param data --- Description: data is a dictionary containing the data to save. --- Type: dictionary.
    # @status
    #
    def saveData(self, key, data):
        # Create a new object and augment it with the key value.
        dataPack = {}
        dataPack["fileName"] = key;
        dataPack["data"] = data;

        # Send the request to MachineMotion
        self.mySocket.emit('saveData', json.dumps(dataPack))
        time.sleep(0.05)

    #
    # Function to retrieve saved/persisted data in the MachineMotion Controller (key - data pair)
    # @param key --- Description: key is a string that identifies the data to retrieve. --- Type: string.
    # @param callback --- Description: callback is the function to invoke when the asynchronous data is received. --- Type: function with on argument that will contain the data in json serialized format.
    # @status
    #
    def getData(self, key, callback):
        #Send the request to MachineMotion

        self.mySocket.emit('getData', key)

        # On reception of the data invoke the callback function.
        self.mySocket.on('getDataResponse', callback)

    # ------------------------------------------------------------------------
    # Retreive the last recieved encoder realtime position from local storage.
    #
    # @param encoder - The encoder identifier from which to get the position
    # @return        - The last realtime position
    def readEncoderRealtimePosition(self, encoder):
        # -- Grow the encoder position storage. --
        while (len(self.encoderRealtimePositions) <= encoder):
            self.encoderRealtimePositions.append(0)
        return self.encoderRealtimePositions[encoder]
        
    # ------------------------------------------------------------------------
    # Save the received encoder realtime position into local storage.
    #
    # @param encoder  - The encoder identifier that reported the new position
    # @param position - The realtime position received
    def setEncoderRealtimePosition(self, encoder, position):
        # -- Grow the encoder position storage. --
        while (len(self.encoderRealtimePositions) <= encoder):
            self.encoderRealtimePositions.append(0)
        self.encoderRealtimePositions[encoder] = position

    # ------------------------------------------------------------------------
    # Retreive the digital input from local storage.
    #
    # @param device - The device associated with the digital input
    # @param pin    - The pin index on the device
    # @return       - 0/1 depending on the voltage state of the input
    def getDigitalInput(self, device, pin):
        # -- Grow the digital inputs device storage. --
        while (len(self.digitalInputs) <= device):
            self.digitalInputs.append([])
        # -- Grow the gitial inputs pin storage. --
        while (len(self.digitalInputs[device]) <= pin):
            self.digitalInputs[device].append(int(0))
        return self.digitalInputs[device][pin]
        
    # ------------------------------------------------------------------------
    # Save the digital input for later retreival.
    #
    # @param device - The device associated with the digital input
    # @param pin    - The pin index on the device
    # @param state  - 0/1 depending on the voltage state of the input
    def setDigitalInput(self, device, pin, state):
        # -- Grow the digital inputs device storage. --
        while (len(self.digitalInputs) <= device):
            self.digitalInputs.append([])
        # -- Grow the gitial inputs pin storage. --
        while (len(self.digitalInputs[device]) <= pin):
            self.digitalInputs[device].append(int(0))
        self.digitalInputs[device][pin]= state
        
    # ------------------------------------------------------------------------
    # Save the digital input for later retreival.
    #
    # @param device              - The IO expander device identifier
    # @param {bool} availability - IO Expander availability state
    def setIoExpanderAvailability(self, device, availability):
        # -- Grow the IO expander availability local storage. --
        while (len(self.ioExpanderAvailability) <= device):
            self.ioExpanderAvailability.append( False )
        self.ioExpanderAvailability[device]= availability
        
    # ------------------------------------------------------------------------
    # Save the digital input for later retreival.
    #
    # @param device   - The IO expander device identifier
    # @preturn {bool} - IO Expander availability state
    def isIoExpanderAvailable(self, device):
        # -- Grow the IO expander availability local storage. --
        while (len(self.ioExpanderAvailability) <= device):
            self.ioExpanderAvailability.append( False )
        return self.ioExpanderAvailability[device]
        
    # ------------------------------------------------------------------------
    # Returns the last known state of the specified dgital input.
    #
    # @param device - The IO Expander device identifier
    # @param pin    - The pin identifier to be read
    # @return       - 0/1 reflecting the voltage state of the input
    def digitalRead(self, device, pin):
        if (self.isIoExpanderInputIdValid( device, pin ) == False):
            print ( "DEBUG: unexpected digitalOutput parameters: device= " + str(device) + " pin= " + str(pin) )
            return 0
        return self.getDigitalInput(device, pin)
        
    # ------------------------------------------------------------------------
    # Changes the digital output state of the specified digital output.
    #
    # @param device - The IO Expander device identifier
    # @param pin    - The pin identifier to be read
    # @param value  - 0/1 reflecting the new voltage state of the output
    def digitalWrite(self, device, pin, value):
        if (self.isIoExpanderOutputIdValid( device, pin ) == False):
            print ( "DEBUG: unexpected digitalOutput parameters: device= " + str(device) + " pin= " + str(pin) )
            return
        self.myMqttClient.publish('devices/io-expander/' + str(device) + '/digitalOutput/' +  str(pin), '1' if value else '0')
            
    # ------------------------------------------------------------------------
    # Returns the last received encoder position.
    #
    # @param {int} encoder - The identifier of the encoder.
    # @return              - The relatime encoder position (deled by up to 250ms)
    #
    # NOTE: The encoder position return may be offset by up to 250ms caused by
    #       internal propagation delays
    
    def encoderRead(self, encoder):
        encoder.upper()
        if (self.isEncoderIdValid( encoder ) == False):
            print ( "DEBUG: unexpected encoder identifier: encoderId= " + str(encoder) )
            return 0
        return self.encoderRealTimePosition[encoder]
        

    # ------------------------------------------------------------------------
    # Register to the MQTT broker on each connection.
    #
    # @param client   - The MQTT client identifier (us)
    # @param userData - The user data we have supply on registration (none)
    # @param flags    - Connection flags
    # @param rc       - The connection return code
    def __onConnect(self, client, userData, flags, rc):
        if rc == 0:
            self.myMqttClient.subscribe('devices/io-expander/+/digitalInput/#')
            self.myMqttClient.subscribe('devices/encoder/+/realtimePosition')
            self.myMqttClient.subscribe('devices/io-expander/+/available')

    # ------------------------------------------------------------------------
    # Update our internal state from the messages received from the MQTT broker
    #
    # @param client   - The MQTT client identifier (us)
    # @param userData - The user data we have supply on registration (none)
    # @param msg      - The MQTT message recieved
    def __onMessage(self, client, userData, msg):
        payload = msg.payload.decode('ascii')
        topicParts = msg.topic.split('/')
        deviceType = topicParts[1]
        device = int( topicParts[2] )
        if (deviceType == 'io-expander'):
            # -- Manage IO Expander availability. --
            attribute = topicParts[3]
            if( attribute == 'available' ):
                self.setIoExpanderAvailability( device, self.toBool( payload ) )
                return
            # -- Manage IO Expander digital input. --
            pin = int( topicParts[4] )
            if (self.isIoExpanderInputIdValid(device, pin) == False):
                return
            value  = int( payload )
            self.setDigitalInput( device, pin, value )
            return
        if (deviceType == 'encoder'):
            position = float( payload )
            self.setEncoderRealtimePosition( device, position )

    def __onDisconnect(self, client, userData, rc):
       print( "Disconnected with rtn code [%d]"% (rc) )

    def __establishConnection(self, isReconnection):
        global gCodeCallbackRef

        # Create the web socket
        self.mySocket = SocketIO(self.myConfiguration['machineIp'], 8888, MySocketCallbacks)
        self.myGCode = GCode(self.mySocket)

        # Send a command to initialize the MachineMotion system
        configCmd = {"parameter": "init", "value": "sysInit"}
        packet = json.dumps(configCmd)
        self.mySocket.emit('sysInit', packet)

        # Give 5 seconds to the MachineMotion system to initialize the hardware
        time.sleep(5)

        # Set the callback to the user specified function. This callback is used to process incoming messages from the machineMotion controller
        self.myGCode.__setUserCallback__(gCodeCallbackRef)

        # Set the line number to initialize the communication
        self.myGCode.__setLineNumber__(0)
        while self.isReady() != "true": pass

        #Set the debug level of the motionController to "247" to enable echo on all commands. Refer to http://marlinfw.org/docs/gcode/M111.html for more details.
        self.emitgCode("M111 S247")
        while self.isReady() != "true": pass

    # Class constructor
    def __init__(self, gCodeCallback, machineIp):
        global machineMotionRef
        global gCodeCallbackRef

        self.myConfiguration['machineIp'] = machineIp

        # MQTT
        self.myMqttClient = mqtt.Client()
        self.myMqttClient.on_connect = self.__onConnect
        self.myMqttClient.on_message = self.__onMessage
        self.myMqttClient.on_disconnect = self.__onDisconnect
        self.myMqttClient.connect_async(machineIp)
        self.myMqttClient.loop_start()

        machineMotionRef = self
        gCodeCallbackRef = gCodeCallback

        self.__establishConnection(False)

class MySocketCallbacks(BaseNamespace):

    def on_connect(self):
        print('[SocketIO Connected]')

    def on_reconnect(self):
        print('[SocketIO Reconnected]')
        global lastSendTimeStamp
        global machineMotionRef

        lastSendTimeStamp = time.time()
        machineMotionRef.myGCode.__setLineNumber__(1)

    def on_disconnect(self):
        print('[SocketIO Disconnected]')
