#!/usr/bin/env python
#  -*- coding: utf-8 -*-

from time import sleep
from sys import stdout
from daqhats import mcc128, OptionFlags, TriggerModes, HatIDs, HatError, \
    AnalogInputMode, AnalogInputRange

from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string
    
import numpy as np
import time
from datetime import datetime
from pathlib import Path
from multiprocessing import Queue, Process 
from scipy import signal 


#Imports for server
import socket
import threading
from socketserver import ThreadingTCPServer, StreamRequestHandler
import io 
import struct 



#DAQ Settings
SAMPLE_FREQUENCY = 10000.0 #Hz
SAMPLE_NUMBER = 1000
# CHANNELS = [0,4,1,5] #All channels on specified block
CHANNELS = [0,1] #Hotwire channels
# CHANNELS = [0]


#Data Dir
DATA_DIR = Path('/home/vki/Documents/Data/record_test')
DATA_DIR.mkdir(parents = True, exist_ok=True)

#Output file name
OUTPUT_FILE = DATA_DIR / 'hotwire_test.txt'

#Server settings
PORT = 8000


#Class to handle DAQ i/o - call read_data to return an array of data
class DAQHandler():
    def __init__(self):
        #Inherit process function 
        super(DAQHandler, self).__init__()

        self.channels = CHANNELS
        self.sampleFrequency = SAMPLE_FREQUENCY 
        self.sampleNumber = SAMPLE_NUMBER


        #Setup the DAQ
        self.setup_daq()

    #Setup the DAQ device  
    def setup_daq(self):
        print('[DAQ] Setting up the DAQ System')

        # Store the channels in a list and convert the list to a channel mask that
        # can be passed as a parameter to the MCC 128 functions.
        self.channelMask = chan_list_to_mask(self.channels)
        self.numChannels = len(self.channels)

        #Set input mode to single channel (range is +/-5V)
        inputMode = AnalogInputMode.SE
        inputRange = AnalogInputRange.BIP_5V

        # Select an MCC 128 HAT device to use, currently just the one 
        self.address = select_hat_device(HatIDs.MCC_128)
        self.hat = mcc128(self.address)


        #Set the DAQ to differential input mode
        self.hat.a_in_mode_write(inputMode)
        self.hat.a_in_range_write(inputRange)


        #Set continuous scan
        self.options = OptionFlags.CONTINUOUS

        self.set_sample_rate()


    def set_sample_rate(self):
        print('\n [DAQ] Selected MCC 128 HAT device at address', self.address)

        actualScanRate = self.hat.a_in_scan_actual_rate(self.numChannels, self.sampleFrequency)

        print('    Requested scan rate: ', self.sampleFrequency)   
        print('    Actual scan rate: ', actualScanRate)
        print('    Channels: ', end='')
        print(', '.join([str(chan) for chan in self.channels]))
        print('    Samples per channel', self.sampleNumber)

        #Configure and start the scan.
        self.hat.a_in_scan_start(self.channelMask, self.sampleNumber, self.sampleFrequency,
                                self.options)



    def change_sample_settings(self, sampleFrequency, sampleNumber):
        self.sampleFrequency = sampleFrequency
        self.sampleNumber = int(sampleNumber)
        
        #Stop the hat 
        self.stop_hat()

        #Set the sample rate and start again
        self.set_sample_rate()


    def read_data(self, sampleNumber):
        """This is a single read request, need to specify number for proper sample freuquency """

        #Hardcoded read parameter 
        timeout = sampleNumber*self.sampleFrequency + 1 #Set the timeout to be a little more than the sample time 
        
        #Read from the DAQ
        readResult = self.hat.a_in_scan_read(sampleNumber, self.sampleFrequency)

        # Check for an overrun error - return 1 if error happens
        if readResult.hardware_overrun:
            print('\n\nHardware overrun\n')
            return np.array([1]), np.array([1]) 

        #Reset the DAQ if there's a buffer error 
        elif readResult.buffer_overrun:
            print('\n\nBuffer overrun\n')
            self.stop_hat()
            self.setup_daq()
            
            return np.array([1]),  np.array([1]) 


        #Create time array 
        timeArray = np.linspace(0, SAMPLE_NUMBER/SAMPLE_FREQUENCY, SAMPLE_NUMBER)

        #Needs to be reshaped like this specifically - otherwise each channel is a cycle of the others (i.e. (4,1000))
        dataArray = np.array(readResult.data).reshape(len(CHANNELS), SAMPLE_NUMBER)

        return timeArray, dataArray

    def read_spectrum(self, binNumber):
        #Hardcoded read parameter 
        timeArray, dataArray = self.read_data()
        #Create zero array with data
        welchOutput, welchFrequency = signal.welch(dataArray[0,:], fs = SAMPLE_FREQUENCY, nperseg = NPERSEG)
        welchOutput = np.zeros((len(CHANNELS), welchOutput.shape[0])) 

        for ii, data in enumerate(dataArray):
            welchOutput[ii,:], _ = signal.welch(data, fs = SAMPLE_FREQUENCY, nperseg = NPERSEG)

        return welchOutput, welchFrequency


    def record_data(self):
        """
        Reads data from the specified channels on the specified DAQ HAT devices
        and updates the data on the terminal display.  The reads are executed in a
        loop that continues until either the scan completes or an overrun error
        is detected.

        Args:
            hat (mcc128): The mcc128 HAT device object.
            SAMPLE_NUMBER: The number of samples to read for each channel.
            num_channels (int): The number of channels to display.

        Returns:
            None

        """

        total_samples_read = 0
        read_request_size = SAMPLE_NUMBER

        print('[DAQ] Recording ')
       
        #Write header file
        with open(OUTPUT_FILE, 'w') as f:      
            f.write("Timestamp,Sound Lvl ch.0 (V),Sound Lvl ch.1 (V),Sound Lvl ch.2 (V),Sound Lvl ch.3 (V)\n")

        while total_samples_read < SAMPLE_NUMBER:

            #Write results to output file
            with open(OUTPUT_FILE, 'a') as f:
                np.savetxt(f,data.T,fmt='%6e',delimiter=',')
            
            total_samples_read+=1 
                    
        print('\n')

        print('[DAQ] Finished Recording')

    def stop_hat(self):
        #Cleanup and stop hat 
        self.hat.a_in_scan_stop()
        self.hat.a_in_scan_cleanup()

    def __del__(self):
        self.stop_hat()


