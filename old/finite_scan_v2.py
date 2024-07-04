#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
    MCC 128 Functions Demonstrated:
        mcc128.a_in_scan_start
        mcc128.a_in_scan_read
        
        mcc128.a_in_scan_stop
        mcc128_a_in_scan_cleanup
        mcc128.a_in_mode_write
        mcc128.a_in_range_write

    Purpose:
        Perform a finite acquisition on 1 or more channels.

    Description:
        Acquires blocks of analog input data for a user-specified group
        of channels.  The last sample of data for each channel is
        displayed for each block of data received from the device.  The
        acquisition is stopped when the specified number of samples is
        acquired for each channel.

"""
from __future__ import print_function
from time import sleep
from sys import stdout
from daqhats import mcc128, OptionFlags, HatIDs, HatError, AnalogInputMode, \
    AnalogInputRange
from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string

import pyaudio
import numpy as np
import time
import math
from datetime import datetime

CURSOR_BACK_2 = '\x1b[2D'
ERASE_TO_END_OF_LINE = '\x1b[0K'

scan_rate_glob = 1000.0 #Hz

def main():
    """
    This function is executed automatically when the module is run directly.
    """

    # Store the channels in a list and convert the list to a channel mask that
    # can be passed as a parameter to the MCC 128 functions.
    channels = [0, 1, 2, 3]
    channel_mask = chan_list_to_mask(channels)
    num_channels = len(channels)

    input_mode = AnalogInputMode.DIFF
    input_range = AnalogInputRange.BIP_1V

    samples_per_channel = 10000     #nombre d'echantillons a mesurer
    scan_rate = scan_rate_glob      #mesures par seconde
    options = OptionFlags.DEFAULT

    try:
        # Select an MCC 128 HAT device to use.
        address = select_hat_device(HatIDs.MCC_128)
        hat = mcc128(address)

        hat.a_in_mode_write(input_mode)
        hat.a_in_range_write(input_range)

        print('\nSelected MCC 128 HAT device at address', address)

        actual_scan_rate = hat.a_in_scan_actual_rate(num_channels, scan_rate)

        print('\nMCC 128 continuous scan example')
        print('    Functions demonstrated:')
        print('         mcc128.a_in_scan_start')
        print('         mcc128.a_in_scan_read')
        print('         mcc128.a_in_scan_stop')
        print('         mcc128.a_in_scan_cleanup')
        print('         mcc128.a_in_mode_write')
        print('         mcc128.a_in_range_write')
        print('    Input mode: ', input_mode_to_string(input_mode))
        print('    Input range: ', input_range_to_string(input_range))
        print('    Channels: ', end='')
        print(', '.join([str(chan) for chan in channels]))
        print('    Requested scan rate: ', scan_rate)
        print('    Actual scan rate: ', actual_scan_rate)
        print('    Samples per channel', samples_per_channel)
        print('    Options: ', enum_mask_to_string(OptionFlags, options))

        try:
            input('\nPress ENTER to continue ...')
        except (NameError, SyntaxError):
            pass

        # Configure and start the scan.
        hat.a_in_scan_start(channel_mask, samples_per_channel, scan_rate,
                            options)

        print('Starting scan ... Press Ctrl-C to stop\n')

        # Display the header row for the data table.
        print('Samples Read    Scan Count', end='')
        for chan in channels:
            print('    Channel ', chan, sep='', end='')
        print('')

        try:
            read_and_display_data(hat, samples_per_channel, num_channels)

        except KeyboardInterrupt:
            # Clear the '^C' from the display.
            print(CURSOR_BACK_2, ERASE_TO_END_OF_LINE, '\n')
            hat.a_in_scan_stop()

        hat.a_in_scan_cleanup()

    except (HatError, ValueError) as err:
        print('\n', err)

# Initialisation du fichier de sortie
output_file = "sound_levels_v2.txt"
with open(output_file, 'w') as f:       #argumemt w : ouvre en ecriture et efface le  contenu du fichier / a : ouvre le fichier en ecriture et ecrit a la fin
    f.write("Timestamp,Sound Lvl ch.0 (V),Sound Lvl ch.1 (V),Sound Lvl ch.2 (V),Sound Lvl ch.3 (V)\n")

def read_and_display_data(hat, samples_per_channel, num_channels):
    """
    Reads data from the specified channels on the specified DAQ HAT devices
    and updates the data on the terminal display.  The reads are executed in a
    loop that continues until either the scan completes or an overrun error
    is detected.

    Args:
        hat (mcc128): The mcc128 HAT device object.
        samples_per_channel: The number of samples to read for each channel.
        num_channels (int): The number of channels to display.

    Returns:
        None

    """
    total_samples_read = 0
    read_request_size = 1
    timeout = 5.0


    # Continuously update the display value until Ctrl-C is
    # pressed or the number of samples requested has been read.
    while total_samples_read < samples_per_channel:
        read_result = hat.a_in_scan_read(read_request_size, timeout)

        # Check for an overrun error
        if read_result.hardware_overrun:
            print('\n\nHardware overrun\n')
            break
        elif read_result.buffer_overrun:
            print('\n\nBuffer overrun\n')
            break

        samples_read_per_channel = int(len(read_result.data) / num_channels)
        total_samples_read += samples_read_per_channel

        # Display the last sample for each channel.
        print('\r{:12}'.format(samples_read_per_channel),
              ' {:12} '.format(total_samples_read), end='')     #affiche les mesures dans le terminal

        if samples_read_per_channel > 0:
            index = samples_read_per_channel * num_channels - num_channels

            # timestamp = datetime.now().strftime("%H:%M:%S") # lit la date (pas besoin)
            sound_level = np.zeros((4, 1))      # array de taille 4,1 remplit de 0
            
            for i in range(num_channels):
                
                print('{:10.5f}'.format(read_result.data[index + i]), 'V ',
                      end='')                                                   # affiche les mesures dans le terminal
                #sound_level.append (str('{:10.6f}'.format(read_result.data[index + i]) + ' V'))  # ajoute le niveau de chaque channel dans la liste 
                sound_level[i] = read_result.data[index + i]            # ajoute le niveau de chaque channel dans la liste 
                
            with open(output_file, 'a') as f:
                #f.write(f"{timestamp},{sound_level}\n")     # ecrit tout dans le fichier
                # f.write(sound_level, sep=',')             # ecrit tout dans le fichier
                np.savetxt(f,sound_level.T,fmt='%6e',delimiter=',')     # ecrit les resultats dans le fichier
                
            stdout.flush()

            #sleep(1/scan_rate_glob)        # inutile : fait perdre du temps

    print('\n')


if __name__ == '__main__':
    main()
