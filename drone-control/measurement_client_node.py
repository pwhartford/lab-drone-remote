import socket
import struct 
# import numpy as np 
import io 


#Pi config
PI_ADDRESS = "host.docker.internal"
PORT = 8000

# #Open socket 
# piSocket = socket.

# while True: 
#     socket.

stream = io.BytesIO()
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
    print('Connecting to DAQ on %s:%s'%(PI_ADDRESS, PORT))

    #Create connection
    clientSocket.connect((PI_ADDRESS, PORT))
    
    #Create a file in memory to pass data between the two 
    connection = clientSocket.makefile('rwb')

    ii = 0
    while True:
        #Calculate data length 
        data_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]

        data = connection.read(data_len)

        print(np.frombuffer(data), end = '\r')

        if ii == 20:
            handshake = np.array([1], dtype = 'uint8')        
        else:
            handshake = np.array([0], dtype = 'uint8')

        
        #Tell the client the length of the data (uses stream object to do this)
        stream.write(handshake)
        connection.write(struct.pack('<L', stream.tell()))
        connection.flush()
        stream.seek(0)

        #Send data as double
        connection.write(stream.read())
        stream.seek(0)
        stream.truncate()
        connection.flush()

        ii +=1 
