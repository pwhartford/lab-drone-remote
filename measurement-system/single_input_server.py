#!/usr/bin/env python
#  -*- coding: utf-8 -*-

from time import sleep
from sys import stdout
from daqhats import mcc128, OptionFlags, TriggerModes, HatIDs, HatError, \
    AnalogInputMode, AnalogInputRange

from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string
    
import dataclasses

import pyaudio
import numpy as np
import time
import math
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
SAMPLE_NUMBER = 10000
CHANNELS = [1]

#FFT Settings
FFT_BIN_NUMBER = 4096
NPERSEG = FFT_BIN_NUMBER//16


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

        #Setup the DAQ
        self.setup_daq()

    #Setup the DAQ device  
    def setup_daq(self):
        print('[DAQ] Setting up the DAQ System')

        # Store the channels in a list and convert the list to a channel mask that
        # can be passed as a parameter to the MCC 128 functions.
        self.channel_mask = chan_list_to_mask(CHANNELS)
        self.num_channels = len(CHANNELS)

        #Set input mode to differential
        input_mode = AnalogInputMode.SE
        input_range = AnalogInputRange.BIP_1V

        # Select an MCC 128 HAT device to use.
        self.address = select_hat_device(HatIDs.MCC_128)
        self.hat = mcc128(self.address)

        #Set the DAQ to differential input mode
        self.hat.a_in_mode_write(input_mode)
        self.hat.a_in_range_write(input_range)

        #Set continuous scan
        options = OptionFlags.CONTINUOUS

        print('\n [DAQ] Selected MCC 128 HAT device at address', self.address)

        actual_scan_rate = self.hat.a_in_scan_actual_rate(self.num_channels, SAMPLE_FREQUENCY)

        print(self.hat.a_in_range_read())

        print('    Requested scan rate: ', SAMPLE_FREQUENCY)   
        print('    Actual scan rate: ', actual_scan_rate)
        print('    Channels: ', end='')
        print(', '.join([str(chan) for chan in CHANNELS]))
        print('    Samples per channel', SAMPLE_NUMBER)

        #Configure and start the scan.
        self.hat.a_in_scan_start(self.channel_mask, SAMPLE_NUMBER, SAMPLE_FREQUENCY,
                                options)


    def read_data(self):
        """This is a single read request, need to specify number for proper sample freuquency """

        #Hardcoded read parameter 
        read_request_size = SAMPLE_NUMBER
        timeout = 5.0
        read_result = self.hat.a_in_scan_read(read_request_size, timeout)

        # Check for an overrun error
        if read_result.hardware_overrun:
            print('\n\nHardware overrun\n')
            
            return np.array([1]), np.array([1]) 

        elif read_result.buffer_overrun:
            print('\n\nBuffer overrun\n')
            self.stop_hat()
            self.setup_daq()
            
            return np.array([1]),  np.array([1]) 

        #Create zero array with data
        timeArray = np.linspace(0, SAMPLE_NUMBER/SAMPLE_FREQUENCY, SAMPLE_NUMBER)

        samples_read_per_channel = int(len(read_result.data) / self.num_channels)

        if samples_read_per_channel > 0:
            index = samples_read_per_channel * self.num_channels - self.num_channels
            
            dataArray = np.array(read_result.data).reshape(len(CHANNELS), SAMPLE_NUMBER)       

        # print(timeArray)
        # print(dataArray)

        return timeArray, dataArray

    def read_spectrum(self, binNumber):
        #Hardcoded read parameter 
        timeArray, dataArray = self.read_data()
        #Create zero array with data
        welchOutput, welchFrequency = signal.welch(dataArray, fs = SAMPLE_FREQUENCY, nperseg = NPERSEG)

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
        response = np.frombuffer(self.rfile.read(data_len), dtype = 'uint8')

        #Save data if the array reads 1
        if response[0] == 0:
            self.on_stream_command()

        elif response[0] == 1:
            self.on_save_command()

        elif response[0]==2:
            self.on_spectrum_command()
    

    def on_stream_command(self):
        timeArray, dataArray = self.daq.read_data() 

        stream = io.BytesIO()

        #Send data to stream
        self.send_data(stream, timeArray)
        self.send_data(stream, dataArray)

    def on_save_command(self):
        print(f"[DAQ Server] Client sent save command: {self.client_address[0]}:{self.client_address[1]}")

        self.daq.record_data()

    def on_spectrum_command(self):
        welchFrequency, welchOutput = self.daq.read_spectrum(FFT_BIN_NUMBER)

        stream = io.BytesIO()

        #Send data to the 
        self.send_data(stream, welchFrequency)
        self.send_data(stream, welchOutput)


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
    server.serve_forever()


# @dataclass 
# class DAQSettings()



#Run if file is ran directly
if __name__ == "__main__":
    main() 

