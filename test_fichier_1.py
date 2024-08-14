
from __future__ import print_function
from sys import stdout
from time import sleep
from daqhats import mcc128, OptionFlags, HatIDs, HatError, AnalogInputMode, \
    AnalogInputRange, hat_list, HatIDs
from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string

import time
import numpy as np
from datetime import datetime


# Configuration du DAQ HAT
board_num = 0
channel = [0]
channel_mask = chan_list_to_mask(channel)
input_mode = AnalogInputMode.DIFF
input_range = AnalogInputRange.BIP_1V
READ_ALL_AVAILABLE = -1

# Initialisation du fichier de sortie
output_file = "sound_levels.txt"
with open(output_file, 'w') as f:
    f.write("Timestamp,Sound Level (V)\n")


samples_per_channel = 5000

# CONTINUOUS : Run until explicitely stopped
options = OptionFlags.DEFAULT

scan_rate = 1000.0

try:
    # Select an MCC 128 HAT device to use.
    address = select_hat_device(HatIDs.MCC_128)
    hat = mcc128(address)

    hat.a_in_mode_write(input_mode)
    hat.a_in_range_write(input_range)

    print('\nSelected MCC 128 HAT device at address', address)
    #num_chanels = len (channel) = 1
    actual_scan_rate = hat.a_in_scan_actual_rate(1, scan_rate)

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
    print(', '.join([str(chan) for chan in channel]))
    print('    Requested scan rate: ', scan_rate)
    print('    Actual scan rate: ', actual_scan_rate)
    print('    Options: ', enum_mask_to_string(OptionFlags, options))

    try:
        input('\nPress ENTER to continue ...')
    except (NameError, SyntaxError):
        pass


    # Configure and start the scan.
    # Since the continuous option is being used, the samples_per_channel
    # parameter is ignored if the value is less than the default internal
    # buffer size (10000 * num_channels in this case). If a larger internal
    # buffer size is desired, set the value of this parameter accordingly.
    hat.a_in_scan_start(channel_mask, samples_per_channel, scan_rate,
                        options)
except (HatError, ValueError) as err:
    print('\n', err)

def read_sound_level():
    
    read_request_size = READ_ALL_AVAILABLE
    timeout = 5.0
    read_result = hat.a_in_scan_read(read_request_size, timeout)
    return read_result

try:
    while True:
        sound_level = read_sound_level()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(output_file, 'a') as f:
            f.write(f"{timestamp},{sound_level}\n")
        print(f"{timestamp} - Sound Level: {sound_level} V")
        time.sleep(1)  # Lire une fois par seconde
except KeyboardInterrupt:
    print("Acquisition terminée par l'utilisateur.")
except Exception as e:
    print(f"Erreur: {e}")
finally:
    print("Programme terminé.")