#Handles TCP server requests - once connected the server reads from the daq, waits for a handshake/command, and 
class DAQRequestHandler(StreamRequestHandler):
    def __init__(self, daq):
        # super(DAQRequestHandler, self).__init__()
        self.daq = daq


    #Override to call function - calls init class and inputs the read queue 
    def __call__(self, request, client_address, server):
        h = DAQRequestHandler(self.daq)
        StreamRequestHandler.__init__(h, request, client_address, server)


    def handle(self):
        print(f"[DAQ Server] Client connected: {self.client_address[0]}:{self.client_address[1]}")

        #Create BytesIO object to handle sending/receiving data
        stream = io.BytesIO()

        #Send the channel info and sample frequency/sample amount
        self.send_data(stream, np.array(CHANNELS, dtype = 'float'))
        self.send_data(stream, np.array([SAMPLE_FREQUENCY, SAMPLE_NUMBER]))


        while True: 
            #Read handshake/command
            self.read_command()

    def send_data(self, stream, data):
        #Create numpy array from DAQ data
        #Tell the client the length of the data (uses stream object to do this)
        stream.write(data)
        self.wfile.write(struct.pack('<L', stream.tell()))
        self.wfile.flush()
        stream.seek(0)

        #Send data as double
        self.wfile.write(stream.read())
        stream.seek(0)
        stream.truncate()
        self.wfile.flush()

    def read_command(self):
        data_len = struct.unpack('<L', self.rfile.read(struct.calcsize('<L')))[0]
        response = np.frombuffer(self.rfile.read(data_len), dtype = 'float')

        print(response)

        #Save data if the array reads 1
        if int(response[0]) == 0:
            self.on_stream_command()

        elif int(response[0]) == 1:
            self.on_save_command()

        elif response[0]==2:
            self.on_parameter_command(response[1], response[2])
        

    def on_stream_command(self):
        timeArray, dataArray = self.daq.read_data(SAMPLE_NUMBER) 

        stream = io.BytesIO()

        #Send data to stream
        self.send_data(stream, timeArray)
        self.send_data(stream, dataArray)

    def on_save_command(self):
        print(f"[DAQ Server] Client sent save command: {self.client_address[0]}:{self.client_address[1]}")

        self.daq.record_data()

    def on_parameter_command(self, sampleFrequency, sampleNumber):
        print(f"[DAQ Server] Client sent change parameter command: {self.client_address[0]}:{self.client_address[1]}")

        self.daq.change_sample_settings(sampleFrequency, sampleNumber)

        self.on_stream_command()

def main():
    #Initialize data acquisition device 
    daq = DAQHandler()

    #Local host
    HOST = '0.0.0.0'
    
    #Create server
    print('Creating server %s:%s'%(HOST, PORT))

    server = ThreadingTCPServer((HOST, PORT), DAQRequestHandler(daq), False)
    
    #Fix for when server shuts down inproperly - enables rebinding to the same address
    server.allow_reuse_address = True 
    server.server_bind() 
    server.server_activate() 

    #Start server 
    try:
        server.serve_forever()
    except KeyboardInterrupt: daq.stop_hat()

# @dataclass 
# class DAQSettings()



#Run if file is ran directly
if __name__ == "__main__":
    main() 

