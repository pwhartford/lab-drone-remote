#!/usr/bin/env python3
import socket
import struct 
import numpy as np 
import io 

import rospy 
from std_msgs.msg import String
import mavros_msgs.msg 
from multiprocessing import Queue


#Pi config
PI_ADDRESS = "host.docker.internal"
PORT = 8000

COMMAND_QUEUE = Queue() 



def read_data(connection):
    data_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
    data = np.frombuffer(connection.read(data_len))

    return data 

def write_data(stream, connection, data):
   #Tell the client the length of the data (uses stream object to do this)
    stream.write(data)
    connection.write(struct.pack('<L', stream.tell()))
    connection.flush()
    stream.seek(0)

    #Send data as double
    connection.write(stream.read())
    stream.seek(0)
    stream.truncate()
    connection.flush()



def listener():
    rospy.init_node('listener', anonymous = True)
    
    MAVROS_RADIO_SUBSCRIBER = rospy.Subscriber("/mavros/rc/in", mavros_msgs.msg.RCIn, callback)
        
    stream = io.BytesIO()

    handshake = np.array([0], dtype = 'uint8')    
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
        print('Connecting to DAQ on %s:%s'%(PI_ADDRESS, PORT))

        #Create connection
        clientSocket.connect((PI_ADDRESS, PORT))
        
        #Create a file in memory to pass data between the two 
        connection = clientSocket.makefile('rwb')

        ii = 0
        while True:
            write_data(stream, connection, handshake)
            
            timeArray = read_data(connection)
            dataArray = read_data(connection)
            
            command = COMMAND_QUEUE.get()
            if command==1:
                handshake = np.array([1], dtype = 'uint8')        
            else:
                handshake = np.array([0], dtype = 'uint8')

        



def callback(data):
    print(data.channels)
    
    if len(data.channels)>0:
        if data.channels[-5]>1500:
            COMMAND_QUEUE.put(1)
            print('sending record command')
        
        else:
            COMMAND_QUEUE.put(0)

listener() 
