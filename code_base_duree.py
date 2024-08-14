from __future__ import print_function
from sys import stdout
from time import sleep
from daqhats import mcc128, OptionFlags, HatIDs, HatError, AnalogInputMode, \
    AnalogInputRange, hat_list, HatIDs
from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string
    
import pyaudio
import numpy as np
import time
import math


# Fonction pour sélectionner l'appareil HAT
def select_hat_device(filter_by_id):
    selected_hat_address = None
    hats = hat_list(filter_by_id=filter_by_id)
    number_of_hats = len(hats)

    if number_of_hats < 1:
        raise HatError(0, 'Error: No HAT devices found')
    elif number_of_hats == 1:
        selected_hat_address = hats[0].address
    else:
        for hat in hats:
            print('Address ', hat.address, ': ', hat.product_name, sep='')
        print('')
        address = int(input('Select the address of the HAT device to use: '))
        for hat in hats:
            if address == hat.address:
                selected_hat_address = address
                break

    if selected_hat_address is None:
        raise ValueError('Error: Invalid HAT selection')

    return selected_hat_address

# Fonction pour l'acquisition audio via le micro
def record_audio(duration, rate=44100, chunk=1024, channels=1):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
    frames = []

    print(f"Recording audio for {duration} seconds...")
    for _ in range(0, int(rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(np.frombuffer(data, dtype=np.int16))

    stream.stop_stream()
    stream.close()
    audio.terminate()

    return np.concatenate(frames)

# Fonction pour l'acquisition de données via le DAQ HAT
def record_daq(duration, rate=1000.0, channels=[0]):
    address = select_hat_device(HatIDs.MCC_128)
    hat = mcc128(address)
    channel_mask = sum([1 << chan for chan in channels])
    options = OptionFlags.CONTINUOUS
    samples_per_channel = 0

    hat.a_in_mode_write(AnalogInputMode.DIFF)
    hat.a_in_range_write(AnalogInputRange.BIP_1V)
    hat.a_in_scan_start(channel_mask, samples_per_channel, rate, options)
    print(f"Recording DAQ data for {duration} seconds...")

    data = []
    start_time = time.time()
    while (time.time() - start_time) < duration:
        read_result = hat.a_in_scan_read(-1, 1)
        if read_result.hardware_overrun or read_result.buffer_overrun:
            break
        if len(read_result.data) > 0:
            data.extend(read_result.data)

    hat.a_in_scan_stop()
    hat.a_in_scan_cleanup()

    return np.array(data).reshape((-1, len(channels)))

# Fonction principale
def main(duration):
    audio_data = record_audio(duration)
    daq_data = record_daq(duration)


    # Sauvegarde des données dans un fichier txt
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    audio_file = f"audio_data_{timestamp}.txt"
    daq_file = f"daq_data_{timestamp}.txt"

    '''pd.DataFrame(audio_dB, columns=['dB']).to_csv(audio_file, index=False)
    pd.DataFrame(daq_data, columns=[f'Channel {i}' for i in range(daq_data.shape[1])]).to_csv(daq_file, index=False)'''

    print(f"Audio data saved to {audio_file}")
    print(f"DAQ data saved to {daq_file}")

if __name__ == "__main__":
    duration = float(input("Enter the duration for data acquisition (in seconds): "))
    main(duration)
