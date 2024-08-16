#!/usr/bin/env python
#  -*- coding: utf-8 -*-

from time import sleep
from sys import stdout
from daqhats import mcc128, OptionFlags, TriggerModes, HatIDs, HatError, \
    AnalogInputMode, AnalogInputRange

from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string
    

import pyaudio
import numpy as np
import time
import math
from datetime import datetime
from pathlib import Path
from multiprocessing import Queue, Process 


#Imports for server
import socket
import threading
import socketserver

#DAQ Settings
SAMPLE_FREQUENCY = 1000.0 #Hz
SAMPLE_NUMBER = 10000
CHANNELS = [0, 1, 2, 3]

#Data Dir
DATA_DIR = Path('/home/vki/Documents/Data/record_test')
DATA_DIR.mkdir(parents = True, exist_ok=True)

#Output file name
OUTPUT_FILE = DATA_DIR / 'sound_levels_test.txt'



class DAQHandler():
    def __init__(self):
        #Inherit process function 
        super(DAQHandler, self).__init__()

        #Setup the DAQ
        self.setup_daq()

    #Setup the DAQ device  
    def setup_daq(self):
        # Store the channels in a list and convert the list to a channel mask that
        # can be passed as a parameter to the MCC 128 functions.
        self.channel_mask = chan_list_to_mask(CHANNELS)
        self.num_channels = len(CHANNELS)

        #Set input mode to differential
        input_mode = AnalogInputMode.DIFF
        input_range = AnalogInputRange.BIP_1V

        # Select an MCC 128 HAT device to use.
        self.address = select_hat_device(HatIDs.MCC_128)
        self.hat = mcc128(self.address)

        #Set the DAQ to differential input mode
        self.hat.a_in_mode_write(input_mode)
        self.hat.a_in_range_write(input_range)

        #Set default options
        options = OptionFlags.DEFAULT


        print('\nSelected MCC 128 HAT device at address', self.address)

        actual_scan_rate = self.hat.a_in_scan_actual_rate(self.num_channels, SAMPLE_FREQUENCY)

        print('    Requested scan rate: ', SAMPLE_FREQUENCY)   
        print('    Actual scan rate: ', actual_scan_rate)
        print('    Channels: ', end='')
        print(', '.join([str(chan) for chan in CHANNELS]))
        print('    Samples per channel', SAMPLE_NUMBER)

        #Configure and start the scan.
        self.hat.a_in_scan_start(self.channel_mask, SAMPLE_NUMBER, SAMPLE_FREQUENCY,
                                options)


    def read_data(self):

        #Hardcoded read parameter 
        total_samples_read = 0
        read_request_size = 1
        timeout = 5.0
        read_result = self.hat.a_in_scan_read(read_request_size, timeout)

        # Check for an overrun error
        if read_result.hardware_overrun:
            print('\n\nHardware overrun\n')
            return 1 
        elif read_result.buffer_overrun:
            print('\n\nBuffer overrun\n')
            return 1 


        return data

    def read_and_display_data(self):
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



        # Continuously update the display value until Ctrl-C is pressed
        # or the number of samples requested has been read.
        while total_samples_read < SAMPLE_NUMBER:
            #Get reading 
            read_result = self.hat.a_in_scan_read(read_request_size, timeout)

            # Check for an overrun error
            if read_result.hardware_overrun:
                print('\n\nHardware overrun\n')
                break
            elif read_result.buffer_overrun:
                print('\n\nBuffer overrun\n')
                break

            samples_read_per_channel = int(len(read_result.data) / self.num_channels)
            total_samples_read += samples_read_per_channel

            # Display the last sample for each channel.
            print('\r{:12}'.format(samples_read_per_channel),
                ' {:12} '.format(total_samples_read), end='')

            if samples_read_per_channel > 0:
                index = samples_read_per_channel * self.num_channels - self.num_channels

                # timestamp = datetime.now().strftime("%H:%M:%S") # lit la date (pas besoin)
                sound_level = np.zeros((4, 1))      # array de taille 4,1 remplit de 0
                
                for i in range(self.num_channels):
                    
                    print('{:10.5f}'.format(read_result.data[index + i]), 'V ',
                        end='')                                                   

                    #Append to numpy array
                    sound_level[i] = read_result.data[index + i]           

                #Write results to output file
                with open(OUTPUT_FILE, 'a') as f:
                    np.savetxt(f,sound_level.T,fmt='%6e',delimiter=',')
                    
                stdout.flush()

        print('\n')

    def stop_hat(self):
        #Cleanup and stop hat 
        self.hat.a_in_scan_stop()
        self.hat.a_in_scan_cleanup()


class TCPRequestHandler(socketserver.BaseRequestHandler):
    def __init__(self):
        super(TCPRequestHandler, self).__init__()
        self.daqHandler = DAQHandler() 

    
    def handle(self):
        
        while True:
            data = self.daqHandler.read_data() 
            
            # self.wfile.write(data)
            self.request.sendall(data)
        
        # data = str(self.request.recv(1024), 'ascii')
        # cur_thread = threading.current_thread()
        # response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
        self.request.sendall(response)




def create_server():
    HOST, PORT = "localhost", 9999

    # Create the server, binding to localhost on port 9999
    with socketserver.ThreadedTCPServer((HOST, PORT), TCPRequestHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()





def main():
    #Setup the DAQ
    daqHandler = DAQHandler()    

    #Create header for CSV file
    with open(OUTPUT_FILE, 'w') as f:      
        f.write("Timestamp,Sound Lvl ch.0 (V),Sound Lvl ch.1 (V),Sound Lvl ch.2 (V),Sound Lvl ch.3 (V)\n")


    try:
        # # wait for the external trigger to occur
        # print('\nWaiting for trigger ... hit Ctrl-C to cancel the trigger')
        # wait_for_trigger(hat)

        print('\nStarting scan ... Press Ctrl-C to stop\n')

        # Display the header row for the data table.
        print('Samples Read    Scan Count', end='')
        for chan in CHANNELS:
            print('    Channel ', chan, sep='', end='')
        print('')

        daqHandler.read_and_display_data()

    #Stop on ctrl+c
    except KeyboardInterrupt:   
        print('Stopping')
    
    #Stop and cleanup daq
    daqHandler.stop_hat()


#Run if file is ran directly
if __name__ == "__main__":
    main() 




# if __name__ == "__main__":
#     # Port 0 means to select an arbitrary unused port
#     HOST, PORT = "localhost", 0

#     server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
#     with server:
#         ip, port = server.server_address

#         # Start a thread with the server -- that thread will then start one
#         # more thread for each request
#         server_thread = threading.Thread(target=server.serve_forever)
#         # Exit the server thread when the main thread terminates
#         server_thread.daemon = True
#         server_thread.start()
#         print("Server loop running in thread:", server_thread.name)

#         client(ip, port, "Hello World 1")
#         client(ip, port, "Hello World 2")
#         client(ip, port, "Hello World 3")

#         server.shutdown()
